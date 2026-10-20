# AsterFire Open API v1 实现摘要

本文件只保留本 Skill 需要的发布和调用契约。权威来源是用户提供的《Open API v1 接口参考》。

## 基础契约

- 生产 Base URL：`https://sidereus-ai.com/api/open/v1`
- 私有部署：`https://<host>/api/open/v1`
- 请求头：`Asterfire-Token: <api_token>`
- 成功 JSON：`{"success": true, "data": ...}`
- 失败 JSON：`{"success": false, "error": {"code", "message", "details", "request_id"}}`

客户端应对 `data` 统一解包，并保留 HTTP 状态、`error.code`、`details` 和 `request_id`。不得匹配可变的 `error.message` 来决定程序分支。

## 鉴权和 scope

- 镜像/Toolbox 读：`dev:read` + `DEVELOPER`
- 镜像/Toolbox 写：`dev:write` + `DEVELOPER`
- Kit 调用：`kit:write`
- Agent 任务读/写：`task:read` / `task:write`
- 文件读/写：`file:read` / `file:write`
- Workflow 读/执行：`workflow:read` / `workflow:execute`
- Toolbox 目录：`toolbox:read`

首次连接先调用 `GET /info`。`403 auth.developer_required` 表示账号缺少开发者身份，不是仅增加 scope 就能解决。

## Dev 镜像

| 用途 | 方法与路径 | 关键输入/输出 |
|---|---|---|
| 列表 | `GET /dev/images` | `page`, `per_page`, `name`, `version` |
| 详情 | `GET /dev/images/{image_id}` | `DevImage` |
| 登记 | `POST /dev/images` | `name`, `version`；`file_id`/`docker_url` 二选一 |
| 更新 | `PUT /dev/images/{image_id}` | 名称和版本创建后不可改 |
| 集群 | `GET /dev/images/build-clusters` | optional `sif_id` |
| 构建 | `POST /dev/images/{image_id}/build` | required `target_cluster_codes`; returns `task_id` |
| 删除 | `DELETE /dev/images/{image_id}` | 破坏性操作 |

登记镜像不等于构建 SIF。必须使用登记结果的 `id` 再调用 build。

## Dev 异步任务

- `GET /dev/async-tasks/{task_id}`：任务详情、步骤和日志预览。
- `GET /dev/async-tasks/{task_id}/log?step_id=<id>&stream=stdout|stderr`：纯文本，不带 JSON 信封。

## Dev Toolbox

- `POST /dev/toolboxes`：multipart，字段 `file`，optional `force=false`。
- `GET /dev/toolboxes`：列出开发者的所有 Toolbox 版本。

Open API v1 未公开旧版 Toolbox update/delete/set-tags/download 端点，不要自行构造。

## Kit

- `GET /toolboxes?type=kit`：查询可调用 Kit 和 `input_schema`。
- `POST /kits/submit`：`toolbox`, `input`, optional `workspace_id`；返回 `task_id`, `step_id`, `message`。
- `POST /tasks/{task_id}/kit-run`：`kit_name`, `input`；在已有任务里追跑。

Open API v1 没有 `/dev/kit/submit`。

## Agent/Tasks

- `GET /tasks`
- `POST /tasks`：`message`, `toolbox`, optional `llm_model`, `file_ids`, `folder_id`, `workspace_id`
- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/status`；传 `step_id` 时返回 `job_status`
- `POST /tasks/{task_id}/messages`：`message`, optional `llm_model`, `file_ids`
- `POST /tasks/{task_id}/stop`
- `POST /tasks/{task_id}/rename`
- `DELETE /tasks/{task_id}`

字段名使用 `file_ids`，不是旧版 `fileIds`。

## Files

- `POST /files/upload`：multipart `file`, optional `task_id`
- `GET /tasks/files?path=<path>`
- `GET /files/{file_id}/download`：可能返回 302 预签名 URL，下载客户端需跟随重定向并流式写盘。

## Workflow 最小调用集

- `GET /workflows`
- `POST /workflows/{plan_id}/execute?no_cache=false`
  - body: `use_default_inputs`, optional `inherit_inputs_from`
  - header: `Idempotency-Key`
  - returns `plan_id`, `execution_id`, `task_id`, `status`
- `GET /workflows/{plan_id}/executions/{execution_id}/status`

## 重试原则

- GET/HEAD 可对 429/5xx 做有界重试。
- 写请求默认只发送一次。
- 只有契约明确支持幂等键且已传入键时，才能自动重试写请求。
- 429 优先使用 `error.details.retry_after_seconds`。
