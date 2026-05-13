#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conservative ProteinMPNN runner path patcher for Asterfire.

This script replaces the common workspace fallback:

    mpnn_dir = cwd / "ProteinMPNN-main"
    if not mpnn_dir.is_dir():
        mpnn_dir = cwd

with an image absolute path, preferably read from the Asterfire-dockerfile-builder generated image layout document, normally /opt/ProteinMPNN.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from docker_path_analyzer import analyze_dockerfile  # noqa: E402
from image_layout_analyzer import analyze_image_layout  # noqa: E402


def _find_proteinmpnn_root_from_candidates(candidates) -> str | None:
    for item in candidates or []:
        p = str(item.get("path", ""))
        src = str(item.get("source", ""))
        if "ProteinMPNN".lower() in (p + " " + src).lower():
            return p
    return None


def infer_proteinmpnn_root(
    layout: str | None, dockerfile: str | None, default: str | None
) -> tuple[str | None, str]:
    """Infer ProteinMPNN image root.

    Priority:
    1. Explicit --image-root from the user.
    2. Asterfire-dockerfile-builder generated image layout document.
    3. Dockerfile ENV/COPY/WORKDIR analysis.
    """
    if default:
        return default, "explicit --image-root"

    if layout:
        data = analyze_image_layout(layout)
        env_roots = data.get("env_roots", {})
        if env_roots.get("PROTEINMPNN_HOME"):
            return str(env_roots["PROTEINMPNN_HOME"]), "image layout ENV PROTEINMPNN_HOME"
        root = _find_proteinmpnn_root_from_candidates(data.get("candidate_image_roots", []))
        if root:
            return root, "image layout candidate"

    if dockerfile:
        data = analyze_dockerfile(dockerfile)
        env = data.get("env", {})
        if env.get("PROTEINMPNN_HOME"):
            return str(env["PROTEINMPNN_HOME"]), "Dockerfile ENV PROTEINMPNN_HOME"
        root = _find_proteinmpnn_root_from_candidates(data.get("candidate_image_roots", []))
        if root:
            return root, "Dockerfile candidate"

    return None, "not found"


def patch_text(text: str, image_root: str) -> str:
    old_re = re.compile(
        r"(?P<indent>[ \t]*)mpnn_dir\s*=\s*cwd\s*/\s*['\"]ProteinMPNN-main['\"]\s*\n"
        r"(?P=indent)if\s+not\s+mpnn_dir\.is_dir\(\):\s*\n"
        r"(?P=indent)[ \t]+mpnn_dir\s*=\s*cwd",
        re.MULTILINE,
    )
    new_block = (
        "{indent}mpnn_dir = Path(os.environ.get(\"PROTEINMPNN_HOME\", \"{image_root}\"))\n"
        "{indent}if not mpnn_dir.is_dir():\n"
        "{indent}    raise FileNotFoundError(\n"
        "{indent}        f\"镜像内 ProteinMPNN 项目目录不存在: {{mpnn_dir}}. \"\n"
        "{indent}        \"请检查镜像目录结构说明、Dockerfile 的 COPY 目标路径或 PROTEINMPNN_HOME 环境变量。\"\n"
        "{indent}    )\n\n"
        "{indent}required_image_files = [\n"
        "{indent}    mpnn_dir / \"protein_mpnn_run.py\",\n"
        "{indent}    mpnn_dir / \"helper_scripts\" / \"parse_multiple_chains.py\",\n"
        "{indent}    mpnn_dir / \"helper_scripts\" / \"assign_fixed_chains.py\",\n"
        "{indent}    mpnn_dir / \"helper_scripts\" / \"make_fixed_positions_dict.py\",\n"
        "{indent}    mpnn_dir / \"helper_scripts\" / \"make_tied_positions_dict.py\",\n"
        "{indent}]\n"
        "{indent}for fp in required_image_files:\n"
        "{indent}    if not fp.exists():\n"
        "{indent}        raise FileNotFoundError(f\"镜像内 ProteinMPNN 必要文件不存在: {{fp}}\")"
    )

    def repl(m: re.Match[str]) -> str:
        return new_block.format(indent=m.group("indent"), image_root=image_root)

    patched, count = old_re.subn(repl, text, count=1)
    if count == 0:
        marker = "        # ---------- 4. 构建命令链 ----------"
        insert = new_block.format(indent="        ", image_root=image_root) + "\n\n"
        if marker in patched:
            patched = patched.replace(marker, insert + marker, 1)
        else:
            raise RuntimeError("未找到 ProteinMPNN 常见路径块，也找不到插入锚点。请手动校准。")
    return patched


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch ProteinMPNN runner to use image absolute path.")
    ap.add_argument("--runner", required=True)
    ap.add_argument("--layout", default=None, help="Asterfire-dockerfile-builder generated image_layout.md. Highest priority after --image-root.")
    ap.add_argument("--dockerfile", default=None)
    ap.add_argument("--image-root", default=None, help="Explicit image path, e.g. /opt/ProteinMPNN")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    image_root, source = infer_proteinmpnn_root(args.layout, args.dockerfile, args.image_root)
    if not image_root:
        raise SystemExit(
            "无法从 Asterfire-dockerfile-builder 生成的目录说明或 Dockerfile 推断 ProteinMPNN 镜像路径。"
            "请用 --layout image_layout.md、--dockerfile Dockerfile，或 --image-root /opt/ProteinMPNN 指定。"
        )

    text = Path(args.runner).read_text(encoding="utf-8", errors="replace")
    patched = patch_text(text, image_root)
    Path(args.output).write_text(patched, encoding="utf-8")
    print(json.dumps({"output": args.output, "image_root": image_root, "source": source}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
