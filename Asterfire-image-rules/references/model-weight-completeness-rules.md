# 深度学习模型权重完整性检查规则

## 必查对象

- `.pt`、`.pth`、`.ckpt`、`.safetensors`、`.bin`、`.onnx`、`.pkl` 等模型文件。
- tokenizer、vocab、config、database、template、MSA/database index 等运行必需资源。
- `model_name`、`checkpoint`、`weights`、`pretrained`、`model_dir`、`use_soluble_model`、`ca_only` 等会切换模型分支的参数。

## 检查顺序

1. 读取 GitHub README/docs/release/download.sh，确认是否要求外部下载权重。
2. 读取 Dockerfile/image_layout.md，确认权重被 COPY 或下载到镜像内绝对路径。
3. 查找 `RUN test -s` / `test -f` / `test -d` / `ls -lh` 自检；没有自检则建议补充。
4. 读取 runner，确认实际使用的权重路径与镜像路径一致。
5. 对多模型分支逐一检查，不要只检查默认模型。

## 处理原则

- 运行必需的大权重应固化进镜像或稳定挂载目录，并用环境变量暴露路径。
- 小型 demo 输入文件应放在 Kit 的 `demos/` 目录，不要 COPY 进镜像。
- 如果权重来源不可访问，应提醒用户改用可访问镜像源、OSS、内网对象存储或手动提供权重。
