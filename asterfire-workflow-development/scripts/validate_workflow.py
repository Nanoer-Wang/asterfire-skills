"""Workflow 静态校验。节点类型开放；不执行脚本，不代替平台契约和真实运行。"""
from __future__ import annotations

import argparse
import ast
from collections import deque
import json
from pathlib import Path
import re
import textwrap

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'重复 YAML key: {key}，第 {key_node.start_mark.line + 1} 行')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
REF = re.compile(r'\{\{\s*nodes\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}')


def references(value):
    if isinstance(value, str):
        yield from REF.findall(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


class ScriptReturns(ast.NodeVisitor):
    """仅分析当前脚本函数的 return，不把嵌套函数返回当成节点返回。"""
    def __init__(self):
        self.returns = []

    def visit_Return(self, node):
        self.returns.append(node.value)

    def visit_FunctionDef(self, node):
        pass

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        pass


def script_check(nid, ac, params, errors, warnings):
    io = ac.get('io_spec') or {}
    if not isinstance(io, dict):
        errors.append(f'{nid}: io_spec 必须是对象')
        return set()

    def keys(direction):
        ports = io.get(direction, [])
        if not isinstance(ports, list) or any(not isinstance(x, dict) or not x.get('key') for x in ports):
            errors.append(f'{nid}: io_spec.{direction} 必须是包含 key 的对象列表')
            return set()
        values = [x['key'] for x in ports]
        if any(not isinstance(x, str) for x in values):
            errors.append(f'{nid}: 端口 key 必须为字符串')
            return set()
        if len(set(values)) != len(values):
            errors.append(f'{nid}: {direction} 存在重复端口')
        return set(values)

    inputs, outputs = keys('inputs'), keys('outputs')
    if set(params) != inputs:
        errors.append(f'{nid}: params 与 io_spec.inputs 不一致；缺绑定={sorted(inputs - set(params))}，未声明={sorted(set(params) - inputs)}')
    code = ac.get('script_code')
    if not isinstance(code, str) or not code.strip():
        errors.append(f'{nid}: 缺少 script_code')
        return outputs
    try:
        tree = ast.parse('def __node__(kwargs):\n' + textwrap.indent(code, '    '))
        compile(tree, '<workflow-script>', 'exec')
    except SyntaxError as exc:
        errors.append(f'{nid}: Python 语法错误: {exc.msg}（脚本行约 {max(1, (exc.lineno or 2) - 1)}）')
        return outputs
    has_args = any(isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name)
                   and x.value.id == 'kwargs' and isinstance(x.slice, ast.Constant)
                   and x.slice.value == 'args' for x in ast.walk(tree))
    if not has_args:
        errors.append(f"{nid}: 未从 kwargs['args'] 读取输入")
    visitor = ScriptReturns()
    for statement in tree.body[0].body:
        visitor.visit(statement)
    if not visitor.returns:
        errors.append(f'{nid}: 缺少节点 return，嵌套函数的 return 不算')
    for value in visitor.returns:
        if isinstance(value, ast.Name) and value.id == 'dict':
            errors.append(f'{nid}: return dict 返回类，必须返回字典实例')
        elif isinstance(value, ast.Dict) and all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in value.keys):
            actual = {x.value for x in value.keys}
            if actual != outputs:
                errors.append(f'{nid}: return key 与输出端口不一致；缺={sorted(outputs - actual)}，多={sorted(actual - outputs)}')
        elif value is None or isinstance(value, (ast.Constant, ast.List, ast.Tuple, ast.Set)):
            errors.append(f'{nid}: 节点 return 必须返回字典实例')
        else:
            warnings.append(f'{nid}: 动态 return，需人工/运行确认字典 key 与输出端口一致')
    requirements = ac.get('requirements', [])
    if not isinstance(requirements, list):
        errors.append(f'{nid}: requirements 必须是列表')
    return outputs


