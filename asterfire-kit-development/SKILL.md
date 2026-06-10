---
name: asterfire-kit-development
description: 规范、开发、重构、审查和打包 Asterfire 平台 Kit 工具。凡涉及 Kit 项目、config/input.json 表单、config/configure.json 元数据、config/long_description.md、config/long_description_en.md、runner(Tool)、@tool_io 输出端口、kwargs['args']、report.md、Asterfire Tool Protocol、平台 workflow 脚本节点或打包交付，都使用本 Skill。
---

# Asterfire Kit 开发规范

本 Skill 用于把 Kit 工具开发固定为“强约束开发规范 + 最小输入原则 + SIF 强绑定 + input.json 表单知识库 + 可复用模板 + 审查清单”。处理 Kit 项目时，先遵守本文件；需要细节时读取 `references/kit-development-rules.md`；需要生成或审查 `input.json` 时读取 `references/input_form_catalog.json`；需要新建项目时优先复制 `assets/templates/`。

## 最重要的 10 条硬规则

1. **必须指定 SIF。** 写 `runner(Tool)` 之前，必须先确定 `SIF`。SIF 可以由用户明确给出，也可以从 `references/sif_registry.json` 查询得到。无法确定 SIF 时，不要生成任何 Python 入口代码，直接回复：`请先指定该 Kit 使用的 SIF，或先把该 SIF 登记到 references/sif_registry.json。`
2. **入口文件不固定叫 `main.py`。** 修改已有项目时，入口文件由包含 `class runner(Tool)` 的 Python 文件决定。不要仅凭文件名判断。
3. **输入参数必须最小化。** `config/input.json` 只写运行该 Kit 真正需要用户填写的字段。不要为了“示例完整性”加入无关参数。
4. **生成 `input.json` 前必须查表单知识库。** 平台已支持的表单结构、字段类型、验证规则、条件显示和常见最小模板记录在 `references/input_form_catalog.json`。写 `input.json` 时先查该文件，优先匹配 `task_templates`，再从 `field_recipes` 组合最小字段。
5. **中文优先。** 代码注释、`report.md`、`long_description.md`、`input.json` / `configure.json` 中面向用户的说明、label、description、message 都使用中文。平台支持中文，不要强行写英文说明。
6. **Makefile 不重复创建。** 项目已有 `Makefile` 时不要覆盖；没有时，提醒用户缺失并按模板创建一个合格的 `Makefile`。
7. **必须维护 Demo 配置。** 发布或交付 Kit 时，项目根目录应包含 `demos/` 目录；其中必须有 `demos.json`，并放入该 Demo 引用的所有示例文件。`demos.json` 的 `value` 必须和 `config/input.json` 的字段 key 对齐。
8. **结构和图片必须进报告。** 只要主要输出中包含 `.pdb`、`.cif/.mmcif`、`.sdf` 等结构文件，`report.md` 必须使用 `molstar` 代码块直接渲染；多个结构文件需要同空间对比时，写在同一个 `molstar` 块中。只要输出中包含 PNG/JPG/SVG/WebP 等可视化图片，也必须在 `report.md` 中用 Markdown 图片语法展示。
9. **元数据和详情页必须同步更新。** 每次修改 Kit 都必须更新 `config/configure.json` 的 `version`；`description` 要用户友好、尽量详细但不超过 400 个字符。`config/long_description.md` 和 `config/long_description_en.md` 必须完整维护，并按“概述、功能、输入、输出、注意事项、参考文献”结构撰写。
10. **报告不展示运行日志，交付必须打包。** `report.md` 不得直接展示 stdout/stderr 或大段运行日志；需要留痕时写入 `run.log`、`stdout.log`、`stderr.log` 等输出文件。每次修改完成后都要重新打包生成新版 zip，并把更新后的压缩包作为交付物。

## 标准结构

推荐 Kit 项目结构为：

