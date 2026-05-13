#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight checker for Asterfire Dockerfile path conventions."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dockerfile", nargs="?", default="Dockerfile")
    args = parser.parse_args()
    path = Path(args.dockerfile)
    text = path.read_text(encoding="utf-8")

    warnings = []
    if "WORKDIR /app" not in text:
        warnings.append("建议设置 WORKDIR /app。")
    if 'CMD ["bash"]' not in text and "CMD ['bash']" not in text:
        warnings.append('建议设置 CMD ["bash"]，避免容器默认执行训练或服务进程。')
    if "rm -rf /var/lib/apt/lists/*" not in text and "apt-get install" in text:
        warnings.append("检测到 apt-get install，但没有清理 /var/lib/apt/lists/*，镜像可能偏大。")

    for m in re.finditer(r"^COPY\s+([^\s]+)\s+([^\s]+)", text, flags=re.MULTILINE):
        src, dst = m.group(1), m.group(2)
        if not dst.startswith("/"):
            warnings.append(f"COPY {src} {dst} 的目标路径不是绝对路径，建议改为 /app/... 或 /opt/...")

    if "/workspace" in text:
        warnings.append("Dockerfile 中一般不建议 COPY 到 /workspace；/workspace 是平台运行时挂载目录。")

    if warnings:
        print("[WARN] 发现以下建议：")
        for item in warnings:
            print(f"- {item}")
    else:
        print("[OK] Dockerfile 路径规则检查未发现明显问题。")


if __name__ == "__main__":
    main()
