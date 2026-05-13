---
name: asterfire-project-to-kit-adapter
description: 将普通 Python/命令行项目改造成 Asterfire 平台 Kit。凡涉及把已有项目接入平台、补写 class runner(Tool)、确定 DISPLAY_NAME/NETWORK/CPU/GPU/SIF、从 SIF 注册表选镜像、生成 config/input.json、config/configure.json、config/long_description.md、report.md、@tool_io 输出端口、kwargs['args'] 参数映射或打包交付，都使用本 Skill。
---

# 普通项目 → 平台 Kit 适配 Skill

本 Skill 专门处理“我有一个普通项目代码，需要改造成适配我们平台 Kit 的代码”的场景。它不是从零写一个示例 Kit，而是先分析已有项目，再把项目入口、输入、输出、依赖、环境和平台元数据统一改造成 Asterfire Kit 规范。

需要更细的规则时读取：

- `references/project-to-kit-porting-rules.md`
- `references/sif_registry.json`
- `references/input_form_catalog.json`

可使用辅助脚本：

- `scripts/porting_analyzer.py`：扫描普通项目，提取入口、依赖、疑似输入输出和 runner 配置缺口。
- `scripts/sif_registry_cli.py`：查询、增删改查 SIF 注册表。
- `scripts/input_form_cli.py`：查询平台表单字段和最小 input.json 模板。
- `scripts/demo_cli.py`：创建和校验 `demos/demos.json`，检查 Demo 必填字段和引用文件。

## 最重要的硬规则

### 1. 没有 runner 配置时，先问配置，不要直接改代码

把普通项目改成平台 Kit 前，必须先确定 `class runner(Tool):` 下方的这些配置：

```python
class runner(Tool):
    DISPLAY_NAME = "xxx"
    NETWORK = False
    CPU = 2
    GPU = 0
    SIF = "xxx:1.0.0"
```

其中 `SIF` 是硬性必填项，不允许为空、不允许占位。

如果用户没有明确指定这些配置，也没有明确说“根据 SIF 注册表自动选择”，不要生成或修改平台入口代码。直接回复用户，让用户补充配置。推荐回复格式：

```text
要把这个普通项目改造成平台 Kit，我需要先确定 runner 配置，尤其是 SIF。请你指定下面这些项：

1. DISPLAY_NAME：平台前端显示名称，例如“PDB 结构验证工具”。
2. SIF：平台运行镜像，例如 xxx:1.0.0。
3. CPU：默认 CPU 数。
4. GPU：默认 GPU 数。
5. NETWORK：运行时是否需要网络，True/False。

你也可以直接说：根据现有 SIF 注册表帮我选择合适的 SIF 和默认资源。这样我会先分析项目依赖，再从 references/sif_registry.json 中选择候选镜像。
```

只有当用户完成配置，或者明确授权“根据 SIF 注册表自动选择”后，才能继续改造代码。

### 2. 用户授权自动选择 SIF 时，必须查注册表

如果用户说“根据已有 SIF 选择”“你帮我选 SIF”“根据 SIF 注册表选择”等，必须读取：

```text
references/sif_registry.json
```

选择逻辑：

1. 先分析普通项目依赖、命令、导入包和任务类型。
2. 在 SIF 注册表中按 `purpose`、`environment`、`contains`、`tags`、`notes` 匹配。
3. 如果只有一个明显最合适的 SIF，可以直接采用该 SIF，并使用其 `default_resources` 填写 `CPU`、`GPU`、`NETWORK`。
4. 如果有多个候选，不要擅自选；列出候选并请用户确认。
5. 如果没有合适候选，停止改造入口代码，并要求用户先指定 SIF 或登记新 SIF。

推荐候选展示格式：

```text
我在 SIF 注册表中找到了这些候选：

1. xxx:1.0.0：用途……；环境……；默认 CPU/GPU/NETWORK = 2/0/False。
2. yyy:1.0.0：用途……；环境……；默认 CPU/GPU/NETWORK = 8/1/False。

请确认使用哪一个。也可以补充一个新的 SIF 配置。
```

### 3. 普通项目不能被粗暴改坏

优先采用“薄包装”策略：保留原项目主要业务代码，只新增或改造一个平台入口文件，让 `runner.call()` 调用原有函数或命令。

推荐结构：

```text
my-kit/
├── config/
│   ├── configure.json
│   ├── input.json
│   └── long_description.md
├── demos/
│   ├── demos.json
│   └── 示例输入文件...
├── utils/
│   └── 原项目可复用模块或适配辅助函数.py
├── <平台入口文件>.py
├── 原项目代码...
└── Makefile
```

如果原项目已有清晰的函数入口，优先 `import` 后调用；如果原项目是命令行脚本且重构风险高，可以在 `runner.call()` 中用 `subprocess.run()` 调用原脚本，但必须记录命令、stdout、stderr、返回码，并生成中文 `report.md`。

### 4. 必须保持四个映射一致

改造完成后，以下四者必须完全同步：

1. `config/input.json` 的 `fields[].name`
2. Python 代码里的 `kwargs['args']['xxx']`
3. `@tool_io(outputs={...})` 的输出 key
4. `call()` 最后的 `return { ... }` key

不允许出现前端字段叫 `input_pdb`，代码却读 `pdb_file` 的情况。

### 5. input.json 必须按最小输入原则生成

写 `config/input.json` 前必须查：

```text
references/input_form_catalog.json
```

只保留项目真正需要用户提供的字段。不要把内部变量、调试变量、输出路径、运行时间、作者、标签等无关字段暴露给用户。

生成顺序：