```text
my-kit/
├── config/
│   ├── configure.json
│   ├── input.json
│   ├── long_description.md
│   └── long_description_en.md
├── utils(这是用来定义各种辅助函数的，定义好之后可以在主函数中import)/
│   ├── xxx.py
│   ├── xxx.py
│   └── .....
├── demos/
│   ├── demos.json
│   ├── sample.csv
│   └── test_file.txt
├── <入口文件>.py
└── Makefile
```

注意：`<入口文件>.py` 不一定是 `main.py`。在已有项目中，必须通过搜索 `class runner(Tool)` 来定位真实入口文件。

## 入口文件定位规则

修改已有 Kit 时按以下顺序定位入口：

1. 在项目内搜索所有 `.py` 文件。
2. 找到包含 `class runner(Tool)` 或 `class runner( Tool )` 等等价写法的文件。
3. 若只有一个匹配文件，该文件就是入口文件。
4. 若有多个匹配文件，不要盲改；需要让用户明确选择哪一个是真入口。
5. 若没有匹配文件，但用户要求新建 Kit，则先确定 SIF，再创建入口文件。

不要把“入口文件必须叫 `main.py`”写进规则或模板。

## SIF 强约束

`runner` 类中必须显式写出平台运行资源和镜像信息：

```python
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
        ...
```

硬性要求：

- `SIF` 不允许为空字符串。
- `SIF` 不允许写成 `None`、`TODO`、`待定`、`example` 等占位值。
- 如果用户没有指定 SIF，并且 `references/sif_registry.json` 也无法匹配到合适镜像，不要继续写入口代码。
- 如果已有代码没有 `SIF`，审查时必须标为不合格。
- 如果已有代码 `SIF` 与 `references/sif_registry.json` 中记录的用途明显不一致，必须提示风险。

SIF 注册表位置：

```text
references/sif_registry.json
```

该文件记录每个 SIF 的负责人、用途、环境、主要软件、默认资源、更新时间和备注。维护方式见本文件最后的“ SIF 注册表增删改查”。

## Python 入口强约束

- 先导包，导包后立即写 `@tool_io(outputs={...})`，再写唯一类 `runner(Tool)`。
- 一个 Kit 中只能有一个平台入口类，且只能是 `runner`。
- 平台唯一入口必须是 `def call(self, kwargs):`。
- 所有输入参数必须从 `kwargs['args']` 读取，例如：

```python
args = kwargs["args"]
input_pdb = args["input_pdb"]
```

- 需要用到的辅助函数写在 `runner` 类之后，不要在 `runner` 前放业务函数。
- `config/input.json` 中 `fields[].name` 必须和 Python 中 `kwargs['args']['xxx']` 的 key 完全一致。
- 必须使用 `@tool_io(outputs={...})` 显式声明输出端口。
- `@tool_io(outputs={...})` 的 key 必须和 `call()` 最后 `return dict` 的 key 完全一致。
- `call()` 必须以 `return { ... }` 结束；即使只返回一个变量，也必须使用字典。
- 所有输出文件必须写入当前工作目录，也就是 `os.getcwd()` 或 `Path.cwd()`。
- 优先返回当前工作目录下的相对路径。
- 不允许把本机绝对路径硬编码进工具逻辑。外部程序路径只能来自 SIF 镜像、`PATH` 环境变量或 `input.json` 中真正必要的可选参数。

## input.json 表单知识库与最小输入原则

`input.json` 的目标不是“展示所有字段类型”，而是**只暴露用户必须提供或确实需要调节的参数**。平台支持的表单结构、字段类型、验证规则、条件显示、数组字段和级联字段已经整理到：

```text
references/input_form_catalog.json
```

开发或重构 `input.json` 时必须按这个顺序做：

1. 先根据需求和入口代码列出真正会从 `kwargs['args']` 读取的 key。
2. 到 `references/input_form_catalog.json` 中查找是否已有合适的 `task_templates`。
3. 如果有合适模板，直接用模板生成最小 `input.json`，再按真实需求裁剪。
4. 如果没有合适模板，从 `field_recipes` 中选择字段组合。
5. 如果 `field_recipes` 也没有，再按 `supported_field_types` 的字段规范手写，但字段 `type` 不得超出平台支持范围。
6. 最后检查 `formRules.required`、`fields[].validation.required`、`fields[].name`、Python 的 `kwargs['args']` key 是否一致。

