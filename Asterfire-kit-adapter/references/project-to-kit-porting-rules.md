# 普通项目改造成平台 Kit 的详细规则

## 目标

把一个普通 Python/命令行项目适配成 Asterfire 平台 Kit。适配后的项目必须能通过平台前端表单接收输入，通过 `runner.call(kwargs)` 执行业务逻辑，并返回平台可识别的输出端口。

## 必须先确认的 runner 配置

平台入口类必须显式包含：

```python
class runner(Tool):
    DISPLAY_NAME = "中文前端显示名"
    NETWORK = False
    CPU = 2
    GPU = 0
    SIF = "真实镜像:版本"
```

这些配置不能靠猜。

### 用户没指定配置时

如果用户没有指定 `DISPLAY_NAME`、`NETWORK`、`CPU`、`GPU`、`SIF`，并且没有明确授权从 SIF 注册表选择，则必须停下来询问。不要生成入口代码，不要写占位 SIF。

### 用户授权自动选择时

必须读取 `references/sif_registry.json`。

匹配维度：

- Python 版本和依赖包。
- 外部命令，例如 `gmx`、`obabel`、`orca`、`python`、`Rscript`。
- 任务类型，例如分子动力学、PDB 处理、CSV 建模、图像处理、文本处理。
- 是否需要 GPU。
- 是否需要网络。

无法唯一确定时，列候选让用户确认。没有候选时，要求用户补充或登记新 SIF。

## 普通项目分析清单

查看项目时必须记录：

1. 项目根目录结构。
2. Python 文件列表。
3. 是否已有 `class runner(Tool)`。
4. 是否已有 `config/input.json`、`config/configure.json`、`config/long_description.md`。
5. 是否已有 `Makefile`。
6. 可能的普通入口文件：`main.py`、`app.py`、`cli.py`、`run.py`、`predict.py`、`train.py`、带 `if __name__ == "__main__"` 的脚本。
7. 命令行参数：`argparse`、`click`、`typer`。
8. 第三方 Python 依赖。
9. 外部二进制命令。
10. 真实输入文件、文本参数和可选参数。
11. 真实输出文件和目录。
12. 项目运行时是否写入固定路径或绝对路径。
13. 运行是否依赖当前工作目录。

## 入口选择规则

### 已经是 Kit

如果已有 `class runner(Tool)`：

- 定位包含该类的文件。
- 检查是否有 `DISPLAY_NAME`、`NETWORK`、`CPU`、`GPU`、`SIF`。
- 若缺 `SIF` 或 `SIF` 是占位，必须先确认 SIF。
- 不要新建第二个 `runner` 类。

### 普通项目

如果没有 `class runner(Tool)`：

- 如果有清晰命令行入口，优先新建平台入口文件包装该命令。
- 如果有清晰函数入口，优先新建平台入口文件导入并调用该函数。
- 如果顶层代码复杂，先拆出业务函数到 `utils/`，再让 `runner.call()` 调用。

不要假设入口文件一定叫 `main.py`。

## 适配方式

### 函数调用式

适合原项目已经有函数：

```python
def run(input_file, output_dir, threshold=0.5):
    ...
```

平台入口负责：

- 从 `kwargs['args']` 取参数。
- 检查输入存在。
- 创建当前工作目录下的输出路径。
- 调用原函数。
- 检查输出是否存在。
- 写专业中文 report.md，展示关键结果和可视化，不直接展开运行日志。
- return dict。

### 命令行包装式

适合原项目已经稳定支持 CLI：

```bash
python predict.py --input xxx.csv --output result.csv
```

平台入口中使用：

```python
completed = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False)
```

必须打印或记录：

- command
- returncode
- 输出文件路径
- 文件是否存在
- 详细命令输出和错误信息写入 `run.log`、`stdout.log`、`stderr.log` 等文件

注意：`report.md` 不直接展示 stdout/stderr 全文，只在“如何查看结果”中说明日志文件位置。

### 拆分 utils 式

如果原项目是顶层脚本，把业务逻辑拆成：

```text
utils/project_core.py
```

入口文件只保留平台适配层，不把大量业务代码堆在 `runner.call()` 里。

## input.json 生成规则

`input.json` 字段必须来自真实输入需求。

常见映射：

| 普通项目参数 | input.json 字段类型 |
| --- | --- |
| 输入文件路径 | file |
| 输出格式 | select |
| 阈值、pH、温度、步数 | number |
| 是否启用某模式 | boolean |
| 多行序列、SMILES 列表 | text |
| 多个配体或多个文件 | array + file |
| 少量固定算法选项 | select / multiselect |

不应暴露：

- 输出文件名，除非用户确实需要自定义。
- 当前工作目录。
- 内部临时文件名。
- 调试开关，除非平台用户需要。
- 作者、标签、日期等元数据。


## demos 目录与 demos.json 规则

