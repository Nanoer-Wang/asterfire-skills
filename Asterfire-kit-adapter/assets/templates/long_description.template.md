# 概述

这是一个由普通 Python/命令行项目适配而来的 Asterfire 平台 Kit。它通过平台表单接收输入，在指定 SIF 环境中调用原项目函数或命令行入口，并在当前工作目录生成主要结果、专业 `report.md` 和独立运行日志。

# 功能

- 将原项目的函数入口或命令行入口封装为 `class runner(Tool)`。
- 从 `kwargs['args']` 读取平台表单参数，并检查必填输入。
- 自动准备当前工作目录下的输入、输出和临时文件。
- 调用原项目逻辑，检查输出文件是否生成。
- 返回平台可识别的输出端口，并保持 `@tool_io(outputs)` 与 `return` 字段一致。
- 生成用户友好的 `report.md`，展示运行概览、方法说明、结果展示、结构/图片可视化、结果查看方式和后续建议。
- 当主要输出包含 `.pdb`、`.cif/.mmcif`、`.sdf` 时，报告中使用 `molstar` 直接渲染；当输出包含图片或可绘图数据时，用 Markdown 图片或 matplotlib 图展示。
- 将详细命令输出和错误信息保存为 `run.log`，不在报告正文中展开。
- 提供 `demos/` 目录，可在前端一键加载示例输入。

# 输入

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| input_file | file | 是 | 示例输入文件。实际适配时应替换为原项目真正需要的输入，并说明文件格式、字段要求或结构要求。 |

# 输出

| 输出 | 说明 |
| --- | --- |
| result_file | 主要结果文件。实际适配时应替换为原项目真实输出，例如 CSV、JSON、结构文件、图片或压缩包。 |
| report.md | 用户报告。直接展示关键结果、结构渲染、图片可视化、结果解释和后续分析建议。 |
| run.log | 详细运行日志。用于排查原项目命令输出、错误输出和异常信息，不在报告中直接展开。 |
| success | 布尔值，表示主要输出和报告是否成功生成。 |

# 注意事项

- 本 Kit 的 `SIF` 必须来自用户指定或 SIF 注册表，不允许使用占位值。
- `input.json` 只暴露用户真正需要填写或调节的参数，不要加入内部路径、调试开关或无关元数据。
- 每次修改 Kit 必须更新 `config/configure.json` 的 `version`，并重新打包生成新版 zip。
- `config/configure.json` 的 `description` 要说明工具能力、输入和输出，最高不超过 400 个字符。
- 如果输出结构文件或图片，必须在 `report.md` 中直接展示；如果只有数据但需要可视化，应使用 matplotlib 生成图。
- 修改 `input.json` 后，请同步更新 `demos/demos.json`，确保 Demo 字段和示例文件仍然可用。

# 参考文献

1. Asterfire Platform Kit Development Guidelines.
2. Mol* / Molstar molecular visualization framework documentation.
