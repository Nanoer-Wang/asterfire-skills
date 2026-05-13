---
name: asterfire-image-path-calibrator
description: 校准 Asterfire 平台 Kit 主入口代码中对镜像内置项目、权重、脚本和资源文件的路径引用。优先读取 Asterfire-dockerfile-builder 生成的镜像目录结构说明；若没有目录说明，再解析 Dockerfile 中 COPY/ENV/WORKDIR 固化到镜像里的目录。凡涉及运行时 workspace 与镜像绝对路径区分、.pt/.pth/.ckpt 权重路径、helper_scripts/protein_mpnn_run.py 等镜像内程序路径匹配、将本地项目路径映射为容器内绝对路径，都使用本 Skill。
---

# Asterfire 镜像内资源路径校准 Skill

本 Skill 用于解决 Asterfire Kit 运行时的典型路径问题：平台把 `runner.py` 和用户上传文件放在运行时工作目录，例如 `/workspace`；但 Dockerfile 构建进镜像的代码、模型权重、脚本、数据库等资源不在 `/workspace`，必须使用镜像内绝对路径，例如 `/opt/ProteinMPNN`、`/app/modelforge/rf3_latest.pt`。

## 适用场景

用户给出以下任意信息时使用本 Skill：

- `Asterfire-dockerfile-builder` 生成的镜像目录结构说明，例如 `image_layout.md`、`镜像目录结构说明.md`、`project_tree_*.txt`。
- 一个 Dockerfile，里面通过 `COPY` / `ADD` 把项目、权重或资源固化进镜像。
- 一个 Asterfire Kit 主入口，例如 `ProteinMPNN.py`、`rf3.py`、`runner.py`。
- 用户明确说：代码里 `.pt`、`.py`、`helper_scripts`、模型目录、项目目录需要从镜像路径读取。
- 用户希望优先根据镜像目录结构说明自动确定镜像内路径；如果没有目录说明，再从 Dockerfile 自动推断；仍推断不了时，再让用户指定。
- 用户希望根据本地项目目录结构，拼出容器内绝对路径。

## 核心原则

### 1. 严格区分 workspace 和 image resource

Asterfire 运行时通常类似：

```text
/
├── app/ 或 opt/              # 镜像构建时固化的代码、权重、数据库
│   └── ...
└── workspace/                # 平台运行时挂载的工作目录，PWD 通常在这里
    ├── runner.py             # 平台执行入口
    ├── 用户上传文件
    ├── 中间文件
    └── 输出文件
```

规则：

- 用户上传文件、中间文件、输出文件、报告、zip：写到 `Path.cwd()` 或其子目录。
- Dockerfile 里 `COPY` 到镜像的代码、权重、数据库：用镜像内绝对路径读取。
- 不要假设镜像内项目会出现在 `Path.cwd()`。
- 不要把输出写进 `/opt/...` 或 `/app/...` 这类镜像只读/构建目录。
- 不要在 Asterfire Kit 主函数中依赖 `cd` 到本地项目目录；应显式设置 `execCmd(..., cwd=str(镜像内项目根目录))` 或使用绝对脚本路径。

### 2. 路径来源优先级：先目录说明，再 Dockerfile

本 Skill 与 `Asterfire-dockerfile-builder` 配套使用时，必须优先读取它生成的镜像目录结构说明。常见文件名包括：

```text
image_layout.md
镜像目录结构说明.md
project_tree_*.txt
```

