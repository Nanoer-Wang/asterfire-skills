# asterfire-kit-adapter

用于把普通项目代码适配为 Asterfire 平台 Kit 的 Codex/OpenAI Skill。

核心行为：

1. 先分析普通项目入口、依赖、输入输出和是否已有 runner。
2. 如果用户没有指定 `DISPLAY_NAME / NETWORK / CPU / GPU / SIF`，先询问配置，不直接写入口代码。
3. 如果用户授权自动选择，则从 `references/sif_registry.json` 中选择或推荐 SIF。
4. 确认配置后，生成/修改平台入口、`config/input.json`、`config/configure.json`、`config/long_description.md`、`Makefile`。
5. 保持 `input.json`、`kwargs['args']`、`@tool_io(outputs)`、`return dict` 同步。

6. 适配交付时同步创建 `demos/demos.json` 和所引用的示例文件，确保前端 Demo 可一键加载。
