# Asterfire Kit Dockerfile 编写规则

## 1. 路径规则

- `/app`：通用构建目录，放 requirements、environment.yml、轻量脚本、配置文件。
- `/opt/<ProjectName>`：固化第三方项目、权重、数据库、源码包。
- `/workspace`：平台运行时挂载目录，runner.py、输入、中间文件、输出都在这里。

## 2. COPY 规则

推荐写绝对目标路径：

```dockerfile
COPY requirements.txt /app/requirements.txt
COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
COPY weights/rf3_latest.pt /app/modelforge/rf3_latest.pt
```

不要只写相对目标路径：

```dockerfile
COPY ProteinMPNN-main ProteinMPNN-main
```

## 3. 环境变量规则

固化项目后，应写出 HOME/ROOT/DIR 类环境变量：

```dockerfile
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
ENV PYTHONPATH=/opt/ProteinMPNN:/app:$PYTHONPATH
```

runner.py 中可以读取：

```python
Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
```

## 4. 依赖规则

pip：

```dockerfile
RUN pip3 install --no-cache-dir -r /app/requirements.txt
```

apt：

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends <packages> \
    && rm -rf /var/lib/apt/lists/*
```

Conda：环境名必须和 `environment.yml` 中 `name:` 一致。

## 5. 自检规则

每个关键固化路径都应该至少有一个构建期自检：

```dockerfile
RUN test -f /opt/ProteinMPNN/protein_mpnn_run.py
RUN test -f /app/modelforge/rf3_latest.pt
```
