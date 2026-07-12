---
name: asterfire-agent-skill
description: Use when developing, reviewing, debugging, refactoring, packaging, or validating AsterFire ATP Agent Toolbox tools；适用于 Tool 子类、docstring、calltype、hooks、resources、@tool_io、文件交接、Agent config、demos 与 adam-cli build 暴露。
---

# AsterFire Agent Toolbox Skill

本 Skill 面向 AsterFire Adam Tool Protocol (ATP) 的 **Agent Toolbox** 开发。它服务于由多个 `adam_community.tool.Tool` 类组成的 Agent 工具箱，覆盖 Tool 暴露、Agent 可见 docstring、parser/build 元数据、runtime hooks、package config、demos 以及 `adam-cli build` 打包边界。

这不是 Kit 开发 Skill。涉及 Kit 专属入口、配置、表单、demo 或 report 规则时，应使用 AsterFire Kit skills。

- adam-community PyPI README 快照：`references/adam-community/README.md`
  - 来源：`https://pypi.org/project/adam-community/`
  - 刷新来源：`https://pypi.org/pypi/adam-community/json`

当官方 ATP 行为与本地项目记录冲突时，优先采用官方 ATP 行为；只有本地文档明确记录为兼容性选择时，才按本地记录执行。

## 使用场景

当工作涉及以下内容时使用本 Skill：

- 创建、修改或审查继承自 `adam_community.tool.Tool` 的类。
- 编写或审查 Tool class docstring 以及 JSON-schema-visible arguments。
- 实现或审查 `call(self, kwargs)`、`inputShow`、`resAlloc`、`monitor`、`outputShow` 或 `summary`。
- 判断或审查 `calltype="bash"` 与 `calltype="python"` 的使用。
- 声明或审查 `@tool_io(inputs=..., outputs=...)` 契约。
- 配置 parser/build 可见元数据，例如 `DISPLAY_NAME`、`CONDA_ENV`、`SIF`、`NETWORK`、`CPU`、`GPU`、`MEM_PER_CPU`、`PARTITION`。
- 审查 Agent package 中的 `config/`、可选但强烈推荐的 `demos/`，以及最终 `adam-cli build` 打包内容。
- 调试工具未暴露、默认值错误、输出静默、文件交接失败、隐藏异常或 package contents 与预期不一致等问题。

不要把本 Skill 作为 AsterFire Kit 工作的主规则源。Kit 项目应先使用 Kit skill；只有共享的 `Tool` 与 `@tool_io` 机制需要交叉确认时，才补充使用本 Skill。

## Agent 与 Kit 边界

| 领域 | Agent Toolbox | Kit |
|---|---|---|
| 平台形态 | 一个 toolbox 文件集暴露多个 `Tool` 类。 | 单个平台入口类，通常是 `runner(Tool)`。 |
| `adam-community==1.2.5` build 所需 config | `config/configure.json`、`config/initial_assistant_message.md`、`config/initial_system_prompt.md`、`config/long_description.md`。 | `config/configure.json`、`config/long_description.md`、`config/input.json`。 |
| `demos/` | build 可选；生产级、面向用户的 Agent 强烈推荐提供，存在时会被打包。 | Kit skills 中属于强发布质量预期。 |
| 结构化输出 | Bash Toolbox tools 使用 `self.declare_outputs(...)`；Python tools 仍需打印用户/LLM 可见状态。 | Python Kit/DAG tools 返回与 `@tool_io(outputs=...)` 匹配的 flat dict。 |
| SIF | 直接赋值时是 parser-visible class metadata；Agent Toolbox 是否强制要求取决于项目/平台策略。 | Kit skills 对 SIF 有独立确认要求。 |

## Tool 执行链路

设计 Tool 时，应让 Agent 能从 docstring 判断调用时机，并让每个 hook 给用户和 LLM 留下清晰反馈。ATP 执行链路可按下列顺序检查：

```text
docstring
  -> Agent 判断是否以及如何调用 Tool
  -> inputShow(...)
  -> resAlloc(...)
  -> call(...)
  -> monitor(...)
  -> outputShow(...)
  -> summary(...)
```

## Tool 类契约

- 每个对外暴露的 ATP tool 都必须继承 `Tool`。
- 具体暴露类必须在 class bases 中直接列出 `Tool` 或 `*.Tool`；通过中间基类间接继承的 class 不会作为平台可见 Tool 暴露。
- `call(self, kwargs)` 必须存在。
- Tool 参数从 `kwargs["args"]` 读取。
- 除非上游契约明确要求绝对路径，文件输出路径应保持为任务工作目录下的相对路径。
- 当输入很长或结构很复杂时，优先使用文件交接，而不是让 LLM 填写复杂嵌套参数。
- 使用 Adam file state（`trackPath` / `getState("files")`，或项目 wrapper）做持久文件浏览和兼容交接。
- 不要把 `kwargs["tool_data"]` 当作持久跨 Tool 存储，也不要把它当作 DAG 结构化输出通道。

