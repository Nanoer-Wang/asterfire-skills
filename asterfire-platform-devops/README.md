# asterfire-platform-devops

AsterFire 项目发布与 Open API v1 外部调用 Skill。

它保留 Docker/ACR/云效构建能力，并实现：

- Docker 镜像登记、SIF 构建和异步状态追踪
- Kit/Agent Toolbox 上传
- Kit 提交、Agent 任务、Workflow 执行
- 任务状态轮询、详情读取和文件上传/下载

## 配置

复制 `.env.example` 为项目或工作区根目录的 `.env`，填写 AsterFire、云效组织和两个服务连接。CLI 会自动向上查找 `.env`，且不会覆盖终端中已经设置的变量。

默认 Base URL 是 `https://sidereus-ai.com/api/open/v1`。私有部署在 `templates/asterfire.yaml` 修改。

## 常用命令

```bash
python -m scripts.cli info

python -m scripts.cli project publish \
  --path ./my-kit --name my-kit \
  --smoke-input ./input.json

# 已创建镜像记录但 SIF 转换未完成时，从该记录继续
python -m scripts.cli image build-existing --image-id 10660

python -m scripts.cli kit run --toolbox my-kit --input ./input.json
python -m scripts.cli agent run --toolbox my-agent --message "run analysis"
python -m scripts.cli workflow run --plan-id 42
```

`kit run`、`agent run` 和 `workflow run` 默认等待完成；使用 `--no-wait` 只提交。所有流程都可先用 `--dry-run` 检查计划。

不要写死历史集群别名（例如 `sai`）。省略 `--target-cluster` 时会读取平台当前默认集群；只有平台无法唯一确定默认值时，才显式传入接口返回的集群 `code`。

## 测试

```bash
python -m unittest discover -s tests -v
```
