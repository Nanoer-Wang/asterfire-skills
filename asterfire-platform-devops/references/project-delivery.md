# 镜像与 Kit 发布执行细节

镜像名称、版本和可用状态见同目录 [image-discovery.md](image-discovery.md)，以目标平台实时查询为准。

以下脚本和 references 路径以 DevOps 技能目录为基准。Workflow 专用开发与执行机制以工作流技能为准。

## 从 GitHub / 脚本开发 Kit 的默认入口

用户给出 GitHub 链接、普通项目或零散脚本并要求“开发成 Kit / 接入 Asterfire”时，默认按本流程推进。仅修改 Skill、分析可行性、审查代码、只生成 Dockerfile 或明确“只做代码/ZIP、暂不发布”时，遵守该限定范围，不启动实际发布。

1. 先读取现有上下文与项目，识别目标功能、入口、依赖、权重及官方最小示例。没有确认镜像状态时，先问：“这个项目是否已经构建镜像并推送到 Asterfire 平台？已有的话请提供镜像名称/版本或 SIF；也可以选择尚未构建或不确定。” 已有明确答案不重复问。
2. 用户答已有：查询平台镜像记录、目标集群 `cluster_build_status`，核对依赖、权重与架构。ACR 有镜像不代表平台已有可用 SIF；只补齐缺失的登记/转换阶段。可复用则直接进入 Kit 开发，不能无理由重建。
3. 用户答没有，或确认现有镜像不适配：询问“采用云效流水线构建（默认推荐），还是本地 Docker？确定后我会完成镜像构建与推送、平台转换、Kit 开发上传及最小案例调试。” 默认推荐云效；用户说“按默认”即采用云效。等待选择，不把未回复当确认。用户已指定方式时直接沿用。
4. 用户答不确定：有凭据时先只读查询平台和已有配置；仍不能确定再请其选择复用候选或新建。不要先要求用户手工填写完整 runner 配置。
5. 构建路线与端到端范围确定后，持续执行下面的发布流程，不在镜像、Kit、上传、调试各阶段重复索取授权。`DISPLAY_NAME`、CPU/GPU/NETWORK 根据项目文档、依赖和资源要求合理确定并说明；仅缺少会阻断工作的信息时询问。镜像尚未就绪可先分析、整理业务模块与表单，真实可用 SIF 就绪后才完成 runner 和发布包，不能用占位 SIF 冒充可用镜像。

凭据缺失只询问缺少的配置，不要求聊天中粘贴秘密；继续完成无需凭据的代码和构建材料。流水线失败不能擅自切换本地 Docker。此流程不授权删除资源、覆盖既有同版本或启动大型生产任务。

## 镜像与 Kit 的职责边界

- **镜像负责依赖环境**：操作系统库、Python/Conda、CUDA、第三方包和可执行工具、完整模型权重、tokenizer、模型配置与运行必需数据库。固定版本/提交和资源路径，构建期校验文件非空、非 LFS 指针及必要的完整性；运行时不补装依赖或临时下载必需权重。
- **Kit 负责核心业务逻辑**：原项目业务模块与零散脚本、runner、输入校验和配置组装、任务编排、前后处理、输出及 report.md，随 Kit ZIP 一起交付。不能把这些业务代码全塞入镜像，使 Kit 只调用镜像中固化的本项目入口。
- 可把稳定第三方引擎/库作为镜像依赖，包括其必要代码；需明确它与本 Kit 业务代码的边界。待适配仓库不能仅因来自 GitHub 就整仓视为依赖。能随 Kit 运行的业务脚本应放进 Kit；业务代码修改只更新 Kit，依赖或权重改变才重建镜像。
- `image_layout.md` 记录依赖、权重路径和版本，并注明 Kit 业务代码的交付位置。镜像资源用环境变量/绝对路径访问，Kit 模块从实际投递目录加载，输入输出写运行工作目录；检查最终 ZIP 确实包含业务模块且不包含依赖环境、权重或凭据。

### 平台运行时契约

Asterfire 会在 SIF 中通过 Bash 和 `python` 启动 Kit 入口。每个 Kit 镜像无论项目自身使用 `python3`、Conda 还是其他命令，都必须在最终 `PATH` 中提供以下运行契约：

- `bash` 可执行；
- `python` 可执行，不能只有 `python3`；
- `python` 指向实际安装项目依赖的环境；
- `python -c "import adam_community"` 成功；
- Conda 环境通过 Dockerfile `ENV PATH=/opt/conda/envs/<env>/bin:$PATH` 固化，不能依赖交互式 `conda activate`。

完整发布在创建云效流水线或本地构建前调用 `scripts/runtime_contract.py` 静态检查 Dockerfile。Dockerfile 必须包含构建期的 `command -v bash`、`command -v python`、`python --version` 和 `python -c "import adam_community"`；只写 `python3 --version` 不合格。`CMD`/`ENTRYPOINT` 不能证明平台入口可运行，因为平台可能覆盖它们。

