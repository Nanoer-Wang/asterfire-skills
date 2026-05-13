#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan an Asterfire Kit runner for path risks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

SCRIPT_RE = re.compile(r"(?:python|python3)\s+([^\s;&|]+\.py)")
WEIGHT_RE = re.compile(r"[\w./${}+-]+\.(?:pt|pth|ckpt|safetensors)")
CWD_RISK_RE = re.compile(r"(?:Path\.cwd\(\)|os\.getcwd\(\)|cwd\s*/\s*['\"][^'\"]+['\"])")
EXEC_CWD_RE = re.compile(r"cwd\s*=\s*([^,)]+)")


def scan_runner(path: str) -> Dict[str, object]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    findings: List[Dict[str, object]] = []

    for i, line in enumerate(lines, 1):
        for m in SCRIPT_RE.finditer(line):
            findings.append({"line": i, "type": "python_script_call", "value": m.group(1), "text": line.strip()})
        for m in WEIGHT_RE.finditer(line):
            findings.append({"line": i, "type": "model_weight_path", "value": m.group(0), "text": line.strip()})
        if CWD_RISK_RE.search(line):
            findings.append({"line": i, "type": "cwd_relative_risk", "value": line.strip(), "text": line.strip()})

    for i, line in enumerate(lines, 1):
        if ("execCmd" in line or "runCmd" in line or "subprocess." in line) and "cwd=" in line:
            m = EXEC_CWD_RE.search(line)
            if m:
                findings.append({"line": i, "type": "exec_cwd", "value": m.group(1).strip(), "text": line.strip()})

    recommendations: List[str] = []
    if any(f["type"] == "cwd_relative_risk" for f in findings):
        recommendations.append("发现 Path.cwd()/cwd 相对路径风险：确认这些路径是否属于运行时工作目录；镜像内置项目不能用 cwd 查找。")
    if any(f["type"] == "python_script_call" for f in findings):
        recommendations.append("发现 python xxx.py 调用：若脚本来自镜像内项目，应设置 execCmd cwd 为镜像项目根目录，或改成绝对脚本路径。")
    if any(f["type"] == "model_weight_path" for f in findings):
        recommendations.append("发现模型权重路径：.pt/.pth/.ckpt 应使用镜像内绝对路径，并在运行前检查存在性。")

    return {"runner": path, "findings": findings, "recommendations": recommendations}


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan Asterfire runner path risks.")
    ap.add_argument("--runner", required=True, help="Path to runner python file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = scan_runner(args.runner)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("# Runner 路径风险扫描")
    print(f"Runner: {data['runner']}")
    print("\n## Findings")
    for f in data["findings"]:
        print(f"- line {f['line']}: [{f['type']}] {f['value']}")
    print("\n## Recommendations")
    for rec in data["recommendations"]:
        print(f"- {rec}")


if __name__ == "__main__":
    main()