目录说明通常包含：

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用工作目录
├── opt/                  # 镜像构建时固化的大项目、权重、数据库
│   └── ProteinMPNN/      # COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
├── workspace/            # Asterfire 运行时挂载目录，runner.py 实际在这里执行
└── ...
```

若目录说明中已经明确了 `COPY 源路径 -> 镜像目标路径`、`/opt/<ProjectName>`、`/app/<ProjectName>`、`XXX_HOME=/absolute/path`，则以该目录说明作为最高优先级路径来源。这样可以避免 Dockerfile 经过人工修改、重命名或多阶段构建后，AI 只看某一段 Dockerfile 造成误判。

完整路径确定优先级：

1. 用户显式指定的镜像路径，例如 `/opt/ProteinMPNN`。
2. `Asterfire-dockerfile-builder` 生成的镜像目录结构说明。
3. Dockerfile 中的 `ENV XXX_HOME=/absolute/path`、`ENV XXX_ROOT=/absolute/path`、`ENV XXX_DIR=/absolute/path`。
4. Dockerfile 中的 `COPY local_project /absolute/path` 或 `ADD local_project /absolute/path`。
5. Dockerfile 中 `RUN ls ... && test -f ...` 出现的绝对路径，仅作为校验线索。
6. Dockerfile 中 `WORKDIR /absolute/path`，只作为次级线索，不能单独证明项目根目录。

如果目录说明与 Dockerfile 推断结果冲突，默认采用目录说明，同时在回复中明确提示冲突，让用户确认是否需要同步修改 Dockerfile 或目录说明。

### 3. 没有目录说明时，再从 Dockerfile 推断镜像路径

读取 Dockerfile，重点解析：

```dockerfile
WORKDIR /app
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
ENV PYTHONPATH=/opt/ProteinMPNN:/app
```

如果 Dockerfile 显示：

```dockerfile
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
```

那么 Kit 主入口中 ProteinMPNN 项目根目录应写为：

```python
mpnn_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
```

并且不能继续使用：

```python
mpnn_dir = cwd / "ProteinMPNN-main"
if not mpnn_dir.is_dir():
    mpnn_dir = cwd
```

这会把运行时工作目录误当成镜像内项目目录。

### 4. 目录说明和 Dockerfile 都解析不到时，不要猜

如果既没有 `Asterfire-dockerfile-builder` 生成的目录说明，Dockerfile 也没有暴露目标路径，必须让用户补充：

```text
我没有在镜像目录结构说明或 Dockerfile 中找到项目/权重被 COPY 到镜像内的绝对路径。请你指定镜像内路径，例如：
- ProteinMPNN 项目根目录：/opt/ProteinMPNN
- 权重文件目录：/opt/ProteinMPNN/vanilla_model_weights
- 主运行脚本：/opt/ProteinMPNN/protein_mpnn_run.py

指定后我再校准主函数代码。
```

只有当用户提供了明确路径，或目录说明/Dockerfile 能明确推断，才能改代码。

### 5. 本地目录结构只能用于映射相对路径

用户可能本地有：

```text
ProteinMPNN/ProteinMPNN-main/
├── protein_mpnn_run.py
├── helper_scripts/
│   ├── parse_multiple_chains.py
│   └── assign_fixed_chains.py
└── vanilla_model_weights/
    └── v_48_020.pt
```

Dockerfile 有：

```dockerfile
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
```

则可映射：

```text
本地 ProteinMPNN/ProteinMPNN-main/protein_mpnn_run.py
=> 镜像 /opt/ProteinMPNN/protein_mpnn_run.py
```

但必须满足：本地目录就是 Dockerfile `COPY` 的源目录；不能把任意本地路径强行拼到镜像路径下。

### 6. `.pt` / `.pth` / `.ckpt` 权重路径处理

遇到模型权重时按以下顺序处理：

1. 如果程序本身支持 `--model_name` 并在项目根目录下自动找权重，只需确保 `cwd` 是镜像内项目根目录。
2. 如果主函数直接传 `ckpt_path`、`model_path`、`weights`，必须传镜像内绝对路径，例如：

```python
ckpt_path = Path("/app/modelforge/rf3_latest.pt")
runCmd(f"rf3 fold inputs={json_path} ckpt_path={shlex.quote(str(ckpt_path))}")
```

3. 如果权重目录来自 Dockerfile 的 `ENV MODEL_HOME=/...`，优先使用环境变量加默认值：

```python
model_home = Path(os.environ.get("MODEL_HOME", "/app/modelforge"))
ckpt_path = model_home / "rf3_latest.pt"
```

4. 必须在运行前检查关键权重是否存在；不存在时抛出清晰错误。

### 6. 命令构造推荐写法

推荐写法 A：设置 `cwd` 到镜像内项目根目录，命令内部使用项目相对路径。

```python
image_project_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
if not image_project_dir.is_dir():
    raise FileNotFoundError(f"镜像内 ProteinMPNN 项目目录不存在: {image_project_dir}")

