#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze Dockerfile image paths for Asterfire Kit path calibration."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import PurePosixPath
from typing import Dict, List, Tuple


def _join_continuations(text: str) -> List[str]:
    lines: List[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        lines.append((buf + line).strip())
        buf = ""
    if buf.strip():
        lines.append(buf.strip())
    return lines


def _is_abs_path(value: str) -> bool:
    return value.startswith("/")


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def parse_env(line: str) -> Dict[str, str]:
    body = line.split(None, 1)[1].strip()
    envs: Dict[str, str] = {}
    # Handles both: ENV A=B C=D, and ENV A B
    if "=" not in body:
        parts = shlex.split(body)
        if len(parts) >= 2:
            envs[parts[0]] = parts[1]
        return envs
    for token in shlex.split(body):
        if "=" in token:
            k, v = token.split("=", 1)
            envs[k] = v
    return envs


def parse_copy_add(line: str) -> Tuple[str, List[str], str] | None:
    instr = line.split(None, 1)[0].upper()
    body = line.split(None, 1)[1].strip()
    if body.startswith("--"):
        # Drop simple flags such as --chown=x:y; repeat until no leading flag.
        parts = shlex.split(body)
        parts = [p for p in parts if not p.startswith("--")]
    else:
        parts = shlex.split(body)
    if len(parts) < 2:
        return None
    *srcs, dest = parts
    return instr, srcs, dest


def analyze_dockerfile(path: str) -> Dict[str, object]:
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    lines = _join_continuations(text)

    env: Dict[str, str] = {}
    workdirs: List[str] = []
    copies: List[Dict[str, object]] = []
    run_path_checks: List[str] = []

    for line in lines:
        upper = line.upper()
        if upper.startswith("ENV "):
            env.update(parse_env(line))
        elif upper.startswith("WORKDIR "):
            wd = _strip_quotes(line.split(None, 1)[1].strip())
            workdirs.append(wd)
        elif upper.startswith("COPY ") or upper.startswith("ADD "):
            parsed = parse_copy_add(line)
            if parsed:
                instr, srcs, dest = parsed
                copies.append({"instruction": instr, "sources": srcs, "destination": dest})
        elif upper.startswith("RUN "):
            for m in re.finditer(r"(?:test\s+-[fe]\s+|ls\s+(?:-[A-Za-z]+\s+)?)(/[\w./+-]+)", line):
                run_path_checks.append(m.group(1))

    candidate_roots: List[Dict[str, str]] = []
    for k, v in env.items():
        if _is_abs_path(v) and re.search(r"(_HOME|_ROOT|_DIR|HOME|ROOT)$", k):
            candidate_roots.append({"path": v, "source": f"ENV {k}", "confidence": "high"})

    for cp in copies:
        dest = str(cp["destination"])
        if _is_abs_path(dest):
            src_text = ",".join(cp["sources"])
            # COPY foo.txt /path/foo.txt likely points to a file, not a resource root.
            root_path = dest
            if not dest.endswith("/") and PurePosixPath(dest).suffix:
                root_path = str(PurePosixPath(dest).parent)
            confidence = "high" if any(name.lower() in (src_text + " " + dest).lower() for name in ["proteinmpnn", "model", "weights", "ckpt"]) else "medium"
            candidate_roots.append({"path": root_path, "source": f"{cp['instruction']} {src_text} -> {dest}", "confidence": confidence})

    for p in run_path_checks:
        parent = str(PurePosixPath(p).parent)
        if parent != "/":
            candidate_roots.append({"path": parent, "source": f"RUN path check {p}", "confidence": "low"})

    # Deduplicate while keeping best occurrence order.
    seen = set()
    deduped = []
    for item in candidate_roots:
        if item["path"] in seen:
            continue
        seen.add(item["path"])
        deduped.append(item)

    return {
        "dockerfile": path,
        "env": env,
        "workdirs": workdirs,
        "copy_add": copies,
        "run_path_checks": run_path_checks,
        "candidate_image_roots": deduped,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze Dockerfile image paths for Asterfire Kit calibration.")
    ap.add_argument("--dockerfile", required=True, help="Path to Dockerfile")
    ap.add_argument("--json", action="store_true", help="Print JSON only")
    args = ap.parse_args()

    data = analyze_dockerfile(args.dockerfile)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print("# Dockerfile 镜像路径分析")
    print(f"Dockerfile: {data['dockerfile']}")
    print("\n## ENV")
    for k, v in data["env"].items():
        print(f"- {k}={v}")
    print("\n## WORKDIR")
    for wd in data["workdirs"]:
        print(f"- {wd}")
    print("\n## COPY / ADD")
    for cp in data["copy_add"]:
        print(f"- {cp['instruction']} {cp['sources']} -> {cp['destination']}")
    print("\n## 候选镜像内资源根目录")
    for item in data["candidate_image_roots"]:
        print(f"- {item['path']}  ({item['confidence']}, {item['source']})")


if __name__ == "__main__":
    main()
