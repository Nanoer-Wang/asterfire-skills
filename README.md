# Asterfire Skills

面向 Asterfire / Galileo / Adam Community Kit 开发流程的 Codex/OpenAI Skills 集合。  
本仓库用于沉淀平台 Kit 开发、普通项目适配、Dockerfile 镜像构建、镜像内路径校准等规范，让开发者可以通过 `npx skills add` 一键安装并在 Codex 中复用这些能力。

## 快速开始

### 1. 查看仓库中已有的 Skills

可以先使用下面的命令查看当前仓库中可用的 Skill 列表：

```bash
npx skills add https://github.com/Nanoer-Wang/asterfire-skills.git --list
```

该命令会克隆仓库并列出其中已经发布的 Skills，适合在安装前确认 Skill 名称是否正确。

### 2. 为 Codex 全局安装 / 配置 Skills

如果希望把本仓库中的 Skills 配置到 Codex 中，可以使用：

```bash
npx skills add https://github.com/Nanoer-Wang/asterfire-skills.git -a codex -g -y
```

参数含义：

- `-a codex`：将 Skill 配置到 Codex 使用的 agent 环境中。
- `-g`：全局安装，方便在不同项目目录中复用。
- `-y`：自动确认安装过程中的提示。

安装完成后，Codex 在处理 Asterfire Kit 开发相关任务时即可自动读取这些 Skills。

---

## 已包含的 Skills

当前仓库包含 4 个核心 Skill。

| Skill 名称 | 用途 | 典型场景 |
|---|---|---|
| `asterfire-kit-development` | Asterfire Kit 标准开发、重构、审查与打包 | 从零开发 Kit、检查 `runner(Tool)`、生成 `input.json`、维护 `SIF`、补充 `demos` |
| `asterfire-project-to-kit-adapter` | 将普通 Python / 命令行项目适配成 Asterfire 平台 Kit | 已有项目接入平台、补写 `class runner(Tool)`、生成平台配置文件 |
| `asterfire-dockerfile-builder` | 为 Asterfire Kit 生成 Dockerfile、镜像构建命令和镜像目录结构说明 | 把项目、依赖、模型权重、数据库打包进平台镜像 |
| `asterfire-image-path-calibrator` | 校准 Kit 代码中镜像内资源路径与运行时工作目录路径 | 修复代码把 `/workspace` 当成镜像内项目目录、找不到 `.pt` 权重或 helper 脚本的问题 |

---

## Skill 说明

### 1. `asterfire-kit-development`

用于规范 Asterfire 平台 Kit 的开发、审查和交付。

核心能力：

- 约束标准 Kit 项目结构。
- 强制 `runner(Tool)` 中指定 `DISPLAY_NAME / NETWORK / CPU / GPU / SIF`。
- 保证所有输入参数通过 `kwargs['args']` 读取。
- 保证 `@tool_io(outputs={...})` 与 `return dict` 输出端口一致。
- 根据平台已支持的表单规则生成最小化 `config/input.json`。
- 维护 `config/configure.json`、`config/long_description.md`、`report.md`、`Makefile` 和 `demos/demos.json`。
- 支持查询和维护 `references/sif_registry.json`。

适合使用的提示词示例：

```text
使用 asterfire-kit-development 帮我从零开发一个 PDB Validator Kit，要求符合平台规范，并生成 config/input.json、configure.json、long_description.md、runner.py、Makefile 和 demos。
```

---

### 2. `asterfire-project-to-kit-adapter`

用于把已有普通项目改造成 Asterfire 平台 Kit。

核心能力：

- 分析已有项目入口、依赖、输入输出和运行方式。
- 在确认 `DISPLAY_NAME / NETWORK / CPU / GPU / SIF` 后生成平台入口。
- 优先采用“薄包装”策略，不粗暴破坏原项目代码。
- 将原始命令行脚本、Python 函数或项目主入口封装进 `runner.call()`。
- 自动同步 `input.json`、`kwargs['args']`、`@tool_io(outputs)` 和 `return dict`。
- 创建或校验 `demos/demos.json`，保证前端可以一键加载 Demo。

适合使用的提示词示例：

```text
使用 asterfire-project-to-kit-adapter 分析这个普通 Python 项目，并把它改造成 Asterfire 平台 Kit。根据已有 SIF 注册表帮我选择合适镜像。
```

---

### 3. `asterfire-dockerfile-builder`

用于为 Asterfire Kit 生成平台镜像构建方案。

核心能力：

- 生成符合平台运行逻辑的 Dockerfile。
- 区分镜像内置路径 `/app`、`/opt` 与平台运行时工作目录 `/workspace`。
- 给出 `docker build`、`docker images`、`docker login`、`docker tag`、`docker push` 命令模板。
- 输出镜像目录结构说明，例如 `image_layout.md`。
- 为 Kit 入口代码中的 `SIF = "name:version"` 提供命名建议。
- 支持把本地项目、模型权重、数据库、第三方工具打包进镜像。

适合使用的提示词示例：

```text
使用 asterfire-dockerfile-builder 帮我把 ProteinMPNN/ProteinMPNN-main 打包进 Asterfire Kit 镜像，项目放到 /opt/ProteinMPNN，并给出 docker build 和 push 命令。
```