def validate(document, ports=None):
    errors, warnings = [], []
    ports = ports or {}
    if not isinstance(document, dict):
        return {'errors': ['顶层必须是对象'], 'warnings': []}
    for key in ('version', 'title', 'nodes', 'edges'):
        if key not in document:
            errors.append('缺少顶层字段: ' + key)
    nodes, edges = document.get('nodes'), document.get('edges')
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return {'errors': errors + ['nodes/edges 必须是列表'], 'warnings': warnings}
    if not nodes:
        errors.append('工作流至少需要一个节点')
    if not isinstance(document.get('title'), str) or not document.get('title', '').strip():
        errors.append('title 必须是非空字符串')
    if 'version' in document and not isinstance(document['version'], str):
        errors.append("version 必须是字符串，例如 '1'")
    by_id, outputs, adjacency, indegree = {}, {}, {}, {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            errors.append('节点必须有非空字符串 id')
            continue
        nid = node['id']
        if nid in by_id:
            errors.append('重复节点 id: ' + nid)
        by_id[nid] = node
        adjacency[nid], indegree[nid] = set(), 0
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append('edge 必须是对象')
            continue
        source, target = edge.get('from'), edge.get('to')
        if not isinstance(source, str) or not isinstance(target, str) or source not in by_id or target not in by_id:
            errors.append(f'edge 端点不存在: {source} -> {target}')
        elif target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1
    queue = deque(n for n in indegree if indegree[n] == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for target in adjacency[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(by_id):
        errors.append('DAG 存在环（包括自引用边）')

    for nid, node in by_id.items():
        params, ac = node.get('params') or {}, node.get('agent_config') or {}
        if not isinstance(params, dict) or not isinstance(ac, dict):
            errors.append(f'{nid}: params/agent_config 必须是对象')
            continue
        kind = node.get('type')
        if not isinstance(kind, str) or not kind:
            errors.append(f'{nid}: 缺少节点 type')
        outputs[nid] = None
        if kind == 'input':
            outputs[nid] = {'user_input'}
        elif kind == 'script':
            outputs[nid] = script_check(nid, ac, params, errors, warnings)
        elif kind == 'kit':
            name = node.get('kit')
            if not isinstance(name, str) or not name:
                errors.append(f'{nid}: 缺少真实 Kit 注册名')
            elif name not in ports:
                warnings.append(f'{nid}: 未提供 {name} 的真实端口索引，Kit 接口尚未验证')
            else:
                contract = ports[name]
                if not isinstance(contract, dict) or any(not isinstance(contract.get(k), list) for k in ('inputs', 'required_inputs', 'outputs')):
                    errors.append(f'{nid}: 本地 ports 索引缺少 inputs/required_inputs/outputs 列表')
                else:
                    allowed, required = set(contract['inputs']), set(contract['required_inputs'])
                    if set(params) - allowed:
                        errors.append(f'{nid}: 未知 Kit 参数 {sorted(set(params) - allowed)}')
                    if required - set(params):
                        errors.append(f'{nid}: 缺少 Kit 必填参数 {sorted(required - set(params))}')
                    outputs[nid] = set(contract['outputs'])
        else:
            # 平台支持多种节点：未知类型不据此拒绝，交由实际契约与平台验证。
            warnings.append(f'{nid}: type={kind} 使用部署契约验证，未纳入本地专用规则')
        scatter = ac.get('scatter')
        if scatter is not None:
            if not isinstance(scatter, dict):
                errors.append(f'{nid}: scatter 必须是对象')
                continue
            if True in scatter:
                errors.append(f"{nid}: YAML 将 on 解析为布尔，请写 'on':")
            on = scatter.get('on')
            fields = [on] if isinstance(on, str) else on
            if not isinstance(fields, list) or not fields or any(not isinstance(x, str) or x not in params for x in fields):
                errors.append(f'{nid}: scatter.on 必须引用当前节点 params key')
            elif isinstance(on, list):
                if scatter.get('mode') != 'pair':
                    errors.append(f'{nid}: 多字段 scatter 需显式 mode: pair 并确认平台支持')
                values = [params[x] for x in fields]
                if all(isinstance(v, list) for v in values) and len({len(v) for v in values}) > 1:
                    errors.append(f'{nid}: pair scatter 的静态列表长度不同')
                warnings.append(f'{nid}: 确认部署支持 pair，并验证动态列表等长及对应关系')
            concurrency = scatter.get('concurrency', 1)
            if type(concurrency) is not int or concurrency < 1:
                errors.append(f'{nid}: scatter.concurrency 必须是正整数')
            ratio = scatter.get('min_success_ratio', 1)
            if type(ratio) not in (int, float) or not 0 <= ratio <= 1:
                errors.append(f'{nid}: min_success_ratio 必须位于 [0,1]')

    def reachable(source, target):
        todo, seen = list(adjacency.get(source, set())), set()
        while todo:
            n = todo.pop()
            if n == target:
                return True
            if n not in seen:
                seen.add(n)
                todo.extend(adjacency.get(n, set()))
        return False

    for nid, node in by_id.items():
        # agent_config 的条件等也可能引用输出；代码文本本身不做模板解析。
        ac = node.get('agent_config')
        bindings = {'params': node.get('params'), 'config': {
            k: v for k, v in ac.items() if k != 'script_code'} if isinstance(ac, dict) else None}
        for source, key in references(bindings):
            if source not in by_id:
                errors.append(f'{nid}: 引用节点不存在 {source}')
            elif source == nid or not reachable(source, nid):
                errors.append(f'{nid}: 引用 {source}，但它不是该节点的上游')
            if source in outputs and outputs[source] is not None:
                if key not in outputs[source]:
                    errors.append(f'{nid}: 引用了未声明的 {source}.outputs.{key}')
            elif source in by_id:
                warnings.append(f'{nid}: {source}.outputs.{key} 需要平台真实契约核对')
    return {'errors': errors, 'warnings': warnings}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('workflow')
    p.add_argument('--ports', help='从真实契约整理的本地端口 JSON 索引')
    args = p.parse_args()
    try:
        document = yaml.load(Path(args.workflow).read_text(encoding='utf-8-sig'), Loader=UniqueLoader)
        ports = json.loads(Path(args.ports).read_text(encoding='utf-8-sig')) if args.ports else None
        if ports is not None and not isinstance(ports, dict):
            raise ValueError('ports 索引必须是对象')
        result = validate(document, ports)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        result = {'errors': [str(exc)], 'warnings': []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
