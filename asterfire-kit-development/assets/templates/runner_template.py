import hashlib
import json
import os
import shutil
import subprocess
import traceback
from pathlib import Path

from adam_community.tool import Tool
from adam_community.tool_types import MDFile, TXTFile, tool_io


STRUCTURE_SUFFIXES = {".pdb", ".cif", ".mmcif", ".sdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp"}


@tool_io(
    outputs={
        "output_file": TXTFile,
        "report": MDFile,
        "run_log": TXTFile,
        "success": bool,
    }
)
class runner(Tool):
    """Asterfire Kit 标准 runner 模板。"""

    DISPLAY_NAME = "Example Kit"
    NETWORK = False
    CPU = 2
    GPU = 0
    SIF = "example-kit:1.0.0"

    def call(self, kwargs):
        args = kwargs["args"]
        cwd = Path.cwd()
        warnings = []

        output_file = cwd / "result.txt"
        report_file = cwd / "report.md"
        run_log = cwd / "run.log"

        print("[调试] incoming args:", json.dumps(args, ensure_ascii=False, default=str))
        print("[调试] 当前工作目录:", str(cwd))
        print("[调试] 使用 SIF:", self.SIF)

        command = []
        returncode = 0
        log_chunks = []

        try:
            input_file = _as_path(args["input_file"])
            print("[调试] 归一化后的输入文件:", str(input_file))

            if not input_file.exists():
                raise FileNotFoundError(f"输入文件不存在: {input_file}")

            # 示例命令：真实 Kit 中应替换为该工具真正需要执行的命令。
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
                    "# 运行日志",
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
            if returncode != 0:
                warnings.append(f"命令返回非零状态码: {returncode}")

            # 所有输出都写入当前工作目录。这里复制一份输入文件，便于报告追踪。
            copied_input = cwd / input_file.name
            if input_file.resolve() != copied_input.resolve():
                shutil.copy2(input_file, copied_input)
                print("[调试] 输入文件已复制到当前工作目录:", str(copied_input))

            file_size = copied_input.stat().st_size
            sha256 = _sha256(copied_input)
            output_file.write_text(
                "\n".join(
                    [
                        "# 示例 Kit 结果",
                        "",
                        f"输入文件: {_rel(copied_input)}",
                        f"文件大小: {file_size} bytes",
                        f"SHA256: {sha256}",
                        f"SIF: {self.SIF}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            print("[调试] 生成 output_file:", str(output_file))
            print("[调试] output_file 是否存在:", output_file.exists())

            run_log.write_text("\n".join(log_chunks) + "\n", encoding="utf-8")
            print("[调试] 生成 run_log:", str(run_log))

            outputs = {"output_file": output_file, "report": report_file, "run_log": run_log}
            _write_report(
                report_file=report_file,
                status="成功" if output_file.exists() and returncode == 0 else "失败",
                args=args,
                method="示例模板会检查输入文件、执行核心命令，并在当前工作目录生成结果文件。真实 Kit 应把这里替换为实际模型、算法或外部程序调用逻辑。",
                outputs=outputs,
                warnings=warnings,
                structure_files=_find_files(cwd, STRUCTURE_SUFFIXES),
                image_files=_find_files(cwd, IMAGE_SUFFIXES),
                followup_suggestions=[
                    "优先查看 report.md 中的结果汇总和可视化区域。",
                    "如需排查运行细节，请下载 run.log；报告正文不会直接展开运行日志。",
                ],
            )
            print("[调试] 生成 report:", str(report_file))
            print("[调试] report 是否存在:", report_file.exists())

            return {
                "output_file": _rel(output_file),
                "report": _rel(report_file),
                "run_log": _rel(run_log),
                "success": bool(output_file.exists() and report_file.exists() and returncode == 0),
            }

        except Exception:
            error_text = traceback.format_exc()
            warnings.append("运行失败，详细错误已写入 run.log。")
            log_chunks.extend(["", "## 异常信息", error_text])
            run_log.write_text("\n".join(log_chunks) + "\n", encoding="utf-8")
            _write_report(
                report_file=report_file,
                status="失败",
                args=args,
                method="任务执行过程中发生错误，主要原因请先查看运行概览和输出文件检查。",
                outputs={"output_file": output_file, "report": report_file, "run_log": run_log},
                warnings=warnings,
                structure_files=_find_files(cwd, STRUCTURE_SUFFIXES),
                image_files=_find_files(cwd, IMAGE_SUFFIXES),
                followup_suggestions=["检查输入文件格式和必填参数是否正确。", "下载 run.log 查看完整错误细节。"],
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


def _sha256(path):
    """计算文件 SHA256，便于报告追踪输入。"""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_files(cwd, suffixes):
    """从当前工作目录收集可在报告中展示的结构或图片文件。"""
    found = []
    for path in sorted(Path(cwd).iterdir()):
        if path.is_file() and path.suffix.lower() in suffixes:
            found.append(path)
    return found


def _write_report(report_file, status, args, method, outputs, warnings, structure_files=None, image_files=None, followup_suggestions=None):
    """生成中文平台运行报告；只展示用户关心的结果，不展开运行日志。"""
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
        f"| 主要输出数量 | {sum(1 for p in outputs.values() if Path(p).exists())} |",
        "",
        "## 方法说明",
        "",
        method,
        "",
        "## 输入参数",
        "",
        "| 参数 | 值 |",
        "| --- | --- |",
    ]
    for key, value in args.items():
        lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## 结果展示与说明", "", "| 输出 | 路径 | 文件是否存在 | 说明 |", "| --- | --- | --- | --- |"])
    for key, value in outputs.items():
        output_path = Path(value)
        note = "主要结果文件" if key not in {"report", "run_log"} else ("运行报告" if key == "report" else "详细日志文件，用于排错")
        lines.append(f"| {key} | `{_rel(output_path)}` | {'是' if output_path.exists() else '否'} | {note} |")

    lines.extend(["", "## 可视化结果", ""])
    if structure_files:
        lines.append("### 结构文件")
        lines.append("")
        lines.append("以下结构文件可在报告中直接交互式查看。")
        lines.append("")
        lines.append("```molstar")
        for path in structure_files:
            lines.append(_rel(path))
        lines.append("```")
        lines.append("")
    if image_files:
        lines.append("### 图片结果")
        lines.append("")
        for path in image_files:
            lines.append(f"![{path.name}]({_rel(path)})")
            lines.append("")
            lines.append(f"图：`{path.name}`，用于直观查看本次运行生成的可视化结果。")
            lines.append("")
    if not structure_files and not image_files:
        lines.append("本次运行未检测到可直接嵌入的结构文件或图片文件。若主要结果是 CSV/JSON/TSV/XVG 等数据，建议在真实 Kit 中用 matplotlib 生成图后嵌入本节。")

    lines.extend(["", "## 如何查看结果", ""])
    lines.append("优先阅读本报告的结果展示与可视化区域；完整结果文件可在输出产物表中下载。详细运行日志保存在 `run.log`，用于排错，不在报告正文中展开。")

    lines.extend(["", "## 后续分析建议", ""])
    if followup_suggestions:
        for item in followup_suggestions:
            lines.append(f"- {item}")
    else:
        lines.append("- 根据主要输出文件继续开展下游分析。")

    lines.extend(["", "## 注意事项", ""])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- 未发现需要特别提醒的问题。")

    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