required_files = [
    image_project_dir / "protein_mpnn_run.py",
    image_project_dir / "helper_scripts" / "parse_multiple_chains.py",
]
for fp in required_files:
    if not fp.exists():
        raise FileNotFoundError(f"镜像内必要文件不存在: {fp}")

full_cmd = " && ".join(cmd_parts)
result = execCmd(full_cmd, cwd=str(image_project_dir), timeout=3600)
```

推荐写法 B：命令中全部使用绝对路径。

```python
parse_script = image_project_dir / "helper_scripts" / "parse_multiple_chains.py"
run_script = image_project_dir / "protein_mpnn_run.py"

parse_cmd = f"python {shlex.quote(str(parse_script))} --input_path={work_dir} --output_path={parsed_chains}"
run_cmd = f"python {shlex.quote(str(run_script))} --jsonl_path {parsed_chains} --out_folder {output_dir}"
result = execCmd(full_cmd, cwd=str(Path.cwd()), timeout=3600)
```

通常推荐写法 A，因为很多项目内部还会相对读取权重、配置、包文件。

## 修改 Asterfire Kit 主入口的标准流程

### 第一步：优先读取镜像目录结构说明

如果用户同时给了 `Asterfire-dockerfile-builder` 生成的目录说明和 Dockerfile，先读目录说明。必须提取：

- `/opt/<ProjectName>`、`/app/<ProjectName>` 这类镜像固定目录。
- `# COPY local/path /absolute/path` 注释中的源路径和镜像目标路径。
- `XXX_HOME=/absolute/path`、`XXX_ROOT=/absolute/path`、`XXX_DIR=/absolute/path`。
- `/workspace` 的含义：运行时挂载目录，只能放输入、输出和中间文件。

### 第二步：没有目录说明时读取 Dockerfile

必须提取：

- `COPY` / `ADD` 源路径和目标路径。
- `ENV` 中的 `*_HOME`、`*_ROOT`、`*_DIR`、`PYTHONPATH`。
- `WORKDIR`。
- `RUN test -f`、`RUN ls` 中的路径校验线索。

### 第三步：读取 Kit 主入口代码

重点查找：

- `Path.cwd()`、`cwd / "项目名"`、`os.getcwd()`。
- `python xxx.py`、`python helper_scripts/xxx.py`、`runCmd(...)`、`execCmd(...)`。
- `.pt`、`.pth`、`.ckpt`、`.json`、`.yaml` 等资源文件。
- `cwd=str(...)` 是否指向了工作目录而不是镜像项目目录。
- 是否错误地尝试 `conda activate`。Asterfire 已通过 SIF 固化环境时通常不需要激活 conda。

### 第四步：建立路径映射表

输出或在修改前形成类似表格：

| 资源 | 当前代码中的路径 | 目录说明/Dockerfile/用户确认的镜像路径 | 处理方式 |
|---|---|---|---|
| ProteinMPNN 项目根目录 | `cwd / "ProteinMPNN-main"` | `/opt/ProteinMPNN` | 改为 `PROTEINMPNN_HOME` 默认值 |
| 主脚本 | `protein_mpnn_run.py` | `/opt/ProteinMPNN/protein_mpnn_run.py` | `cwd=/opt/ProteinMPNN` 后保持相对路径 |
| helper 脚本 | `helper_scripts/*.py` | `/opt/ProteinMPNN/helper_scripts/*.py` | `cwd=/opt/ProteinMPNN` 后保持相对路径 |
| 输入 PDB | 平台上传路径 | `/workspace/...` | 保持 `Path.cwd()` / 平台上传路径 |
| 输出 zip/report | `Path.cwd()` | `/workspace/...` | 保持写到工作目录 |

