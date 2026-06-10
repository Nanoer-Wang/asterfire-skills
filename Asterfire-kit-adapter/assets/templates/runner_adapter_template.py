#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普通项目适配为平台 Kit 的入口模板。

使用方式：
1. 先确认 DISPLAY_NAME / NETWORK / CPU / GPU / SIF。
2. 再把下面的占位符替换为真实项目参数、输出和调用逻辑。
3. 保持 input.json、kwargs['args']、@tool_io(outputs)、return dict 四者同步。
4. report.md 展示用户关心的结果、结构和图片；详细命令日志保存为 run.log。
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
# SDFFile = Annotated[str, FileType(".sdf", "SDF 小分子结构文件")]
# ZIPFile = Annotated[str, FileType(".zip", "ZIP 压缩包")]

STRUCTURE_SUFFIXES = {".pdb", ".cif", ".mmcif", ".sdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp"}


@tool_io(
    outputs={
        "result_file": TXTFile,
        "report": MDFile,
        "run_log": TXTFile,
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
        run_log = cwd / "run.log"
        warnings = []
        command = []
        returncode = 0
        log_chunks = [
            "# 运行日志",
            "",
            f"DISPLAY_NAME: {self.DISPLAY_NAME}",
            f"SIF: {self.SIF}",
            f"CPU/GPU/NETWORK: {self.CPU}/{self.GPU}/{self.NETWORK}",
            "",
            "## 输入参数",
            json.dumps(args, ensure_ascii=False, indent=2, default=str),
        ]

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
            returncode = int(completed.returncode)
            log_chunks.extend(
                [
                    "",
                    "## 命令",
                    " ".join(command),
                    "",
                    "## 返回码",
                    str(returncode),
                    "",
                    "## 命令输出",
                    completed.stdout or "",
                    "",
                    "## 错误输出",
                    completed.stderr or "",
                ]
            )
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
            run_log.write_text("\n".join(log_chunks) + "\n", encoding="utf-8")

            success = bool(result_path.exists() and returncode == 0)
            outputs = {"result_file": result_path, "report": report_path, "run_log": run_log}
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
                method="本模板以薄包装方式适配普通项目：平台入口读取输入、准备工作目录、调用原项目函数或命令行入口，然后检查并汇总输出。真实 Kit 应将本段替换为具体方法说明。",
                command=command,
                returncode=returncode,
                outputs=outputs,
                warnings=warnings,
                structure_files=_find_files(cwd, STRUCTURE_SUFFIXES),
                image_files=_find_files(cwd, IMAGE_SUFFIXES),
                followup_suggestions=[
                    "优先查看 report.md 中的结果展示与可视化区域。",
                    "如需排查原项目运行细节，请下载 run.log；报告正文不会直接展开运行日志。",
                ],
            )

            return {
                "result_file": _rel(result_path),
                "report": _rel(report_path),
                "run_log": _rel(run_log),
                "success": success,
            }

        except Exception as exc:
            warnings.append(str(exc))
            log_chunks.extend(["", "## 异常信息", traceback.format_exc()])
            run_log.write_text("\n".join(log_chunks) + "\n", encoding="utf-8")
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
                method="项目适配入口执行失败。请优先检查输入参数、文件格式和原项目依赖环境。",
                command=command,
                returncode=returncode,
                outputs={"result_file": result_path, "report": report_path, "run_log": run_log},
                warnings=warnings,
                structure_files=_find_files(cwd, STRUCTURE_SUFFIXES),
                image_files=_find_files(cwd, IMAGE_SUFFIXES),
                followup_suggestions=["检查输入文件是否符合原项目要求。", "下载 run.log 查看完整错误细节。"],
            )
            print("[错误] 运行失败，详细信息已写入 run.log")
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
        return "./" + path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _find_files(cwd, suffixes):
    """从当前工作目录收集可在报告中展示的结构或图片文件。"""
    found = []
    for path in sorted(Path(cwd).iterdir()):
        if path.is_file() and path.suffix.lower() in suffixes:
            found.append(path)
    return found


def _write_report(report_path, status, args, runner_config, method, command, returncode, outputs, warnings, structure_files=None, image_files=None, followup_suggestions=None):
    """生成中文平台运行报告；只展示结果和解释，不展开运行日志。"""
    structure_files = structure_files or []
    image_files = image_files or []
    followup_suggestions = followup_suggestions or []

    lines = [
        "# 运行报告",
        "",
        "## 运行概览",
        "",
        "| 项目 | 内容 |",
        "| --- | --- |",
        f"| 运行状态 | {status} |",
        f"| Kit 名称 | {runner_config.get('DISPLAY_NAME', '')} |",
        f"| SIF | `{runner_config.get('SIF', '')}` |",
        f"| CPU/GPU/NETWORK | `{runner_config.get('CPU')}/{runner_config.get('GPU')}/{runner_config.get('NETWORK')}` |",
        f"| 返回码 | `{returncode}` |",
        "",
        "## 方法说明",
        "",
        method,
        "",
    ]
    if command:
        lines.extend(["本次调用的核心命令如下：", "", "```bash", " ".join(str(x) for x in command), "```", ""])
    else:
        lines.append("本次可能为函数调用式适配，未记录外部命令。")
        lines.append("")

    lines.extend(["## 输入参数", "", "| 参数 | 值 |", "| --- | --- |"])
    for key, value in args.items():
        lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## 结果展示与说明", "", "| 输出 | 路径 | 文件是否存在 | 说明 |", "| --- | --- | --- | --- |"])
    for key, value in outputs.items():
        output_path = Path(value)
        note = "主要结果文件" if key not in {"report", "run_log"} else ("运行报告" if key == "report" else "详细日志文件，用于排错")
        lines.append(f"| {key} | `{_rel(output_path)}` | {'是' if output_path.exists() else '否'} | {note} |")

    lines.extend(["", "## 可视化结果", ""])
    if structure_files:
        lines.extend(["### 结构文件", "", "以下结构文件可在报告中直接交互式查看。", "", "```molstar"])
        for path in structure_files:
            lines.append(_rel(path))
        lines.extend(["```", ""])
    if image_files:
        lines.extend(["### 图片结果", ""])
        for path in image_files:
            lines.append(f"![{path.name}]({_rel(path)})")
            lines.append("")
            lines.append(f"图：`{path.name}`，用于直观查看本次运行生成的可视化结果。")
            lines.append("")
    if not structure_files and not image_files:
        lines.append("本次运行未检测到可直接嵌入的结构文件或图片文件。若原项目输出 CSV/JSON/TSV/XVG 等数据，建议在真实适配时用 matplotlib 生成图并嵌入本节。")

    lines.extend(["", "## 如何查看结果", ""])
    lines.append("优先查看本报告的结果展示与可视化区域；完整结果文件可在输出产物表中下载。详细运行日志保存在 `run.log`，用于排错，不在报告正文中展开。")

    lines.extend(["", "## 后续分析建议", ""])
    if followup_suggestions:
        for item in followup_suggestions:
            lines.append(f"- {item}")
    else:
        lines.append("- 根据主要输出文件继续开展下游分析。")

    lines.extend(["", "## 注意事项", ""])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- 未发现需要特别提醒的问题。")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