## Docstring 契约

Class docstring 是 Agent-facing API。当前 `adam-community==1.2.5` parser 行为如下：

- class docstring 必须紧贴 class 定义。
- 使用 `docstring_parser.parse(...)` 解析。
- `function.description` 只接收 `docs.short_description`。
- `function.parameters` 接收 `docs.params`。
- `docs.long_description` 会从 parse/build metadata 中丢弃。
- 参数描述会保留，因此 `[PATH_REQUIRED]` 这类 marker 对 Agent 侧消费者可见。

规则：

- short description 必须是一句完整的能力与使用场景契约。
- 参数级约束放在对应参数项描述中；Google `Args:` 与 reST `:param ...:` 等 `docstring_parser` 支持的格式都可以被解析，但项目应选择一种风格并保持一致。
- 不要把必要的 Agent-facing 语义只写在 long-description 段落里。
- 优先使用 parser-safe types，例如 `str`、`int`、`float`、`bool`、`List[str]`、`Dict[str, str]`、`Optional[str]`、`Union[str, int]`、`Literal[...]`。
- `Optional[T]` 这种 type spelling 不一定让 parser output 把参数视为非必填；是否进入 `parameters.required` 以实际 `adam-cli parse` / `docstring_parser` 输出为准。
- 每个必填路径参数的描述必须以 `[PATH_REQUIRED]` 开头。
- `[PATH_REQUIRED]` 是 Agent-facing marker，不替代 runtime path validation。
- 长参数目录、调参说明和大示例应放到可检索的项目 references 或 knowledge docs 中，再通过 short description 或参数描述指向检索路线。

## `@tool_io` 契约

- 用 `@tool_io(outputs={...})` 声明 DAG-visible outputs。
- 使用稳定 port names 和简洁 port descriptions，优先写成 `(Type, "description")`。
- 文件输出优先使用预定义 file aliases，或使用 `Annotated[str, FileType(...)]`。
- 标量输出必须是 JSON-serializable scalar types。
- 返回或声明一个 flat dict，其 keys 必须与 `@tool_io(outputs={...})` keys 完全一致。

需区分 parser 与 runtime 的契约形态：`adam-cli parse` 会把文件和标量 declared outputs 都放入 `function.io_contract.outputs`，标量使用 `{"raw_type": "float"}` 这类形状；runtime `get_tool_contract()` 会把标量 outputs 分离到 `output_params`。

Runtime 映射：

| Tool 风格 | 执行行为 | 结构化输出规则 |
|---|---|---|
| Bash Toolbox | `call()` 返回 bash script。 | 返回 script 前调用 `self.declare_outputs(flat_dict)`。 |
| Python Kit/DAG | `call()` 以 Python 运行，平台运行时记录 declared outputs。 | 返回与 declared output ports 匹配的 flat dict。 |
| 无 DAG outputs 的 Python Agent utility | 旧 hook runtime 可能忽略任意 return 值。 | 打印 Agent 必须感知的值。 |

不要把 declared output values 用相同 port names 复制进 `kwargs["tool_data"]`。如果 `outputShow` 或 `summary` 需要展示状态，应使用 hook-local fields，例如 `generated_files`、`display_files` 或领域内状态字段。

## Build 与 Package 暴露

对于 `adam-cli` / `adam-community==1.2.5`：

- `adam-cli parse .` 扫描 `*.py`，跳过文件名以 `_` 开头的文件，并跳过路径中包含 `config` 的文件。
- parser 只暴露文件中显式直接继承 `Tool` 或 `*.Tool` 的 class；间接继承不会让 Tool 平台可见。
- 若要让某字段进入 parser metadata，必须直接赋值在具体 Tool class 上：`SIF`、`NETWORK`、`GPU`、`CPU`、`MEM_PER_CPU`、`PARTITION`、`CONDA_ENV`、`DISPLAY_NAME`。这些资源字段的必填与建议边界由后文 `Resource Metadata` 的资源策略说明决定。
- Mixin 或 base class 继承来的 metadata 可服务 runtime 代码复用，但对 build metadata 不可见。
- `calltype` 是 Python runtime 处理的行为，不是当前 parser metadata。
- `@tool_io` metadata 会作为 `function.io_contract` 对 parser 可见。

`adam-cli build .` 会先运行 parser，再验证 package files：

