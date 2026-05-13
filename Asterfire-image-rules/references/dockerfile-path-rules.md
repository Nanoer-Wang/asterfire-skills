# Dockerfile 路径推断规则

注意：如果存在 `Asterfire-dockerfile-builder` 生成的 `image_layout.md` / 镜像目录结构说明，应先读目录说明。本文件规则仅用于没有目录说明时的兜底推断。

## 优先级

1. `ENV XXX_HOME=/absolute/path`、`ENV XXX_ROOT=/absolute/path`、`ENV XXX_DIR=/absolute/path`。
2. `COPY local_dir /absolute/path` 或 `ADD local_dir /absolute/path`。
3. `RUN test -f /absolute/path/file`、`RUN ls /absolute/path`。
4. `WORKDIR /absolute/path` 只能作为辅助线索，不能单独认定为项目根目录。

## 不可接受的做法

- 看到本地目录名就假设镜像里路径相同。
- 在 runner 中使用 `Path.cwd() / "项目名"` 查找镜像内项目。
- 把模型权重路径写成相对路径，除非 `execCmd(cwd=镜像项目根目录)` 且上游程序明确按该根目录相对读取。

## 用户必须补充的情况

- Dockerfile 未提供 COPY/ADD/ENV 目标路径。
- Dockerfile 多个候选目录都可能是项目根目录。
- 代码中直接使用权重文件，但 Dockerfile 未显示具体权重位置。
