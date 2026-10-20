# 从平台实时查询镜像

用户的 CLI 发布日志 v0.3.5 已列出 image list/get，v0.4.0 迁移至 Open API v1。用户的 Open API v1 文档明确 GET /dev/images 为“分页列出当前开发者的 SIF 镜像”，支持 name/version/page/per_page，详情含名称、版本和 cluster_build_status。因此镜像名称以目标平台实时结果为准，不再维护本地名称注册表。

## 查询与筛选

已核验使用 Open API v1 的原生 CLI：

```bash
asterfire image list --json
asterfire image list --name <关键词> --json
asterfire image get <image_id> --json
asterfire image clusters --image-id <image_id> --json
```

先检查 CLI 版本/help；本机旧二进制不支持或仍走旧路由时，使用本技能 Open API 客户端。下面是本技能辅助命令，在技能目录运行并沿用已确认的平台配置：

```bash
python -m scripts.cli image list --name <关键词> --page 1 --per-page 50
python -m scripts.cli image list --version <版本> --page 1 --per-page 50
python -m scripts.cli image get --image-id <image_id>
```

对应接口 GET /dev/images、GET /dev/images/{image_id}、GET /dev/images/build-clusters?sif_id={image_id}。列表响应 data.items/total/page_index/per_page/total_page；按分页读完相关结果，不能只查第一页就断言没有镜像。用精确 ID 查详情，核对 name/version、来源、架构/CUDA、依赖/权重证据与目标集群 cluster_build_status。

## 可见范围与选择

此接口需要 dev:read 和开发者身份，查的是当前开发者可见镜像，不能声称覆盖所有公共/共享 SIF。列表为空、403 或缺权限时区分原因；如果用户指定公共/团队镜像但此接口不可见，查已授权的对应目录/配置或询问具体镜像，不从旧名单猜测。查询受限不触发重建同名资源。

名称不能证明依赖、权重、版本或集群已就绪；用户已有明确 SIF 时验证实际可用性。唯一匹配且证据充分可选用，多候选按需求和版本比较，仍无法确定才询问。没有适用候选再进入镜像准备流程。

## 记录与刷新

仅在当前项目交付记录保存选中镜像的 ID、精确 SIF/版本、目标集群、核验时间与必要证据；这是运行溯源，不是手工维护的通用镜像目录。若缓存查询响应，标记环境和时间，发布前重查关键状态。SIF 绑定格式来自平台实际路径/名称与版本，不根据 Docker URL 或显示名猜测。
