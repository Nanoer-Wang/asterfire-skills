---
name: asterfire-platform-devops
description: Asterfire 唯一全链路编排入口：项目到镜像、Kit、Workflow 的构建推送、发布调用和调试。也处理独立 Dockerfile、镜像路径/权重检查、云效/ACR、SIF 转换、Kit/Agent 上传和已有任务调用；按用户范围选择阶段，代码与 DAG 分别交给对应开发技能。
---

# Asterfire 平台交付与镜像开发

统一决定阶段、复用资产、推进发布和恢复中断。完整链路是镜像 → SIF → Kit 独立验证 → Workflow 发布和验证。仅做 Dockerfile、路径诊断、Kit ZIP 或调用已有流程时限定到该任务，不自动扩大为完整发布。

## 选择模式并按需读取

| 任务 | 本技能负责 | 按需参考 |
| --- | --- | --- |
| GitHub/脚本到 Kit/Workflow，完整端到端 | 统一阶段、状态、发布和验收 | [全链路](references/end-to-end.md)、[发布细节](references/project-delivery.md) |
| Dockerfile、依赖/权重固化、镜像路径诊断 | 镜像材料、自检、目录说明、路径核对 | [镜像阶段](references/image-lifecycle.md) |
| 云效构建推送、ACR、SIF | 所选路线构建、推送、登记、转换、恢复 | [云效](references/yunxiao-flow.md)、[ACR](references/aliyun-acr.md)、[发布规则](references/publishing-rules.md) |
| Kit/Agent 上传、调用和调试 | 版本/冲突检查、上传、任务和产物 | [发布细节](references/project-delivery.md)、[Open API](references/adam-api.md) |
| Workflow 方案开发/发布/调用 | 全链路时衔接阶段；DAG 细节交工作流技能 | [Workflow](../asterfire-workflow-development/SKILL.md) |

Kit 代码、项目适配、表单、Demo、报告和 ZIP 使用 [Kit 开发](../asterfire-kit-development/SKILL.md)；Agent Tool/docstring/hooks/ATP 使用 [Agent 开发](../asterfire-agent-skill/SKILL.md)。它们是专业实现规则；整套链路仍由本技能编排。不要求用户逐项提示构建、上传、调试，也不重复已确认的路线和授权。

镜像名称与版本始终按 [平台实时查询](references/image-discovery.md) 获取；不维护本地名称注册表。

## 通用决策与阶段交接

1. 读取请求、项目和已有配置，确认平台环境、空间与产物目标。已有镜像/Kit/Workflow 优先复用；只读核查后从缺失阶段继续。镜像状态仍未知且会影响工作时询问必要信息；用户已选择方式则沿用。云效为推荐构建方式，用户“按默认/走流水线”即沿用，不把沉默当选择。
2. 镜像只提供依赖、稳定第三方引擎、完整权重和运行数据库；Kit ZIP 包含业务代码和入口。业务变化更新 Kit；依赖/权重变化才重建镜像。路径以当前节点/Kit工作目录和实际镜像布局区分，不能因 Python 后缀就把业务搬入镜像。
3. 按镜像阶段生成/核对 Dockerfile 与 image_layout.md，在构建前运行 `scripts/runtime_contract.py`。唯一启动检查实现位于该模块，发布流程与兼容检查命令均复用它。最终非交互环境应能执行 bash、python，并导入 adam_community。
4. 新镜像按已选云效/本地路线 build/push；云效显式 `build.backend: yunxiao`，不沿用模板隐式 local。Codeup 来源、服务连接公开 UUID、ACR 企业版精确配置按用户现有配置。失败不擅自切换路线。本机不需要 Docker 即可走云效。
5. 登记平台镜像后在目标集群转换 SIF，以 `cluster_build_status` 确认可用；ACR push 成功不等于 SIF 就绪。已存在登记/流水线 run 时按原 ID 继续，不重复创建。
6. 使用 Kit 开发技能完成绑定真实 SIF 的包；上传前读取 ZIP 内真实名称和版本，做不区分大小写冲突检查；日常改动递增版本，同名同版本 force 仅按明确覆盖要求。端到端 Kit 开发默认独立跑真实轻量 Demo，等终态并核对报告、文件和关键结果。
7. 仅当目标包含 Workflow 时交给 Workflow 技能查询真实契约、编写/校验 DAG、导入/更新、提交输入、执行并检查各节点与产物；独立 Kit 任务不新建 Workflow。Workflow 发现缺少 Kit/镜像时回到本编排的缺失阶段，不在工作流技能内复制发布步骤。
8. 保存流水线/run、镜像/SIF、Kit 版本与 smoke task、plan/execution/task 和产物 ID。恢复先查原状态；Workflow execute 持久化幂等键，换输入或改 DAG 的新实验使用新执行记录。

## 平台与凭据

API base 为 `https://sidereus-ai.com/api/open/v1`，私有部署按实际地址；鉴权 `Asterfire-Token`，成功解包 data，错误保留 code/details/request_id。Dev 写入需对应 scope 和开发者身份。未受幂等保护的写请求不自动重试。

凭据从环境/受保护配置读取，不写入源码、镜像、ZIP 或技能。支持项目最近 .env 且不覆盖进程变量，变量名见 `.env.example`。复用历史 CLI 配置前核对 base URL。权限/数据缺失时继续独立本地工作，仅询问阻塞信息。

## 执行工具与验收

镜像工具及路径扫描见镜像参考；现有平台 CLI 使用本技能的 `python -m scripts.cli`，在本技能目录运行并给项目文件使用绝对路径。调用前查 help 和配置，先 dry-run；发布自动化不能凭生成命令宣布成功。Workflow 优先使用工作流技能的 state-aware API 工具，按 execution 查询并访问节点目录产物。

相同失败连续三次停止自动重跑并保留证据；新增大规模计算、删除和跨范围覆盖按用户明确范围。交付各阶段实际状态、产物和可复用调用方法，未运行项如实说明。仅修改技能时做本地验证，不触发生产发布/计算。
