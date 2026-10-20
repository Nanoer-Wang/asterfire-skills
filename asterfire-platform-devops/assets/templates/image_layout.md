# 镜像目录结构说明模板

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用目录
│   ├── requirements.txt
│   ├── environment.yml
│   └── ...
├── opt/                  # 镜像构建时固化的大项目、权重、数据库
│   └── ProjectName/
│       ├── main.py
│       ├── helper_scripts/
│       └── weights/
├── workspace/            # Asterfire 运行时挂载目录，runner.py 在这里执行
│   ├── runner.py
│   ├── 用户上传文件
│   ├── 中间文件
│   ├── 输出文件
│   └── report.md
└── ...
```

路径使用规则：

- `/opt/ProjectName`：镜像内固定路径，用于读取程序、权重、数据库。
- `/app`：镜像内固定路径，用于 requirements、配置、轻量工具脚本。
- `/workspace`：运行时路径，用于用户输入、中间文件、输出文件、报告。