## 标准环境变量

CLI 启动时自动向上查找并加载距离项目目录、当前目录或配置目录最近的 `.env`，但不会覆盖进程中已经存在的环境变量。以 `.env.example` 为模板；真实 `.env` 不得加入版本控制或打包产物。

内部云效 + ACR 企业版 + AsterFire 端到端发布必须提供：

```dotenv
ASTERFIRE_TOKEN=
YUNXIAO_TOKEN=
YUNXIAO_ORGANIZATION_ID=
YUNXIAO_CODEUP_SERVICE_CONNECTION=
YUNXIAO_ACR_SERVICE_CONNECTION=
```

两个 service connection 值必须是云效公开 UUID，不是接口返回的内部数字 ID。使用本地 Docker 构建时才额外需要 `ACR_USERNAME` 和 `ACR_PASSWORD`。不得使用个人网页登录密码代替 Token 或服务连接。

## Open API v1 不可变约定

- Base URL：生产环境 `https://sidereus-ai.com/api/open/v1`；私有部署 `https://<host>/api/open/v1`。
- 鉴权头：`Asterfire-Token: <token>`，token 仅从环境变量或受保护配置读取。
- 普通成功响应从 `data` 解包；程序根据稳定的 `error.code` 分支，并保留 `error.request_id`。
- Dev 接口同时需要 `dev:read`/`dev:write` scope 和 `DEVELOPER` 身份。
- 未使用幂等键的写请求不得自动重试。Workflow 执行必须携带 `Idempotency-Key`。
- 真实发布、运行和 Workflow 执行可能消耗计算资源；只在用户的当前请求明确需要时执行。

## 项目发布

1. 根据已确认路线分析项目并拆分依赖与业务代码；读取同目录 image-lifecycle.md，调用镜像构建和路径工具 完成依赖镜像、权重清单、平台运行时契约及构建自检。镜像可复用时跳过构建和推送，但仍要用已有日志或最小探针确认 `bash`、`python`、`adam_community` 和项目依赖可用。Agent 发布继续遵守 Agent Skill。
2. 新建镜像时按所选云效流水线或本地 Docker 构建 `linux/amd64` 镜像，完成依赖与权重自检并推送 ACR。流水线模式的检查在构建环境中执行，不要求用户本机安装 Docker；GPU 最小任务可在平台目标集群验证。保留现有版本策略：首版 `1.0.0`，默认 patch +1，显式覆盖时保持指定 tag。
3. `POST /dev/images` 登记 Docker 镜像，保存返回的 `id`。
4. `GET /dev/images/build-clusters`。优先使用 `is_default_target=true` 的集群；无唯一默认时要求显式指定。
5. `POST /dev/images/{image_id}/build`。优先轮询 `GET /dev/images/{image_id}` 的 `cluster_build_status`；当前平台返回的镜像构建 `task_id`/`async_task_id` 不一定能由 `/dev/async-tasks/{task_id}` 查询。仅当该异步任务接口确实返回任务详情时，才用其状态和日志辅助诊断。
6. SIF 就绪后使用 `asterfire-kit-development` 完成业务逻辑、表单、Demo、报告与元数据，核对镜像资源路径。将 Kit 中唯一 `runner(Tool)` 的 `SIF` 回写为 `{repository}:{tag}`，执行 `adam-cli build .`。
7. 上传前必须从 ZIP 的 `config/configure.json` 读取真实名称，并用 `GET /dev/toolboxes` 做不区分大小写的冲突检查。若新名称与已有工具箱仅大小写不同（如 `protenix` / `Protenix`），上传前直接失败并要求换成真正唯一的名称；`force=true` 也不得绕过该检查。然后用 `POST /dev/toolboxes` 上传 ZIP；仅在用户明确要求覆盖同名同版本时使用 `force=true`。
8. 端到端 Kit 开发默认从官方 examples/tests/README 提取一个轻量真实 Demo，转换成 smoke input，调用平台 Kit 并等待终态，检查输出文件、报告和关键结果。无需用户再次明确说“调试”。已有产物仅发布时按用户范围及提供的 smoke input 执行；缺少可用输入时询问必要数据，并明确标记尚未验证，不能伪造通过。
9. 调试失败先定位：业务问题修改 Kit 并递增 Kit 版本、重新打包上传；依赖/权重问题才修镜像并递增镜像版本、转换 SIF、回写 Kit。查询确认上次写入/任务状态后再提交，遵守幂等与覆盖约束。相同失败连续三次或涉及新费用规模、缺失权限/数据时，保留日志和进度，请用户解决具体阻碍，不无限重跑。
10. 交付 GitHub 提交/源码来源、镜像 tag/平台记录及 SIF 状态、Kit 版本和 ZIP、上传记录、调试任务及结果。任何未完成阶段明确列出，不把“已生成命令”当成“已发布成功”。

