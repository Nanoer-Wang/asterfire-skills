# Asterfire Runner 路径改写规则

## 保留在 workspace 的路径

- 用户上传文件。
- `result.json`、`report.md`。
- 运行产生的中间目录，例如 `proteinmpnn_work/`、`msa_out_0/`。
- 输出 zip、CSV、CIF、PDB、日志文件。

这些路径通常基于：

```python
cwd = Path.cwd()
work_dir = cwd / "xxx_work"
```

## 改为镜像绝对路径的资源

- Dockerfile 中 COPY 进去的项目代码。
- 预装模型权重：`.pt`、`.pth`、`.ckpt`、`.safetensors`。
- helper 脚本、数据库、固定配置文件。
- 第三方项目目录，例如 `/opt/ProteinMPNN`、`/app/modelforge`。

## 推荐结构

```python
cwd = Path.cwd()
image_project_dir = Path(os.environ.get("PROJECT_HOME", "/opt/project"))
if not image_project_dir.is_dir():
    raise FileNotFoundError(f"镜像内项目目录不存在: {image_project_dir}")

# workspace 输入输出
work_dir = cwd / "work"
output_dir = work_dir / "outputs"

# image project execution
result = execCmd(full_cmd, cwd=str(image_project_dir), timeout=3600)
```

## 命令安全

含空格或用户输入的路径建议用 `shlex.quote`。Asterfire runner 中常见路径来自平台临时目录，虽然通常无空格，但生成通用模板时仍推荐 quote。
