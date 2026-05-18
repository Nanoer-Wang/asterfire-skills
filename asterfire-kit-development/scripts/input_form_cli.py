#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""input.json 表单知识库辅助脚本。

用途：
- 查询平台支持的字段类型；
- 查询/导出常见 Kit 的最小 input.json 模板；
- 按关键词推荐最接近的最小表单模板；
- 对已有 input.json 做基础结构校验。
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "references" / "input_form_catalog.json"


def load_catalog(path: Path = CATALOG_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"找不到表单知识库: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def list_types(catalog: Dict[str, Any]) -> None:
    for field_type, spec in catalog["supported_field_types"].items():
        print(f"{field_type}\t{spec.get('label', '')}\t{spec.get('use_for', '')}")


def show_type(catalog: Dict[str, Any], field_type: str) -> None:
    specs = catalog["supported_field_types"]
    if field_type not in specs:
        raise KeyError(f"不支持的字段类型: {field_type}")
    print(dump_json(specs[field_type]))


def list_templates(catalog: Dict[str, Any]) -> None:
    for name, tpl in catalog["task_templates"].items():
        tags = ",".join(tpl.get("tags", []))
        print(f"{name}\t{tpl.get('formName', '')}\t{tags}\t{tpl.get('description', '')}")


def _resolve_field(catalog: Dict[str, Any], item: Any) -> Dict[str, Any]:
    recipes = catalog["field_recipes"]
    if isinstance(item, str):
        if item not in recipes:
            raise KeyError(f"模板引用了不存在的 field_recipe: {item}")
        return copy.deepcopy(recipes[item])
    if isinstance(item, dict):
        return copy.deepcopy(item)
    raise TypeError(f"无法解析字段模板项: {item!r}")


def render_template(catalog: Dict[str, Any], template_name: str) -> Dict[str, Any]:
    templates = catalog["task_templates"]
    if template_name not in templates:
        raise KeyError(f"不存在的任务模板: {template_name}")
    tpl = templates[template_name]
    field_items = tpl.get("fields", tpl.get("field_recipes", []))
    fields = [_resolve_field(catalog, item) for item in field_items]
    required = tpl.get("required", [])
    form = {
        "formName": tpl["formName"],
        "description": tpl["description"],
        "defaultValues": copy.deepcopy(tpl.get("defaultValues", {})),
        "formRules": {"required": required},
        "fields": fields,
    }
    return form


def show_template(catalog: Dict[str, Any], template_name: str) -> None:
    print(dump_json(render_template(catalog, template_name)))


def write_template(catalog: Dict[str, Any], template_name: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dump_json(render_template(catalog, template_name)) + "\n", encoding="utf-8")
    print(f"已写出: {output}")


def suggest_templates(catalog: Dict[str, Any], keywords: Iterable[str], top_k: int = 5) -> None:
    kws = [k.lower() for k in keywords if k]
    if not kws:
        raise ValueError("请至少提供一个关键词，例如：pdb validator")

    scored: List[Tuple[int, str, Dict[str, Any]]] = []
    for name, tpl in catalog["task_templates"].items():
        haystack = " ".join(
            [
                name,
                tpl.get("formName", ""),
                tpl.get("description", ""),
                " ".join(tpl.get("tags", [])),
            ]
        ).lower()
        score = sum(1 for kw in kws if kw in haystack)
        if score:
            scored.append((score, name, tpl))

    scored.sort(key=lambda x: (-x[0], x[1]))
    if not scored:
        print("未找到匹配模板。请从 field_recipes 手动组合最小 input.json。")
        return
    for score, name, tpl in scored[:top_k]:
        tags = ",".join(tpl.get("tags", []))
        print(f"{name}\t得分={score}\t{tpl.get('formName', '')}\t{tags}\t{tpl.get('description', '')}")


def validate_input_json(catalog: Dict[str, Any], path: Path) -> int:
    errors: List[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))

    required_top = catalog["form_config"]["required_top_level_keys"]
    for key in required_top:
        if key not in data:
            errors.append(f"缺少顶层字段: {key}")

    supported_types = set(catalog["supported_field_types"].keys())
    fields = data.get("fields", [])
    if not isinstance(fields, list):
        errors.append("fields 必须是数组")
        fields = []

    names: List[str] = []
    for idx, field in enumerate(fields):
        if not isinstance(field, dict):
            errors.append(f"fields[{idx}] 必须是对象")
            continue
        for key in ("name", "label", "type"):
            if key not in field:
                errors.append(f"fields[{idx}] 缺少字段: {key}")
        name = field.get("name")
        if isinstance(name, str):
            names.append(name)
        field_type = field.get("type")
        if field_type not in supported_types:
            errors.append(f"字段 {name or idx} 使用了不支持的 type: {field_type}")
        if field_type == "array" and "itemTemplate" not in field:
            errors.append(f"数组字段 {name or idx} 缺少 itemTemplate")
        if field_type in {"select", "multiselect", "cascader"} and "options" not in field:
            errors.append(f"选择字段 {name or idx} 缺少 options")

    if len(names) != len(set(names)):
        errors.append("fields[].name 存在重复")

    form_required = data.get("formRules", {}).get("required", [])
    if not isinstance(form_required, list):
        errors.append("formRules.required 必须是数组")
        form_required = []
    for name in form_required:
        if name not in names:
            errors.append(f"formRules.required 中的 {name} 不存在于 fields[].name")

    if errors:
        print("校验失败：")
        for item in errors:
            print(f"- {item}")
        return 1
    print("校验通过。")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Asterfire Kit input.json 表单知识库辅助脚本")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-types", help="列出平台支持的字段类型")

    p_show_type = sub.add_parser("show-type", help="显示某个字段类型的定义")
    p_show_type.add_argument("field_type")

    sub.add_parser("list-templates", help="列出内置最小 input.json 任务模板")

    p_show_tpl = sub.add_parser("show-template", help="渲染某个任务模板")
    p_show_tpl.add_argument("template_name")

    p_write_tpl = sub.add_parser("write-template", help="把某个任务模板写成 input.json")
    p_write_tpl.add_argument("template_name")
    p_write_tpl.add_argument("output", type=Path)

    p_suggest = sub.add_parser("suggest", help="按关键词推荐最接近的任务模板")
    p_suggest.add_argument("keywords", nargs="+")
    p_suggest.add_argument("--top-k", type=int, default=5)

    p_validate = sub.add_parser("validate", help="校验已有 input.json 的基础结构")
    p_validate.add_argument("input_json", type=Path)

    args = parser.parse_args(argv)
    catalog = load_catalog()

    try:
        if args.command == "list-types":
            list_types(catalog)
        elif args.command == "show-type":
            show_type(catalog, args.field_type)
        elif args.command == "list-templates":
            list_templates(catalog)
        elif args.command == "show-template":
            show_template(catalog, args.template_name)
        elif args.command == "write-template":
            write_template(catalog, args.template_name, args.output)
        elif args.command == "suggest":
            suggest_templates(catalog, args.keywords, args.top_k)
        elif args.command == "validate":
            return validate_input_json(catalog, args.input_json)
        else:
            parser.error(f"未知命令: {args.command}")
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