适配后的 Asterfire Kit 应在项目根目录提供 `demos/` 目录，用于前端一键加载示例参数和示例文件。`demos/` 与 `config/`、入口 Python 文件、`Makefile` 同级。

推荐结构：

```text
my-kit/
├── config/
│   ├── configure.json
│   ├── input.json
│   ├── long_description.md
│   └── long_description_en.md
├── demos/
│   ├── demos.json
│   ├── sample.csv
│   ├── test_file.txt
│   └── demo.jpg
├── <入口文件>.py
└── Makefile
```

`demos/demos.json` 是一个 JSON 数组。每个元素必须包含：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | Demo 展示名称 |
| `description` | string | 是 | Demo 说明 |
| `value` | object | 是 | 表单参数对象，key 必须与 `config/input.json` 的 `fields[].name` 对齐 |

复杂表单示例：

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

规则：

- `value` 里的 key 必须来自 `config/input.json` 的字段名；不要额外添加入口代码不会读取的参数。
- `formRules.required` 中的必填字段必须在每个 Demo 的 `value` 中给出。
- 文件字段写 `demos/` 目录内的相对文件名，例如 `"input_pdb": "5L33.pdb"`、`"avatar": "demo.jpg"`。
- `demos.json` 引用到的每个文件，都必须真实放在 `demos/` 目录下。
- 多文件字段可以写成数组，例如 `"input_files": ["a.pdb", "b.pdb"]`。
- Demo 文件应尽量小，优先用于快速调试，不要把大型生产数据放进 Demo。
- 修改 `input.json` 字段名、必填项或文件输入后，必须同步更新 `demos.json`。

### GitHub/开源项目案例迁移为 Demo

将 GitHub 项目、论文代码仓库或开源 CLI 改造成 Kit 时，`demos/` 不能只保留模板示例，应优先迁移原仓库自带的官方案例。

必须检查的来源：

| 来源 | 需要提取什么 | Demo 转换方式 |
| --- | --- | --- |
| `README.md` / `docs/` | 官方快速开始命令、推荐参数、示例输出说明 | 把命令行参数映射到 `input.json` 字段，并写入 `demos.json.value` |
| `examples/` / `example/` / `demo/` / `sample/` | 小型示例输入文件、配置文件、脚本 | 复制轻量文件到 `demos/`，路径改为 Demo 相对文件名 |
| `tests/` / `test/` | 可快速运行的测试输入、最小用例 | 优先转成 smoke-test Demo，验证入口可跑通 |
| `notebooks/` / `tutorials/` | 教程中的典型流程和参数组合 | 提炼为一个或多个前端 Demo，不直接要求用户运行 notebook |
| `scripts/` | 官方示例脚本和预置参数 | 解析核心参数，转成表单参数和 Demo 描述 |

迁移原则：

1. 每个主要运行模式、任务类型或常见输入格式，尽量配置一个独立 Demo。
2. Demo 名称和描述要面向平台用户，说明该案例对应什么功能、输入什么、会得到什么输出。
3. 优先选择小文件、短耗时、确定性强的官方案例；不要把超大数据集或长时间训练任务作为默认 Demo。
4. 原示例文件若过大，可以裁剪为最小可运行子集；若不能内置，需要说明原因，并保留一个用户上传文件版 Demo。
5. 不依赖运行时联网下载示例数据；需要模型权重或公共数据时，应在镜像/Kit 内置，或在文档中说明用户需自行提供。
6. 如果原项目完全没有案例，至少根据 README 的最小命令和可推断输入构造一个 smoke-test Demo；确实不能构造时，在交付说明里明确原因。
7. `demos.json` 中不要保留 GitHub 原命令的旧参数名；必须全部使用平台 `input.json` 字段名。

最小文件输入模板：

```json
[
  {
    "name": "CSV 文件示例",
    "description": "使用 sample.csv 运行最小 Kit 模板。",
    "value": {
      "input_file": "sample.csv"
    }
  },
  {
    "name": "文本文件示例",
    "description": "使用 test_file.txt 运行最小 Kit 模板。",
    "value": {
      "input_file": "test_file.txt"
    }
  }
]
```

基础校验命令：

```bash
python scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json
```

## 输出端口规则

必须根据真实输出声明 `@tool_io(outputs={...})`。

常用类型：

```python
from adam_community.tool_types import MDFile, TXTFile, CSVFile, JSONFile, ZIPFile, tool_io
```

如果平台没有内置类型，用：

```python
from typing import Annotated
from adam_community import FileType

PDBFile = Annotated[str, FileType(".pdb", "PDB 结构文件")]
MOL2File = Annotated[str, FileType(".mol2", "MOL2 小分子文件")]
```

输出 key 必须与 return key 一致。

## report.md 规则

每次运行都应生成 `report.md`。报告面向平台用户，不是日志转储。

报告至少包含：