- `config/configure.json` 必须存在，并包含 `name`、`version`、`display_name`。
- 如果 `configure.json` 省略 `type`，build 会把 package 视为 `agent`。
- Agent/default packages 需要 `config/initial_assistant_message.md`、`config/initial_system_prompt.md` 和 `config/long_description.md`。
- Kit packages 需要 `config/long_description.md` 和 `config/input.json`。

Build zip 会包含：

- build 目录下所有 Python 文件；注意这包括 parser 会跳过的 `_*.py` 和 `config/*.py`，因此隐藏工具、临时代码或敏感信息不能依赖 parser skip 规则避免进入 zip。
- 所有文件名不以 `_` 开头的 `.md` 和 `.jinja2` 文件。
- `config/configure.json`。
- 如果存在 `demos/`，包含其下所有文件。
- 如存在 `config/icon.svg`、`config/icon.png`、`config/icon.jpg` 或 `config/icon.jpeg`，则包含该 icon。
- 对 Agent/default packages：存在时包含 `initial_assistant_message*.md`、`initial_system_prompt*.md` 和 `long_description*.md`。
- 对 Kit packages：存在时包含 `long_description*.md` 和 `input.json`。

Package 规则：

- 不要把凭据、token、API key、私有 URL 或本地敏感信息放入 `config/`、`demos/`、docs、templates 或任何可能被打包的文件。
- `adam-cli parse` 的暴露范围不等于 `adam-cli build` 的打包范围；`_*.py`、`config/*.py` 和其他非暴露 Python 文件仍可能被打包，需要用项目级 package-scope checks 管控。
- `demos/` 对上游 Agent build 是可选项，但生产级、面向用户的 Agents 强烈推荐提供。
- 如果存在 `demos/`，保持 `demos/demos.json` 与被引用文件使用包内相对路径，并控制文件大小，适合作为用户示例。
- `adam-cli build` 会打包 demos，但不会验证 demo schema 或引用文件完整性；需要项目级 checks 补足。
- 修改单个 Tool 文件后，用 `adam_community.cli.parser.parse_python_file(Path("changed_file.py"))` 验证；修改 package-level 文件后，用 `make build`、`adam-cli build .` 或仓库 package checks 验证。

## Audit Scripts

本 Skill 随附 `scripts/check_atp_tool_integrity.py`，用于把 `adam-cli parse` / 项目级 `make parse` 暴露检查与通用 Tool 完整性审查结合起来。
推荐验证顺序:

```bash
python3 scripts/check_atp_tool_integrity.py --root . --parser-command "adam-cli parse ." --strict-parser
```

如果项目像 ABACUS 一样通过 `make parse` 做 staging，应改用:

```bash
python3 scripts/check_atp_tool_integrity.py --root . --parser-command "make parse" --strict-parser
```

该脚本不会替代 `adam-cli parse`；parser output 仍是 Tool 是否平台可见的事实来源。脚本额外检查 `call()`、strict kwargs、`calltype`、`@tool_io` output 落地、docstring 风险和 `tool_data` 误用等 parser 不覆盖的契约。

项目特定规则应由仓库本地 wrapper 承载，不应写入通用分发版 skill。

## Runtime Hooks

| `calltype` | 执行行为 | `call` 应做什么 |
|---|---|---|
| 无 `@tool_io(outputs=...)` 的 `"bash"` | Runtime 执行返回的 bash script。 | 返回完整 script string。 |
| 有 `@tool_io(outputs=...)` 的 `"bash"` | Runtime 执行 script 并读取 `_outputs.json`。 | 调用 `self.declare_outputs(flat_dict)`，再返回 script string。 |
| 无 `@tool_io(outputs=...)` 的 `"python"` | Runtime 以 Python 执行 tool。 | 打印 LLM 必须感知的值。 |
| 有 `@tool_io(outputs=...)` 的 `"python"` | DAG/Kit runtime 记录 structured outputs。 | 返回匹配 declared outputs 的 flat dict，并打印有用状态。 |

- 打印 generated paths、关键结果、warnings 和 failure causes。会产出文件但什么都不打印的 Tool，容易让 Agent 误以为没有发生任何事。
- 当默认 raw script display 太嘈杂或可能泄露敏感信息时，覆盖 `inputShow`。
- `outputShow` 面向用户，应简洁；在支持时返回正确 file list。
- `summary` 面向 LLM，应简洁、结构化，并截断长日志。
- 仅当资源依赖输入或 runtime scheduling 需要自定义逻辑时，才实现 `resAlloc(self, kwargs)`。如果固定 class metadata 已经准确，优先使用默认 `Tool.resAlloc`。
- 只有长任务需要且当前平台支持相关字段时，才使用 `monitor`。
- 只有在验证 runtime 支持后，才依赖平台支持的可变 `kwargs` 字段，常见字段包括 `tool_data`、`tip` 和 progress 相关字段。

