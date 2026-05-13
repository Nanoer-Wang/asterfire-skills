# runner 配置询问模板

当用户要求把普通项目改造成平台 Kit，但没有指定 runner 配置，也没有授权根据 SIF 注册表自动选择时，使用下面这段回复：

```text
要把这个普通项目改造成平台 Kit，我需要先确定 runner 配置，尤其是 SIF。请你指定下面这些项：

1. DISPLAY_NAME：平台前端显示名称，例如“PDB 结构验证工具”。
2. SIF：平台运行镜像，例如 xxx:1.0.0。
3. CPU：默认 CPU 数。
4. GPU：默认 GPU 数。
5. NETWORK：运行时是否需要网络，True/False。

你也可以直接说：根据现有 SIF 注册表帮我选择合适的 SIF 和默认资源。这样我会先分析项目依赖，再从 references/sif_registry.json 中选择候选镜像。
```

如果用户已经给了部分配置，则只询问缺失项，不要重复询问已给出的内容。