可以用辅助脚本查询和生成：

```bash
# 查看平台支持的字段类型
python scripts/input_form_cli.py list-types

# 查看内置最小任务模板
python scripts/input_form_cli.py list-templates

# 按关键词推荐模板
python scripts/input_form_cli.py suggest pdb validator

# 渲染 PDB 验证 Kit 的最小 input.json
python scripts/input_form_cli.py show-template pdb_validator

# 写出到 config/input.json
python scripts/input_form_cli.py write-template pdb_validator config/input.json

# 校验已有 input.json
python scripts/input_form_cli.py validate config/input.json
```

例如：开发“PDB 数据有效性验证 Kit”时，最小输入通常只需要：

```json
{
  "formName": "PDB 数据有效性验证",
  "description": "上传一个 PDB 文件，检查文件是否存在、格式是否可读以及是否包含基础结构记录。",
  "defaultValues": {},
  "formRules": {
    "required": ["input_pdb"]
  },
  "fields": [
    {
      "name": "input_pdb",
      "label": "PDB 文件",
      "type": "file",
      "description": "上传需要验证的 .pdb 文件。",
      "validation": {
        "required": true,
        "accept": [".pdb", "chemical/x-pdb"],
        "message": "请上传 .pdb 文件。"
      }
    }
  ]
}
```
对应字段的description要用户友好，描述详细，但不能过长，能让客户知道是什么，要填什么，上传什么即可。
不要加入 `title`、`tags`、`metadata`、`run_date`、`advanced_threshold` 这类与任务无关的字段。

如果确实需要高级参数，才加入可选字段，并给出中文说明。例如严格模式、pH、阈值、分析窗口等。

## demos 目录与 demos.json 配置规则

Asterfire Kit 建议在项目根目录提供 `demos/` 目录，用于前端一键加载示例参数和示例文件。`demos/` 与 `config/`、入口 Python 文件、`Makefile` 同级。

标准结构：

```text
my-kit/
├── config/
├── demos/
│   ├── demos.json
│   ├── sample.csv
│   ├── test_file.txt
│   └── demo.jpg
├── <入口文件>.py
└── Makefile
```

`demos/demos.json` 必须是 JSON 数组，每个元素是一组可加载的 Demo：

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

字段规则：

- `name`：Demo 在前端展示的名称，建议简短清楚。
- `description`：Demo 的用途说明，建议说明该 Demo 会跑什么输入。
- `value`：表单参数对象；其中的 key 必须与 `config/input.json` 中 `fields[].name` 完全一致。
- 文件字段的值写 `demos/` 目录下的相对文件名，例如 `"avatar": "demo.jpg"`、`"input_pdb": "5L33.pdb"`。凡是 `demos.json` 中引用的文件，都必须真实放在 `demos/` 目录里。
- 多文件字段可以写成字符串数组，例如 `"input_files": ["a.pdb", "b.pdb"]`；数组、对象、级联字段按 `input.json` 对应字段实际结构填写。
- 不要在 `value` 中加入 `input.json` 没有定义、Python 也不会读取的字段。
- 每个 Demo 至少要覆盖 `formRules.required` 中的全部必填字段。
- Demo 文件应尽量小，适合快速调试；不要放入过大的生产数据。

对于本 Skill 自带的最小模板，`demos/demos.json` 可以写成：

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

可以用辅助脚本做基础校验：

```bash
# 校验 Demo 结构、必填字段和引用文件是否存在
python scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json

# 为当前最小模板创建 demos/ 示例
python scripts/demo_cli.py create-template --output demos
```

## 输入、输出与报告

