# asterfire-kit-adapter

用于把普通 Python/命令行项目适配为 Asterfire 平台 Kit 的 Codex/OpenAI Skill。

核心行为：

1. 先分析普通项目入口、依赖、输入输出和是否已有 runner。
2. 如果用户没有指定 `DISPLAY_NAME / NETWORK / CPU / GPU / SIF`，先询问配置，不直接写入口代码。
3. 如果用户授权自动选择，则从 `references/sif_registry.json` 中选择或推荐 SIF。
4. 确认配置后，生成/修改平台入口、`config/input.json`、`config/configure.json`、`config/long_description.md`、`config/long_description_en.md`、`Makefile`。
5. 保持 `input.json`、`kwargs['args']`、`@tool_io(outputs)`、`return dict` 同步。
6. 适配交付时同步创建 `demos/demos.json` 和所引用的示例文件；GitHub/开源项目要优先把 README、examples、tests、tutorials、notebooks 中的官方案例尽可能迁移为 Kit Demo，覆盖主要运行模式。
7. `report.md` 必须展示运行概览、方法说明、关键结果、结构/图片可视化、结果查看方式和后续建议；stdout/stderr 等运行日志保存为 `run.log`，不直接写进报告正文。
8. 如果主要输出包含 `.pdb`、`.cif/.mmcif`、`.sdf`，报告中必须用 `molstar` 块渲染；如果有图片或可绘图数据，必须嵌入图片或用 matplotlib 生成图。
9. 每次修改 Kit 都要更新 `configure.json` 版本号，并重新打包生成新版 zip。