1. 从项目入口和需求中确定真实输入 key。
2. 用 `task_templates` 匹配最小模板。
3. 没有模板时，从 `field_recipes` 组合。
4. 仍不够时，按 `supported_field_types` 手写，但不得创造平台不支持的字段类型。
5. 最后用 `scripts/input_form_cli.py validate config/input.json` 校验。


### 6. demos 目录与 demos.json 必须同步生成

把普通项目适配成 Asterfire Kit 时，交付项目根目录应包含 `demos/` 目录。`demos/` 与 `config/`、入口 Python 文件、`Makefile` 同级，用于前端一键加载示例参数和示例文件。

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

对于最小文件输入模板，`demos/demos.json` 可以写成：

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

适配完成后必须运行或等价检查：

```bash
python scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json
```

### 7. 中文优先

面向用户的内容必须使用中文，包括：

- 代码注释
- `config/input.json` 的 label、description、message
- `config/configure.json` 的 display_name、description、tags
- `config/long_description.md`
- `demos/demos.json` 和所引用的示例文件
- 运行时生成的 `report.md`
- 调试日志中需要给平台用户看的说明

### 8. Python 入口强约束

平台入口文件必须满足：

- 导入后尽快写 `@tool_io(outputs={...})`。
- 唯一平台入口类名必须是 `runner`。
- 入口方法必须是 `def call(self, kwargs):`。
- 输入只从 `kwargs['args']` 读取。
- 输出文件必须写到当前工作目录，即 `Path.cwd()` 或 `os.getcwd()`。
- 返回路径优先使用当前工作目录下的相对路径。
- 必须生成中文 `report.md`。
- 必须打印 incoming args、当前工作目录、关键命令、stdout/stderr、输出文件是否存在。
- 必须有输入文件存在性检查。
- `SIF` 必须是真实可用镜像，不能是 `example`、`TODO`、`待定`、空字符串或 `None`。

## 推荐工作流

### 第一步：分析普通项目

先查看项目结构，再运行或等价执行：

```bash
python scripts/porting_analyzer.py /path/to/project --json-out /tmp/porting_analysis.json --md-out /tmp/porting_analysis.md
```

分析重点：

- 是否已经是 Kit。
- 是否已有 `class runner(Tool)`。
- 普通项目入口在哪个文件。
- 是否使用 argparse/click/typer 等命令行参数。
- 导入了哪些第三方库。
- 调用了哪些外部命令。
- 读取哪些输入文件。
- 生成哪些输出文件。
- 是否能从项目依赖匹配 SIF。
- runner 配置是否缺失。

### 第二步：确认 runner 配置

如果用户没有提供 `DISPLAY_NAME`、`CPU`、`GPU`、`NETWORK`、`SIF`，并且没有授权自动选 SIF：停止，询问配置。

如果用户授权自动选 SIF：查 `references/sif_registry.json`。如果无法唯一确定，列候选让用户确认。

### 第三步：设计适配策略

根据项目情况选择：

- **函数调用式适配**：原项目有 `main(args)`、`run(...)`、`predict(...)`、`process(...)` 等函数，优先导入调用。
- **命令行包装式适配**：原项目是成熟 CLI，优先 `subprocess.run()` 调用，减少重构风险。
- **拆分 utils 式适配**：原脚本大量顶层代码，需要把业务函数放入 `utils/`，平台入口只做参数解析、调用、报告和返回。

### 第四步：生成平台文件

必须补齐或更新：

```text
config/configure.json
config/input.json
config/long_description.md
demos/demos.json
<入口文件>.py
Makefile
```

已有 `Makefile` 时不要覆盖，除非版本号或 APP_NAME 明显不对且需要修正。

### 第五步：审查

完成后检查：

- Python 语法是否通过。
- JSON 是否有效。
- `input.json` 是否通过 `input_form_cli.py validate`。
- `SIF` 是否来自用户或注册表。
- `CPU/GPU/NETWORK` 是否已写入 `runner`。
- `@tool_io(outputs)` key 与 `return` key 是否一致。
- `input.json fields[].name` 与 `kwargs['args']` key 是否一致。
- 所有输出是否写入当前工作目录。
- 是否生成中文 `report.md`。
- 是否没有硬编码本机绝对路径。
- 是否没有把无关参数塞进 `input.json`。
- 是否存在 `demos/demos.json`，且 Demo 的 `value` 与 `input.json` 字段一致、引用文件真实存在。

## 用户常见说法与行为

| 用户说法 | 正确行为 |
| --- | --- |
| “把这个项目改成平台 kit” | 先分析项目；若无 runner 配置，先问配置或询问是否按 SIF 注册表选择。 |
| “你帮我根据现有 SIF 选” | 查注册表，匹配依赖和用途；唯一匹配则采用，否则列候选。 |
| “SIF 用 xxx，CPU 4，GPU 1” | 直接使用用户配置继续改造。 |
| “先随便写一个 example” | 不允许。SIF 不能写 example/TODO/待定。 |
| “入口就用 main.py” | 仍需检查项目真实入口；入口文件名不固定。 |
| “不用 report.md” | 平台 Kit 仍必须生成中文 report.md。 |

## 资源

- 详细迁移规则：`references/project-to-kit-porting-rules.md`
- SIF 注册表：`references/sif_registry.json`
- SIF 注册表维护脚本：`scripts/sif_registry_cli.py`
- 表单知识库：`references/input_form_catalog.json`
- 表单辅助脚本：`scripts/input_form_cli.py`
- 项目分析脚本：`scripts/porting_analyzer.py`
- Demo 辅助脚本：`scripts/demo_cli.py`
- Demo 模板目录：`assets/templates/demos/`
- 适配入口模板：`assets/templates/runner_adapter_template.py`
- 配置询问模板：`assets/templates/config_request_template.md`
