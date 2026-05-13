#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普通项目 → 平台 Kit 适配前分析脚本。

该脚本只做静态扫描，帮助判断：
- 项目是否已有 runner(Tool)
- 可能的普通入口文件
- 第三方依赖和外部命令
- 疑似输入/输出文件参数
- runner 配置缺口
- SIF 注册表候选

用法：
  python scripts/porting_analyzer.py /path/to/project
  python scripts/porting_analyzer.py /path/to/project --json-out analysis.json --md-out analysis.md
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "references" / "sif_registry.json"

COMMON_STDLIB = {
    "argparse", "ast", "collections", "csv", "dataclasses", "datetime", "functools", "glob",
    "hashlib", "itertools", "json", "logging", "math", "os", "pathlib", "pickle", "re",
    "shutil", "statistics", "subprocess", "sys", "tempfile", "time", "traceback", "typing",
    "zipfile", "gzip", "tarfile", "threading", "multiprocessing", "random", "string",
}
ENTRY_NAME_HINTS = {"main.py", "app.py", "cli.py", "run.py", "predict.py", "train.py", "infer.py", "inference.py"}
EXTERNAL_COMMAND_PATTERNS = [
    r"subprocess\.(?:run|call|Popen|check_call|check_output)\s*\(\s*\[\s*['\"]([^'\"]+)",
    r"os\.system\s*\(\s*['\"]([^'\"\s]+)",
]
FILE_EXT_PATTERN = re.compile(r"\.(pdb|cif|mol2|sdf|xyz|csv|json|txt|fa|fasta|zip|tar|gz|png|jpg|jpeg|pdf|md|itp|top|gro|xtc|tpr)\b", re.I)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="gbk")
        except Exception:
            return ""
    except Exception:
        return ""


def iter_python_files(project: Path) -> List[Path]:
    ignored = {".git", "__pycache__", ".venv", "venv", "env", "build", "dist", ".mypy_cache", ".pytest_cache"}
    files = []
    for path in project.rglob("*.py"):
        if any(part in ignored for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def parse_python(path: Path) -> Dict[str, Any]:
    text = read_text(path)
    info: Dict[str, Any] = {
        "path": str(path),
        "has_runner": bool(re.search(r"class\s+runner\s*\(\s*Tool\s*\)", text)),
        "has_main_guard": "if __name__" in text and "__main__" in text,
        "uses_argparse": "argparse" in text or "ArgumentParser" in text,
        "uses_click": "click." in text or "@click" in text,
        "uses_typer": "typer." in text or "Typer(" in text,
        "imports": [],
        "functions": [],
        "runner_config": {},
        "external_commands": [],
        "file_extensions": sorted(set(FILE_EXT_PATTERN.findall(text))),
        "argparse_options": [],
    }
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        info["syntax_error"] = str(exc)
        return info

    imports: Set[str] = set()
    functions: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef) and node.name == "runner":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id in {"DISPLAY_NAME", "NETWORK", "CPU", "GPU", "SIF"}:
                            try:
                                info["runner_config"][target.id] = ast.literal_eval(stmt.value)
                            except Exception:
                                info["runner_config"][target.id] = "<无法静态解析>"
    info["imports"] = sorted(imports)
    info["functions"] = functions[:50]

    for pattern in EXTERNAL_COMMAND_PATTERNS:
        info["external_commands"].extend(re.findall(pattern, text))
    info["external_commands"] = sorted(set(info["external_commands"]))

    # 提取 argparse 参数名，仅作为线索。
    opts = re.findall(r"add_argument\s*\(\s*['\"](--?[A-Za-z0-9_\-]+)['\"]", text)
    info["argparse_options"] = sorted(set(opts))
    return info


def load_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"sifs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def score_sifs(registry: Dict[str, Any], keywords: Set[str]) -> List[Dict[str, Any]]:
    results = []
    lowered = {k.lower() for k in keywords if k}
    for item in registry.get("sifs", []):
        haystack = " ".join([
            item.get("sif", ""),
            item.get("purpose", ""),
            " ".join(item.get("environment", [])),
            " ".join(item.get("contains", [])),
            " ".join(item.get("tags", [])),
            item.get("notes", ""),
        ]).lower()
        hits = sorted(k for k in lowered if k and k in haystack)
        score = len(hits)
        if score:
            out = dict(item)
            out["match_score"] = score
            out["match_hits"] = hits
            results.append(out)
    return sorted(results, key=lambda x: (-x["match_score"], x.get("sif", "")))