- 运行概览：成功、失败或部分成功；Kit 名称、版本、关键输入和主要输出。
- 方法说明：说明调用了原项目的哪个函数、脚本或命令，关键参数代表什么。
- 结果展示与说明：展示主要结果表格、指标、候选文件和解释。
- 可视化结果：结构文件、图片或由数据生成的图必须直接嵌入。
- 如何查看结果：说明主要输出文件、结构文件、图表文件和日志文件在哪里。
- 后续分析建议：给出可执行的下一步建议。

结果展示规则：

- 主要输出包含 `.pdb`、`.cif/.mmcif`、`.sdf` 时，必须使用 `molstar` 代码块展示。
- 多个文件需要同空间展示时，写在同一个 `molstar` 块中，例如：

````markdown
```molstar
./1.pdb
./2.pdb
./candidate.sdf
```
````

- 输出包含 `.png`、`.jpg/.jpeg`、`.svg`、`.webp` 图片时，必须使用 Markdown 图片语法展示，并解释图片含义。
- 输出只有 CSV/JSON/TSV/XVG 等数据但用户需要图形理解时，先用 matplotlib 生成 PNG/SVG，再嵌入报告。
- 关键指标和 Top N 结果应使用 Markdown 表格汇总，完整大表另存为 CSV/JSON。

禁止：

- 不要在报告中直接展示 stdout/stderr 全文、完整外部程序日志或 Traceback 堆栈。
- 不要把报告写成纯粹的文件清单。
- 不要只让用户下载结果，重要结果必须在报告正文中可见。

日志处理：

- 命令输出、错误输出和异常堆栈写入 `run.log`、`stdout.log`、`stderr.log` 或原项目日志文件。
- 日志文件可以在 `@tool_io(outputs)` 中声明为普通输出文件。
- `report.md` 只需要说明日志文件位置，例如“详细运行日志保存在 `run.log`，用于排错”。

## configure 与详情页规则

- `config/configure.json` 的 `type` 固定为 `"kit"`。
- 每次修改 Kit 都必须更新 `version`，并同步检查 `Makefile` 中的 `VERSION`。
- `description` 要用户友好，说明 Kit 能做什么、输入什么、输出什么，但最高不能超过 400 个字符。
- 必须同时维护 `config/long_description.md` 和 `config/long_description_en.md`。
- 详情页固定包含：`概述/Overview`、`功能/Features`、`输入/Inputs`、`输出/Outputs`、`注意事项/Notes`、`参考文献/References`。
- 输入章节必须用表格，列为：参数、类型、必填、说明。英文版对应为 Parameter、Type、Required、Description。
- 输出章节要解释主要结果是什么、怎么看、适合什么后续分析。

## Makefile 规则

没有 Makefile 时创建：

```makefile
APP_NAME := your-kit-name
VERSION := 1.0.0

.PHONY: build clean

build:
	adam-cli parse .
	adam-cli build .

clean:
	rm -f *.zip
	rm -f functions.json
```

已有 Makefile 不要覆盖。只在 APP_NAME 或 VERSION 明显错误时谨慎修改。

## 审查 checklist

- [ ] runner 配置已确认，不是占位。
- [ ] SIF 来自用户指定或注册表选择。
- [ ] 若自动选 SIF，已说明选择依据。
- [ ] 只有一个 `class runner(Tool)`。
- [ ] `def call(self, kwargs):` 存在。
- [ ] 输入只从 `kwargs['args']` 读取。
- [ ] `input.json fields[].name` 与代码读取 key 一致。
- [ ] `@tool_io(outputs)` 与 return key 一致。
- [ ] 输出写入当前工作目录。
- [ ] 返回相对路径。
- [ ] 生成中文 `report.md`，且包含运行概览、方法说明、结果展示与说明、可视化结果、如何查看结果、后续分析建议。
- [ ] `report.md` 没有直接展开 stdout/stderr 或大段运行日志。
- [ ] 若输出包含 `.pdb/.cif/.sdf`，报告中已有 molstar 块。
- [ ] 若输出包含图片或可绘图数据，报告中已有图片展示或 matplotlib 生成图。
- [ ] 日志包含 incoming args、cwd、SIF、关键命令、返回码、输出文件检查，并保存为日志文件。
- [ ] JSON 语法通过。
- [ ] Python 语法通过。
- [ ] `input_form_cli.py validate config/input.json` 通过。
- [ ] 存在 `demos/demos.json`，且 Demo 的 `value` 覆盖必填字段、引用文件真实存在。
- [ ] 如果源项目来自 GitHub/开源仓库，已尽可能迁移 README、docs、examples、tests、notebooks/tutorials 中的官方案例为 Kit Demo，并覆盖主要运行模式。
- [ ] 没有本机绝对路径硬编码。
- [ ] 没有无关字段塞进 input.json。

## 打包交付规则

每次适配或修改完成后，都必须重新打包生成新版 zip。交付说明应指向更新后的压缩包，并说明如果 `make build` 或 `adam-cli` 无法运行的原因。
