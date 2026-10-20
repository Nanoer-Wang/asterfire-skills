# -*- coding: utf-8 -*-
"""Asterfire image resource path resolver template."""

import os
from pathlib import Path


def get_image_dir(env_name: str, default_path: str, required_files=None) -> Path:
    """Return an image-bundled directory and validate required files."""
    image_dir = Path(os.environ.get(env_name, default_path))
    if not image_dir.is_dir():
        raise FileNotFoundError(
            f"镜像内资源目录不存在: {image_dir}. "
            f"请检查 Dockerfile COPY 目标路径或环境变量 {env_name}。"
        )
    for rel in required_files or []:
        fp = image_dir / rel
        if not fp.exists():
            raise FileNotFoundError(f"镜像内必要资源不存在: {fp}")
    return image_dir


# Example:
# proteinmpnn_home = get_image_dir(
#     "PROTEINMPNN_HOME",
#     "/opt/ProteinMPNN",
#     ["protein_mpnn_run.py", "helper_scripts/parse_multiple_chains.py"],
# )
