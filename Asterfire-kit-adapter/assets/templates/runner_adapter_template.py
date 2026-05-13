#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普通项目适配为平台 Kit 的入口模板。

使用方式：
1. 先确认 DISPLAY_NAME / NETWORK / CPU / GPU / SIF。
2. 再把下面的占位符替换为真实项目参数、输出和调用逻辑。
3. 保持 input.json、kwargs['args']、@tool_io(outputs)、return dict 四者同步。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Annotated

from adam_community import FileType
from adam_community.tool import Tool
from adam_community.tool_types import MDFile, TXTFile, tool_io

# 按真实输出扩展文件类型，例如：
# PDBFile = Annotated[str, FileType(".pdb", "PDB 结构文件")]
# ZIPFile = Annotated[str, FileType(".zip", "ZIP 压缩包")]


@tool_io(
    outputs={
        "result_file": TXTFile,
        "report": MDFile,
        "success": bool,
    }
)
class runner(Tool):
    """Asterfire Kit 平台入口。"""

    DISPLAY_NAME = "__DISPLAY_NAME__"  # 生成真实 Kit 前必须替换
    NETWORK = False  # 生成真实 Kit 前按确认配置替换
    CPU = 2  # 生成真实 Kit 前按确认配置替换
    GPU = 0  # 生成真实 Kit 前按确认配置替换
    SIF = "__SIF__"  # 生成真实 Kit 前必须替换为真实 SIF

    def call(self, kwargs):
        args = kwargs["args"]
        cwd = Path.cwd()
        report_path = cwd / "report.md"
        result_path = cwd / "result.txt"
        warnings = []
        command = []
        stdout = ""
        stderr = ""
        returncode = 0

        print("[调试] incoming args:", json.dumps(args, ensure_ascii=False, default=str))
        print("[调试] 当前工作目录:", str(cwd))
        print("[调试] DISPLAY_NAME:", self.DISPLAY_NAME)
        print("[调试] SIF:", self.SIF)
        print("[调试] CPU/GPU/NETWORK:", self.CPU, self.GPU, self.NETWORK)

        try:
            # 示例：读取一个输入文件。请按真实 input.json 字段名修改。
            input_file = _as_path(args["input_file"])
            if not input_file.exists():
                raise FileNotFoundError(f"输入文件不存在: {input_file}")

            local_input = cwd / input_file.name
            if input_file.resolve() != local_input.resolve():
                shutil.copy2(input_file, local_input)
            print("[调试] 输入文件已准备:", str(local_input))

            # 方案 A：调用原项目函数。
            # from utils.project_core import run_project
            # run_project(input_file=str(local_input), output_file=str(result_path), **其他参数)

            # 方案 B：包装原项目命令行。请替换为真实命令。
            command = ["python", "--version"]
            print("[调试] 关键命令:", " ".join(command))
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                text=True,
                capture_output=True,
                check=False,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            returncode = int(completed.returncode)
            print("[调试] stdout:", stdout)
            print("[调试] stderr:", stderr)
            print("[调试] returncode:", returncode)
            if returncode != 0:
                warnings.append(f"命令返回非零状态码: {returncode}")

            result_path.write_text(
                "\n".join([
                    "# Kit 运行结果",
                    "",
                    f"输入文件: {_rel(local_input)}",
                    f"SIF: {self.SIF}",
                    f"命令返回码: {returncode}",
                ]) + "\n",
                encoding="utf-8",
            )

            success = bool(result_path.exists() and returncode == 0)
            _write_report(
                report_path=report_path,
                status="成功" if success else "失败",
                args=args,
                runner_config={
                    "DISPLAY_NAME": self.DISPLAY_NAME,
                    "SIF": self.SIF,
                    "CPU": self.CPU,
                    "GPU": self.GPU,
                    "NETWORK": self.NETWORK,
                },
                command=command,
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
                outputs={"result_file": result_path, "report": report_path},
                warnings=warnings,
            )

            return {
                "result_file": _rel(result_path),
                "report": _rel(report_path),
                "success": success,
            }

        except Exception as exc:
            warnings.append(str(exc))
            stderr = stderr + "\n" + traceback.format_exc()
            _write_report(
                report_path=report_path,
                status="失败",
                args=args,
                runner_config={
                    "DISPLAY_NAME": self.DISPLAY_NAME,
                    "SIF": self.SIF,
                    "CPU": self.CPU,
                    "GPU": self.GPU,
                    "NETWORK": self.NETWORK,
                },
                command=command,
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
                outputs={"result_file": result_path, "report": report_path},
                warnings=warnings,
            )
            print("[错误] 运行失败:", traceback.format_exc())
            raise


def _as_path(value):
    """归一化平台上传文件值，兼容字符串、对象和列表。"""
    if isinstance(value, list):
        if not value:
            raise ValueError("文件列表为空")
        value = value[0]
    if isinstance(value, dict):
        for key in ("path", "file", "url", "value", "name"):
            if value.get(key):
                value = value[key]
                break
    if not isinstance(value, (str, os.PathLike)):
        raise TypeError(f"无法识别的文件路径格式: {type(value).__name__}")
    return Path(value).expanduser()


def _rel(path):
    """返回相对当前工作目录的路径；不在当前目录时返回原路径字符串。"""
    path = Path(path)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _short_text(text, limit=4000):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[内容过长，已截断]"


def _write_report(report_path, status, args, runner_config, command, stdout, stderr, returncode, outputs, warnings):
    """生成中文平台运行报告。"""
    lines = [
        "# 运行报告",
        "",
        "## 运行状态",
        "",
        status,
        "",
        "## Runner 配置",
        "",
        "| 配置 | 值 |",
        "| --- | --- |",
    ]
    for key, value in runner_config.items():
        lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## 输入参数", "", "| 参数 | 值 |", "| --- | --- |"])
    for key, value in args.items():
        lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## 关键命令", ""])
    if command:
        lines.append("```bash")
        lines.append(" ".join(str(x) for x in command))
        lines.append("```")
    else:
        lines.append("未记录命令，可能为函数调用式适配。")
    lines.append(f"\n返回码：`{returncode}`")

    lines.extend(["", "## 标准输出 stdout", "", "```text", _short_text(stdout), "```"])
    lines.extend(["", "## 标准错误 stderr", "", "```text", _short_text(stderr), "```"])

    lines.extend(["", "## 输出产物", "", "| 输出 | 路径 | 文件是否存在 |", "| --- | --- | --- |"])
    for key, value in outputs.items():
        output_path = Path(value)
        lines.append(f"| {key} | `{_rel(output_path)}` | {'是' if output_path.exists() else '否'} |")

    lines.extend(["", "## 警告和假设", ""])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- 无")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
