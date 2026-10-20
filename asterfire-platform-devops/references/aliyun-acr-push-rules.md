# ACR 上传命令的使用范围

企业版/个人版与云效/本地路线统一按同目录 [aliyun-acr.md](aliyun-acr.md)、[yunxiao-flow.md](yunxiao-flow.md) 和 [publishing-rules.md](publishing-rules.md) 执行。本地登录/打标/push 模板在 `../assets/templates/build_and_push_commands.md`，仅在用户选择本地 Docker 时使用。

Registry、namespace、repository 和 tag 来自当前项目配置；模板中的历史个人仓库地址不是默认值。最终推送 tag、平台登记版本和 Kit 的真实 SIF 绑定需要核对。
