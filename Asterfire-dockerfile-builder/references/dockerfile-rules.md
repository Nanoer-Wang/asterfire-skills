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

## 6. Smoke Test 规则

镜像构建完成后，必须先通过 Smoke Test 再推送到镜像仓库。Smoke Test 以 `docker run` 命令执行，分两个层次：

### 层次一：模块/依赖验证

验证关键 Python 包可导入、命令行工具可执行、固化文件存在：

```bash
# 依赖导入验证
docker run --rm <image>:<version> python -c "import numpy; import torch; print('OK')"

# 工具可执行验证
docker run --rm <image>:<version> bash -c "which gmx && gmx --version"

# 固化路径验证
docker run --rm <image>:<version> bash -c "test -f /opt/Project/main.py && echo 'OK'"
```

### 层次二：端到端基础案例

验证镜像能跑通一个最小真实任务（输入 → 计算 → 输出文件生成）：

```bash
docker run --rm \
  -v $(pwd)/test_inputs:/workspace \
  -w /workspace \
  <image>:<version> \
  bash -c "
    python /opt/Project/run.py --input /workspace/test.pdb --output /workspace/result.txt \
    && test -f /workspace/result.txt \
    && echo 'SMOKE TEST PASSED' \
    || echo 'SMOKE TEST FAILED'
  "
```

案例设计原则：

- 优先参考官方仓库提供的基础测试命令。
- 官方无测试命令时自行设计最小案例，覆盖核心计算流程。
- 案例应轻量，建议 5 分钟内完成。
- 必须验证输出文件确实生成。

### 工作流位置

`docker build` → **Smoke Test 通过** → `docker tag` → `docker push`

Smoke Test 失败时不得推送镜像。
