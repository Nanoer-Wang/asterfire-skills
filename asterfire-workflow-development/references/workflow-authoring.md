# Workflow 编写与契约

来源：用户本地 Workflow YAML、开发草稿与 CLI 源码。历史模板仅提供结构证据，可用字段以目标环境为准。

## 真实工具端口

查询 `GET /workflow-tools?dag_only=true`，再查相关工具的 `/{name}/contract` 与 `/detail`。Kit 节点的 `kit` 填精确注册名，不填显示名。不复制整份过时工具目录。

将真实 contract 整理为以下**本地校验索引**。这是校验器格式，不是平台 API schema；保留原 contract 供核对。`required_inputs` 按已生效默认值判断，条件必填另行验证。

```json
{
  "工具注册名": {
    "inputs": ["input_pdb", "seed"],
    "required_inputs": ["input_pdb"],
    "outputs": ["output_pdb", "report"]
  }
}
```

使用 `validate_workflow.py workflow.yaml --ports ports.json`。索引不证明版本、文件类型、语义、条件参数或运行环境正确，本地检查后仍需平台校验和 smoke run。

## 节点规则

顶层 `version: '1'`、中文 `title`、`nodes`、`edges`。节点类型不限于 `input/script/kit`；本机服务端 schema 还包括 `agent/conditional/template/kit_gen`，各部署可扩展。按实际导出/契约配置，未知类型由平台验证，不能本地一概拒绝。引用 `{{nodes.<id>.outputs.<key>}}`，生产节点必须是消费者上游。完整最小样例见 `../assets/minimal-workflow.yaml`，用于结构和本地脚本验证，未声称已在生产运行。

- `input`：`params.input_mode: file`，常用输出 `user_input`；具体模式和默认值从部署导出确认。
- `kit`：真实 `kit` 注册名与按 contract 生成的 `params`，输出按契约精确连接。
- `script`：`agent_config.io_spec.inputs/outputs`、`script_code`、`requirements`，输入从 `kwargs['args']` 读取。

## 脚本的关键点

- 平台将代码放在函数上下文执行，可出现顶层 return；本地语法检查要先包装成函数。
- `params` 与 `io_spec.inputs` 对齐。返回字典**实例**，如 `return {'count': 1}`；裸 `return dict` 返回类，运行会失败。输出 key 与 `io_spec.outputs` 一致，不能误把辅助函数 return 当成节点输出。
- 新文件写当前节点目录，再返回相对路径；读取相对路径以当前 node_directory 为基准。scatter 子任务分别处理各自目录。跨节点使用输出端口解析/投递路径，或核实可读范围后访问其他节点目录；不假定本机路径或所有上游目录均可用，不把云盘 ID 当路径。
- `requirements` 是脚本节点依赖声明，与 Kit 的 SIF 固化不同；能否联网安装以目标环境为准。重依赖/模型计算优先作为 Kit 提供。
- 不将 `str/list/dict` 盲目压平成路径；先核对真实输出与包装格式。聚合文件复制到当前目录稳定子目录；只收单文件的下游用 ZIP。

## Scatter / gather

Scatter 是节点级并行能力，不限定 Kit；对脚本和其他类型的具体支持与配置按当前部署确认。先单条跑通，调试从 `concurrency: 1` 开始，正式规模遵循用户要求。常见 `agent_config` 配置：

```yaml
scatter:
  'on': input_file
  gather:
    strategy: collect_all
  concurrency: 1
  min_success_ratio: 1
```

`on` 是当前节点 `params` key，其值绑定上游真实列表。用引号写 `'on'`，避免 YAML 1.1 工具解释为布尔。

多字段成对展开仅在部署已确认支持时使用：

```yaml
scatter:
  'on': [protein_file, ligand_file]
  mode: pair
  gather:
    strategy: collect_all
  concurrency: 1
  min_success_ratio: 1
```

上游保证列表等长、一一对应，定义空列表与失败策略；动态长度无法本地证明时保留提示。不要误做笛卡尔积。本地旧草稿对 pair 支持存在不一致，须以当前导出/契约/最小实验确认。

未支持原生 pair 时，可编码为单个 job 描述，交给能接受它的单一 Kit/已证实子流程；不假定独立脚本节点会自动进入同一 scatter 上下文。聚合先确认 gather 是列表、目录还是文件引用；保持任务标识与配对，不依赖目录字典序。