def analyze(project: Path, registry_path: Path) -> Dict[str, Any]:
    project = project.resolve()
    py_files = iter_python_files(project)
    parsed = [parse_python(p) for p in py_files]
    runner_files = [p for p in parsed if p.get("has_runner")]

    config_dir = project / "config"
    existing = {
        "config/input.json": (config_dir / "input.json").exists(),
        "config/configure.json": (config_dir / "configure.json").exists(),
        "config/long_description.md": (config_dir / "long_description.md").exists(),
        "demos/demos.json": (project / "demos" / "demos.json").exists(),
        "Makefile": (project / "Makefile").exists(),
    }

    third_party: Set[str] = set()
    external_commands: Set[str] = set()
    file_exts: Set[str] = set()
    possible_entries: List[str] = []
    argparse_options: Set[str] = set()
    for info in parsed:
        imports = set(info.get("imports", []))
        third_party.update(x for x in imports if x not in COMMON_STDLIB and not x.startswith("adam_community"))
        external_commands.update(info.get("external_commands", []))
        file_exts.update(info.get("file_extensions", []))
        argparse_options.update(info.get("argparse_options", []))
        name = Path(info["path"]).name
        if name in ENTRY_NAME_HINTS or info.get("has_main_guard") or info.get("uses_argparse") or info.get("uses_click") or info.get("uses_typer"):
            possible_entries.append(str(Path(info["path"]).relative_to(project)))

    req_files = []
    for req_name in ["requirements.txt", "environment.yml", "pyproject.toml", "setup.py"]:
        p = project / req_name
        if p.exists():
            req_files.append(req_name)
            text = read_text(p)
            # 粗略抽取依赖关键词
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_\-]+", text):
                if token.lower() not in {"version", "dependencies", "requires", "python"}:
                    third_party.add(token.split("-")[0])

    runner_config = {}
    if len(runner_files) == 1:
        runner_config = runner_files[0].get("runner_config", {})
    missing_runner_config = [k for k in ["DISPLAY_NAME", "NETWORK", "CPU", "GPU", "SIF"] if k not in runner_config]
    invalid_sif = False
    sif = runner_config.get("SIF")
    if sif in (None, "", "TODO", "待定") or (isinstance(sif, str) and "example" in sif.lower()):
        invalid_sif = True
        if "SIF" not in missing_runner_config:
            missing_runner_config.append("SIF")

    keywords = set(third_party) | set(external_commands) | set(file_exts)
    for entry in possible_entries:
        keywords.update(Path(entry).stem.replace("_", " ").replace("-", " ").split())
    registry = load_registry(registry_path)
    sif_candidates = score_sifs(registry, keywords)[:8]

    return {
        "project": str(project),
        "python_file_count": len(py_files),
        "existing_platform_files": existing,
        "runner_files": [str(Path(x["path"]).relative_to(project)) for x in runner_files],
        "runner_config": runner_config,
        "missing_runner_config": sorted(set(missing_runner_config)),
        "invalid_sif": invalid_sif,
        "possible_entries": possible_entries[:20],
        "requirement_files": req_files,
        "third_party_imports_or_deps": sorted(third_party),
        "external_commands": sorted(external_commands),
        "detected_file_extensions": sorted(file_exts),
        "argparse_options": sorted(argparse_options),
        "sif_candidates": sif_candidates,
        "notes": build_notes(runner_files, missing_runner_config, sif_candidates),
    }


def build_notes(runner_files: List[Dict[str, Any]], missing: List[str], candidates: List[Dict[str, Any]]) -> List[str]:
    notes = []
    if not runner_files:
        notes.append("未发现 class runner(Tool)，这是普通项目，需要新增平台入口文件。")
    elif len(runner_files) == 1:
        notes.append("发现一个已有 runner，可在该入口上补齐或修正平台配置。")
    else:
        notes.append("发现多个 runner，不能自动判断真实入口，需要用户确认。")
    if missing:
        notes.append("runner 配置缺失或无效：" + ", ".join(sorted(set(missing))) + "。改造前必须先确认这些配置。")
    if candidates:
        notes.append("SIF 注册表存在候选镜像；如果用户授权自动选择，需要根据候选与项目依赖进一步确认。")
    else:
        notes.append("未在 SIF 注册表中找到明显候选；可能需要用户指定或先登记新 SIF。")
    notes.append("适配交付时需要同步创建或检查 demos/demos.json，并确保引用的示例文件位于 demos/ 目录。")
    return notes


def render_markdown(data: Dict[str, Any]) -> str:
    lines = [
        "# 普通项目适配分析报告",
        "",
        f"项目路径：`{data['project']}`",
        "",
        "## 平台文件现状",
        "",
        "| 文件 | 是否存在 |",
        "| --- | --- |",
    ]
    for k, v in data["existing_platform_files"].items():
        lines.append(f"| {k} | {'是' if v else '否'} |")

    lines.extend(["", "## runner 检查", ""])
    lines.append(f"runner 文件：`{data['runner_files']}`")
    lines.append(f"runner 配置：`{data['runner_config']}`")
    lines.append(f"缺失或无效配置：`{data['missing_runner_config']}`")

    lines.extend(["", "## 疑似普通入口", ""])
    if data["possible_entries"]:
        for x in data["possible_entries"]:
            lines.append(f"- `{x}`")
    else:
        lines.append("- 未发现明显入口，需要人工查看项目结构。")

    lines.extend(["", "## 依赖和命令线索", ""])
    lines.append(f"第三方依赖/导入：`{data['third_party_imports_or_deps']}`")
    lines.append(f"外部命令：`{data['external_commands']}`")
    lines.append(f"文件扩展名线索：`{data['detected_file_extensions']}`")
    lines.append(f"argparse 参数线索：`{data['argparse_options']}`")

    lines.extend(["", "## SIF 候选", ""])
    if data["sif_candidates"]:
        lines.append("| SIF | 分数 | 命中 | 用途 | 默认资源 |")
        lines.append("| --- | ---: | --- | --- | --- |")
        for item in data["sif_candidates"]:
            res = item.get("default_resources", {})
            lines.append(
                f"| `{item.get('sif')}` | {item.get('match_score')} | `{item.get('match_hits')}` | {item.get('purpose','')} | CPU={res.get('cpu')}, GPU={res.get('gpu')}, NETWORK={res.get('network')} |"
            )
    else:
        lines.append("未找到明显候选。")

    lines.extend(["", "## 建议", ""])
    for note in data["notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="分析普通项目能否适配为平台 Kit")
    parser.add_argument("project", type=Path, help="普通项目根目录")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="SIF 注册表路径")
    parser.add_argument("--json-out", type=Path, help="写出 JSON 分析结果")
    parser.add_argument("--md-out", type=Path, help="写出 Markdown 分析报告")
    args = parser.parse_args()

    if not args.project.exists():
        raise SystemExit(f"项目路径不存在: {args.project}")
    data = analyze(args.project, args.registry)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(data), encoding="utf-8")

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
