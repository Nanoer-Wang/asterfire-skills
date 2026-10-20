---
name: asterfire-workflow-development
description: 开发、导入发布、修改、调用和调试 Asterfire DAG Workflow；将多个 Kit 串联，处理 input/script/kit 节点与 scatter/gather。专注节点类型、端口、节点级 scatter、相对路径产物和执行调试；完整镜像→Kit→Workflow 链路由 asterfire-platform-devops 统一编排。
---

# Asterfire Workflow 开发与调试

将用户要求交付成可复现的工作流：真实工具契约 → DAG → 本地校验 → 平台导入/更新 → 提交输入 → 执行 → 节点和产物验证。本技能只负责 Workflow 专业阶段；缺镜像/Kit 时把缺口交给 DevOps，由它统一编排准备与发布，再回到本阶段。

## 范围与入口

| 用户目标 | 执行范围 |
| --- | --- |
| 多个现有 Kit 串成工作流 / 开发 Workflow | 查询工具契约，开发、发布并用轻量真实案例调试工作流；已有 Kit/镜像直接复用 |
| 从 GitHub/脚本到 Kit 再到 Workflow / 完整端到端 | 由 DevOps 统一编排；本技能负责其中的 Workflow 阶段 |
| 只要 YAML / 本地开发 / 暂不发布 | 交付文件与本地验证；不进行远程写入或计算 |
| 调用已有 Workflow | 查询并调用指定方案；不修改 DAG、重发 Kit 或新建镜像 |
| 修改已有 Workflow | 先读取并导出备份，再作必要修改；执行沿用用户范围 |
| 创建或修改本 Skill | 只操作技能及本地验证，不发布实际项目、不调用生产计算 |

“发布 Workflow”默认指方案导入到用户指定的个人/团队空间并可调用；不等于公开到市场。未要求市场公开时不改变分享权限。不假设存在 `workflow push/build` 命令。仅会话生成、仅导入成功、仅提交执行均不算运行验证通过。

## 按需参考与交接

- 编写各类节点、脚本、scatter：读 [references/workflow-authoring.md](references/workflow-authoring.md)。
- 平台导入、更新、执行、输入、日志和节点产物：读 [references/platform-operations.md](references/platform-operations.md)。
- 全链路、缺镜像/Kit、需要修复依赖：交给 [DevOps](../asterfire-platform-devops/SKILL.md)，本技能不另定义云效/ACR/SIF/Kit 发布流程。
- 需要修改 Kit IO 或业务代码时使用 [Kit 开发](../asterfire-kit-development/SKILL.md)，发布与独立调试由 DevOps 衔接。

API 工具仅复用同级 DevOps 的公共客户端；这种代码依赖不要求每次查询工作流都加载整套发布流程。已有授权和路线选择继续有效。

## 执行流程

1. **盘点与契约。** 读取现有 YAML/代码、指定平台环境、空间、数据和目标。查询 `/info`、可用 DAG 工具及每个工具 IO contract；缓存相关契约到项目 `workflow/contracts/`。名称、必填项、输出 key、格式及版本以实际响应和已发布 Kit 为准。目录描述只用于找候选。
2. **补齐依赖。** 已有可用 Kit/镜像就跳过对应发布步骤。需要新增或发布 Kit 时交回 DevOps；收到可用 Kit 和独立 smoke test 证据后再接入 Workflow。编排错误只改 Workflow；业务问题改 Kit；依赖/权重问题才重建镜像。
3. **开发。** 先明确每个节点的输入、输出和边，再写 `workflow/workflow.yaml`，按需保留源脚本与轻量 Demo。节点类型开放，除文件输入、Kit、Python 脚本外，还按部署契约使用其他类型；scatter 是节点级能力，不限定在 Kit。使用 `{{nodes.<id>.outputs.<key>}}` 精确绑定；生产节点须为消费者的上游。脚本返回字典实例，不能写裸 `return dict`。产物保存在当前节点目录，优先返回相对路径；读取以真实 node_directory 为基准，跨节点通过端口或已核实可读路径访问。
4. **本地检查。** 用 `scripts/validate_workflow.py` 检查 YAML、重复 key、环、引用、脚本语法/输出和 scatter。Kit 接口检查使用从真实契约整理的 ports 文件；未提供时保留“接口尚未验证”提示，不能宣布通过所有检查。
5. **发布。** 新方案 import 一次并立即记录 plan ID；已有方案先 export 备份，再 validate-yaml 和 replace/patch。平台校验的 `issues` 须为空。导入后重新读取/导出，核对节点、边和端口映射。原生 CLI 须先验证版本和 Open API v1 路由；旧 CLI 使用本技能 API 工具替代。
6. **调试与调用。** 首次使用小输入、少量任务、低并发。先检查默认值和历史输入，覆盖不适用的旧配置。按平台机制创建 execution，再向等待输入的节点提交该 execution 的数据；已确认默认输入则直接运行。执行前保存幂等键和意图，执行后记录 execution/task ID；按本次 execution 查询节点、步骤、日志和文件。
7. **验收与恢复。** 检查所有预期计算节点终态及关键产物的存在、格式和科学意义；缓存命中须如实标记，等待输入不算失败或成功。失败取本次 execution 的详情和日志后修复。连续三次相同失败停止自动重跑并交付证据；权限、缺数据或超出约定规模时只请求必要信息。中断后先查状态，不重建流水线或重复导入/执行。

## 本地工具

以下路径相对本技能目录。使用脚本绝对路径，在用户项目目录执行；不要切换到技能目录导致 Demo/凭据/执行记录写错位置。

```text
python <skill>/scripts/validate_workflow.py workflow/workflow.yaml --ports workflow/contracts/ports.json
python <skill>/scripts/workflow_api.py --help
python <skill>/scripts/workflow_api.py --dry-run request POST /workflows/import --yaml-file workflow/workflow.yaml
```

API 工具复用同级 devops 的 Open API 客户端，从环境变量或受保护 CLI 配置读取 Token，支持明确 base URL，不打印凭据。所有 dry-run 只生成计划，不访问网络。命令、断点恢复和环境变量见平台参考。

## 完成交付

按需交付 YAML、相关契约/源脚本、Demo 和验收说明。发布/调试时维护项目 `workflow/release.json`：环境、空间、相关 Kit 名称/版本与契约、plan ID、YAML hash、execution/task ID、缓存情况、节点产物文件 ID、状态和未完成项。流水线/镜像/SIF 等上游阶段由 DevOps 的交付记录负责，仅引用已有记录。只记录确实执行的阶段，不写 Token、密码或签名下载 URL。幂等键由 `run` 的 state 文件保存，不跨不同输入或修改后的 DAG 复用。

向用户说明已交付什么、发布到哪里、哪个案例通过和如何再次调用。只完成本地技能验证时明确这一点，不宣称生产端到端已通过。
