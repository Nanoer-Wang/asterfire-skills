# 镜像目录结构说明优先规则

本 Skill 与 `Asterfire-dockerfile-builder` 配套使用时，优先读取它生成的目录说明文件，而不是直接从 Dockerfile 开始猜路径。

常见文件名：

- `image_layout.md`
- `镜像目录结构说明.md`
- `project_tree_*.txt`

## 读取优先级

1. 用户显式指定的路径，例如 `/opt/ProteinMPNN`。
2. `Asterfire-dockerfile-builder` 生成的目录说明。
3. Dockerfile 中的 `ENV *_HOME/*_ROOT/*_DIR`。
4. Dockerfile 中的 `COPY / ADD` 目标路径。
5. Dockerfile 中 `RUN test -f`、`RUN ls` 的校验路径。
6. `WORKDIR` 只能辅助判断，不能单独作为项目根目录。

## 目录说明中需要识别的内容

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用工作目录
├── opt/                  # 镜像构建时固化的大项目、权重、数据库
│   └── ProteinMPNN/      # COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
├── workspace/            # Asterfire 运行时挂载目录，runner.py 实际在这里执行
└── ...
```

从上面应识别：

- ProteinMPNN 镜像项目根目录：`/opt/ProteinMPNN`
- 本地源目录：`ProteinMPNN/ProteinMPNN-main`
- workspace：运行时输入、输出、中间文件目录，不能当成镜像项目根目录

## 冲突处理

如果目录说明与 Dockerfile 推断结果不一致：

- 默认采用目录说明。
- 在回复中提醒用户存在冲突。
- 建议用户同步修改 Dockerfile 或重新用 `Asterfire-dockerfile-builder` 生成目录说明。