### 第五步：修改代码

必须做到：

- 镜像资源根目录使用 `Path(os.environ.get("XXX_HOME", "/absolute/default"))`。
- 对关键镜像资源做存在性检查。
- `execCmd` / `subprocess.run` 的 `cwd` 与命令路径一致。
- 输出路径返回相对路径，符合 Asterfire 平台链式传递规则。
- 保留 `kwargs["args"]` 读取方式。
- 保留 `return dict`，且返回 key 与 `@tool_io(outputs)` 一致。
- `class runner(Tool)` 中必须有 `DISPLAY_NAME / NETWORK / CPU / GPU / SIF`。

### 第六步：写报告说明

修改后要告诉用户：

- 优先从镜像目录结构说明识别到了哪个路径；如果没有目录说明，再说明从 Dockerfile 识别到了哪个路径。
- 哪些路径被替换。
- 哪些路径仍需用户确认，例如具体 `.pt` 文件名。
- Asterfire 运行时输入/输出仍在工作目录，不会写入镜像目录。

## ProteinMPNN 专用修复模板

当 Dockerfile 类似：

```dockerfile
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
```

而主函数里有：

```python
mpnn_dir = cwd / "ProteinMPNN-main"
if not mpnn_dir.is_dir():
    mpnn_dir = cwd
```

应改为：

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

随后保留：

```python
result = execCmd(full_cmd, cwd=str(mpnn_dir), timeout=3600)
```

因为 `full_cmd` 里的 `python helper_scripts/...` 和 `python protein_mpnn_run.py` 都会相对于 `/opt/ProteinMPNN` 运行。

## Demo 配置规范

如果本 Skill 被用于改造一个完整 Asterfire Kit，也要同步检查或创建：

```text
demos/
├── demos.json
├── image_layout.md        # 可选：Asterfire-dockerfile-builder 生成的镜像目录结构说明示例
├── sample.csv
├── test_file.txt
└── demo.jpg
```

`demos/demos.json` 必须是数组，每个元素包含：

```json
[
  {
    "name": "Basic Kit Demo",
    "description": "Simple kit execution without files",
    "value": {
      "name": "",
      "age": 18,
      "gender": "male",
      "isStudent": false,
      "interests": ["reading"],
      "avatar": "demo.jpg",
      "address": {
        "province": "北京市",
        "city": "北京市",
        "detail": ""
      }
    }
  }
]
```

要求：

- `name`：Demo 名称。
- `description`：Demo 说明。
- `value`：与 `config/input.json` 的字段 key 对齐。
- Demo 中引用的文件必须放在 `demos/` 目录下，用相对文件名引用，例如 `"avatar": "demo.jpg"`。
- 不要在 `demos.json` 中写本地绝对路径。

## 可用辅助脚本

- `scripts/image_layout_analyzer.py`：优先解析 `Asterfire-dockerfile-builder` 生成的 `image_layout.md` / 镜像目录结构说明，提取镜像内资源根目录。
- `scripts/docker_path_analyzer.py`：在没有目录说明时解析 Dockerfile，提取镜像内路径、环境变量、COPY 映射和疑似项目根目录。
- `scripts/runner_path_scanner.py`：扫描 Asterfire Kit 主入口中的相对路径、脚本路径、权重路径和 `cwd` 风险点。
- `scripts/patch_proteinmpnn_runner.py`：对 ProteinMPNN 类 runner 做保守路径修复，支持 `--layout image_layout.md` 优先读目录说明，也支持 `--dockerfile Dockerfile` 兜底，把 `cwd / "ProteinMPNN-main"` 逻辑替换为镜像内 `PROTEINMPNN_HOME`。