- 必须对输入文件进行存在性检查。
- 必须打印足够调试日志：incoming args、当前工作目录、关键命令、返回码、生成文件路径、输出文件是否存在。
- 如需保存命令输出或异常堆栈，写入当前工作目录下的日志文件，例如 `run.log`、`stdout.log`、`stderr.log`；日志文件可以作为普通输出文件返回，但不要把全文写入 `report.md`。
- 每个 Kit 运行时必须在当前工作目录生成 `report.md`。
- `report.md` 必须使用中文，至少包含：运行概览、方法说明、结果展示与说明、可视化结果、如何查看结果、后续分析建议。
- 重要结果必须直接展示在 `report.md` 中：结构文件用 `molstar` 代码块，图片用 Markdown 图片语法，数据结果优先汇总成表格；必要的数据曲线、热图、柱状图等应在 Kit 中先用 matplotlib 生成图片，再写入报告。

## report.md 渲染规范

Kit 生成 `report.md` 时，必须根据输出文件类型使用对应的平台渲染方式：

### 结构文件 → 使用 molstar 代码块（交互式 3D 展示）

支持格式：`.pdb`, `.cif`, `.mmcif`, `.sdf`；如平台可识别，也可扩展到 `.mol2`, `.pdbqt`, `.gro`

写法：

````markdown
```molstar
./output_structure.pdb
```
````

多个结构文件需要在同一个空间中对比时，写在同一个 `molstar` 代码块中：

````markdown
```molstar
./1.pdb
./2.pdb
./candidate.sdf
```
````

### 轨迹文件 → 使用 mdtraj 代码块（交互式轨迹回放）

需要先将轨迹转为 `.mdtraj` 格式（使用 grotoxyz 等工具将 GRO 轨迹转为 PDB + 二进制 XYZ + mdtraj JSON）。

支持格式：`.xtc`, `.trr`, `.dcd`（需先转换为 `.mdtraj`）

写法：

````markdown
```mdtraj
./trajectory.mdtraj
```
````

### 数据图表 → matplotlib 渲染为 PNG 后用 markdown 图片嵌入

适用场景：`.xvg` 数据画曲线图、`.xpm` 解析后画自由能图、各类分析结果图表。

写法：

```markdown
![图表描述](./plot.png)
```

要求：在 Kit 主函数中优先用 matplotlib 生成 PNG/SVG，`report.md` 中用相对路径引用。若工具本身已经生成图片，也必须在报告中嵌入展示，并说明图片含义。

### 统计表格 → 标准 markdown 表格

适用场景：汇总数据、参数回显、关键指标对比。

直接在 `report.md` 中用 markdown 表格语法。

### 默认渲染流程

在开发或修改 Kit 时，不要再询问用户是否需要渲染。只要输出中存在可展示结果，就按以下默认规则直接写入 `report.md`：

1. 主要结构输出包含 `.pdb`、`.cif/.mmcif`、`.sdf` 时，必须使用 `molstar` 代码块渲染；同一组候选或同一体系的多个结构可放入同一个 `molstar` 块。
2. 输出中已有 `.png`、`.jpg/.jpeg`、`.svg`、`.webp` 图片时，必须用 Markdown 图片语法展示，并在图片下方解释它说明了什么。
3. 输出只有 CSV/JSON/TSV/XVG 等数据但用户需要图形化理解时，应使用 matplotlib 生成可视化图片，再在报告中展示。
4. `report.md` 不展示 stdout/stderr 或完整运行日志；日志写入 `run.log` 等文件，需要时在“如何查看结果”中说明日志文件位置。
- 如果平台不支持某种文件类型，必须使用 `Annotated[str, FileType(...)]` 自定义：

```python
from typing import Annotated
from adam_community import FileType

ITPFile = Annotated[str, FileType(".itp", "GROMACS 分子参数文件")]
ZIPFile = Annotated[str, FileType(".zip", "ZIP 压缩包")]
```

## configure、详情页与 Makefile

- `config/configure.json` 必须包含 `name`、`display_name`、`version`、`visible`、`description`、`type`、`tags`、`cover`，其中 `type` 固定为 `"kit"`。
- 每次修改 Kit 必须更新 `config/configure.json` 的 `version`，并同步检查 `Makefile` 中的版本号。
- `description` 要尽可能清楚地告诉用户“这个 Kit 能做什么、需要什么输入、会得到什么结果”，但不能超过 400 个字符；不要写空泛宣传语，也不要长篇大论。
- `config/long_description.md` 和 `config/long_description_en.md` 都要写成前端可展示的工具介绍页，固定包含：`# 概述`、`# 功能`、`# 输入`、`# 输出`、`# 注意事项`、`# 参考文献`。其中“输入”必须用表格展示，列为：参数、类型、必填、说明。
- 面向用户的所有文字使用中文。
- `Makefile` 已存在时检查版本号是否正确，不正确要修改，否则不需要覆盖；缺失时创建模板：

