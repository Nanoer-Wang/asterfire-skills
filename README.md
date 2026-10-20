# Asterfire Skills

面向 Asterfire / Galileo / Adam Community 的技能集合，覆盖镜像构建、Kit 开发适配、Agent Toolbox 和 Workflow 发布调用。当前提供四个入口，具体规则、脚本和模板按阶段读取。

## 安装

```bash
# 查看可用技能
npx skills add https://github.com/Nanoer-Wang/asterfire-skills.git --list

# 为 Codex 安装整套技能
npx skills add https://github.com/Nanoer-Wang/asterfire-skills.git -a codex -g -y
```

推荐整套安装，保持四个技能目录同级。Workflow 的 API 工具复用 DevOps 的公共客户端；DevOps 按任务需要读取 Kit、Workflow 或 Agent 的专业规则。

本地辅助工具使用 Python 3.10+；YAML 校验需要 PyYAML，可按 [Workflow requirements](asterfire-workflow-development/requirements.txt) 安装。平台 HTTP 客户端使用 Python 标准库。

## 四个技能的分工

| Skill | 职责 | 典型任务 |
| --- | --- | --- |
| [asterfire-platform-devops](asterfire-platform-devops/SKILL.md) | 唯一全链路编排入口；镜像开发、构建推送、SIF、发布与恢复 | 从项目到镜像、Kit，再到 Workflow；独立 Dockerfile、路径/权重检查、上传和调用调试 |
| [asterfire-kit-development](asterfire-kit-development/SKILL.md) | Kit 代码开发与原项目适配、审查和打包 | runner、最小表单、IO 端口、Demo、报告、详情页与新版 ZIP |
| [asterfire-workflow-development](asterfire-workflow-development/SKILL.md) | Workflow 专业开发、发布、调用和节点调试 | 多类节点、端口连接、节点级 scatter/gather、输入、相对路径产物和执行恢复 |
| [asterfire-agent-skill](asterfire-agent-skill/SKILL.md) | Agent Toolbox 与 ATP 工具开发 | 多 Tool、docstring、hooks、资源元数据、工具暴露和包结构 |

### 如何选择入口

- **完整交付**：使用 `$asterfire-platform-devops`。它按已有资产跳过完成阶段，推进镜像 → SIF → Kit 独立验证 → Workflow 验证。
- **仅开发或适配 Kit、交付 ZIP**：使用 `$asterfire-kit-development`。需要镜像或真实发布调试时由 DevOps 衔接。
- **已有 Kit 组装工作流**：使用 `$asterfire-workflow-development`。缺少 Kit/镜像时交回 DevOps 准备，上游可用后继续工作流。
- **Agent 工具开发**：使用 `$asterfire-agent-skill`；发布和外部调用由 DevOps 处理。

每个入口遵循当前任务范围。只做本地代码、Dockerfile 或 YAML 时不会自动扩展为远程发布；端到端请求则继续完成约定的轻量调试。

## 镜像从平台实时查询

不再维护本地 SIF 名称注册表。使用支持 Open API v1 的 CLI 查询当前账号可见镜像，核对精确版本、依赖与目标集群 SIF 构建状态：

```bash
asterfire image list --json
asterfire image list --name <关键词> --json
asterfire image get <image_id> --json
asterfire image clusters --image-id <image_id> --json
```

原生 CLI 版本或路由不兼容时，DevOps 提供基于 `/api/open/v1` 的客户端及分页筛选工具。详情见 [平台镜像查询](asterfire-platform-devops/references/image-discovery.md)。开发者镜像列表受账号权限限制，不能当成所有公共/共享 SIF 的全集。项目仅记录本次选中镜像的 ID、版本和核验证据。

## 主要约定

- 镜像固化依赖、稳定第三方引擎、完整权重和运行资源；Kit ZIP 交付本项目的核心业务模块与入口。
- Kit 使用唯一 `runner(Tool)`，输入从 `kwargs['args']` 读取，表单字段与代码一致。输出端口包含实际类型和中文描述，与返回的字典实例 key 一致。
- 镜像路径、启动检查和权重验证统一在 DevOps 镜像阶段维护；平台入口依赖最终非交互环境中的 `bash`、`python` 与 `adam_community`。
- Workflow 节点不限于文件输入、Kit 和 Python 脚本；按目标部署契约使用其他类型与节点级 scatter。产物保存在当前节点目录，优先返回相对路径；跨节点通过输出端口或已核实的可读路径访问。
- 真实发布前核对环境、空间、版本、SIF 和权限。执行后按本次 execution/node/step 检查状态、日志和产物，不将“已提交”当成“已验证成功”。
- Token、密码和真实 `.env` 只放在本机受保护配置中，不提交到仓库、镜像或 ZIP。环境变量名称参考 [DevOps 示例](asterfire-platform-devops/.env.example)。

## 从旧版升级

旧能力已迁移，保留脚本与模板的同时取消重复入口：

| 旧入口/旧文档名称 | 新入口 |
| --- | --- |
| `asterfire-kit-adapter` / `asterfire-project-to-kit-adapter` | `asterfire-kit-development` |
| `asterfire-dockerfile-builder` | `asterfire-platform-devops` 的镜像阶段 |
| `asterfire-image-rules` / `asterfire-image-path-calibrator` | `asterfire-platform-devops` 的路径与权重检查 |

更新安装后，若本机仍有旧的 `Asterfire-kit-adapter`、`Asterfire-dockerfile-builder` 或 `Asterfire-image-rules` 目录，先备份，再移出技能发现目录，避免新旧规则同时生效。旧镜像注册表不再迁入新技能；需要镜像时查询目标平台。

## 本地验证

平台和工作流测试均采用本地样例、临时目录或模拟请求，不调用生产计算：

```bash
cd asterfire-platform-devops
python -m unittest discover -s tests

cd ../asterfire-workflow-development
python -m unittest discover -s tests
```

Kit 的表单、Demo 校验与项目分析命令见 [Kit Skill](asterfire-kit-development/SKILL.md)，镜像工具见 [镜像阶段](asterfire-platform-devops/references/image-lifecycle.md)。静态校验通过仍需在实际发布任务中检查构建结果、权限和最小真实案例。

## License

[MIT](LICENSE)。
