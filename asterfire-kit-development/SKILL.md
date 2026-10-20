---
name: asterfire-kit-development
description: 开发、适配、修改、审查和打包 Asterfire Kit；支持从 GitHub 项目、普通 Python/CLI 或零散脚本迁移，维护 runner、表单、输出端口、Demo、报告与发布 ZIP。镜像准备和实际上传调试由 asterfire-platform-devops 统一编排，完整 Workflow 开发由工作流技能负责。
---

# Asterfire Kit 开发与项目适配

本 Skill 是 Kit 代码与包结构的唯一规则入口。已有 Kit 在真实入口上修改；普通项目保留业务模块并增加平台适配层。镜像构建、推送、SIF 转换、上传与平台调试统一按 [DevOps](../asterfire-platform-devops/SKILL.md) 执行，不另起一套发布流程。

## 按任务读取

- 通用开发规则、表单、输出、报告、Demo 与打包：读 [references/kit-development-rules.md](references/kit-development-rules.md)。
- GitHub/脚本/普通项目迁移：再读 [references/project-to-kit-porting-rules.md](references/project-to-kit-porting-rules.md)，可运行 `scripts/porting_analyzer.py`。
- 生成/修改表单前查 `references/input_form_catalog.json`，优先 task_templates 和 field_recipes，使用 `scripts/input_form_cli.py`。
- 镜像名称、版本和可用状态从目标平台实时查询，不维护本地镜像名单。由 DevOps 的 [镜像查询](../asterfire-platform-devops/references/image-discovery.md) 获取候选并核对 SIF 构建状态；项目只记录本次选定镜像及证据。
- 新建模板在 `assets/templates/`：`runner_template.py` 用于新 Kit，`runner_adapter_template.py` 用于项目迁移；配置、Makefile 和 Demo 模板按需复制，不覆盖已有实现。
- 仅需路径/依赖/权重诊断时读 DevOps 的 [镜像阶段](../asterfire-platform-devops/references/image-lifecycle.md)；完整 DAG、scatter 与产物调试读 [Workflow](../asterfire-workflow-development/SKILL.md)。

## 必须保持的契约

1. 平台唯一入口为 `class runner(Tool)` 和 `call(self, kwargs)`，文件名不固定。导包后声明 `@tool_io` 再写 runner；辅助业务函数放在 runner 后或独立模块。多个 runner 时先查现有打包/入口配置，仍无法确定才询问。
2. 输入从 `kwargs['args']` 读取；`input.json fields[].name`、代码读取和 Demo value key 一致。仅暴露必要字段，默认逐项低代码表单，由 runner 生成上游 JSON/YAML；用户明确需要原始配置上传时遵从。
3. 每个输出声明 `(实际类型, 简短中文描述)`；`@tool_io(outputs)` 与返回字典 key 一致，文件用对应 FileType，标量使用真实类型。返回字典实例，不能裸写 `return dict`。所有产物写当前工作目录，优先返回相对路径，检查输入及产物存在性。
4. `runner` 显式包含 DISPLAY_NAME、NETWORK、CPU、GPU、真实可用 SIF；按项目确定资源。发布 ZIP 绑定可用 SIF，不用占位镜像。缺镜像时由 DevOps 确认复用/构建路线；可同时整理业务代码，不能只停在索要 SIF。
5. 依赖、稳定第三方引擎、完整权重和数据库属于镜像；本 Kit 的核心业务模块、runner、前后处理与报告随 ZIP 交付。业务变更只更新 Kit，依赖变化才由 DevOps 重建镜像。
6. 面向用户的说明、表单、Demo 和报告中文优先。维护 configure 中 name/display_name/version/visible/description/type/tags/cover，type 为 kit；description 清楚且不超过 400 字符。修改递增版本，检查 Makefile 版本，不重建已有 Makefile。
7. 同时维护 long_description.md 与 long_description_en.md，按概述、功能、输入、输出、注意事项、参考文献组织，输入用参数表；语言要求沿用现有项目和用户选择。
8. 交付包含真实轻量 demos/demos.json 及其引用文件，值与表单一致。优先迁移原项目官方 examples/tests/README 的可复现案例，覆盖主要模式；缺数据时明确未验证，不写占位 Demo 冒充通过。
9. 每次运行生成专业中文 report.md：运行概览、方法、结果解释、可视化、结果访问和后续建议。结构用 molstar，轨迹按平台能力转换展示，图片 Markdown 嵌入；有绘图价值的数据生成图。详细 stdout/stderr/traceback 放日志文件，报告不展开。
10. 修改后完成语法、JSON、表单、Demo 和输出检查，重新 `adam-cli build .` 交付新版 ZIP；检查包内业务完整且没有环境、权重或凭据。只做本地代码/ZIP时不自动发布；端到端请求由 DevOps 继续上传和轻量调试。

## 本地检查与交接

脚本使用本技能绝对路径，在用户项目目录执行：

```text
python <skill>/scripts/porting_analyzer.py <project> --json-out porting.json --md-out porting.md
python <skill>/scripts/input_form_cli.py validate config/input.json
python <skill>/scripts/demo_cli.py validate --input config/input.json --demos demos/demos.json
adam-cli build .
```

向 DevOps 交接包内真实名称和版本、ZIP、SIF、输入 schema、输出端口、Demo 与 smoke input。Kit IO 改动时同步检查受影响 Workflow 的契约和连接；按请求范围完成调试，不自行增加生产计算规模。
