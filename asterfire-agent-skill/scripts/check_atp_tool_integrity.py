"""Audit generic AsterFire ATP Agent Toolbox Tool classes."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ATP_METADATA_FIELDS = {
    "DISPLAY_NAME": "display_name",
    "CONDA_ENV": "conda_env",
    "NETWORK": "network",
    "CPU": "cpu",
    "GPU": "gpu",
    "MEM_PER_CPU": "mem_per_cpu",
    "PARTITION": "partition",
    "SIF": "sif",
}

HOOK_REQUIRED_KWARGS = {
    "inputShow": {"args", "files", "message", "user", "task_id"},
    "resAlloc": {"args", "files", "message", "user", "task_id", "tool_data", "tip"},
    "call": {"args", "files", "message", "user", "task_id", "tool_data", "tip"},
    "monitor": {"args", "files", "message", "user", "task_id", "tool_data", "tip", "run_time", "progress"},
    "outputShow": {
        "args",
        "files",
        "message",
        "user",
        "task_id",
        "tool_data",
        "tip",
        "run_time",
        "progress",
        "stdout",
        "stderr",
        "exit_code",
    },
    "summary": {
        "args",
        "files",
        "message",
        "user",
        "task_id",
        "tool_data",
        "tip",
        "run_time",
        "progress",
        "stdout",
        "stderr",
        "exit_code",
    },
}

VALID_CALLTYPES = {"python", "bash"}
PATH_NAME_PATTERN = re.compile(r"(?:^|_)(?:path|file|dir|directory|folder)(?:$|_)")
IGNORED_UNUSED_REQUIRED_ARGS = {"note"}
OPTIONAL_PATH_COMPAT_ARG_PREFIXES = ("auto_resolve_",)
OPTIONAL_PATH_COMPAT_ARG_NAMES = {"path_type"}
FORBIDDEN_DOC_TYPE_PATTERNS = (
    re.compile(r"\b\w+\s*\|\s*\w+"),
    re.compile(r"\b(?:List|Dict|Optional|Union|Literal)\[[^\n)]*\]\s*\|"),
    re.compile(r"\|\s*(?:List|Dict|Optional|Union|Literal)\["),
    re.compile(r"\b0\s*\|\s*1\b"),
    re.compile(r"\bdict,\s*optional\b", re.IGNORECASE),
    re.compile(r"\bfloat\s*/\s*str\b", re.IGNORECASE),
    re.compile(r"\bstr\s*/\s*list\b", re.IGNORECASE),
    re.compile(r"\blist\["),
)


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    message: str


@dataclass
class AuditResult:
    tool_count: int = 0
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def add_error(self, path: Path | str, message: str) -> None:
        self.errors.append(Finding("error", str(path), message))

    def add_warning(self, path: Path | str, message: str) -> None:
        self.warnings.append(Finding("warning", str(path), message))

    def merge(self, other: "AuditResult") -> None:
        self.tool_count += other.tool_count
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


@dataclass
class ToolClass:
    path: Path
    node: ast.ClassDef
    function_name: str
    docstring: str
    assignments: dict[str, Any]
    methods: dict[str, ast.FunctionDef]
    calltype: str | None
    io_outputs: set[str]
    doc_args: dict[str, tuple[str, str, bool]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--parser-command", default=None)
    parser.add_argument("--functions-json", type=Path, default=None)
    parser.add_argument("--changed-file", type=Path, action="append", default=[])
    parser.add_argument("--scan-path", type=Path, action="append", default=[])
    parser.add_argument("--exclude-dir", action="append", default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict-parser", action="store_true")
    parser.add_argument("--strict-metadata", action="store_true")
    return parser.parse_args(argv)


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _path_for_display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_tool_base(base: ast.AST) -> bool:
    return (isinstance(base, ast.Name) and base.id == "Tool") or (
        isinstance(base, ast.Attribute) and base.attr == "Tool"
    )


def _parse_docstring(docstring: str):
    try:
        from docstring_parser import parse as parse_docstring
    except ImportError as exc:
        raise RuntimeError(
            "check_atp_tool_integrity.py requires docstring-parser; install adam-community or docstring-parser"
        ) from exc
    return parse_docstring(docstring or "")


def _doc_args(docstring: str) -> dict[str, tuple[str, str, bool]]:
    args: dict[str, tuple[str, str, bool]] = {}
    docs = _parse_docstring(docstring)
    for param in docs.params:
        if not param.arg_name:
            continue
        args[param.arg_name] = (
            param.type_name or "str",
            param.description or "",
            bool(param.is_optional),
        )
    return args


def _doc_intro_paragraphs(docstring: str) -> list[str]:
    docs = _parse_docstring(docstring)
    paragraphs: list[str] = []
    if docs.short_description:
        paragraphs.append(docs.short_description.strip())
    if docs.long_description:
        paragraphs.append(docs.long_description.strip())
    return paragraphs


def _class_assignments(cls: ast.ClassDef) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in cls.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = _literal(item.value)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            values[item.target.id] = _literal(item.value) if item.value is not None else None
    return values


def _class_calltype(cls: ast.ClassDef) -> str | None:
    for keyword in cls.keywords:
        if keyword.arg == "calltype":
            value = _literal(keyword.value)
            return value if isinstance(value, str) else None
    return None


def _tool_io_outputs(cls: ast.ClassDef) -> set[str]:
    outputs: set[str] = set()
    for decorator in cls.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func_name = decorator.func.id if isinstance(decorator.func, ast.Name) else getattr(decorator.func, "attr", "")
        if func_name != "tool_io":
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "outputs" and isinstance(keyword.value, ast.Dict):
                outputs.update(_dict_keys(keyword.value))
    return outputs


def _iter_scan_paths(root: Path, scan_paths: list[Path] | None) -> list[Path]:
    if not scan_paths:
        return [root]
    return [path if path.is_absolute() else root / path for path in scan_paths]


def discover_python_files(
    root: Path,
    changed_files: list[Path] | None = None,
    scan_paths: list[Path] | None = None,
    exclude_dirs: set[str] | None = None,
) -> list[Path]:
    root = root.resolve()
    excluded = {".git", "__pycache__", *(exclude_dirs or set())}
    if changed_files:
        return [path.resolve() for path in changed_files if path.suffix == ".py"]

    files: list[Path] = []
    seen: set[Path] = set()
    for scan_path in _iter_scan_paths(root, scan_paths):
        scan_path = scan_path.resolve()
        candidates = [scan_path] if scan_path.is_file() else sorted(scan_path.rglob("*.py"))
        for path in candidates:
            path = path.resolve()
            if path in seen or path.suffix != ".py" or path.name.startswith("_"):
                continue
            try:
                relative_parts = path.relative_to(root).parts
            except ValueError:
                continue
            if "config" in relative_parts:
                continue
            if any(part in excluded for part in relative_parts):
                continue
            seen.add(path)
            files.append(path)
    return files


def discover_tools(
    root: Path,
    changed_files: list[Path] | None = None,
    scan_paths: list[Path] | None = None,
    exclude_dirs: set[str] | None = None,
) -> list[ToolClass]:
    root = root.resolve()
    tools: list[ToolClass] = []
    for path in discover_python_files(root, changed_files, scan_paths, exclude_dirs):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(_is_tool_base(base) for base in node.bases):
                continue
            methods = {item.name: item for item in node.body if isinstance(item, ast.FunctionDef)}
            relative = Path(_path_for_display(path, root))
            tools.append(
                ToolClass(
                    path=path,
                    node=node,
                    function_name=f"{relative.with_suffix('').as_posix().replace('/', '.')}.{node.name}",
                    docstring=ast.get_docstring(node) or "",
                    assignments=_class_assignments(node),
                    methods=methods,
                    calltype=_class_calltype(node),
                    io_outputs=_tool_io_outputs(node),
                    doc_args=_doc_args(ast.get_docstring(node) or ""),
                )
            )
    return tools


def run_parser_command(root: Path, parser_command: str | None, strict_parser: bool, result: AuditResult) -> bool:
    if not parser_command:
        return True
    try:
        proc = subprocess.run(shlex.split(parser_command), cwd=root, text=True, capture_output=True, check=False)
    except OSError as exc:
        message = f"parser command failed to start: {exc}"
        if strict_parser:
            result.add_error(root, message)
        else:
            result.add_warning(root, message)
        return False
    if proc.returncode != 0:
        message = f"parser command exited {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"
        if strict_parser:
            result.add_error(root, message)
        else:
            result.add_warning(root, message)
        return False
    return True


def load_parser_functions(path: Path, result: AuditResult) -> dict[str, dict[str, Any]] | None:
    if not path.is_file():
        result.add_error(path, "parser output functions.json not found")
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.add_error(path, f"invalid parser output: {exc}")
        return None

    functions: dict[str, dict[str, Any]] = {}
    for item in raw:
        function = item.get("function") if isinstance(item, dict) else None
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            functions[function["name"]] = function
    return functions


def check_parser_exposure(
    tools: list[ToolClass],
    parser_functions: dict[str, dict[str, Any]],
    result: AuditResult,
) -> None:
    tool_names = {tool.function_name for tool in tools}
    for tool in tools:
        function = parser_functions.get(tool.function_name)
        if function is None:
            result.add_error(tool.path, f"{tool.node.name}: missing parser exposure for {tool.function_name}")
            continue

        for class_key, parser_key in ATP_METADATA_FIELDS.items():
            if class_key not in tool.assignments:
                continue
            expected = tool.assignments[class_key]
            actual = function.get(parser_key)
            if actual != expected:
                result.add_error(
                    tool.path,
                    f"{tool.node.name}: metadata {class_key} expected {expected!r}, parser exposed {actual!r}",
                )

        parameters = function.get("parameters") or {}
        parser_params = set((parameters.get("properties") or {}).keys()) if isinstance(parameters, dict) else set()
        parser_required = set(parameters.get("required") or []) if isinstance(parameters, dict) else set()
        doc_params = set(tool.doc_args)
        doc_required = {name for name, (_, _, optional) in tool.doc_args.items() if not optional}
        if parser_params != doc_params:
            result.add_error(
                tool.path,
                f"{tool.node.name}: parser parameters {sorted(parser_params)} do not match doc args {sorted(doc_params)}",
            )
        if parser_required != doc_required:
            result.add_error(
                tool.path,
                f"{tool.node.name}: parser required args {sorted(parser_required)} do not match doc required args {sorted(doc_required)}",
            )

        exposed_outputs = set(((function.get("io_contract") or {}).get("outputs") or {}).keys())
        if tool.io_outputs and exposed_outputs != tool.io_outputs:
            result.add_error(
                tool.path,
                f"{tool.node.name}: parser io_contract outputs {sorted(exposed_outputs)} do not match @tool_io outputs {sorted(tool.io_outputs)}",
            )

    for name in sorted(set(parser_functions) - tool_names):
        result.add_warning(".", f"parser exposed {name}, but AST audit did not discover a matching direct Tool class")


def _uses_kwargs_args(call_node: ast.FunctionDef) -> bool:
    for node in ast.walk(call_node):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "kwargs":
            if isinstance(node.slice, ast.Constant) and node.slice.value == "args":
                return True
        if isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            if (
                func_name in {"_args", "tool_args", "get_tool_args"}
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "kwargs"
            ):
                return True
    return False


def _dict_keys(node: ast.AST) -> set[str]:
    if not isinstance(node, ast.Dict):
        return set()
    return {key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}


def _publish_outputs_keys(node: ast.AST) -> set[str]:
    if not isinstance(node, ast.Call):
        return set()
    name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
    if name not in {"publish_outputs", "declare_outputs"}:
        return set()
    if node.args and isinstance(node.args[0], ast.Dict):
        return _dict_keys(node.args[0])
    return set()


def _assigned_dict_key_sets(call_node: ast.FunctionDef) -> dict[str, set[str]]:
    assigned: dict[str, set[str]] = {}
    for node in ast.walk(call_node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                if isinstance(node.value, ast.Dict):
                    assigned[target.id] = _dict_keys(node.value)
                elif keys := _publish_outputs_keys(node.value):
                    assigned[target.id] = keys
            elif (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                assigned.setdefault(target.value.id, set()).add(target.slice.value)
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "update"
            and isinstance(node.value.func.value, ast.Name)
            and node.value.args
            and isinstance(node.value.args[0], ast.Dict)
        ):
            assigned.setdefault(node.value.func.value.id, set()).update(_dict_keys(node.value.args[0]))
    return assigned


def _returned_key_sets(call_node: ast.FunctionDef) -> list[set[str]]:
    assigned = _assigned_dict_key_sets(call_node)
    returned: list[set[str]] = []
    for node in ast.walk(call_node):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        if isinstance(value, ast.Dict):
            returned.append(_dict_keys(value))
        elif isinstance(value, ast.Name) and value.id in assigned:
            returned.append(assigned[value.id])
        elif isinstance(value, ast.Tuple):
            keys: set[str] = set()
            for element in value.elts:
                if isinstance(element, ast.Dict):
                    keys.update(_dict_keys(element))
                elif isinstance(element, ast.Name) and element.id in assigned:
                    keys.update(assigned[element.id])
            if keys:
                returned.append(keys)
    return returned


def _published_output_keys(call_node: ast.FunctionDef) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(call_node):
        keys.update(_publish_outputs_keys(node))
    return keys


def _is_kwargs_key(node: ast.AST, key: str) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "kwargs"
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == key
    )


def _tool_data_keys(call_node: ast.FunctionDef) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(call_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if _is_kwargs_key(target, "tool_data") and isinstance(node.value, ast.Dict):
                    keys.update(_dict_keys(node.value))
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "update"
            and _is_kwargs_key(node.value.func.value, "tool_data")
            and node.value.args
            and isinstance(node.value.args[0], ast.Dict)
        ):
            keys.update(_dict_keys(node.value.args[0]))
    return keys


def _kwargs_required_gets(method: ast.FunctionDef, required_keys: set[str]) -> list[tuple[int, str]]:
    offenders: list[tuple[int, str]] = []
    for node in ast.walk(method):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "kwargs"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value in required_keys
        ):
            offenders.append((node.lineno, node.args[0].value))
    return offenders


def _kwargs_args_accesses(call_node: ast.FunctionDef) -> set[str]:
    aliases = {"args"}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(call_node):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            is_args_value = (
                isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == "kwargs"
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "args"
            ) or (isinstance(value, ast.Name) and value.id in aliases)
            if not is_args_value:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id not in aliases:
                    aliases.add(target.id)
                    changed = True

    names: set[str] = set()
    for node in ast.walk(call_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            value = node.func.value
            direct_kwargs_args = (
                isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == "kwargs"
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "args"
            )
            alias_args = isinstance(value, ast.Name) and value.id in aliases
            if (direct_kwargs_args or alias_args) and node.args and isinstance(node.args[0], ast.Constant):
                if isinstance(node.args[0].value, str):
                    names.add(node.args[0].value)
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            value = node.value
            direct_kwargs_args = (
                isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == "kwargs"
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "args"
            )
            alias_args = isinstance(value, ast.Name) and value.id in aliases
            if (direct_kwargs_args or alias_args) and isinstance(node.slice.value, str):
                names.add(node.slice.value)
    return names


def check_static_contracts(tools: list[ToolClass], result: AuditResult, *, strict_metadata: bool = False) -> None:
    for tool in tools:
        if not tool.docstring:
            result.add_error(tool.path, f"{tool.node.name}: missing immediate class docstring")
        else:
            intro_paragraphs = _doc_intro_paragraphs(tool.docstring)
            if not intro_paragraphs:
                result.add_error(tool.path, f"{tool.node.name}: missing docstring short description")
            elif len(intro_paragraphs) > 1:
                result.add_warning(
                    tool.path,
                    f"{tool.node.name}: long-description paragraphs before Args are parser-hidden",
                )

        missing_metadata = sorted(key for key in ATP_METADATA_FIELDS if key not in tool.assignments)
        if missing_metadata:
            message = f"{tool.node.name}: missing metadata {missing_metadata}"
            if strict_metadata:
                result.add_error(tool.path, message)
            else:
                result.add_warning(tool.path, message)

        if tool.calltype is None:
            message = f"{tool.node.name}: missing calltype; Adam defaults to bash"
            if strict_metadata:
                result.add_error(tool.path, message)
            else:
                result.add_warning(tool.path, message)
        elif tool.calltype not in VALID_CALLTYPES:
            result.add_error(tool.path, f"{tool.node.name}: invalid or missing calltype {tool.calltype!r}")

        call_node = tool.methods.get("call")
        if call_node is None:
            result.add_error(tool.path, f"{tool.node.name}: missing call()")
        else:
            if tool.calltype == "python" and not _uses_kwargs_args(call_node):
                result.add_error(tool.path, f"{tool.node.name}: call() must read kwargs['args']")

            call_args = _kwargs_args_accesses(call_node)
            undocumented = sorted(set(call_args) - set(tool.doc_args) - {"args"})
            if undocumented:
                result.add_error(tool.path, f"{tool.node.name}: call() reads undocumented args {undocumented}")

            required_args = {name for name, (_, _, optional) in tool.doc_args.items() if not optional}
            unused_required = sorted(required_args - call_args - IGNORED_UNUSED_REQUIRED_ARGS)
            if unused_required:
                result.add_warning(tool.path, f"{tool.node.name}: required doc args not visibly read in call(): {unused_required}")

            landed_outputs = set().union(*_returned_key_sets(call_node), set()) | _published_output_keys(call_node)
            missing_outputs = sorted(tool.io_outputs - landed_outputs)
            if missing_outputs:
                result.add_error(tool.path, f"{tool.node.name}: @tool_io outputs not returned or published: {missing_outputs}")
            undeclared_outputs = sorted(landed_outputs - tool.io_outputs)
            if landed_outputs and not tool.io_outputs:
                result.add_warning(tool.path, f"{tool.node.name}: publishes outputs without @tool_io declaration: {undeclared_outputs}")
            elif tool.io_outputs and undeclared_outputs:
                result.add_error(tool.path, f"{tool.node.name}: lands undeclared @tool_io output keys: {undeclared_outputs}")
            duplicate_tool_data = sorted(_tool_data_keys(call_node) & tool.io_outputs)
            if duplicate_tool_data:
                result.add_warning(
                    tool.path,
                    f"{tool.node.name}: @tool_io output keys redundantly copied into tool_data: {duplicate_tool_data}",
                )

        for method_name, method in tool.methods.items():
            required_keys = HOOK_REQUIRED_KWARGS.get(method_name)
            if not required_keys:
                continue
            for line_number, key in _kwargs_required_gets(method, required_keys):
                result.add_error(
                    tool.path,
                    f"{tool.node.name}.{method_name}:{line_number}: kwargs.get({key!r}) used for required hook kwarg",
                )

        for name, (_, description, optional) in tool.doc_args.items():
            if optional:
                continue
            if name in OPTIONAL_PATH_COMPAT_ARG_NAMES:
                continue
            if any(name.startswith(prefix) for prefix in OPTIONAL_PATH_COMPAT_ARG_PREFIXES):
                continue
            if (
                PATH_NAME_PATTERN.search(name)
                and "[PATH_REQUIRED]" not in description
                and "trackPath" not in description
                and "getState" not in description
            ):
                result.add_warning(tool.path, f"{tool.node.name}: path-like arg {name!r} lacks PATH marker or trackPath guidance")
        for name, (type_name, _, _) in tool.doc_args.items():
            if any(pattern.search(type_name) for pattern in FORBIDDEN_DOC_TYPE_PATTERNS):
                result.add_warning(tool.path, f"{tool.node.name}.{name}: docstring type {type_name!r} may not be parser-safe")


def audit_toolbox(
    root: Path,
    *,
    parser_command: str | None = None,
    functions_json: Path | None = None,
    changed_files: list[Path] | None = None,
    scan_paths: list[Path] | None = None,
    exclude_dirs: set[str] | None = None,
    strict_parser: bool = False,
    strict_metadata: bool = False,
) -> AuditResult:
    root = root.resolve()
    result = AuditResult()
    parser_succeeded = run_parser_command(root, parser_command, strict_parser, result)

    tools = discover_tools(root, changed_files=changed_files, scan_paths=scan_paths, exclude_dirs=exclude_dirs)
    result.tool_count = len(tools)

    parser_output = functions_json
    if parser_output is None and parser_command and parser_succeeded:
        parser_output = root / "functions.json"
    if parser_output is not None:
        parser_functions = load_parser_functions(parser_output if parser_output.is_absolute() else root / parser_output, result)
        if parser_functions is not None:
            check_parser_exposure(tools, parser_functions, result)

    check_static_contracts(tools, result, strict_metadata=strict_metadata)
    return result


def _result_payload(result: AuditResult) -> dict[str, Any]:
    return {
        "tool_count": result.tool_count,
        "errors": [asdict(item) for item in result.errors],
        "warnings": [asdict(item) for item in result.warnings],
    }


def print_result(result: AuditResult, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2))
        return

    print("ATP Tool integrity audit")
    print(f"Tools checked: {result.tool_count}")
    print(f"Errors: {len(result.errors)}")
    for item in result.errors:
        print(f"ERROR {item.path}: {item.message}")
    print(f"Warnings: {len(result.warnings)}")
    for item in result.warnings:
        print(f"WARNING {item.path}: {item.message}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = audit_toolbox(
        args.root,
        parser_command=args.parser_command,
        functions_json=args.functions_json,
        changed_files=args.changed_file,
        scan_paths=args.scan_path,
        exclude_dirs=set(args.exclude_dir),
        strict_parser=args.strict_parser,
        strict_metadata=args.strict_metadata,
    )
    print_result(result, args.format)
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
