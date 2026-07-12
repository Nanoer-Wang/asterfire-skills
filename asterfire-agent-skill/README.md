# asterfire-agent-skill

用于开发、审查、调试、重构、打包和验证 AsterFire Adam Tool Protocol (ATP) Agent Toolbox 的 Codex/OpenAI Skill。

本 Skill 采用中文主文，保留 `Tool`、`@tool_io`、`calltype`、`kwargs["args"]`、`adam-cli build` 等协议/API 原文，便于与 ABACUS Agent 当前中文 system prompt 和 Tool docstring 保持一致。

核心行为：

1. 约束 exposed Tool 必须直接继承 `adam_community.tool.Tool` 或 `*.Tool`，并实现 `call(self, kwargs)`。
2. 明确 Agent Toolbox 与 Kit 的边界，避免把 `config/input.json`、单 `runner(Tool)` 等 Kit 规则套用到 Agent Toolbox。
3. 记录 `adam-community==1.2.5` 的 `adam-cli parse/build` 行为，包括显式 Tool 继承识别、parser-visible metadata、`_*.py` / `config/*.py` parse 与 build 边界、config 文件和 `demos/` 打包范围。
4. 规范 class docstring、`@tool_io` parser/runtime 契约形态、`declare_outputs`、`calltype`、hook、stdout/stderr、`summary`、资源字段和文件交接；资源调度规则保持逐案判断，不把 `PARTITION` 写成硬调度接口。
5. 约束 packaged files 不应包含凭据、token、API key、私有 URL 或本地敏感信息。
6. 随附 `scripts/check_atp_tool_integrity.py`，用 `--parser-command` 接入 `adam-cli parse` 或项目级 `make parse`，并在 `--strict-parser` 下把 parser output 暴露缺口视为错误。
7. 记录 Markdown report 渲染规则，区分结构渲染、二维图片、轨迹和日志文件。

## Tool Audit Script

通用审查脚本位于：

```text
scripts/check_atp_tool_integrity.py
```

推荐先让 parser 生成平台可见的 `functions.json`，再叠加通用完整性检查：

```bash
python3 scripts/check_atp_tool_integrity.py --root . --parser-command "adam-cli parse ." --strict-parser
```

该脚本不会替代 parser；parser output 仍是 Tool 是否平台可见的事实来源。项目特定规则应由项目仓库 wrapper 承载。

## Reference Layout

本 Skill 只捆绑必要的外部参考快照：

```text
references/
  adam-community/
    README.md
```

`SKILL.md` 是唯一活跃规则源；`references/adam-community/README.md` 只用于追溯 PyPI README 中与 parser、build、states 和 Tool I/O 相关的事实。