```makefile
APP_NAME := example-kit
VERSION := 1.0.0

.PHONY: build clean

build:
	adam-cli parse .
	adam-cli build .

clean:
	rm -f *.zip
	rm -f functions.json
```

## Demo 配置与交付

- 发布或交付 Kit 时，根目录建议包含 `demos/`。
- `demos/demos.json` 必须是 JSON 数组，且每个 Demo 都包含 `name`、`description`、`value`。
- `value` 中的 key 必须与 `config/input.json` 的字段名一致，并能被入口代码通过 `kwargs['args']` 正常读取。
- Demo 中引用的文件必须放在 `demos/` 目录下，路径写相对文件名，不写本机绝对路径。
- 如果该 Kit 没有文件输入，也仍可提供只包含普通字段的 `demos.json`。
- 修改 `input.json` 后，要同步检查 `demos.json`；字段改名、必填项变化、文件字段变化都必须同步更新 Demo。

## Workflow 脚本节点

平台 workflow 脚本节点也必须遵守：

- 从 `kwargs['args']` 读取输入。
- 输出文件写入当前工作目录。
- 最后 `return dict`。
- `return dict` 的 key 和下游节点变量名一致。

Scatter / gather 场景必须遵守：

- 每个 `scatter_xx` 子目录独立处理。
- 不要假设其他 scatter 目录存在。
- 需要汇总时，把文件复制到当前节点工作目录的稳定文件夹中。
- 如果下游只接收一个文件，就打包成 zip 再返回。

## Codex 工作流程

修改前：

- 查看项目结构。
- 搜索包含 `class runner(Tool)` 的 Python 文件，不要默认入口叫 `main.py`。
- 检查是否指定了合法 `SIF`；没有则停止写入口代码，并要求用户指定 SIF。
- 查阅 `references/sif_registry.json`，确认镜像用途、负责人和环境是否匹配。
- 查阅 `references/input_form_catalog.json`，根据需求匹配最小 `task_templates` 或 `field_recipes`。
- 找到 `config/input.json`、`config/configure.json`、`config/long_description.md`、`config/long_description_en.md`、`demos/demos.json`、`Makefile`。
- 检查 `input.json` 是否只包含真实需要的参数，并确认字段 type、validation、conditional 均来自平台已支持定义。
- 检查 `demos/demos.json` 是否存在，Demo 的 `value` 是否与 `input.json` 字段一致，引用文件是否放在 `demos/` 目录下。
- 如果 Kit 输出中包含结构文件、图片或可绘图数据，直接按默认规则写入 `report.md`：`.pdb/.cif/.sdf` 用 molstar，图片用 Markdown 嵌入，数据必要时用 matplotlib 生成图；不要再把“是否渲染”作为前置确认问题。
- 检查 `report.md` 是否包含运行概览、方法说明、结果展示与说明、可视化结果、如何查看结果、后续分析建议，并确认没有直接展示 stdout/stderr 全文。

修改时：

- 保持 `input.json`、`kwargs['args']`、`@tool_io(outputs)`、`return dict` 四者同步。
- `input.json` 优先由 `references/input_form_catalog.json` 中的模板或字段配方生成；不要创造未支持的字段类型。
- 所有输出写入当前工作目录。
- 补充中文 `report.md`、输入检查、日志文件、主要结果渲染和文件类型声明。
- 补充或同步 `demos/` 目录，确保至少有一个可快速运行的 Demo。
- 不引入第二个入口类，不把辅助函数放在 `runner` 前面。
- 已有 `Makefile` 不覆盖；缺失时按模板创建。

完成后：

