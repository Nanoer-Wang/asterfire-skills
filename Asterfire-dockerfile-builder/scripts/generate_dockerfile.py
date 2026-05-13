#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate an Asterfire Kit Dockerfile and companion command/layout docs.

Usage:
    python scripts/generate_dockerfile.py \
      --config assets/examples/proteinmpnn_config.json \
      --out Dockerfile \
      --commands build_and_push.md \
      --layout image_layout.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _quote_list(items: List[str]) -> str:
    return " ".join(items)


def generate_dockerfile(cfg: Dict[str, Any]) -> str:
    base_image = cfg.get(
        "base_image",
        "registry.cn-hangzhou.aliyuncs.com/sidereus-ai/python:3.12.12-slim",
    )
    workdir = cfg.get("workdir", "/app")
    dependency_mode = cfg.get("dependency_mode", "pip").lower()
    apt_packages = cfg.get(
        "apt_packages", ["python3", "python3-pip", "ca-certificates"]
    )
    author = cfg.get("author", "Your Name")
    image_version = cfg.get("image_version", "1.0.0")
    description = cfg.get("description", "Asterfire Kit image")
    copies = cfg.get("copies", [])
    env = cfg.get("env", {})
    sanity_checks = cfg.get("sanity_checks", [])

    lines: List[str] = []
    lines.append(f"FROM {base_image}")
    lines.append("")
    lines.append("ENV PATH=/app/bin:$PATH")
    lines.append("ENV PYTHONPATH=/app:$PYTHONPATH")
    lines.append("")

    if dependency_mode == "conda":
        conda_installer = cfg.get(
            "conda_installer", "Miniconda3-latest-Linux-x86_64.sh"
        )
        conda_env_file = cfg.get("environment_file", "environment.yml")
        conda_env_name = cfg.get("conda_env_name", "<env_name>")
        lines.extend(
            [
                "RUN apt-get update \\",
                "    && apt-get install -y --no-install-recommends bzip2 ca-certificates \\",
                "    && rm -rf /var/lib/apt/lists/*",
                "",
                "ENV CONDA_DIR=/opt/conda",
                "ENV PATH=$CONDA_DIR/bin:$PATH",
                f"COPY {conda_installer} /tmp/miniconda.sh",
                "RUN bash /tmp/miniconda.sh -b -p $CONDA_DIR \\",
                "    && rm /tmp/miniconda.sh \\",
                "    && conda clean -afy",
                "",
                f"WORKDIR {workdir}",
                f"COPY {conda_env_file} /app/environment.yml",
                "RUN conda env create -f /app/environment.yml \\",
                "    && conda clean -afy",
                f"ENV PATH=/opt/conda/envs/{conda_env_name}/bin:$PATH",
                "",
            ]
        )
    else:
        req = cfg.get("requirements_file", "requirements.txt")
        lines.extend(
            [
                f"WORKDIR {workdir}",
                f"COPY {req} /app/requirements.txt",
                "RUN apt-get update \\",
                f"    && apt-get install -y --no-install-recommends {_quote_list(apt_packages)} \\",
                "    && pip3 install --no-cache-dir -r /app/requirements.txt \\",
                "    && rm -rf /var/lib/apt/lists/*",
                "",
            ]
        )

    for item in copies:
        src = item["src"]
        dst = item["dst"]
        lines.append(f"COPY {src} {dst}")
    if copies:
        lines.append("")

    for key, value in env.items():
        lines.append(f"ENV {key}={value}")
    if env:
        lines.append("")

    checks = ["python --version", "which python"] + sanity_checks
    if copies:
        for item in copies:
            dst = item["dst"]
            if str(dst).startswith("/"):
                checks.insert(2, f"ls -lah {dst}")
    if checks:
        lines.append("RUN " + " \\\n    && ".join(checks))
        lines.append("")

    lines.extend(
        [
            f"WORKDIR {workdir}",
            'CMD ["bash"]',
            "",
            f'LABEL Author="{author}" \\',
            f'      Version="{image_version}" \\',
            f'      Description="{description}"',
            "",
        ]
    )
    return "\n".join(lines)


def generate_commands(cfg: Dict[str, Any]) -> str:
    local_image = cfg.get("local_image_name", cfg.get("kit_name", "asterfire-kit"))
    version = cfg.get("image_version", "1.0.0")
    registry = cfg.get(
        "registry", "crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com"
    )
    username = cfg.get("registry_username", "xxxxxxxxxxx")
    namespace_repo = cfg.get("namespace_repo", f"mlfold/{local_image}")
    remote = f"{registry}/{namespace_repo}:{version}"

    return f"""# Docker 构建与上传命令

## 1. 构建镜像

```bash
docker build -t {local_image}:{version} .
```

## 2. 查看镜像名称以及 ID

```bash
docker images
```

## 3. 登录阿里云镜像仓库

下面只是示例，实际使用时请替换成自己阿里云平台账号中的镜像网络地址和用户名：

```bash
docker login --username={username} {registry}
```

## 4. 标记镜像名称

使用镜像 ID：

```bash
docker tag [images id] {remote}
```

或者使用本地镜像名：

```bash
docker tag {local_image}:{version} {remote}
```

## 5. 上传到平台镜像仓库

```bash
docker push {remote}
```

## 6. Asterfire Kit 主函数 SIF 建议

```python
SIF = "{local_image}:{version}"
```
"""


def generate_layout(cfg: Dict[str, Any]) -> str:
    copies = cfg.get("copies", [])
    project_lines = []
    for item in copies:
        dst = item.get("dst", "")
        src = item.get("src", "")
        project_lines.append(f"│   └── {Path(str(dst)).name}/    # COPY {src} {dst}")

    project_block = "\n".join(project_lines) if project_lines else "│   └── ProjectName/"
    return f"""# 镜像目录结构说明

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用工作目录
│   ├── requirements.txt 或 environment.yml
│   └── 轻量配置/脚本
├── opt/                  # 镜像构建时固化的大项目、权重、数据库
{project_block}
├── workspace/            # Asterfire 运行时挂载目录，runner.py 实际在这里执行
│   ├── runner.py
│   ├── 用户上传输入文件
│   ├── 中间文件
│   ├── 输出文件
│   └── report.md
└── ...
```

## 路径使用说明

- `/app`：Dockerfile 中的构建工作目录，适合放 requirements、environment.yml、轻量配置文件和轻量脚本。
- `/opt/<ProjectName>`：镜像内固定项目路径，适合放源码、模型权重、数据库。Kit 主函数读取这些资源时应使用绝对路径。
- `/workspace`：平台运行时挂载目录。用户上传文件、中间文件、输出 zip、`report.md` 应写到这里，也就是 Python 中的 `Path.cwd()`。
- 不要在 runner.py 中把 `Path.cwd()` 当成镜像内项目根目录。
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="JSON config file")
    parser.add_argument("--out", default="Dockerfile", help="Dockerfile output path")
    parser.add_argument("--commands", default="build_and_push.md", help="commands output path")
    parser.add_argument("--layout", default="image_layout.md", help="layout output path")
    args = parser.parse_args()

    cfg = _read_json(Path(args.config))
    Path(args.out).write_text(generate_dockerfile(cfg), encoding="utf-8")
    Path(args.commands).write_text(generate_commands(cfg), encoding="utf-8")
    Path(args.layout).write_text(generate_layout(cfg), encoding="utf-8")
    print(f"[OK] wrote {args.out}")
    print(f"[OK] wrote {args.commands}")
    print(f"[OK] wrote {args.layout}")


if __name__ == "__main__":
    main()
