#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demos/demos.json 辅助脚本。

用途：
- 为最小 Kit 模板创建 demos/ 示例；
- 校验 demos.json 的基础结构；
- 检查 Demo value 是否覆盖 input.json 的必填字段；
- 检查 Demo 引用的文件是否真实位于 demos/ 目录下。
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DEMOS = ROOT / "assets" / "templates" / "demos"


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def input_fields(input_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = input_json.get("fields", [])
    if not isinstance(fields, list):
        raise ValueError("input.json 中 fields 必须是数组")
    return fields


def required_names(input_json: Dict[str, Any]) -> Set[str]:
    required = set(input_json.get("formRules", {}).get("required", []) or [])
    for field in input_fields(input_json):
        name = field.get("name")
        validation = field.get("validation", {}) or {}
        if name and validation.get("required") is True:
            required.add(name)
    return required


def known_names(input_json: Dict[str, Any]) -> Set[str]:
    return {field.get("name") for field in input_fields(input_json) if field.get("name")}


def file_field_names(input_json: Dict[str, Any]) -> Set[str]:
    names: Set[str] = set()
    for field in input_fields(input_json):
        name = field.get("name")
        if not name:
            continue
        ftype = str(field.get("type", "")).lower()
        validation = field.get("validation", {}) or {}
        # 兼容平台常见写法：type=file，或 validation.accept 指定上传后缀。
        if ftype in {"file", "files", "upload", "uploads"} or validation.get("accept"):
            names.add(name)
    return names


def iter_file_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_file_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_file_values(item)


def validate(input_path: Path, demos_path: Path) -> int:
    input_json = load_json(input_path)
    demos = load_json(demos_path)
    demo_dir = demos_path.parent

    if not isinstance(demos, list):
        raise ValueError("demos.json 顶层必须是数组")
    if not demos:
        raise ValueError("demos.json 至少需要包含一个 Demo")

    required = required_names(input_json)
    known = known_names(input_json)
    file_names = file_field_names(input_json)
    errors: List[str] = []
    warnings: List[str] = []

    for index, demo in enumerate(demos):
        prefix = f"第 {index + 1} 个 Demo"
        if not isinstance(demo, dict):
            errors.append(f"{prefix}: 必须是对象")
            continue
        for key in ("name", "description", "value"):
            if key not in demo:
                errors.append(f"{prefix}: 缺少字段 {key}")
        value = demo.get("value")
        if not isinstance(value, dict):
            errors.append(f"{prefix}: value 必须是对象")
            continue

        missing = sorted(required - set(value.keys()))
        if missing:
            errors.append(f"{prefix}: value 缺少必填字段 {missing}")

        extra = sorted(set(value.keys()) - known)
        if extra:
            warnings.append(f"{prefix}: value 包含 input.json 未定义字段 {extra}")

        for field_name in sorted(file_names):
            if field_name not in value:
                continue
            for filename in iter_file_values(value[field_name]):
                # URL 或绝对路径不适合作为可打包 Demo。这里直接提醒并按错误处理。
                if filename.startswith(("http://", "https://")):
                    errors.append(f"{prefix}: 文件字段 {field_name} 不应使用 URL: {filename}")
                    continue
                file_path = Path(filename)
                if file_path.is_absolute():
                    errors.append(f"{prefix}: 文件字段 {field_name} 不应使用绝对路径: {filename}")
                    continue
                candidate = demo_dir / file_path
                if not candidate.exists():
                    errors.append(f"{prefix}: 文件字段 {field_name} 引用的文件不存在: {candidate}")

    for warning in warnings:
        print(f"[警告] {warning}")
    if errors:
        for error in errors:
            print(f"[错误] {error}")
        return 1
    print(f"校验通过: {demos_path}")
    return 0


def create_template(output: Path, overwrite: bool = False) -> None:
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise FileExistsError(f"输出目录已存在且非空: {output}；如需覆盖请加 --overwrite")
    output.mkdir(parents=True, exist_ok=True)
    for item in TEMPLATE_DEMOS.iterdir():
        dst = output / item.name
        if item.is_dir():
            if dst.exists() and overwrite:
                shutil.rmtree(dst)
            shutil.copytree(item, dst, dirs_exist_ok=overwrite)
        else:
            if dst.exists() and not overwrite:
                continue
            shutil.copy2(item, dst)
    print(f"已创建 Demo 模板目录: {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="维护和校验 Asterfire Kit demos/demos.json")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="校验 demos.json")
    p_validate.add_argument("--input", default="config/input.json", help="input.json 路径")
    p_validate.add_argument("--demos", default="demos/demos.json", help="demos.json 路径")

    p_template = sub.add_parser("create-template", help="创建最小模板 demos/ 目录")
    p_template.add_argument("--output", default="demos", help="输出目录")
    p_template.add_argument("--overwrite", action="store_true", help="允许覆盖已存在文件")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "validate":
        return validate(Path(args.input), Path(args.demos))
    if args.command == "create-template":
        create_template(Path(args.output), overwrite=args.overwrite)
        return 0
    parser.error(f"未知命令: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
