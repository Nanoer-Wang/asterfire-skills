# ProteinMPNN.py 最小路径修复示例

把：

```python
mpnn_dir = cwd / "ProteinMPNN-main"
if not mpnn_dir.is_dir():
    mpnn_dir = cwd
```

改成：

```python
mpnn_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
if not mpnn_dir.is_dir():
    raise FileNotFoundError(
        f"镜像内 ProteinMPNN 项目目录不存在: {mpnn_dir}. "
        "请检查 Dockerfile 的 COPY 目标路径或 PROTEINMPNN_HOME 环境变量。"
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
