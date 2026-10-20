# 镜像目录结构说明

```text
/                         # 容器根目录
├── app/                  # 镜像构建时固化的通用工作目录
│   └── requirements.txt
├── opt/                  # 镜像构建时固化的大项目、权重、数据库
│   └── ProteinMPNN/      # COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
│       ├── protein_mpnn_run.py
│       ├── helper_scripts/
│       ├── vanilla_model_weights/
│       └── soluble_model_weights/
├── workspace/            # Asterfire 运行时挂载目录，runner.py 实际在这里执行
│   ├── runner.py
│   ├── 用户上传输入文件
│   ├── 中间文件
│   ├── 输出文件
│   └── report.md
└── ...
```

## 路径使用说明

- `/opt/ProteinMPNN`：镜像内固定项目路径。Kit 主函数读取 ProteinMPNN 代码、helper 脚本和权重时使用该路径。
- `/workspace`：平台运行时挂载目录。用户上传文件、中间文件、输出 zip、`report.md` 应写到这里，也就是 Python 中的 `Path.cwd()`。