## Strict kwargs 契约

ATP hook 调用按约定提供下列 kwargs。对这些必备 key 使用直接 dict access `kwargs["key"]`；不要用 `kwargs.get(key, default)`。

| Hook | Required kwargs |
|---|---|
| `inputShow` | `args`、`files`、`message`、`user`、`task_id` |
| `resAlloc` | `args`、`files`、`message`、`user`、`task_id`、`tool_data`、`tip` |
| `call` | 同 `resAlloc` |
| `monitor` | 上述字段外加 `run_time`、`progress` |
| `outputShow` | 上述字段外加 `stdout`、`stderr`、`exit_code` |
| `summary` | 同 `outputShow` |

原因：

- 缺失必备 key 表示平台与 Tool 的 hook 契约已损坏；`kwargs["key"]` 会尽早暴露问题。
- `kwargs.get(key, default)` 会静默掩盖契约缺失，并把失败推迟到更难诊断的下游代码。

嵌套 optional data 仍可使用 `.get`，例如 `kwargs["args"].get("optional_param")` 或 `(kwargs["tool_data"] or {}).get("path")`。

## Resource Metadata

- `adam-community==1.2.5` 中运行时 `Tool` subclass 默认 metadata：`GPU = 0`、`CPU = 1`、`MEM_PER_CPU = 4000`、`PARTITION = "gpu_3090"`、`CONDA_ENV = "base"`、`calltype = "bash"`、`DISPLAY_NAME = class name`。
- `adam-cli parse` 在 class 未直接赋值时会把 `partition` 暴露为 parser 默认值 `gpu`；这与运行时默认 `PARTITION = "gpu_3090"` 不完全相同。因此资源 metadata 需要以 parser output 为事实来源验证。
- 当前平台实践中，`PARTITION` 更接近 tag-like / 兼容性 metadata，不是主要资源调度接口。开发者不应把本地 Slurm partition、SAI 分区名或其他集群名写进通用 ATP Tool 作为调度修复。
- 调度语义应保持保守：`GPU` 请求决定 GPU 资源路径；CPU-only 工具主要受 `CPU` 请求影响；GPU 工具的 CPU 可能由平台按服务器策略自动分配，此时 Tool-level `CPU` 不一定是独立有效的调度杠杆。
- 当 build/parser metadata 重要时，每个具体暴露 Tool class 都应直接赋值 `GPU`、`CPU`、`MEM_PER_CPU`、`CONDA_ENV`、`DISPLAY_NAME` 等资源或展示 metadata。`PARTITION` 可按项目策略作为 tag-like metadata 保留，但不要在通用 Skill 中写死资源路由策略。
- `check_atp_tool_integrity.py --strict-metadata` 是显式的项目/发布策略模式，会要求所有 parser-visible metadata 字段直接赋值，包括 `PARTITION`；只有项目有意采用这套发布门禁时才启用。默认通用指导仍把 `PARTITION` 视为 tag-like / 兼容性 metadata，而不是硬调度接口。
- `SIF` 和 `NETWORK` 直接赋值时 parser-visible；Agent Toolbox 是否强制要求它们取决于项目/平台策略。
- Mixin 只用于 runtime behavior reuse，不用于 build-time exposure。
- 提供 hooks 的 mixins 放在 `Tool` 前：`class MyTool(_RuntimeMixin, Tool, calltype="python")`。
- 避免间接暴露基类，例如 `BaseTool`、`ToolBase` 或 `AbstractTool`；它们会破坏静态 direct-`Tool` requirement。

## Report Markdown 渲染

当 Tool 或 Kit 写 Markdown report 时，遵循 AsterFire report renderer 的同一渲染契约：

- `molstar` 只用于交互式 3D 结构渲染。仅对真实结构文件使用，例如 `.pdb`、`.cif`、`.mmcif` 或 `.sdf`；其他结构格式必须先确认 frontend renderer 支持。
- 只有当多个结构文件需要在同一 3D scene 中比较时，才把它们放入同一个 `molstar` block。
- 不要用 `molstar` 展示 plots、scalar charts、screenshots 或 data images。Band、DOS、PDOS、phonon spectra、optical spectra、convergence curves、heatmaps 等二维结果应生成 PNG/JPG/SVG/WebP 并用 Markdown 图片语法嵌入。
- `mdtraj` 只用于平台可回放的 converted trajectory artifacts，例如 `.mdtraj`。
- 小型表格摘要使用标准 Markdown tables。
- 不要把 stdout/stderr 或完整 logs 直接铺进 `report.md`；应写入 `run.log`、`stdout.log` 或 `stderr.log` 等文件，再简要引用。