---

### 4. `asterfire-image-path-calibrator`

用于修复 Asterfire Kit 中常见的路径混淆问题。

Asterfire 平台运行 Kit 时，用户上传文件、中间文件、输出文件通常位于运行时工作目录，例如 `/workspace`；而 Dockerfile 构建进镜像的代码、模型权重、helper 脚本、数据库等资源位于镜像内部，例如 `/opt/ProteinMPNN` 或 `/app/...`。

该 Skill 的核心能力：

- 优先读取 `asterfire-dockerfile-builder` 生成的 `image_layout.md` 或镜像目录结构说明。
- 如果没有目录说明，再解析 Dockerfile 中的 `COPY / ADD / ENV / WORKDIR`。
- 扫描 `runner.py`、`ProteinMPNN.py` 等入口代码中的路径风险。
- 修复把 `Path.cwd()` 错当成镜像内项目目录的问题。
- 将模型权重、helper 脚本和内置项目路径改为明确的镜像绝对路径或环境变量路径。
- 保证输出文件仍然写回当前工作目录，便于平台收集和链式传递。

适合使用的提示词示例：

```text
使用 asterfire-image-path-calibrator，根据 image_layout.md 和 Dockerfile 帮我检查 ProteinMPNN.py 中的路径问题，把镜像内项目路径改成 /opt/ProteinMPNN，同时输出仍写到当前工作目录。
```

---

## 推荐工作流

这 4 个 Skills 可以按下面的顺序配合使用。

### 场景 A：从零开发一个新的 Asterfire Kit

1. 使用 `asterfire-kit-development` 设计 Kit 结构、入口文件和表单。
2. 使用 `asterfire-dockerfile-builder` 构建运行镜像。
3. 使用 `asterfire-image-path-calibrator` 检查入口代码中是否正确引用镜像内资源。
4. 回到 `asterfire-kit-development` 做最终规范审查和打包。

### 场景 B：把已有项目适配为平台 Kit

1. 使用 `asterfire-project-to-kit-adapter` 分析普通项目并生成平台入口。
2. 使用 `asterfire-dockerfile-builder` 将项目依赖、权重、数据库打包进镜像。
3. 使用 `asterfire-image-path-calibrator` 修复路径引用。
4. 使用 `asterfire-kit-development` 校验 `input.json`、`configure.json`、`@tool_io`、`return dict` 和 `demos`。

### 场景 C：Kit 调试时找不到模型、脚本或权重

1. 使用 `asterfire-image-path-calibrator` 读取 `image_layout.md` 或 Dockerfile。
2. 定位代码中错误使用 `Path.cwd()`、相对路径或本地绝对路径的位置。
3. 将镜像内资源路径改为 `/opt/...`、`/app/...` 或环境变量路径。
4. 确保输出文件仍写入 `Path.cwd()`。

---

## Asterfire Kit 开发中的关键约定

这些约定是本仓库 Skills 默认遵循的核心规则。

### 1. 必须指定 SIF

平台入口类中必须明确指定 `SIF`：

```python
class runner(Tool):
    DISPLAY_NAME = "Example Kit"
    NETWORK = False
    CPU = 2
    GPU = 0
    SIF = "example-kit:1.0.0"
```

不允许使用空字符串、`None`、`TODO` 或占位镜像。

### 2. 输入必须来自 `kwargs['args']`

```python
def call(self, kwargs):
    args = kwargs["args"]
    input_file = args["input_file"]
```

`config/input.json` 中的字段名必须和 `kwargs['args']` 中读取的 key 完全一致。

### 3. 输出端口必须和返回字典一致

```python
@tool_io(
    outputs={
        "output_file": TXTFile,
        "report": MDFile,
        "success": bool,
    }
)
class runner(Tool):
    def call(self, kwargs):
        ...
        return {
            "output_file": "result.txt",
            "report": "report.md",
            "success": True,
        }
```

`@tool_io(outputs={...})` 的 key 必须与 `return { ... }` 的 key 完全一致。

### 4. 输出文件写到当前工作目录

平台运行时会在工作目录中收集输出文件。因此 Kit 运行产生的文件应写入：

```python
from pathlib import Path

workdir = Path.cwd()
output_file = workdir / "result.txt"
```

返回时优先返回相对路径：

```python
return {"output_file": "result.txt"}
```

### 5. 镜像内资源使用绝对路径

Dockerfile 中固化进镜像的项目、权重和数据库不要通过 `Path.cwd()` 查找。

推荐：

```python
from pathlib import Path
import os

project_root = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
script = project_root / "protein_mpnn_run.py"
```

不推荐：

```python
project_root = Path.cwd() / "ProteinMPNN-main"
```

---


## 注意事项

1. 在 WSL 或国内网络环境中，如果 GitHub 访问不稳定，建议先确认本地可以正常 `git clone` 该仓库。
2. 安装前建议先运行 `--list`，确认仓库中的 Skill 都能被正确发现。
3. 如果只需要某一个 Skill，可先通过 `--list` 查看准确名称，再按实际 CLI 支持的参数选择性安装。

---

## License

项目使用MIT许可协议。