云效/ACR 策略继续按 `references/yunxiao-flow.md`、`references/aliyun-acr.md` 和 `references/publishing-rules.md` 执行。所有 Token、AccessKey、registry password 和 service connection ID 均不得写入源码、Skill 或打包产物。

本 Skill 当前服务内部用户，保留企业版 ACR 的 `region`、`instance_name`、`namespace`、Registry 域名和服务连接配置。`instance_name` 使用云效界面自动生成 YAML 中的精确值，不做外部用户环境的自动猜测。

## 已完成项目的外部调用

### Kit

- 先用 `GET /toolboxes?type=kit` 确认 toolbox 名称和输入 schema。
- `POST /kits/submit` 创建任务。
- 使用返回的 `task_id`/`step_id` 轮询 `GET /tasks/{task_id}/status`。
- 完成后读取 `GET /tasks/{task_id}`，并按文件 ID 下载产物。
- 在既有任务中追跑 Kit 时使用 `POST /tasks/{task_id}/kit-run`。

### Agent

- 先用 `GET /toolboxes?type=agent` 确认 toolbox。
- `POST /tasks` 创建 Agent 任务；附件字段是 `file_ids`。
- `POST /tasks/{task_id}/messages` 追加消息。
- `GET /tasks/{task_id}/status` 和 `GET /tasks/{task_id}` 追踪运行。
- 仅当用户要求时调用 stop/delete/rename；delete 需要显式 `--yes`。

`/tasks` 是 Agent/Kit 运行任务；`/dev/async-tasks` 是开发调试异步任务，两者不得混用。SIF 转换是否完成以镜像记录的 `cluster_build_status` 为准。

### Workflow

Workflow 的开发、发布、调用、节点输入、执行记录和产物访问统一使用 `../../asterfire-workflow-development/SKILL.md`。DevOps 只衔接上游镜像/Kit 阶段与整体验收；用户仅调用已有方案时不扩展为修改 DAG、重发 Kit 或构建镜像。

## CLI

```bash
# 验证 token/base URL
python -m scripts.cli info

# 发布（如需端到端 smoke test，显式提供输入）
python -m scripts.cli project publish --path ./my-kit --name my-kit \
  --smoke-input ./input.json

# 调用 Kit / Agent，默认等待终态；Workflow 按工作流技能操作
python -m scripts.cli kit run --toolbox my-kit --input ./input.json
python -m scripts.cli agent run --toolbox my-agent --message "run analysis"
```

执行前按用户选择在配置中显式设置 `build.backend: yunxiao` 或 `build.backend: local`；现有 CLI 的隐式默认值是 local，不能省略配置导致误用本地 Docker。云效当前实现使用 Codeup 源，GitHub/零散脚本需准备包含依赖构建材料的 Codeup 源和提交；遵守用户已有仓库权限，不擅自公开源码。复用镜像时使用镜像查询/登记及 Toolbox 上传阶段，不直接调用会重新构建镜像的完整 project publish。

默认不写死目标集群代码，由 `/dev/images/build-clusters` 返回的 `is_default_target` 自动选择。只有无法唯一选出默认集群时，才传 `--target-cluster <接口返回的 code>`；历史别名（例如 `sai`）可能无权限或已经失效。若镜像记录已经创建、仅 SIF 转换中断，使用 `image build-existing --image-id <id>` 从现有记录继续，禁止重复登记或重跑镜像流水线。

可用 `--dry-run` 检查操作计划，用 `--no-wait` 仅提交而不轮询；端到端任务仍须继续跟踪到终态。

## 完成门禁

- 新镜像构建和 ACR push 成功；复用镜像则已核验依赖/权重和平台可用状态。
- Dockerfile 的平台运行时契约检查通过：`bash`、`python`、`adam_community` 均可用，Conda/Python 环境已进入非交互 Shell 的 `PATH`。
- `/dev/images` 登记成功，目标集群明确，SIF 异步任务成功。
- Kit `SIF` 不是占位符，Toolbox ZIP 通过 `adam-cli build` 或等价检查。
- `/dev/toolboxes` 上传成功。
- 端到端开发已用最小真实案例在平台验证成功并检查产物；仅发布任务在提供 smoke input 时完成验证。缺输入/资源时标记调试未完成。
- 核心业务模块随 Kit ZIP 交付，镜像仅固化依赖和运行资源。
- 未将任何凭据写入代码、镜像、ZIP 或日志。

## 删除操作

删除镜像、任务或其他平台资源必须由用户明确要求，并要求 `--yes`。
