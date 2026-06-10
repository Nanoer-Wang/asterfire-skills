# Asterfire Kit 开发规则参考

## 目录

- 入口文件定位规则
- SIF 指定与注册表
- `input.json` ↔ `kwargs['args']` 映射关系
- input.json 表单知识库
- 最小输入原则
- `@tool_io(outputs)` ↔ `return dict` 映射关系
- `report.md` 规则
- 文件路径规则
- Makefile 规则
- demos 目录与 demos.json 规则
- 打包规则
- Workflow 与 scatter/gather
- 审查 checklist

## 入口文件定位规则

已有 Kit 的 Python 入口文件不一定叫 `main.py`。必须以代码内容为准：

1. 搜索项目中所有 `.py` 文件。
2. 找到包含 `class runner(Tool)` 的文件。
3. 若只有一个匹配文件，它就是平台入口文件。
4. 若有多个匹配文件，不能猜测，需要让用户明确选择。
5. 若没有匹配文件，说明项目尚未创建入口；只有在已经明确 SIF 后，才能创建新的入口文件。

推荐命令：

```bash
grep -R "class runner *( *Tool *)" -n . --include="*.py"
```

## SIF 指定与注册表

每个 Kit 的 `runner` 类必须显式指定 SIF：

```python
class runner(Tool):
    DISPLAY_NAME = "Example Kit"
    NETWORK = False
    CPU = 2
    GPU = 0
    SIF = "asterfire-base:1.0.0"
```

硬性规则：

- 不指定 SIF 时，不写入口代码，并直接告诉用户，让用户必须选择一个SIF。
- `SIF` 不能是空字符串、`None`、`TODO`、`待定`、`example` 等占位值。
- 修改已有 Kit 时，如果 `runner` 中缺失 `SIF`，必须补齐；补齐前必须知道真实镜像。
- `CPU`、`GPU`、`NETWORK` 应优先参考 `references/sif_registry.json` 中对应 SIF 的默认资源。
- SIF 用途要与 Kit 功能匹配。例如 PDB 验证工具不能随便使用只包含 GROMACS 的生产镜像，除非该镜像确实包含验证所需环境。

SIF 注册表文件：

```text
references/sif_registry.json
```

注册表字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `sif` | string | 是 | 镜像名称或平台可识别的 SIF 标识 |
| `owner` | string | 是 | 负责人或维护团队 |
| `purpose` | string | 是 | 该镜像主要用途 |
| `environment` | array | 是 | 语言、库、系统环境等 |
| `contains` | array | 否 | 主要命令行工具、软件、包 |
| `default_resources` | object | 是 | 默认 CPU、GPU、NETWORK |
| `tags` | array | 否 | 检索标签 |
| `updated_at` | string | 是 | 最近更新时间，格式建议 `YYYY-MM-DD` |
| `notes` | string | 否 | 备注 |

示例：

```json
{
  "sif": "asterfire-base:1.0.0",
  "owner": "平台维护组",
  "purpose": "最小 Kit 示例和基础 Python 文件处理",
  "environment": ["Python 3.12", "adam_community", "Biopython"],
  "contains": ["python", "biopython","bash"],
  "default_resources": {
    "cpu": 2,
    "gpu": 0,
    "network": false
  },
  "tags": ["example", "template", "base"],
  "updated_at": "2026-05-09",
  "notes": "模板示例。真实项目中请替换为平台已构建并可用的 SIF。"
}
```

## `input.json` ↔ `kwargs['args']` 映射关系

`config/input.json` 是前端表单和运行参数的契约。每个 `fields[].name` 都会成为 `kwargs['args']` 中的 key。Python 代码不得猜测、改名或使用另一个拼写。

在写 `input.json` 前，必须先查阅表单知识库：

```text
references/input_form_catalog.json
```

该文件把平台已支持的表单结构、字段类型、验证规则、条件显示、数组字段、级联字段和常见最小任务模板整理成机器可读 JSON。开发时优先从 `task_templates` 选择最小模板；没有合适模板时，再从 `field_recipes` 组合；仍不够时，才按 `supported_field_types` 手写字段。

辅助脚本：

