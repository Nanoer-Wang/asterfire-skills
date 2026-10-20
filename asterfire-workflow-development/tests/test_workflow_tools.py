"""本地行为验证：不访问生产平台、不执行远程写入。"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


validator = module('validate_workflow')
api = module('workflow_api')


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.wf = validator.yaml.load((ROOT / 'assets/minimal-workflow.yaml').read_text(encoding='utf-8'),
                                      Loader=validator.UniqueLoader)

    def test_example_and_actual_script_outputs(self):
        self.assertEqual(validator.validate(self.wf)['errors'], [])
        code = self.wf['nodes'][1]['agent_config']['script_code']
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                os.chdir(directory)
                Path('sample.txt').write_text('Asterfire 示例', encoding='utf-8')
                namespace = {}
                exec('def node(kwargs):\n' + validator.textwrap.indent(code, '    '), namespace)
                outputs = namespace['node']({'args': {'source': 'sample.txt'}})
                for path in outputs.values():
                    self.assertFalse(Path(path).is_absolute())
                    self.assertTrue(Path(path).is_file())
                self.assertEqual(Path(outputs['copied_file']).read_text(encoding='utf-8'), 'Asterfire 示例')
            finally:
                os.chdir(old)

    def test_duplicate_yaml_key(self):
        with self.assertRaises(ValueError):
            validator.yaml.load('title: a\ntitle: b\n', Loader=validator.UniqueLoader)

    def test_cycle(self):
        self.wf['edges'].append({'from': 'node_copy', 'to': 'node_input'})
        self.assertTrue(validator.validate(self.wf)['errors'])

    def test_missing_dependency_edge(self):
        self.wf['edges'] = []
        self.assertTrue(validator.validate(self.wf)['errors'])

    def test_invalid_output_reference(self):
        self.wf['nodes'][1]['params']['source'] = '{{nodes.node_input.outputs.no_such_output}}'
        self.assertTrue(validator.validate(self.wf)['errors'])

    def test_bare_dict_and_syntax_error(self):
        for code in ("args = kwargs['args']\nreturn dict", "args = kwargs['args']\nreturn {'x':"):
            with self.subTest(code=code):
                wf = copy.deepcopy(self.wf)
                wf['nodes'][1]['agent_config']['script_code'] = code
                self.assertTrue(validator.validate(wf)['errors'])

    def test_nested_helper_return_does_not_prove_node_output(self):
        self.wf['nodes'][1]['agent_config']['script_code'] = (
            "args = kwargs['args']\ndef helper():\n    return {'copied_file': '', 'report': ''}")
        self.assertTrue(validator.validate(self.wf)['errors'])

    def test_non_kit_node_scatter_and_unknown_type_are_not_rejected(self):
        script = self.wf['nodes'][1]
        script['agent_config']['scatter'] = {'on': 'source', 'concurrency': 1}
        self.assertEqual(validator.validate(self.wf)['errors'], [])
        self.wf['nodes'].append({'id': 'node_custom', 'type': 'future-platform-node', 'params': {}})
        result = validator.validate(self.wf)
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['warnings'])

    def test_pair_lengths_and_yaml_boolean_key(self):
        node = {'id': 'parallel', 'type': 'kit', 'kit': 'actual-kit',
                'params': {'a': [1], 'b': [2, 3]},
                'agent_config': {'scatter': {'on': ['a', 'b'], 'mode': 'pair', 'concurrency': 1}}}
        self.wf['nodes'].append(node)
        self.assertTrue(validator.validate(self.wf)['errors'])
        node['agent_config']['scatter'] = {True: 'a'}
        self.assertTrue(validator.validate(self.wf)['errors'])

    def test_real_port_index_catches_wrong_kit_key(self):
        self.wf['nodes'].append({'id': 'kit', 'type': 'kit', 'kit': 'actual-kit', 'params': {'typo': 1}})
        ports = {'actual-kit': {'inputs': ['file'], 'required_inputs': ['file'], 'outputs': ['result']}}
        self.assertTrue(validator.validate(self.wf, ports)['errors'])


class ApiTests(unittest.TestCase):
    def test_real_v1_url_and_envelope(self):
        client_mod, http, _ = api.dependencies()
        client = client_mod.AsterfireClient('https://example.test/api', 'test-only')
        with patch.object(http, 'request_json', return_value={'success': True, 'data': {'id': 7}}) as call:
            result = api.request(client, http, 'POST', '/workflows/import', data={'yaml': 'example'})
        self.assertEqual(result, {'id': 7})
        self.assertEqual(call.call_args.args[1], 'https://example.test/api/open/v1/workflows/import')
        self.assertEqual(call.call_args.kwargs['headers']['Asterfire-Token'], 'test-only')
        self.assertEqual(call.call_args.kwargs['retries'], 1)

    def test_error_keeps_code_request_id(self):
        client_mod, _, _ = api.dependencies()
        client = client_mod.AsterfireClient('https://example.test/api', 'test-only')
        with self.assertRaises(Exception) as caught:
            client._unwrap({'success': False, 'error': {'code': 'auth.scope_required',
                            'message': 'scope missing', 'request_id': 'test-request'}})
        self.assertEqual(caught.exception.code, 'auth.scope_required')
        self.assertEqual(caught.exception.request_id, 'test-request')

    def test_dry_run_has_no_network_or_state_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'run.json'
            args = api.parser().parse_args(['--dry-run', 'run', '42', '--state', str(state)])
            with patch.object(api, 'request', side_effect=AssertionError('dry-run called network')):
                result = api.dispatch(args)
            self.assertTrue(result['dry_run'])
            self.assertFalse(state.exists())

    def test_completed_submission_resume_does_not_post_twice(self):
        client_mod, http, _ = api.dependencies()
        client = client_mod.AsterfireClient('https://example.test/api', 'test-only')
        with tempfile.TemporaryDirectory() as directory:
            args = api.parser().parse_args(['run', '42', '--state', str(Path(directory) / 'run.json')])
            def fake_request(c, h, method, path, **kwargs):
                if method == 'POST':
                    self.assertTrue(Path(args.state).is_file())
                    self.assertIn('Idempotency-Key', kwargs['headers'])
                    return {'plan_id': 42, 'execution_id': 100, 'task_id': 123}
                return {'execution_status': 'running'}
            with patch.object(api, 'request', side_effect=fake_request) as call:
                api.execute_once(args, client, http)
                api.execute_once(args, client, http)
            self.assertEqual(sum(x.args[2] == 'POST' for x in call.call_args_list), 1)
            args.no_cache = True
            with self.assertRaises(ValueError):
                api.execute_once(args, client, http)

    def test_unknown_post_outcome_reuses_original_key(self):
        client_mod, http, _ = api.dependencies()
        client = client_mod.AsterfireClient('https://example.test/api', 'test-only')
        with tempfile.TemporaryDirectory() as directory:
            args = api.parser().parse_args(['run', '42', '--state', str(Path(directory) / 'run.json')])
            with patch.object(api, 'request', side_effect=TimeoutError('unknown outcome')):
                with self.assertRaises(TimeoutError):
                    api.execute_once(args, client, http)
            original = api.read_json(args.state)['idempotency_key']
            with patch.object(api, 'request', side_effect=[{'execution_id': 100}, {'execution_status': 'running'}]) as call:
                api.execute_once(args, client, http)
            self.assertEqual(call.call_args_list[0].kwargs['headers']['Idempotency-Key'], original)

    def test_exclusive_state_creation_stops_concurrent_first_submit(self):
        client_mod, http, _ = api.dependencies()
        client = client_mod.AsterfireClient('https://example.test/api', 'test-only')
        with tempfile.TemporaryDirectory() as directory:
            args = api.parser().parse_args(['run', '42', '--state', str(Path(directory) / 'run.json')])
            with patch.object(api, 'write_json', side_effect=FileExistsError('another process created state')):
                with patch.object(api, 'request') as call:
                    with self.assertRaises(FileExistsError):
                        api.execute_once(args, client, http)
                    call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
