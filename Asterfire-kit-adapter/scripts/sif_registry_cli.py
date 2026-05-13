#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIF 注册表增删改查脚本。

用法示例：
  python scripts/sif_registry_cli.py list
  python scripts/sif_registry_cli.py get example-kit:1.0.0
  python scripts/sif_registry_cli.py add --sif my-kit:1.0.0 --owner 张三 --purpose "用途" --env "Python 3.10"
  python scripts/sif_registry_cli.py update my-kit:1.0.0 --owner 李四 --purpose "新用途"
  python scripts/sif_registry_cli.py remove my-kit:1.0.0
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "references" / "sif_registry.json"


def load_registry() -> Dict[str, Any]:
    if not REGISTRY.exists():
        return {
            "schema_version": "1.0",
            "description": "Asterfire 平台 Kit SIF 注册表。",
            "sifs": [],
        }
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(data: Dict[str, Any]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_index(data: Dict[str, Any], sif: str) -> int:
    for index, item in enumerate(data.get("sifs", [])):
        if item.get("sif") == sif:
            return index
    return -1


def parse_bool(value: str) -> bool:
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y", "是"}:
        return True
    if lowered in {"0", "false", "no", "n", "否"}:
        return False
    raise argparse.ArgumentTypeError(f"无法解析布尔值: {value}")


def print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    data = load_registry()
    items = data.get("sifs", [])
    if args.tag:
        items = [item for item in items if args.tag in item.get("tags", [])]
    if args.keyword:
        keyword = args.keyword.lower()
        items = [
            item
            for item in items
            if keyword in json.dumps(item, ensure_ascii=False).lower()
        ]
    print_json(items)


def cmd_get(args: argparse.Namespace) -> None:
    data = load_registry()
    index = find_index(data, args.sif)
    if index < 0:
        raise SystemExit(f"未找到 SIF: {args.sif}")
    print_json(data["sifs"][index])


def build_item(args: argparse.Namespace, old: Dict[str, Any] | None = None) -> Dict[str, Any]:
    item = dict(old or {})
    item["sif"] = args.sif
    if args.owner is not None:
        item["owner"] = args.owner
    if args.purpose is not None:
        item["purpose"] = args.purpose
    if args.env is not None:
        item["environment"] = args.env
    if args.contains is not None:
        item["contains"] = args.contains
    if args.tag is not None:
        item["tags"] = args.tag
    if args.notes is not None:
        item["notes"] = args.notes

    resources = dict(item.get("default_resources", {}))
    if args.cpu is not None:
        resources["cpu"] = args.cpu
    if args.gpu is not None:
        resources["gpu"] = args.gpu
    if args.network is not None:
        resources["network"] = args.network
    item["default_resources"] = {
        "cpu": int(resources.get("cpu", 2)),
        "gpu": int(resources.get("gpu", 0)),
        "network": bool(resources.get("network", False)),
    }

    item.setdefault("owner", "待补充")
    item.setdefault("purpose", "待补充")
    item.setdefault("environment", [])
    item.setdefault("contains", [])
    item.setdefault("tags", [])
    item["updated_at"] = args.updated_at or date.today().isoformat()
    item.setdefault("notes", "")
    return item


def cmd_add(args: argparse.Namespace) -> None:
    data = load_registry()
    if find_index(data, args.sif) >= 0:
        raise SystemExit(f"SIF 已存在，若需修改请使用 update: {args.sif}")
    item = build_item(args)
    data.setdefault("sifs", []).append(item)
    save_registry(data)
    print_json(item)


def cmd_update(args: argparse.Namespace) -> None:
    data = load_registry()
    index = find_index(data, args.sif)
    if index < 0:
        raise SystemExit(f"未找到 SIF，若需新增请使用 add: {args.sif}")
    item = build_item(args, old=data["sifs"][index])
    data["sifs"][index] = item
    save_registry(data)
    print_json(item)


def cmd_remove(args: argparse.Namespace) -> None:
    data = load_registry()
    index = find_index(data, args.sif)
    if index < 0:
        raise SystemExit(f"未找到 SIF: {args.sif}")
    removed = data["sifs"].pop(index)
    save_registry(data)
    print_json({"removed": removed})


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--owner", help="负责人或维护团队")
    parser.add_argument("--purpose", help="镜像主要用途")
    parser.add_argument("--env", action="append", help="环境说明，可重复传入")
    parser.add_argument("--contains", action="append", help="镜像内主要软件或命令，可重复传入")
    parser.add_argument("--cpu", type=int, help="默认 CPU 数")
    parser.add_argument("--gpu", type=int, help="默认 GPU 数")
    parser.add_argument("--network", type=parse_bool, help="是否需要网络：true/false")
    parser.add_argument("--tag", action="append", help="标签，可重复传入")
    parser.add_argument("--notes", help="备注")
    parser.add_argument("--updated-at", help="更新时间，格式建议 YYYY-MM-DD")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="维护 Asterfire Kit SIF 注册表")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出 SIF")
    p_list.add_argument("--tag", help="按标签过滤")
    p_list.add_argument("--keyword", help="按关键词过滤")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="查询单个 SIF")
    p_get.add_argument("sif")
    p_get.set_defaults(func=cmd_get)

    p_add = sub.add_parser("add", help="新增 SIF")
    p_add.add_argument("--sif", required=True, help="SIF 标识")
    add_common_options(p_add)
    p_add.set_defaults(func=cmd_add)

    p_update = sub.add_parser("update", help="更新 SIF")
    p_update.add_argument("sif", help="SIF 标识")
    add_common_options(p_update)
    p_update.set_defaults(func=cmd_update)

    p_remove = sub.add_parser("remove", help="删除 SIF")
    p_remove.add_argument("sif", help="SIF 标识")
    p_remove.set_defaults(func=cmd_remove)

    return parser


def main() -> None:
    parser = make_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
