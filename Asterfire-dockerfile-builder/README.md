# Asterfire Dockerfile Builder Skill

该 Skill 用于 Asterfire 平台 Kit 开发中的镜像构建环节，帮助开发者生成 Dockerfile、构建/上传命令和镜像目录结构说明。

核心关注点：

- 将本地项目、权重、数据库、脚本固化到镜像内的明确绝对路径。
- 区分镜像构建路径 `/app`、`/opt` 与平台运行时工作目录 `/workspace`。
- 给出 `docker build`、`docker images`、`docker login`、`docker tag`、`docker push` 的标准命令。
- 给后续 Kit 主入口代码开发者提供可读的镜像目录结构说明。

推荐 Skill 名称：`asterfire-dockerfile-builder`。


## 更新规则

- 基础镜像可按项目自由选择；Docker Hub 来源镜像建议使用 `m.daocloud.io/docker.io/` 前缀加速。
- 深度学习项目必须检查并固化运行必需模型权重；小型 demo 输入文件应放入 `demos/`。
