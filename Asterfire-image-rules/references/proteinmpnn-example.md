# ProteinMPNN 路径校准示例

优先目录说明示例：

```text
/
├── opt/
│   └── ProteinMPNN/    # COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
└── workspace/          # Asterfire 运行时目录
```

没有目录说明时，再参考 Dockerfile：

```dockerfile
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
ENV PYTHONPATH=/opt/ProteinMPNN:/app
```

主入口中原逻辑：

```python
mpnn_dir = cwd / "ProteinMPNN-main"
if not mpnn_dir.is_dir():
    mpnn_dir = cwd
```

问题：Asterfire 运行时 `cwd` 是 workspace，不是镜像里的 `/opt/ProteinMPNN`。平台不会自动把 Dockerfile COPY 的项目目录挂到 workspace。

推荐修复：

```python
mpnn_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
if not mpnn_dir.is_dir():
    raise FileNotFoundError(
        f"镜像内 ProteinMPNN 项目目录不存在: {mpnn_dir}. "
        "请检查镜像目录结构说明、Dockerfile 的 COPY 目标路径或 PROTEINMPNN_HOME 环境变量。"
    )

required_image_files = [
    mpnn_dir / "protein_mpnn_run.py",
    mpnn_dir / "helper_scripts" / "parse_multiple_chains.py",
    mpnn_dir / "helper_scripts" / "assign_fixed_chains.py",
    mpnn_dir / "helper_scripts" / "make_fixed_positions_dict.py",
    mpnn_dir / "helper_scripts" / "make_tied_positions_dict.py",
]
for fp in required_image_files:
    if not fp.exists():
        raise FileNotFoundError(f"镜像内 ProteinMPNN 必要文件不存在: {fp}")
```

保留：

```python
result = execCmd(full_cmd, cwd=str(mpnn_dir), timeout=3600)
```

这样 `python helper_scripts/parse_multiple_chains.py` 和 `python protein_mpnn_run.py` 会在 `/opt/ProteinMPNN` 下执行。
