# 镜像 → Kit → Workflow

镜像名称、版本和可用状态见同目录 [image-discovery.md](image-discovery.md)，以目标平台实时查询为准。

用于用户明确要求全链路，或工作流所需 Kit/镜像不存在时。执行已有技能的实际规则和脚本；这里补充阶段交接。

## 启动与复用

先读本技能 SKILL.md 与同目录 project-delivery.md。从上下文、配置和只读查询确定已有资产。镜像来源、构建路线已明确就直接沿用；仅在缺失且会影响工作时询问。云效是推荐路线，已有“按默认/走流水线”授权即可采用，失败后不自行切换本地 Docker。

| 当前资产 | 从哪里继续 |
| --- | --- |
| Kit 已上线且契约/运行满足需求 | 直接开发 Workflow |
| SIF 可用，缺 Kit | 开发、打包、上传并独立测试 Kit |
| ACR 已推送，仅 SIF 未完成 | 复用镜像登记 ID，继续转换与查询 |
| 流水线运行中 | 跟踪现有 run ID，继续本地 Kit/DAG 工作 |
| 完全新项目 | 依赖与业务拆分、Dockerfile、构建推送、SIF、Kit、Workflow |

## 依赖镜像

读取同目录 image-lifecycle.md，按 devops 的 `references/yunxiao-flow.md`、`aliyun-acr.md`、`publishing-rules.md` 与项目配置执行。

- 镜像固化第三方依赖、完整权重、配置/tokenizer、必要数据库；业务模块随 Kit ZIP 交付。运行时不补装核心依赖或下载必要权重。
- 核对 `linux/amd64`、GPU/CUDA/框架相容性，固定版本和路径，生成 `image_layout.md`。
- 构建前运行 devops 的 `scripts/runtime_contract.py`；镜像真实提供 `bash`、指向依赖环境的 `python` 和 `adam_community`，构建期自检不能只有 `python3 --version`。
- 云效显式配置 `build.backend: yunxiao`，不要沿用模板的 local 默认。Codeup 构建上下文仅包含构建材料，Dockerfile 路径相对仓库根目录。
- 需要外网时用云效香港公共构建集群，无外网需求用北京；SIF 目标集群是另一套配置，以平台默认目标/用户选择为准。
- Codeup/ACR 服务连接使用公开 UUID；ACR 企业版实例精确值来自用户/既有 YAML。凭据由环境或受保护配置注入。
- 保存流水线和 run ID、源提交、镜像 tag/digest。实际 build/push 成功后登记镜像、转换 SIF，查询 `cluster_build_status`；ACR push 成功不等于 SIF 就绪。

## Kit 开发与发布调试

按 asterfire-kit-development 实现 `runner(Tool)`、最小表单、`kwargs['args']`、`@tool_io`、业务模块、Demo、报告与详情页；发布包绑定真实可用 SIF。

1. 做表单、Demo、语法和输出端口检查，递增 Kit 版本并 `adam-cli build .`。
2. 解包检查业务模块、配置、Demo 齐全，环境/权重/凭据未混入。
3. 上传前对包内真实名称做大小写冲突检查。只有明确覆盖同名同版本时 force，普通修改递增版本。
4. 通过 `/dev/toolboxes` 或已核验新版 CLI 上传。重新查询运行工具目录和 IO contract；上传成功不代表 DAG 工具已可调用。
5. 用官方轻量示例独立调用 Kit，等终态并检查真实输出和报告。Kit 表单和 Workflow IO contract 都核对，不用历史目录替代。

## Workflow 接入与修复

读取 `../../asterfire-workflow-development/SKILL.md` 及其按需参考。保存工具精确注册名、实际版本/身份和输出端口。未证实 YAML 能锁版本时不发明 `kit_version`；记录契约采集时间，发布后再确认解析结果。

先单条数据串通主链，再按需要增加 scatter/gather。发布默认是方案持久化并可调用；市场公开仅在用户要求时执行。

| 失败位置 | 修复范围 |
| --- | --- |
| 引用/端口/类型/scatter | DAG/脚本/输入，校验并更新 Workflow |
| Kit 业务或报告 | 新 Kit 版本，独立测试后重抓契约、调试 Workflow |
| 缺包/CUDA/权重 | 新镜像版本 → SIF → Kit → Workflow |
| 权限、额度、服务故障 | 保存 ID 和错误码，不以重复创建绕过 |

失败或超时先查现有流水线、镜像、任务，按已存 ID 恢复。相同失败连续三次停止自动重跑；新大规模计算、删除、跨范围覆盖需用户明确范围。端到端已包含发布和轻量调试时，不在每阶段重复确认。
