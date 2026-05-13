# 镜像目录结构说明规范

每次给出 Dockerfile 后，都要给开发者说明镜像内目录结构，因为后续 Kit 主函数需要根据这些绝对路径调用程序和权重。

## 标准结构

```text
/
├── app/
│   ├── requirements.txt
│   ├── environment.yml
│   └── 轻量配置或脚本
├── opt/
│   └── ProjectName/
│       ├── 主程序
│       ├── helper_scripts/
│       └── weights/
└── workspace/
    ├── runner.py
    ├── 用户输入文件
    ├── 中间文件
    ├── 输出文件
    └── report.md
```

## 说明模板

- `/app`：构建期工作目录，Dockerfile 中 `WORKDIR /app`，用于依赖文件和轻量资源。
- `/opt/ProjectName`：镜像内固化项目目录，运行时不会随用户任务改变。
- `/workspace`：平台运行时挂载目录，主函数执行时 `Path.cwd()` 一般指向这里。
- 主函数读取镜像固化资源时使用 `/opt/...` 或 `/app/...` 绝对路径。
- 主函数写输出时使用 `Path.cwd()` 或 `Path.cwd() / "xxx"`。
