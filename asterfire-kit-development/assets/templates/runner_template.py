import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from adam_community.tool import Tool
from adam_community.tool_types import MDFile, TXTFile, tool_io


@tool_io(
    outputs={
        "output_file": TXTFile,
        "report": MDFile,
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

        print("[调试] incoming args:", json.dumps(args, ensure_ascii=False, default=str))
        print("[调试] 当前工作目录:", str(cwd))
        print("[调试] 使用 SIF:", self.SIF)

        input_file = _as_path(args["input_file"])
        print("[调试] 归一化后的输入文件:", str(input_file))

        if not input_file.exists():
            warnings.append(f"输入文件不存在: {input_file}")
            _write_report(
                report_file=report_file,
                status="失败",
                args=args,
                outputs={"output_file": output_file, "report": report_file},
                warnings=warnings,
            )
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
        print("[调试] stdout:", completed.stdout)
        print("[调试] stderr:", completed.stderr)
        if completed.returncode != 0:
            warnings.append(f"命令返回非零状态码: {completed.returncode}")

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

        _write_report(
            report_file=report_file,
            status="成功" if output_file.exists() else "失败",
            args=args,
            outputs={"output_file": output_file, "report": report_file},
            warnings=warnings,
        )
        print("[调试] 生成 report:", str(report_file))
        print("[调试] report 是否存在:", report_file.exists())

        return {
            "output_file": _rel(output_file),
            "report": _rel(report_file),
            "success": bool(output_file.exists() and report_file.exists()),
        }


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


def _sha256(path):
    """计算文件 SHA256，便于报告追踪输入。"""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_report(report_file, status, args, outputs, warnings):
    """生成中文平台运行报告。"""
    lines = [
        "# 运行报告",
        "",
        "## 运行状态",
        "",
        status,
        "",
        "## 输入参数",
        "",
        "| 参数 | 值 |",
        "| --- | --- |",
    ]
    for key, value in args.items():
        lines.append(f"| {key} | `{value}` |")

    lines.extend(
        [
            "",
            "## 输出产物",
            "",
            "| 输出 | 路径 | 文件是否存在 |",
            "| --- | --- | --- |",
        ]
    )
    for key, value in outputs.items():
        output_path = Path(value)
        lines.append(f"| {key} | `{_rel(output_path)}` | {'是' if output_path.exists() else '否'} |")

    lines.extend(["", "## 警告和假设", ""])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- 无")

    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