```bash
# 列出支持字段类型
python scripts/input_form_cli.py list-types

# 列出内置最小模板
python scripts/input_form_cli.py list-templates

# 按关键词推荐模板
python scripts/input_form_cli.py suggest pdb validator

# 直接写出 PDB 验证 Kit 的最小表单
python scripts/input_form_cli.py write-template pdb_validator config/input.json

# 校验已有表单
python scripts/input_form_cli.py validate config/input.json
```

正确映射：

```json
{
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

```python
args = kwargs["args"]
input_pdb = args["input_pdb"]
```

required 字段必须同时出现于：

```json
{
  "formRules": {
    "required": ["input_pdb"]
  },
  "fields": [
    {
      "name": "input_pdb",
      "validation": {
        "required": true
      }
    }
  ]
}
```

字段类型说明：

| type | 用途 | 约束 |
| --- | --- | --- |
| string | 单行文本 | 用于短参数、名称、ID |
| text | 多行文本 | 用于长文本、说明、序列 |
| number | 数值 | 建议设置 min、max、step |
| boolean | 布尔开关 | 默认值写入 `defaultValues` |
| select | 单选 | 只有确实需要用户选择方法时才使用 |
| multiselect | 多选 | 默认值通常为数组，避免无关标签字段 |
| file | 文件上传 | 建议写 `accept` 和 `message` |
| date | 日期 | 只有任务需要日期时才使用 |
| object | 对象 | 仅在确实需要复杂 JSON 参数时使用 |
| array | 数组 | 仅在确实需要列表参数时使用 |
| cascader | 级联选择 | 仅在确实有层级选择需求时使用 |

条件显示字段使用 `conditional`：

```json
{
  "name": "strict_mode",
  "label": "严格模式",
  "type": "boolean",
  "description": "启用后会把格式警告视为失败。",
  "validation": {
    "required": false
  },
  "conditional": {
    "field": "enable_advanced",
    "operator": "equals",
    "value": true
  }
}
```

支持的 `operator`：`equals`、`not_equals`、`contains`、`not_contains`、`greater_than`、`less_than`、`in`、`not_in`。

## input.json 表单知识库

表单知识库文件：

```text
references/input_form_catalog.json
```

核心内容：

| 区域 | 作用 |
| --- | --- |
| `form_config` | 顶层结构定义：`formName`、`description`、`formRules`、`fields`、`defaultValues` |
| `supported_field_types` | 平台支持字段类型：`string`、`text`、`number`、`boolean`、`select`、`multiselect`、`file`、`date`、`object`、`array`、`cascader` |
| `conditional_display` | 条件显示规则与操作符：`equals`、`not_equals`、`contains`、`not_contains`、`greater_than`、`less_than`、`in`、`not_in` |
| `minimal_input_generation_rules` | 生成最小表单时必须遵守的裁剪规则 |
| `field_recipes` | 常用字段配方，例如 `input_pdb`、`input_csv`、`complex_pdb`、`ligands_mol2_array` |
| `task_templates` | 常见 Kit 的最小表单模板，例如 `pdb_validator`、`cif_to_pdb_converter`、`csv_model_baseline` |

生成 `input.json` 的推荐流程：

1. 从用户需求和入口代码确定真实需要的 `kwargs['args']` key。
2. 用 `python scripts/input_form_cli.py suggest <关键词>` 查询是否有合适模板。
3. 有模板时用 `write-template` 写出，再删除不需要的字段。
4. 没有模板时，从 `field_recipes` 挑字段组合。
5. 字段配方不够时，按 `supported_field_types` 手写字段，但不得创造新 type。
6. 用 `validate` 做基础校验。

注意：知识库提供的是“平台支持的表单能力”和“常见最小模板”，不是让每个 Kit 都包含所有字段类型。真实 Kit 仍必须按最小输入原则裁剪。

## 最小输入原则

开发或重构 `input.json` 时先问：这个字段是否真的需要用户填写？

保留字段：

- 代码运行必需的输入文件、文本、数值或开关。
- 用户在不同运行中确实会调整的参数。
- 会显著影响结果的科学参数、算法参数或资源参数。

删除字段：

- 纯示例字段，如 `title`、`tags`、`metadata`、`items`。
- 和当前工具无关的高级参数。
- 前端展示用但代码不用的字段。
- 可以由代码自动推断的字段。

PDB 验证 Kit 的最小表单示例：

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

## `@tool_io(outputs)` ↔ `return dict` 映射关系

`@tool_io(outputs={...})` 是平台输出端口契约，`call()` 的返回字典是运行时真实产物契约。二者 key 必须完全一致。

正确：

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
        return {
            "output_file": "result.txt",
            "report": "report.md",
            "success": True,
        }
```

