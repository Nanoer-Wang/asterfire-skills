# 平台发布、调用、节点调试与产物访问

## 已核对的依据

2026-10-20 对照用户提供的《AsterFire Cli 发布日志》《Open API v1 接口参考》，以及本机 adam-server 源码中的 `app/api/open/v1/workflows/`、`service/workflow/codec/schema.py`、`tests/workflow/test_workflow_execution_files.py` 核对。文档提供路径和 scope，服务端源码补充请求体与运行字段。本机找到的 galileo-cli-main 二进制仍使用旧 `/workflow` 路由，不能用它证明 v0.4.0 已安装。

CLI 先查 `version`/`--help` 和真实路由，v0.4.0 使用 `/api/open/v1` 与 API Token；旧 JWT/密码登录文档不适用于 v1。`workflow session` 是智能设计入口，不是部署和运行成功证据。

## 连接与凭据

生产 API base：`https://sidereus-ai.com/api/open/v1`，鉴权 `Asterfire-Token`。读写工作流需 `workflow:read/write`，执行需 `workflow:execute`；读取产物另需 `file:read`，Kit、任务和镜像权限按 devops 技能。

辅助工具优先级：`--base-url` > `ASTERFIRE_API_BASE` > `~/.asterfire/config.json` 的 base URL > 生产默认。Token 从 `ASTERFIRE_TOKEN` 或该配置读取；复用 devops 的 `.env` 加载器，仅从执行目录向上读最近 `.env`，不覆盖进程变量。选择平台和凭据前先检查 dry-run 的 endpoint，避免误连旧 dev 环境。不要在聊天中索要 Token 或把真实 `.env` 打包。

成功从 `data` 解包。失败保留 HTTP 状态、稳定 `error.code`、`details` 和 `request_id`，不按 message 文案分支。一般写请求只发送一次；未知结果先查询，不能盲重发 import/replace/retry/input。辅助工具不自动重试写请求。

Windows 示例，先在用户项目目录设置脚本路径（不覆盖 CODEX_HOME/HOME）：

```powershell
$workflowApi = Join-Path $env:USERPROFILE '.codex\skills\asterfire-workflow-development\scripts\workflow_api.py'
py -3.12 $workflowApi --dry-run request GET /info
py -3.12 $workflowApi request GET /info
py -3.12 $workflowApi request GET /workflow-tools --query dag_only=true
py -3.12 $workflowApi request GET /workflow-tools/真实注册名/contract --output workflow/contracts/tool.json
```

`--base-url` 与 `--dry-run` 放在子命令前；Linux/macOS 使用相同 Python 脚本。运行脚本不依赖本机安装原生 CLI，需要同级 devops 技能；本地 YAML 校验需要 PyYAML。

## 导入与更新

先本地校验。新方案：

```powershell
py -3.12 $workflowApi --dry-run request POST /workflows/import --yaml-file workflow/workflow.yaml
py -3.12 $workflowApi request POST /workflows/import --yaml-file workflow/workflow.yaml --output workflow/import.json
```

请求体为 `{"yaml":"完整文本"}`。导入到团队空间时，按实际部署支持的字段使用 `--body-file` 提交含 `yaml`、`workspace_id` 的 JSON，而不是给工具添加未实现的参数。新建方案也可 `POST /workflows`：当前服务 DTO 是 `title/prompt/file_ids/workspace_id`，旧 CLI 的 `--request` 不一定对应有效创建字段。以实际版本为准。

记录返回 `id`（不混用 task/session ID）。若网络失败且未得到 ID，先查工作流列表/标题/定义是否已创建；创建接口未确认幂等，不自动重发。

已有方案用实际 ID 替换下列 42：

```powershell
py -3.12 $workflowApi request GET /workflows/42/export --output workflow/before.yaml
py -3.12 $workflowApi request POST /workflows/42/yaml/validate --yaml-file workflow/workflow.yaml
py -3.12 $workflowApi request PUT /workflows/42/yaml --yaml-file workflow/workflow.yaml
py -3.12 $workflowApi request POST /workflows/42/validate
py -3.12 $workflowApi request GET /workflows/42/export --output workflow/published.yaml
```

检查返回中的 issues、warnings、conflict、state_not_editable，HTTP 200 不自动代表校验通过。未知 YAML key 可能被服务端清理并警告，导出后比对不能省略。详情节点字段可能是 `node_type/kit_name/kit_params`，YAML 则是 `type/kit/params`，不要把详情 JSON 当 YAML 原样提交。

高级更新有 `PATCH /workflows/{id}/plan`、`POST /workflows/{id}/patch`、`PATCH /workflows/{id}/nodes/{node}/config`、`PUT /workflows/{id}/demos`；需要时先确认 DTO/导出和定义版本，不凭名字猜请求体。

## 执行与输入

默认缓存策略由平台决定。首次真实集成验证需区分缓存与真实重算；按用户调试意图选择 `--no-cache`，不要默认触发全量重算。

```powershell
py -3.12 $workflowApi run 42 --state workflow/runs/smoke-001.json --no-default-inputs
```

