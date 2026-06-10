# asterfire-image-path-calibrator

用于校准 Asterfire Kit 中“运行时工作目录”和“镜像内置资源目录”的路径关系。

典型用途：

1. 优先读取 `Asterfire-dockerfile-builder` 生成的 `image_layout.md` / `镜像目录结构说明.md`，识别镜像内项目根目录，例如 `/opt/ProteinMPNN`。
2. 如果没有目录说明，再从 Dockerfile 的 `COPY / ENV / WORKDIR` 中识别镜像内项目根目录。
3. 扫描 `ProteinMPNN.py` / `runner.py` 中错误使用 `Path.cwd()` 查找镜像内代码、`.pt` 权重、helper 脚本的问题。
4. 将主函数入口改为使用镜像内绝对路径或环境变量默认路径。
5. 保证 Asterfire 平台上传文件、中间文件、输出 zip、report.md 仍写在运行时工作目录。
6. 在需要时同步维护 `demos/demos.json` 示例配置。

快速使用：

```bash
# 1. 优先分析 Asterfire-dockerfile-builder 生成的镜像目录结构说明
python scripts/image_layout_analyzer.py --layout image_layout.md

# 2. 没有目录说明时，兜底分析 Dockerfile
python scripts/docker_path_analyzer.py --dockerfile Dockerfile

# 3. 扫描 runner 路径风险
python scripts/runner_path_scanner.py --runner ProteinMPNN.py

# 4. 优先按 image_layout.md 修复；Dockerfile 作为兜底
python scripts/patch_proteinmpnn_runner.py \
  --runner ProteinMPNN.py \
  --layout image_layout.md \
  --dockerfile Dockerfile \
  --output ProteinMPNN.path_fixed.py

# 5. 如果没有 image_layout.md / Dockerfile，则由用户显式指定镜像路径
python scripts/patch_proteinmpnn_runner.py \
  --runner ProteinMPNN.py \
  --image-root /opt/ProteinMPNN \
  --output ProteinMPNN.path_fixed.py
```


## 更新规则

- 校准路径时同时检查深度学习模型权重完整性，尤其是 GitHub 之外下载的 checkpoint。
- 小型 demo 输入文件放在 `demos/`，不要作为镜像内置资源处理。