错误：

```python
@tool_io(outputs={"output": TXTFile})
class runner(Tool):
    def call(self, kwargs):
        return {"output_file": "result.txt"}
```

即使只返回一个输出，也必须返回字典：

```python
return {
    "report": "report.md",
}
```

不要返回字符串、列表、Path 对象或自定义对象。

## `report.md` 规则

每次 Kit 运行都必须在当前工作目录生成 `report.md`。报告面向平台用户，不是日志转储；它的目标是让用户快速知道任务做了什么、结果在哪里、主要结果如何理解，以及下一步还能怎么分析。

必须包含：

- 运行概览：成功、失败或部分成功；任务名称、版本、关键输入摘要。
- 方法说明：说明本次调用的核心方法、模型或外部程序，以及关键参数含义。
- 结果展示与说明：直接展示重要结果，解释数值、表格或结构结果代表什么。
- 可视化结果：结构文件、图片或由数据生成的图必须嵌入报告。
- 如何查看结果：说明主要输出文件在哪里、哪些文件最值得优先打开、日志文件在哪里。
- 后续分析建议：给用户 2-5 条可执行建议，例如进一步筛选、结构检查、参数复核或下游分析。

禁止：

- 不要在 `report.md` 中直接展示 stdout/stderr 全文、长命令日志、Traceback 堆栈或大段调试输出。
- 不要把 `report.md` 写成纯文件清单；主要结果必须有解释。
- 不要只说“请下载结果查看”，重要结果应在报告中直接可见。

推荐结构：

```markdown
# 运行报告

## 运行概览

| 项目 | 内容 |
| --- | --- |
| 运行状态 | 成功 |
| Kit 版本 | 1.0.1 |
| 主要输出 | result.csv / best_structure.pdb |

## 方法说明

本次运行使用……方法处理输入文件。关键参数含义如下：……

## 结果展示与说明

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| score | -8.6 | 数值越低通常表示…… |

## 可视化结果

```molstar
./best_structure.pdb
```

![结果图](./score_distribution.png)

## 如何查看结果

主要结果文件为 `result.csv`；结构文件可在上方交互式窗口查看，也可下载 `best_structure.pdb`。
详细运行日志保存在 `run.log`，用于排错，不在本报告中展开。

## 后续分析建议

- 建议优先检查排名靠前的候选结构。
- 建议结合原始输入和关键参数复核结果合理性。
```

报告中的路径优先使用当前工作目录相对路径。报告内容用中文。

## `report.md` 渲染规范

Kit 生成 `report.md` 时，必须根据输出文件类型使用对应的平台渲染方式。不要再把“是否渲染结构/图片”作为前置确认问题；只要输出中存在可展示结果，就默认展示。

### 结构文件 → 使用 molstar 代码块（交互式 3D 展示）

强制覆盖格式：`.pdb`, `.cif`, `.mmcif`, `.sdf`。
可按平台能力扩展：`.mol2`, `.pdbqt`, `.gro`。

单个结构文件写法：

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

要求：

- 只要主要输出结果中包含结构文件，就必须在 `report.md` 中出现 `molstar` 代码块。
- 同一体系的多个构象、多个候选或蛋白-配体组合，需要同空间对比时放在同一个块中。
- 结构文件路径使用相对路径，优先写 `./filename.pdb`。
- 在结构块前后用文字说明结构代表什么，例如“排名第一的候选构象”“优化后的复合物结构”。

### 轨迹文件 → 使用 mdtraj 代码块（交互式轨迹回放）