示例：

````markdown
```molstar
./relaxed_structure.cif
```

![Band structure](./band.png)

![Density of states](./dos.png)

```mdtraj
./trajectory.mdtraj
```
````

## Review Checklist

Tool 暴露：

- [ ] 具体暴露 class 直接继承 `Tool` 或 `*.Tool`。
- [ ] Class docstring 紧贴 class definition。
- [ ] Short description 单独就能说明工具做什么以及何时使用。
- [ ] Agent-visible inputs、constraints、outputs、generated files 和容易歧义的示例写在 `Args` 描述或 short description 中。
- [ ] 没有把必要 Agent-facing 语义只放在 docstring long description 中。
- [ ] 每个必填路径参数描述以 `[PATH_REQUIRED]` 开头。
- [ ] Runtime path existence 和 content checks 位于 `call` 中。
- [ ] 需要进入 parser metadata 的资源字段直接赋值在具体 Tool class 上。
- [ ] Parser check 显示预期 tools、params、metadata 和 `io_contract`。

Runtime：

- [ ] 存在 `call(self, kwargs)`，并从 `kwargs["args"]` 读取参数。
- [ ] `tool_data`、`tip`、`stdout`、`stderr`、`exit_code` 等 required hook kwargs 使用 `kwargs["..."]`，不用 `kwargs.get(...)`。
- [ ] Bash tools 返回 script。
- [ ] 有 declared outputs 的 bash tools 调用 `self.declare_outputs({...})`。
- [ ] Python/DAG tools 有 declared outputs 时返回 keys 匹配的 flat dict。
- [ ] 不把 declared output values 用相同 port names 复制进 `kwargs["tool_data"]`。
- [ ] 有用状态、warnings、generated paths 和关键结果出现在 `stdout`/`stderr` 中。
- [ ] `inputShow` 简洁，且不泄露 raw scripts 或敏感信息。
- [ ] `outputShow` 在支持时返回正确 file list。
- [ ] `summary` 简洁、结构化，并截断长日志。

Agent package：

- [ ] Agent package config files 与 package type 匹配：default Agent packages 有 `configure.json`、`initial_assistant_message.md`、`initial_system_prompt.md` 和 `long_description.md`。
- [ ] `config/configure.json` 包含 `name`、`version` 和 `display_name`。
- [ ] `config/`、`demos/`、Markdown docs、templates 和 packaged Python 文件不包含可分发敏感信息。
- [ ] 面向生产/用户的 Agents 提供 `demos/`，除非有明确记录的省略理由。
- [ ] 如果存在 `demos/`，demo paths 为包内相对路径，且引用文件会被包含。
- [ ] 已检查 final zip contents，或已运行项目 package-scope checks。

## 常见失败

- Tool 在 Python 中可运行但 package metadata 中缺失：确认具体 class 直接继承 `Tool`，且文件名不以 `_` 开头。
- Package metadata 显示默认值错误：在具体 Tool class 中直接赋值 resource metadata，不要只写在 mixin 中。
- Agent 无法判断何时调用工具：强化 short description 和参数描述。
- Tool 运行了但 Agent 认为没有发生任何事：打印关键结果和 generated files，并实现 `summary`。
- Python-calltype tool 返回了值但没有输出可见：用 `print(...)` 提供 Agent-visible feedback。
- DAG workflow 看不到 declared output：Python tools 必须返回 flat dict；bash tools 必须调用 `declare_outputs`。
- 用户看到巨大的 raw script：覆盖 `inputShow`。
- Frontend 不显示文件：从 `outputShow` 返回真实 file list。
- 后续 tools 找不到输出：使用 explicit args、`trackPath` / `getState("files")`、registered files 或稳定 file paths；不要依赖旧 `tool_data`。
- `adam-cli build .` 因无关临时代码失败：移除或移动 scratch directories，因为 parser/build 会扫描大量 `*.py` 文件。
- 已发布 Agent 缺少 onboarding 或 demo 体验：维护 `initial_*`、`long_description*`、icon 和强烈推荐的 `demos/`。
- 凭据通过 package metadata 泄露：`config/`、`demos/`、docs、templates 和 packaged Python 文件都可能进入 build zip。
- Kit 规则被误套到 Agent Toolbox：不要要求 Agent packages 必须有 `config/input.json` 或单一 `runner(Tool)`；遇到 Kit 工作应切换到 Kit skill。
