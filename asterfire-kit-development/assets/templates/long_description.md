# 概述

这是一个符合 Asterfire 平台规范的 Kit 模板。它演示如何接收平台输入、检查文件、执行核心流程，并在当前工作目录生成结果文件、专业中文 `report.md` 和日志文件。

# 功能

- 从 `kwargs['args']` 读取平台表单参数。
- 对输入文件进行存在性和基础格式检查。
- 在当前工作目录生成主要结果文件。
- 使用 `@tool_io(outputs={...})` 显式声明输出端口，并保持 `return` 字段一致。
- 自动生成用户友好的 `report.md`，展示运行概览、方法、关键结果、可视化、结果查看方式和后续建议。
- 当输出包含 `.pdb`、`.cif/.mmcif`、`.sdf` 结构时，可用 `molstar` 块在报告中展示；当输出包含图片或可绘图数据时，可用 matplotlib 生成图并嵌入报告。
- 将详细运行日志保存为 `run.log`，不在报告正文中展开。
- 提供 `demos/` 目录，可在前端一键加载示例输入。

# 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| input_file | file | 是 | 需要处理的输入文件。真实 Kit 应根据任务类型限制文件后缀，并在说明中写清楚文件内容要求。 |

# 输出

| 输出 | 说明 |
| --- | --- |
| output_file | 主要结果文件。模板中为文本结果，真实 Kit 中应替换为 CSV、JSON、结构文件、模型结果或压缩包等实际输出。 |
| report.md | 运行报告。直接展示重要结果、结构渲染、图片可视化、结果解释和后续分析建议。 |
| run.log | 详细运行日志。用于排错，不会在 `report.md` 中直接展开。 |
| success | 布尔值，表示主要输出和报告是否成功生成。 |

# 注意事项

- 新建真实 Kit 时，请删除与任务无关的字段，只保留必要输入和少数真正有用的可选参数。
- `SIF` 必须使用真实镜像，不要保留占位值。
- 每次修改 Kit 必须同步更新 `config/configure.json` 中的 `version`，并重新打包生成新版 zip。
- `config/configure.json` 的 `description` 要用户友好，说明工具能力、输入和输出，但不能超过 400 个字符。
- 如果主要输出包含结构文件，必须在报告中使用 `molstar` 展示；如果输出包含图片或可视化需求，必须在报告中嵌入图片并解释含义。
- 修改 `input.json` 后，请同步更新 `demos/demos.json`，确保 Demo 字段和示例文件仍然可用。

# 参考文献

1. Asterfire Platform Kit Development Guidelines.
2. Mol* / Molstar molecular visualization framework documentation.
