# asterfire-kit-development

用于规范、开发、重构、审查和打包 Asterfire 平台 Kit 的 Codex/OpenAI Skill。

核心行为：

1. 强制确认并维护 SIF、runner 配置、`@tool_io(outputs)` 和 `return dict`。
2. 按最小输入原则生成 `config/input.json`，并与 `kwargs['args']`、Demo 配置同步。
3. 每次修改 Kit 都更新 `config/configure.json` 的 `version`；`description` 要用户友好且不超过 400 个字符。
4. 同步维护 `config/long_description.md` 和 `config/long_description_en.md`，详情页包含概述、功能、输入、输出、注意事项、参考文献。
5. `report.md` 必须展示运行概览、方法说明、结果展示与说明、可视化结果、如何查看结果和后续分析建议。
6. 主要输出包含 `.pdb`、`.cif/.mmcif`、`.sdf` 时，报告中必须用 `molstar` 块渲染；输出包含图片或可绘图数据时，必须直接嵌入图片或用 matplotlib 生成图。
7. stdout/stderr、Traceback 和外部程序日志保存为 `run.log` 等文件，不直接铺在 `report.md` 中。
8. 每次修改完成后都要重新打包生成新版 zip，并把压缩包作为交付物。
