# 镜像开发、路径与权重核对

镜像名称、版本和可用状态见同目录 [image-discovery.md](image-discovery.md)，以目标平台实时查询为准。

本文件统一原镜像构建和路径检查阶段；依照任务范围执行，不因单独写 Dockerfile/排查路径而自动推送。云效/ACR、SIF 与 Kit 发布流程见同目录 `project-delivery.md`，全链路顺序见 `end-to-end.md`。

## 先区分资源归属

- 镜像：系统/语言依赖、CUDA、稳定第三方库或引擎、完整模型权重、tokenizer/config 与必需数据库。
- Kit ZIP：该项目核心业务模块、脚本、runner、参数组装、前后处理和报告；小 Demo 输入在 Kit demos。
- 当前任务/节点目录：用户输入、生成配置、中间结果、日志、报告与输出。以 Path.cwd() 和实际 node_directory 为基准，输出优先返回相对路径。

旧 ProteinMPNN 整仓 COPY 或调用镜像内脚本的模板，只适用于已确认的稳定第三方引擎/既有布局维护；不能因为项目来自 GitHub 就把整个待适配业务仓库固化进镜像。运行输出不写 /opt、/app 等镜像资源目录。生成器提供构建材料，使用后必须审查 COPY 范围与路径。

## 生成与检查 Dockerfile

先从官方项目材料和实际配置核对 Python/CUDA/框架及依赖版本、架构、软件许可和完整权重来源。基础镜像按依赖选择；Docker Hub 来源优先 `m.daocloud.io/docker.io/` 加速，私有/ACR 镜像不加此前缀。默认发布目标 linux/amd64，用户有明确目标时沿用。

1. 编写 Dockerfile、依赖清单、.dockerignore、权重下载/完整性检查和 image_layout.md。固定依赖和模型版本；构建时检查关键资源非空、非 LFS 指针，有校验和时校验。
2. 平台最终非交互环境需有 bash、python，以及 python 可导入的 adam_community。Conda 通过 ENV PATH 暴露实际依赖环境，不能仅依赖激活命令、CMD 或 ENTRYPOINT。
3. 构建期执行 `command -v bash`、`command -v python`、`python --version`、`python -c "import adam_community"`。统一由 `scripts/runtime_contract.py` 检查；静态声明通过仍需实际构建期 import/资源检查和最小案例。
4. 依赖构建/自检在已选云效环境执行，不要求用户本机 Docker。可用 GPU 最小任务在目标平台验证。仅本地 Docker 路线才执行本机 build/login/push。

详细规则按需读 [Dockerfile](dockerfile-rules.md)、[目录说明](image-directory-layout.md)、[权重完整性](model-weight-completeness-rules.md)。ACR 路线、版本和身份统一读 [aliyun-acr.md](aliyun-acr.md)、[publishing-rules.md](publishing-rules.md) 和 [yunxiao-flow.md](yunxiao-flow.md)，不把历史个人仓库示例当默认目的地。

## 现有镜像/Runner 路径诊断

读取当前版本的 image_layout.md，缺失时分析 Dockerfile 的 ENV/COPY/ADD/WORKDIR。用户显式路径优先；目录说明须与实际镜像版本匹配。WORKDIR 只能辅助，不能单独证明项目位置。说明与 Dockerfile 冲突时用构建记录或只读探针核实，修正过时说明；不能默认旧说明总是正确。无法证明路径时请求具体缺失信息，不根据本机目录猜镜像路径。

形成映射：资源 → 交付位置 → 镜像/当前节点路径 → runner 引用。镜像资源用环境变量/绝对路径，随 ZIP 的业务模块从实际投递目录导入，输入输出在当前任务/节点目录。根据目标工具是否内部依赖相对路径决定 cwd；即使 cwd 设到第三方引擎目录，也把输出路径显式指向可写工作目录。

逐个核对模型分支和配套文件，不能只确认一个 checkpoint。稳定挂载资源仅在平台已保证可用且用户要求时使用，记录挂载依赖；默认完整固化进镜像。运行时不补下载核心权重。外部权重无法取得时可继续本地准备，但不宣称镜像/Kit已验证。

按需读 [目录证据优先级](image-layout-priority-rules.md)、[Dockerfile 路径分析](dockerfile-path-rules.md)、[Runner 路径](runner-path-rewrite-rules.md)。[ProteinMPNN 案例](proteinmpnn-example.md) 只用于该引擎，不套用于其他项目。

## 工具与模板

脚本绝对路径指向本技能，在项目目录执行；不会因为文档中列出命令就自动执行远程推送。

```text
python <skill>/scripts/generate_dockerfile.py --config <config.json> --out <Dockerfile> --commands <commands.md> --layout <image_layout.md>
python <skill>/scripts/runtime_contract.py <Dockerfile> --json
python <skill>/scripts/check_dockerfile_paths.py <Dockerfile>
python <skill>/scripts/image_layout_analyzer.py --layout <image_layout.md> --json
python <skill>/scripts/docker_path_analyzer.py --dockerfile <Dockerfile> --json
python <skill>/scripts/runner_path_scanner.py --runner <entry.py> --json
```

兼容命令 `validate_runtime_contract.py` / `runtime_contract_scanner.py` 只是统一检查实现的入口，不再各自维护规则。`patch_proteinmpnn_runner.py` 是专用辅助，只在已确认归属与路径后生成补丁，并审查输出。

模板在 `assets/templates/`（Dockerfile.*、image_layout.md、path_resolver.template.py），历史引擎示例在 `assets/examples/`。轻量工具演示在 `assets/demos/image-build/`、`assets/demos/image-paths/`。模板中的仓库、tag、权重与 SIF 都需按真实项目核对，不将占位值发布。

## 交接与验收

输出依赖构建材料、image_layout.md、权重清单/校验结果、实际版本和路径映射。发布时额外记录源提交、流水线 run、ACR tag/digest、镜像登记 ID 和 SIF 目标集群状态。镜像可用后交给 Kit 技能绑定真实 SIF；业务问题修 Kit，依赖/权重问题才重建镜像。
