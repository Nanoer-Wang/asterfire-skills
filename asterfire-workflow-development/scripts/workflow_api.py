"""Asterfire Open API v1 Workflow 工具；复用同级 devops 客户端。"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote, urlsplit
import uuid


def dependencies():
    root = Path(__file__).resolve().parents[2] / 'asterfire-platform-devops' / 'scripts'
    if not (root / 'asterfire_client.py').is_file():
        raise ValueError('缺少同级 asterfire-platform-devops 技能，请先安装该依赖。')
    name = '_asterfire_workflow_devops'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, root / '__init__.py', submodule_search_locations=[str(root)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return tuple(importlib.import_module(name + '.' + n)
                 for n in ('asterfire_client', 'http_utils', 'config'))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if exclusive:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(text)
    else:
        temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        temp.write_text(text, encoding='utf-8')
        os.replace(temp, path)


def connection(args):
    api, http, config = dependencies()
    config.load_standard_env(Path.cwd())
    stored = {}
    config_path = Path.home() / '.asterfire' / 'config.json'
    if config_path.is_file():
        stored = read_json(config_path)
    endpoint = (args.base_url or os.getenv('ASTERFIRE_API_BASE')
                or stored.get('base_url') or 'https://sidereus-ai.com/api/open/v1')
    parts = urlsplit(endpoint)
    if parts.scheme not in {'https', 'http'} or not parts.hostname:
        raise ValueError('base URL 必须是有效的 HTTP(S) 地址。')
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('base URL 不能包含用户凭据、查询参数或片段。')
    token = os.getenv('ASTERFIRE_TOKEN') or stored.get('token')
    if not token and not args.dry_run:
        raise ValueError('缺少 ASTERFIRE_TOKEN 或已保存的 API Token；请在本机受保护配置中设置。')
    return api.AsterfireClient(endpoint, token or ''), http


def request(client, http, method, path, *, data=None, query=None, headers=None):
    # 无重试写入；execute 的失败通过同一个 state 的幂等键恢复。
    return client._unwrap(http.request_json(
        method, client._url(path, query), headers={**client.headers, **(headers or {})},
        data=data, retries=1))


def query_args(values):
    result = {}
    for item in values:
        key, sep, value = item.partition('=')
        if not sep or not key:
            raise ValueError('--query 使用 key=value。')
        if key in result:
            raise ValueError('重复 query key: ' + key)
        result[key] = value
    return result


def allowed_path(path):
    parts = urlsplit(path)
    if (parts.scheme or parts.netloc or parts.query or parts.fragment
            or not path.startswith('/') or '..' in path.split('/')):
        raise ValueError('path 只接受 Open API v1 下的相对路由；查询参数用 --query。')
    if not any(path == prefix or path.startswith(prefix + '/') for prefix in
               ('/info', '/workflows', '/workflow-tools', '/workflow-templates', '/tasks/files')):
        raise ValueError('此工具只处理 Workflow 路由与 /info。')


def execute_once(args, client, http):
    body = {'use_default_inputs': not args.no_default_inputs}
    if args.inherit_inputs_from is not None:
        body['inherit_inputs_from'] = args.inherit_inputs_from
    query = {'no_cache': str(args.no_cache).lower()}
    identity = {'endpoint': client.endpoint, 'plan_id': args.plan_id,
                'body': body, 'query': query}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    state_path = Path(args.state)
    new_state = not state_path.exists()
    if not new_state:
        state = read_json(state_path)
        if state.get('fingerprint') != digest:
            raise ValueError('state 对应不同的环境、方案或执行参数。新的执行使用新的 state 文件。')
        if not state.get('idempotency_key'):
            raise ValueError('state 缺少原始幂等键，停止提交以避免重复执行。')
    else:
        state = {**identity, 'fingerprint': digest, 'idempotency_key': str(uuid.uuid4())}
    if args.dry_run:
        return {'dry_run': True, 'action': 'execute-or-resume', **identity,
                'state': str(state_path), 'existing_submission': state.get('submission')}
    if new_state:
        write_json(state_path, state, exclusive=True)  # 在网络写入前持久化意图。
    submission = state.get('submission')
    if submission is None:
        submission = request(client, http, 'POST', f'/workflows/{args.plan_id}/execute',
                             data=body, query=query,
                             headers={'Idempotency-Key': state['idempotency_key']})
        state['submission'] = submission
        write_json(state_path, state)
    if not isinstance(submission, dict) or submission.get('execution_id') is None:
        raise ValueError('响应未包含 execution_id；已保存原响应，请检查 state，勿创建新执行重试。')
    execution = submission['execution_id']
    status = request(client, http, 'GET',
                     f'/workflows/{args.plan_id}/executions/{quote(str(execution), safe="")}/status')
    state['last_status'] = status
    write_json(state_path, state)
    return {'state': str(state_path), 'submission': submission, 'status': status,
            'note': '本命令只提交/恢复并查询一次状态；请继续按 execution_id 跟踪并检查产物。'}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', help='显式平台 API 地址，优先于环境和 CLI 配置')
    p.add_argument('--dry-run', action='store_true', help='只显示操作计划，不联网、不写执行记录')
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('request', help='Workflow 通用 JSON/multipart 请求')
    r.add_argument('method', choices=['GET', 'POST', 'PUT', 'PATCH'])
    r.add_argument('path')
    payload = r.add_mutually_exclusive_group()
    payload.add_argument('--body-file', help='UTF-8 JSON 请求体文件')
    payload.add_argument('--yaml-file', help='包装为 {"yaml": "..."} 请求体')
    payload.add_argument('--file', help='multipart file 字段，例如节点输入文件')
    r.add_argument('--query', action='append', default=[], help='key=value，可重复')
    r.add_argument('--output', help='保存解包后的 data；.yaml/.yml 提取 yaml 字段')
    r = sub.add_parser('run', help='携带持久化幂等键执行；同 state 恢复，不创建第二次执行')
    r.add_argument('plan_id', type=int)
    r.add_argument('--state', required=True, help='本次执行的专用 state JSON 路径')
    r.add_argument('--no-default-inputs', action='store_true')
    r.add_argument('--inherit-inputs-from', type=int)
    r.add_argument('--no-cache', action='store_true')
    r = sub.add_parser('download', help='通过真实 File ID 下载节点产物')
    r.add_argument('file_id')
    r.add_argument('--output', required=True)
    r.add_argument('--workspace-id', type=int)
    return p


def dispatch(args):
    client, http = connection(args)
    if args.command == 'download':
        if args.dry_run:
            return {'dry_run': True, 'endpoint': client.endpoint,
                    'file_id': args.file_id, 'output': args.output, 'workspace_id': args.workspace_id}
        path = client.download_file(args.file_id, args.output, workspace_id=args.workspace_id)
        return {'output': str(path)}
    if args.command == 'run':
        if args.plan_id < 1:
            raise ValueError('plan_id 必须为正整数。')
        return execute_once(args, client, http)
    allowed_path(args.path)
    if args.path.startswith('/tasks/files') and args.method != 'GET':
        raise ValueError('任务文件路由仅支持 GET。')
    if args.path.rstrip('/').endswith('/execute') and args.method != 'GET':
        raise ValueError('执行请使用 run 子命令，以保存幂等键与执行记录。')
    query = query_args(args.query)
    data = read_json(args.body_file) if args.body_file else None
    if args.yaml_file:
        data = {'yaml': Path(args.yaml_file).read_text(encoding='utf-8-sig')}
    if args.method == 'GET' and (data is not None or args.file):
        raise ValueError('GET 不能带请求体或上传文件。')
    if args.file and args.method != 'POST':
        raise ValueError('multipart 上传仅支持 POST。')
    if args.dry_run:
        return {'dry_run': True, 'method': args.method, 'endpoint': client.endpoint,
                'path': args.path, 'query': query, 'body': data, 'file': args.file}
    if args.file:
        if args.path.endswith('/input/file') and 'execution_id' not in query:
            raise ValueError('节点文件输入必须指定 --query execution_id=...。')
        # _multipart 复用客户端的单次上传；URL 先组装查询参数。
        from urllib.parse import urlencode
        suffix = '?' + urlencode(query) if query else ''
        result = client._multipart(args.path + suffix, args.file, {})
    else:
        result = request(client, http, args.method, args.path, data=data, query=query)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() in {'.yaml', '.yml'}:
            value = result.get('yaml') if isinstance(result, dict) else result
            if not isinstance(value, str):
                raise ValueError('响应不含 yaml 文本，请改用 .json 保存并检查实际导出结构。')
            out.write_text(value, encoding='utf-8')
        else:
            write_json(out, result)
        return {'output': str(out), 'data': result}
    return result


def main():
    args = parser().parse_args()
    try:
        print(json.dumps(dispatch(args), ensure_ascii=False, indent=2))
    except Exception as exc:
        error = {'message': str(exc)}
        for field in ('status', 'code', 'details', 'request_id'):
            if hasattr(exc, field):
                error[field] = getattr(exc, field)
        # 防止服务端错误体意外回显请求中的 Token。
        value = json.dumps({'success': False, 'error': error}, ensure_ascii=False)
        tokens = [os.getenv('ASTERFIRE_TOKEN')]
        config_path = Path.home() / '.asterfire' / 'config.json'
        if config_path.is_file():
            try:
                tokens.append(read_json(config_path).get('token'))
            except (ValueError, OSError):
                pass
        for token in tokens:
            if token:
                value = value.replace(str(token), '[REDACTED]')
        print(value, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