需要先将轨迹转为 `.mdtraj` 格式（使用 grotoxyz 等工具将 GRO 轨迹转为 PDB + 二进制 XYZ + mdtraj JSON）。

支持格式：`.xtc`, `.trr`, `.dcd`（需先转换为 `.mdtraj`）

写法：

````markdown
```mdtraj
./trajectory.mdtraj
```
````

### 数据图表和图片 → 嵌入 Markdown 图片

适用场景：

- 工具已经生成的 `.png`, `.jpg`, `.jpeg`, `.svg`, `.webp` 图片。
- `.csv`, `.tsv`, `.json`, `.xvg`, `.xpm` 等数据需要图形化解释。
- 分数分布、Top N 排名、RMSD/RMSF/Rg、亲和力热图、置信度曲线、分类统计等用户需要直观看到的结果。

写法：

```markdown
![图表描述](./plot.png)
```

要求：

- 工具已有图片输出时，必须在报告中展示。
- 只有数据文件但有可视化价值时，必须在 Kit 主函数中用 matplotlib 生成 PNG，必要时同时输出 SVG。
- 图片下方要解释这张图的含义，而不是只给图片链接。

### 统计表格 → 标准 markdown 表格

适用场景：汇总数据、参数回显、关键指标对比、Top N 结果列表。

直接在 `report.md` 中用 markdown 表格语法。表格应尽量展示关键结果，不要把超大数据表完整塞进报告；完整数据应保存为 CSV/JSON 文件。

### 日志文件 → 保存为文件，不在报告中展开

命令输出、错误输出、Traceback、外部程序日志应写入 `run.log`、`stdout.log`、`stderr.log` 或工具原生日志文件。

`report.md` 可以在“如何查看结果”中用一句话说明日志文件位置，但不要直接展示日志全文。

## 文件路径规则

- 所有输出必须写入 `os.getcwd()` 或 `Path.cwd()`。
- 返回给平台的文件路径优先使用当前工作目录下的相对路径。
- 输入文件必须做存在性检查。
- 不允许硬编码本机绝对路径，例如 `C:\Users\...`、`/home/user/...`。
- 外部程序路径只能来自 SIF 镜像、`PATH` 环境变量或真正必要的 `input.json` 可选参数。
- 文件上传值可能是字符串、对象或列表；代码应归一化后再使用。

推荐逻辑：

```python
cwd = Path.cwd()
input_path = _as_path(args["input_pdb"])
if not input_path.exists():
    raise FileNotFoundError(f"输入文件不存在: {input_path}")
output_path = cwd / "result.txt"
```

## Makefile 规则

- 项目已有 `Makefile`：不要覆盖。
- 项目没有 `Makefile`：提醒用户缺失，并创建标准模板。
- `Makefile` 至少包含 `build` 和 `clean`。

标准模板：

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

## demos 目录与 demos.json 规则

Asterfire Kit 发布时建议提供 `demos/` 目录，用于前端一键加载示例。`demos/` 与 `config/`、入口 Python 文件、`Makefile` 同级。

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

## 打包规则

`configure.json` 必须包含，并且每次修改 Kit 后都要同步更新版本号：

```json
{
  "name": "example-kit",
  "display_name": "示例 Kit",
  "version": "1.0.0",
  "visible": true,
  "description": "工具说明",
  "type": "kit",
  "tags": ["python", "tool"],
  "cover": "https://example.com/cover.png"
}
```

`type` 固定为 `"kit"`。

额外要求：

- 每次修改 Kit，必须更新 `version`，并同步检查 `Makefile` 里的 `VERSION`。
- `description` 要尽可能详细且用户友好，说明工具能做什么、输入什么、输出什么，但最高不能超过 400 个字符。
- `config/long_description.md` 与 `config/long_description_en.md` 必须同时维护。
- 详情页固定结构：`概述`、`功能`、`输入`、`输出`、`注意事项`、`参考文献`。
- “输入”必须使用表格，列名为：参数、类型、必填、说明。
- “输出”要解释主要结果是什么、怎么看、适合用于什么后续分析。

完成后优先运行：

