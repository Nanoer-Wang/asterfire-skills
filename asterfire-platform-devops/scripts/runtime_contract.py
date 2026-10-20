from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def runtime_evidence(dockerfile: str | Path) -> dict[str, bool]:
    """所有检查入口共享这一份模式，避免三份启动契约逐渐分叉。"""
    path = Path(dockerfile)
    text = path.read_text(encoding="utf-8", errors="replace")
    normalized = re.sub(r"\\\s*\r?\n", " ", text)

    return {key: bool(re.search(pattern, normalized)) for key, pattern in [
        ('bash_check', r'(?:command\s+-v|which)\s+bash\b'),
        ('python_command_check', r'(?:command\s+-v|which)\s+python\b'),
        ('python_version_check', r'\bpython\s+--version\b'),
        ('adam_community_import_check', r'''\bpython\s+(?:-[^\s]+\s+)*-c\s+["'][^"']*\bimport\s+adam_community\b'''),
    ]}


def inspect_runtime_contract(dockerfile: str | Path) -> list[str]:
    evidence = runtime_evidence(dockerfile)
    checks = [
        (
            "bash 命令自检",
            'bash_check',
            "加入构建期 `command -v bash`。",
        ),
        (
            "python 命令自检",
            'python_command_check',
            "平台使用 `python` 启动 Kit；加入 `command -v python`，不能只检查 python3。",
        ),
        (
            "python 版本自检",
            'python_version_check',
            "加入构建期 `python --version`。",
        ),
        (
            "adam_community 导入自检",
            'adam_community_import_check',
            "安装兼容版本的 adam-community，并加入 `python -c \"import adam_community\"`。",
        ),
    ]
    return [f"缺少{name}：{message}" for name, key, message in checks if not evidence[key]]


def validate_runtime_contract(dockerfile: str | Path) -> None:
    problems = inspect_runtime_contract(dockerfile)
    if problems:
        formatted = "\n".join(f"- {item}" for item in problems)
        raise RuntimeError(
            "Dockerfile 未声明完整的 Asterfire Kit 运行时契约，停止镜像发布：\n"
            f"{formatted}\n"
            "构建成功不代表平台能启动 runner；修复后再创建云效流水线或登记镜像。"
        )


def scan_runtime_contract(dockerfile: str | Path) -> dict[str, object]:
    path = Path(dockerfile)
    warnings = []
    if re.search(r'\bconda\s+activate\b', path.read_text(encoding='utf-8', errors='replace')):
        warnings.append('检测到 conda activate；确认最终依赖环境已通过 ENV PATH 固化，平台入口不能只依赖激活。')
    problems = inspect_runtime_contract(path)
    return {'dockerfile': str(path), 'passed': not problems, 'evidence': runtime_evidence(path),
            'risks': problems, 'warnings': warnings}


def main():
    parser = argparse.ArgumentParser(description='统一的 Asterfire 镜像启动契约检查')
    parser.add_argument('dockerfile', nargs='?', default='Dockerfile')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = scan_runtime_contract(args.dockerfile)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('[OK] 运行时契约声明通过。' if result['passed'] else '[FAIL] 缺少运行时契约声明。')
        for message in result['risks'] + result['warnings']:
            print('- ' + message)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
