# Asterfire Dockerfile Builder Skill

该 Skill 用于 Asterfire 平台 Kit 开发中的镜像构建环节，帮助开发者生成 Dockerfile、构建/上传命令和镜像目录结构说明。

核心关注点：

- 将本地项目、权重、数据库、脚本固化到镜像内的明确绝对路径。
- 区分镜像构建路径 `/app`、`/opt` 与平台运行时工作目录 `/workspace`。
- 给出 `docker build`、`docker images`、`docker login`、`docker tag`、`docker push` 的标准命令。
- 给后续 Kit 主入口代码开发者提供可读的镜像目录结构说明。

推荐 Skill 名称：`asterfire-dockerfile-builder`。
