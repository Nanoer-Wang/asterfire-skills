---
name: asterfire-dockerfile-builder
version: 1.0.0
description: 为 Asterfire 平台 Kit 开发生成符合平台运行逻辑和用户项目需求的 Dockerfile、docker build / tag / push 命令，以及镜像内文件目录结构说明。凡用户需要把本地项目、模型权重、脚本、requirements/environment.yml 固化进镜像，或需要解释 /app、/opt、/workspace 路径关系、阿里云镜像仓库上传流程、SIF 与镜像版本命名规则，都使用本 Skill。
---

# Asterfire Kit Dockerfile 构建 Skill

本 Skill 用于帮助开发者为 Asterfire 平台 Kit 编写 Dockerfile，并配套输出：

1. 符合 Asterfire Kit 运行逻辑的 Dockerfile。
2. `docker build` 构建命令。
3. `docker images` 查看镜像命令。
4. 阿里云镜像仓库 `docker login`、`docker tag`、`docker push` 命令模板。
5. 镜像内文件目录结构说明，方便后续 Kit 主函数使用镜像内绝对路径。
6. Asterfire Kit 主入口代码中 `SIF = "name:version"` 与镜像版本的对应建议。

## 必须理解的平台运行模型

Asterfire 平台运行 Kit 时，应区分两类路径：

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用文件、配置、轻量脚本
│   ├── requirements.txt
│   └── ...
├── opt/                  # 镜像构建时固化的第三方项目、大模型、权重、数据库
│   └── ProteinMPNN/
│       ├── protein_mpnn_run.py
│       ├── helper_scripts/
│       └── vanilla_model_weights/
├── workspace/            # 平台运行时挂载的工作目录，PWD 通常在这里
│   ├── runner.py         # 平台投递执行的 Kit 主入口
│   ├── 用户上传文件
│   ├── 中间文件
│   ├── 输出文件
│   └── report.md
└── ...
```

规则：

- Dockerfile `COPY` 进镜像的项目、权重、数据库，推荐放入 `/opt/<ProjectName>`，并在主函数中用绝对路径读取。
- 轻量配置、requirements、平台辅助脚本，推荐放入 `/app`。
- 用户上传文件、运行中间文件、输出文件、报告、zip，一律写到运行时 `Path.cwd()` 或其子目录，也就是 `/workspace`。
- Kit 主函数不要假设镜像内项目会出现在 `/workspace`。
- 需要运行镜像内项目脚本时，优先使用 `execCmd(..., cwd="/opt/<ProjectName>")`，或使用绝对脚本路径。

## 什么时候使用本 Skill

用户提出以下任一需求时，使用本 Skill：

- “帮我写 Dockerfile”。
- “我有一个项目/权重/pt 文件，要打包到 Asterfire Kit 镜像里”。
- “给出 docker build 命令”。
- “给出阿里云镜像仓库 login/tag/push 命令”。
- “解释镜像里的文件路径结构，方便 runner.py 调用”。
- “根据已有 Dockerfile 和项目目录生成 Asterfire Kit Dockerfile”。
- “ProteinMPNN / RFdiffusion / RoseTTAFold / Boltz / GROMACS / ORCA 这类工具要固化进镜像”。

## 开始前必须收集的信息

如果用户没有给全，可以先基于默认值生成，并在输出中明确标注需要用户替换的字段。

| 信息 | 必填 | 默认/建议 |
|---|---:|---|
| Kit 名称 | 是 | 例如 `proteinmpnn` |
| 镜像名称 | 是 | 例如 `proteinmpnn-1` |
| 镜像版本 | 是 | 例如 `1.0.0` |
| 基础镜像 | 否 | `registry.cn-hangzhou.aliyuncs.com/sidereus-ai/python:3.12.12-slim` |
| 依赖安装方式 | 是 | `pip` 或 `conda` |
| 本地项目目录 | 否 | 例如 `ProteinMPNN/ProteinMPNN-main` |
| 镜像内项目目录 | 否 | 推荐 `/opt/<ProjectName>` |
| 权重文件/模型文件 | 否 | 例如 `/opt/ProteinMPNN/vanilla_model_weights/*.pt` |
| requirements.txt | 否 | `/app/requirements.txt` |
| environment.yml | 否 | `/app/environment.yml` |
| 阿里云仓库地址 | 否 | 用户自己的 ACR 地址，不能写死 |
| 命名空间/仓库名 | 否 | 例如 `mlfold/proteinmpnn-1` |

## Dockerfile 生成原则

### 1. 基础镜像

优先使用平台推荐基础镜像：

```dockerfile
FROM registry.cn-hangzhou.aliyuncs.com/sidereus-ai/python:3.12.12-slim
```

如果用户项目需要 CUDA、GROMACS、PyTorch GPU、Conda、系统库，应根据用户给出的已有 Dockerfile 或项目需求改为合适基础镜像。

### 2. 环境变量

必须显式设置常用路径：

```dockerfile
ENV PATH=/app/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH
```

如果固化第三方项目，例如 ProteinMPNN：

```dockerfile
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
ENV PYTHONPATH=/opt/ProteinMPNN:/app:$PYTHONPATH
```

### 3. 依赖安装

pip 方式：

```dockerfile
COPY requirements.txt /app/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && pip3 install --no-cache-dir -r /app/requirements.txt \
    && rm -rf /var/lib/apt/lists/*
```

Conda 方式：

```dockerfile
ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH
COPY Miniconda3-latest-Linux-x86_64.sh /tmp/miniconda.sh
RUN bash /tmp/miniconda.sh -b -p $CONDA_DIR \
    && rm /tmp/miniconda.sh \
    && conda clean -afy
COPY environment.yml /app/environment.yml
RUN conda env create -f /app/environment.yml \
    && conda clean -afy
ENV PATH=/opt/conda/envs/<env_name>/bin:$PATH
```

Conda 环境名必须与 `environment.yml` 中的 `name:` 一致。

### 4. COPY 规则

- `COPY requirements.txt /app/requirements.txt`
- `COPY environment.yml /app/environment.yml`
- `COPY local_file.txt /app/local_file.txt`
- `COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN`
- `COPY weights/rf3_latest.pt /app/modelforge/rf3_latest.pt`

大项目和模型权重优先放 `/opt/<ProjectName>` 或 `/app/<model_dir>`，并在 Dockerfile 里写清楚环境变量。

### 5. WORKDIR 和 CMD

Asterfire Kit 镜像通常写：

```dockerfile
WORKDIR /app
CMD ["bash"]
```

`WORKDIR /app` 只是镜像默认目录。平台运行时主函数通常仍在 `/workspace` 执行，所以 runner 不能把 `Path.cwd()` 当成镜像内项目目录。

### 6. 构建期自检

Dockerfile 中应加入轻量自检，提前暴露路径错误：

```dockerfile
RUN python --version \
    && which python \
    && ls -lah /opt/ProteinMPNN \
    && test -f /opt/ProteinMPNN/protein_mpnn_run.py
```

如果有权重：

```dockerfile
RUN test -f /app/modelforge/rf3_latest.pt
```

### 7. LABEL 元数据

必须给出清晰的作者、版本、描述：

```dockerfile
LABEL Author="Your Name" \
      Version="1.0.0" \
      Description="Asterfire Kit image for ProteinMPNN"
```

## 输出 Dockerfile 的标准结构

回答用户时，推荐按以下顺序输出：

1. “下面是推荐 Dockerfile”。
2. Dockerfile 代码块。
3. “构建命令”。
4. “查看镜像命令”。
5. “Smoke Test 验证命令”（验证镜像可用后再推送）。
6. “登录阿里云镜像仓库命令”。
7. “标记镜像命令”。
8. “上传镜像命令”。
9. “镜像内目录结构说明”。
10. “Kit 主函数中路径使用建议”。

## 标准构建与上传命令模板

### 构建镜像

```bash
docker build -t <local_image_name>:<image_version> .
```

例如：

```bash
docker build -t proteinmpnn-1:1.0.0 .
```

### 查看镜像名称和 ID

```bash
docker images
```

### 登录阿里云镜像仓库

以下命令只是示例，实际使用时必须替换成用户自己阿里云平台账号中的镜像网络地址和用户名：

```bash
docker login --username=xxxxxxxxxxx crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com
```

### 标记镜像

可以用镜像 ID：

```bash
docker tag [images id] crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:[镜像版本]
```

也可以用本地镜像名：

```bash
docker tag proteinmpnn-1:1.0.0 crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:1.0.0
```

### 上传镜像

```bash
docker push crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:[镜像版本]
```

例如：

```bash
docker push crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:1.0.0
```

## SIF 与镜像版本对应

Asterfire Kit 主入口中一般需要指定：

```python
class runner(Tool):
    DISPLAY_NAME = "ProteinMPNN蛋白质序列设计"
    NETWORK = False
    CPU = 4
    GPU = 1
    SIF = "proteinmpnn-1:1.0.0"
```

`SIF` 的命名应与平台镜像登记名称和版本保持一致。不要在主函数里写一个版本，Dockerfile/镜像仓库里又使用另一个版本。

## ProteinMPNN 类项目的推荐 Dockerfile 模板

当用户需要把 ProteinMPNN 固化进镜像时，可以参考：

```dockerfile
FROM registry.cn-hangzhou.aliyuncs.com/sidereus-ai/python:3.12.12-slim

ENV PATH=/app/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates git \
    && pip3 install --no-cache-dir -r /app/requirements.txt \
    && rm -rf /var/lib/apt/lists/*

COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN

ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
ENV PYTHONPATH=/opt/ProteinMPNN:/app:$PYTHONPATH

RUN python --version \
    && which python \
    && ls -lah /opt/ProteinMPNN \
    && test -f /opt/ProteinMPNN/protein_mpnn_run.py \
    && test -d /opt/ProteinMPNN/helper_scripts

WORKDIR /app
CMD ["bash"]

LABEL Author="Your Name" \
      Version="1.0.0" \
      Description="Asterfire Kit image with local ProteinMPNN project"
```

主函数里应使用：

```python
from pathlib import Path
import os

mpnn_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
```

运行脚本时：

```python
result = execCmd(full_cmd, cwd=str(mpnn_dir), timeout=3600)
```

不要写成：

```python
mpnn_dir = Path.cwd() / "ProteinMPNN-main"
```

因为 `Path.cwd()` 在平台运行时通常是 `/workspace`。

## 镜像 Smoke Test 验证规范

Dockerfile 构建完成后，**必须先通过 Smoke Test 验证镜像可用性，再推送到阿里云镜像仓库**。Smoke Test 以 `docker run` 命令的形式执行，目的是在本地验证镜像没有问题。

### Smoke Test 必须覆盖的两个层次

#### 1. 模块/依赖验证

验证镜像内所有关键依赖、工具和路径都正确安装：

```bash
# 验证 Python 和关键包可以正常导入
docker run --rm <image_name>:<version> python -c "
import sys; print('Python:', sys.version)
import numpy; print('numpy:', numpy.__version__)
import torch; print('torch:', torch.__version__)
# ... 根据项目实际依赖添加
"

# 验证命令行工具存在且可执行
docker run --rm <image_name>:<version> bash -c "
which gmx && gmx --version
which python && python --version
# ... 根据项目实际工具添加
"

# 验证固化文件和权重存在
docker run --rm <image_name>:<version> bash -c "
test -f /opt/ProteinMPNN/protein_mpnn_run.py && echo 'OK: protein_mpnn_run.py exists'
test -d /opt/ProteinMPNN/vanilla_model_weights && echo 'OK: weights dir exists'
ls -lh /opt/ProteinMPNN/vanilla_model_weights/
"
```

#### 2. 端到端基础案例验证

验证镜像能端到端跑通一个最小的真实任务。案例设计原则：

- **优先参考官方仓库提供的基础测试命令**。例如开发 BindCraft Kit 时，BindCraft 官方 GitHub 提供了一个专门的基础实验 shell 命令，应直接使用该命令作为 Smoke Test 案例。
- 如果官方没有提供测试命令，或官方测试过于耗时，可以**自行设计一个最小案例**，但必须能覆盖核心计算流程（输入 → 计算 → 输出文件生成）。
- 案例应尽量轻量、快速完成（建议 5 分钟内），不要使用大型生产数据。
- 必须验证输出文件确实生成。

```bash
# 端到端测试示例（以 ProteinMPNN 为例）
# 挂载测试输入文件，运行核心计算，检查输出
docker run --rm \
  -v $(pwd)/test_inputs:/workspace \
  -w /workspace \
  <image_name>:<version> \
  bash -c "
    python /opt/ProteinMPNN/protein_mpnn_run.py \
      --pdb_path /workspace/test.pdb \
      --out_folder /workspace/output \
      --num_seq_per_target 2 \
      --sampling_temp 0.1 \
      --batch_size 1 \
    && test -d /workspace/output \
    && echo 'SMOKE TEST PASSED: output generated' \
    || echo 'SMOKE TEST FAILED'
  "
```

```bash
# 端到端测试示例（以 GROMACS 为例）
# 参考 GROMACS 官方提供的基础测试
docker run --rm \
  -v $(pwd)/test_inputs:/workspace \
  -w /workspace \
  <image_name>:<version> \
  bash -c "
    gmx pdb2gmx -f test.pdb -o processed.gro -water spce -ff amber99sb-ildn -ignh \
    && test -f /workspace/processed.gro \
    && echo 'SMOKE TEST PASSED' \
    || echo 'SMOKE TEST FAILED'
  "
```

### Smoke Test 设计确认流程

在为用户生成 Dockerfile 和构建命令时，如果需要生成 Smoke Test：

1. **先询问用户**是否有官方推荐的测试命令或现成的测试数据。
2. **提供默认方案**：基于项目类型和镜像内容，推荐模块验证命令 + 一个最小端到端案例。
3. 如果用户不答复或明确同意，按默认方案生成 Smoke Test 命令。
4. 如果用户提供了官方测试命令或自定义需求，按用户方案生成。

### Smoke Test 在工作流中的位置

标准流程：`docker build` → **Smoke Test** → `docker tag` → `docker push`

只有 Smoke Test 全部通过后，才应执行 `docker tag` 和 `docker push` 上传镜像。如果 Smoke Test 失败，必须排查问题、修改 Dockerfile、重新构建并再次测试。

## 镜像目录结构说明必须包含

每次输出 Dockerfile 时，最后应给开发者一段目录结构说明，例如：

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用工作目录
│   ├── requirements.txt  # 构建期安装 Python 依赖使用
│   └── ...
├── opt/
│   └── ProteinMPNN/      # COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
│       ├── protein_mpnn_run.py
│       ├── helper_scripts/
│       └── vanilla_model_weights/
├── workspace/            # Asterfire 运行时挂载，runner.py 实际在这里执行
│   ├── runner.py
│   ├── 用户上传输入文件
│   ├── 中间文件
│   ├── 输出文件
│   └── report.md
└── ...
```

并解释：

- `/opt/ProteinMPNN` 是镜像内固定路径，Kit 主函数用它找程序和权重。
- `/workspace` 是运行时路径，只能假定用户输入和输出在这里。
- `/app` 适合放 requirements、轻量脚本、配置文件，不建议把运行输出写到 `/app`。

## 常见错误与修正

### 错误 1：把镜像内项目当成工作目录下的文件

错误：

```python
mpnn_dir = Path.cwd() / "ProteinMPNN-main"
```

修正：

```python
mpnn_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
```

### 错误 2：Dockerfile COPY 目标路径是相对路径

不推荐：

```dockerfile
COPY ProteinMPNN-main ProteinMPNN-main
```

推荐：

```dockerfile
COPY ProteinMPNN-main /opt/ProteinMPNN
```

### 错误 3：构建成功但运行时报找不到模型权重

在 Dockerfile 加自检：

```dockerfile
RUN test -f /app/modelforge/rf3_latest.pt
```

在 runner 中用绝对路径：

```python
ckpt_path = "/app/modelforge/rf3_latest.pt"
```

### 错误 4：忘记清理 apt 缓存导致镜像过大

推荐：

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends <packages> \
    && rm -rf /var/lib/apt/lists/*
```

### 错误 5：Dockerfile 版本、镜像仓库版本、SIF 版本不一致

必须统一：

```dockerfile
LABEL Version="1.0.0"
```

```bash
docker build -t proteinmpnn-1:1.0.0 .
docker push <registry>/mlfold/proteinmpnn-1:1.0.0
```

```python
SIF = "proteinmpnn-1:1.0.0"
```

## 使用脚本

本 Skill 附带 `scripts/generate_dockerfile.py`，可根据 JSON 配置生成 Dockerfile、构建命令、目录说明：

```bash
python scripts/generate_dockerfile.py \
  --config assets/examples/proteinmpnn_config.json \
  --out Dockerfile \
  --commands build_and_push.md \
  --layout image_layout.md
```

也可直接让 AI 根据用户描述手写 Dockerfile。脚本只是辅助，不是强制。