```bash
python -m py_compile <入口文件>.py
python -m json.tool config/input.json
python -m json.tool config/configure.json
test -f config/long_description.md
test -f config/long_description_en.md
python -m json.tool demos/demos.json
python scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json
make build
```

如果 `adam-cli`、`make` 或平台依赖不可用，必须在交付说明中写明无法运行的原因。无论是否能运行 `make build`，只要修改完成并准备交付，就必须重新打包生成新版 zip。

## Workflow 与 scatter/gather

Workflow 脚本节点仍然执行 Asterfire Tool Protocol 的核心契约：

- 从 `kwargs['args']` 读取输入。
- 输出文件写入当前工作目录。
- 最后 `return dict`。
- `return dict` 的 key 与下游节点变量名一致。

scatter/gather 场景：

- 每个 `scatter_xx` 子目录独立处理。
- 不要假设其他 scatter 目录存在。
- 当前节点只依赖传入参数和当前工作目录。
- 需要汇总时，把文件复制到当前节点工作目录的稳定文件夹中，例如 `gathered_outputs/`。
- 如果下游只接收一个文件，把多个文件打包成 zip 再返回。

## 审查 checklist

项目结构：

- [ ] 存在 `config/configure.json`
- [ ] 存在 `config/input.json`
- [ ] 存在 `config/long_description.md`
- [ ] 存在 `config/long_description_en.md`
- [ ] 存在 `demos/demos.json`，并且 Demo 引用的示例文件真实存在
- [ ] 存在包含 `class runner(Tool)` 的 Python 入口文件
- [ ] 若没有 `Makefile`，已提醒并创建标准模板

SIF：

- [ ] `runner` 类中存在 `SIF`
- [ ] `SIF` 不是空值或占位值
- [ ] `SIF` 已在 `references/sif_registry.json` 中登记，或用户已明确指定
- [ ] SIF 用途和当前 Kit 功能匹配
- [ ] `CPU`、`GPU`、`NETWORK` 与该镜像默认资源基本一致，或有明确理由

Python：

- [ ] 导包后立即写 `@tool_io(outputs={...})`
- [ ] 只有一个平台入口类：`runner(Tool)`
- [ ] `call(self, kwargs)` 是唯一平台入口
- [ ] 所有参数来自 `kwargs['args']`
- [ ] 输入文件存在性检查完整
- [ ] 输出写入 `Path.cwd()` 或 `os.getcwd()`
- [ ] 返回当前工作目录相对路径
- [ ] 生成中文 `report.md`，且包含运行概览、方法说明、结果展示与说明、可视化结果、如何查看结果、后续分析建议
- [ ] 报告中没有直接展示 stdout/stderr 全文或大段运行日志
- [ ] 若主要输出包含 `.pdb/.cif/.sdf`，报告中已有 molstar 块
- [ ] 若输出包含图片或可绘图数据，报告中已有图片展示或 matplotlib 生成图
- [ ] 打印 incoming args、cwd、关键命令、返回码、输出文件存在性，并把详细日志保存为文件
- [ ] 没有硬编码本机绝对路径

契约：

- [ ] `input.json fields[].name` 与 `kwargs['args']` key 完全一致
- [ ] `input.json` 已参考 `references/input_form_catalog.json` 的 `task_templates`、`field_recipes` 或 `supported_field_types`
- [ ] `input.json` 只包含必要字段
- [ ] `python scripts/input_form_cli.py validate config/input.json` 能通过基础校验
- [ ] `@tool_io(outputs)` key 与 `return dict` key 完全一致
- [ ] required 字段同时存在于 `formRules.required` 和 `validation.required`
- [ ] `demos/demos.json` 中每个 Demo 的 `value` 覆盖全部必填字段
- [ ] Demo 中的文件字段使用 `demos/` 下的相对文件名，且文件存在
- [ ] 文件类型不支持时使用 `Annotated[str, FileType(...)]`

交付：

- [ ] Python 语法检查通过
- [ ] JSON 语法检查通过
- [ ] `python scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json` 校验通过
- [ ] 能运行时执行 `make build`
- [ ] 不能运行时说明原因

- [ ] 每次修改后已更新 `config/configure.json` 版本号，并重新打包生成新版 zip。