- 检查 Python 语法。
- 检查 JSON 语法。
- 运行 `python scripts/input_form_cli.py validate config/input.json` 校验表单基础结构。
- 运行 `python scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json` 校验 Demo 配置。
- 检查输出 key 是否一致。
- 检查是否生成 `report.md`，且报告展示了主要结构/图片/图表结果，没有直接铺开 stdout/stderr 日志。
- 检查返回路径是否存在。
- 重新打包生成新版 zip，交付更新后的压缩包。
- 如果能运行 `make build`，就运行；如果不能运行，要说明原因。

## 常见错误修复

- 前端不显示输出文件：检查 `@tool_io(outputs)` key、`return dict` key、返回路径和文件是否存在。
- `kwargs['args']` KeyError：检查 `input.json fields[].name`、`formRules.required`、默认值和 Python key 是否完全一致。
- `report.md` 缺失：在 `call()` 中无论成功或失败都生成报告，报告路径写入当前工作目录；报告只展示用户关心的结果和解释，不直接展示 stdout/stderr。
- 上传文件路径格式异常：用路径归一化函数处理字符串、对象、列表形式，再做存在性检查。
- 外部二进制程序找不到：确认 SIF 内是否包含该软件，或确认软件在镜像 `PATH` 中。
- scatter/gather 文件丢失：每个 scatter 子目录独立处理，汇总时复制到当前节点工作目录稳定目录。
- output key 和 return key 不一致：同步修改 `@tool_io(outputs)`、`return {}`、下游节点变量名。
- 入口文件误判：重新搜索 `class runner(Tool)`，不要只看 `main.py`。
- input.json 参数过多：删除与任务无关的字段，只保留必要输入和少数真正有用的可选项。
- Demo 加载失败：检查 `demos/demos.json` 是否是数组、`value` key 是否与 `input.json` 对齐、文件是否真实位于 `demos/` 目录。

## SIF 注册表增删改查

注册表文件：

```text
references/sif_registry.json
```

推荐手动维护方式：直接编辑 JSON 文件。每条记录至少包含：

```json
{
  "sif": "asterfire-base:1.0.0",
  "owner": "平台维护组",
  "purpose": "最小 Kit 示例和基础 Python 文件处理",
  "environment": ["Python 3.12", "adam_community"],
  "contains": ["python", "bash", "coreutils"],
  "default_resources": {
    "cpu": 2,
    "gpu": 0,
    "network": false
  },
  "tags": ["python", "example"],
  "updated_at": "2026-05-09",
  "notes": "模板示例，请按真实镜像修改。"
}
```

推荐脚本维护方式：使用 `scripts/sif_registry_cli.py`：

```bash
# 查看全部 SIF
python scripts/sif_registry_cli.py list

# 查询某个 SIF
python scripts/sif_registry_cli.py get example-kit:1.0.0

# 新增 SIF
python scripts/sif_registry_cli.py add \
  --sif pdb-validator-kit:1.0.0 \
  --owner 结构工具负责人 \
  --purpose PDB 文件有效性验证 \
  --env "Python 3.10" \
  --contains "adam_community" \
  --contains "biopython" \
  --cpu 2 \
  --gpu 0 \
  --network false \
  --tag structure \
  --tag pdb

# 更新 SIF
python scripts/sif_registry_cli.py update pdb-validator-kit:1.0.0 \
  --owner 新负责人 \
  --purpose "PDB / mmCIF 基础验证"

# 删除 SIF
python scripts/sif_registry_cli.py remove pdb-validator-kit:1.0.0
```

## 资源

- 详细规则：`references/kit-development-rules.md`
- input.json 表单知识库：`references/input_form_catalog.json`
- input.json 表单辅助脚本：`scripts/input_form_cli.py`
- Demo 配置辅助脚本：`scripts/demo_cli.py`
- SIF 注册表：`references/sif_registry.json`
- SIF 注册表脚本：`scripts/sif_registry_cli.py`
- 新建模板：`assets/templates/runner_template.py`、`configure.json`、`input.json`、`long_description.md`、`long_description_en.md`、`Makefile`、`demos/`