工具在请求前保存 endpoint、参数、幂等键，返回后保存 `plan_id/execution_id/task_id` 和一次状态。它**不会等待到终态**。重复使用同一个 state：已有 execution 时只查状态；请求结果丢失时携带原幂等键恢复。换输入、修改 DAG 或发起新实验使用新 state，不能为了重试随手生成新 key。超出平台幂等保留期或结果仍不明确，先查执行历史，不假定旧 key 永久有效。

状态优先看本次 `execution_status`，不要只看 `plan_status`。当 input 节点处于等待，按返回 execution ID 提交；示例 100 只是演示，必须换为本次 ID：

```powershell
py -3.12 $workflowApi request POST /workflows/42/nodes/node_input/input/file --query execution_id=100 --file workflow/demos/sample.txt
```

文本/云盘输入用 `POST /workflows/{plan}/nodes/{node}/input?execution_id=...`，通过 `--body-file` 传 `content` 或 `cloud_file_id` 等当前部署支持的字段；`input_type/file_name/remote_url` 仅按真实需求提供，不混用文件 ID、URL、本地路径。所有必需 input 节点都需提交，提交后继续跟踪原 execution，不重新 execute。已有确认默认值/继承输入时，可省略 `--no-default-inputs` 或使用 `--inherit-inputs-from`。

```powershell
py -3.12 $workflowApi request GET /workflows/42/executions/100/status
py -3.12 $workflowApi request GET /workflows/42/executions/100
py -3.12 $workflowApi request GET /workflows/42/nodes/node_copy/execution --query execution_id=100
py -3.12 $workflowApi request GET /workflows/42/nodes/node_copy/outputs --query execution_id=100
```

每次轮询间隔通常 5–15 秒，单次工具等待保持有界；长任务保留 ID 持续跟踪并向用户更新。等待输入/暂停/分支跳过/部分成功按当前部署语义判断，不能把 `is_thinking=false` 当工作流所有节点成功。

## 多类型节点与产物目录

用户明确：平台支持节点 scatter 并行、Kit、Python 脚本及包括文件输入在内的多种节点。不要把节点集合限制为三类，也不要假定 scatter 仅能用于 Kit。

本机服务端 YAML schema 还列出 `agent/conditional/template/kit_gen`；未来部署可扩展。各类配置与 IO 从实际导出/工具契约确认。条件边的 `source_output` 可表达分支标签；一般边表达执行依赖，数据传递仍由目标节点 params 引用。条件节点跳过的分支不应误判为失败。Agent、生成类节点、模板展开须核对其真实产物与运行开销，不用通用 Kit 模板硬套。

**产物放在当前节点目录。** 节点代码以当前工作目录创建输出，用相对路径（如 `results/result.csv`、`report.md`）返回；本地/调试读取从当前节点目录解析。API 执行详情里的 `directory_path` 是 execution 根目录，`node_directory` 是具体节点目录，不混用。

- 节点目录/命名从本次执行详情读取，不硬编码 `/data/.../node_数字`。scatter 每个子任务可能有独立子目录；相同文件名在不同子目录可合法存在，不能直接同名覆盖汇总。
- 跨节点优先通过已声明输出端口绑定，由平台解析/投递路径。平台已允许读取的其他目录产物可在核实路径和挂载范围后访问，不额外断言“节点之间文件不可访问”，也不假定所有目录均已挂载。
- `outputs` 返回的 `output_key/file_path/file_name/file_type/file_size/content_hash` 用于定位和验收，`id` 可能是 NodeOutput 记录 ID，**不是可下载 File ID**。
- 先按实际 `node_directory` 与返回路径查询任务文件列表，取得平台返回的真实 File ID 再下载。通过 devops 客户端 `list_task_files(path, workspace_id=...)` / `download_file(file_id, destination, workspace_id=...)`，或下方辅助工具。团队空间保持同一 workspace 上下文，File ID 当不透明字符串，不自行解码/拼造。

```powershell
py -3.12 $workflowApi request GET /tasks/files --query 'path=执行详情中返回的节点目录'
py -3.12 $workflowApi download '真实FileID' --output workflow/artifacts/result.csv
```

`--query workspace_id=...` / `download --workspace-id ...` 按目标空间补齐。远程节点相对路径不等于用户本机可直接打开的文件：先下载，再本地检查和展示。不要把内网绝对路径或签名 URL 当最终可复用产物交付。

## 失败定位与验收

从 node execution 获取实际 step ID，再查 `GET /workflows/{plan}/nodes/{node}/steps/{step}/logs?execution_id=...`。核对最先失败节点、traceback、路径、退出码、端口和产物，避免只查看最后一个报错。

修复后按真实状态选择节点重试 `/nodes/{node}/retry` 或 step 重试 `/steps/{step}/retry`，必要请求体见当前部署 DTO；它们没有通用幂等保护，未知结果先查。不得默认重试运行中/等待输入节点。整流重跑使用新 state，记录输入/YAML 版本，避免混淆缓存和旧产物。

验收同时检查工作流终态、各预期节点状态、scatter 数量和成功比、最终文件存在/非空及格式、报告引用和关键数值。交付计划与执行 ID、产物、再次调用方式，未完成项如实标记。

模板保存仅在需要复用时调用 `/workflows/{id}/template`；不能把创建模板等同公开市场。用户仅调用已有流程时不扩展 CRUD。删除未包含在此工具命令中，需要明确删除需求再按平台工具执行。
