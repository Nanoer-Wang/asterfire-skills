# 阿里云镜像仓库上传命令规则

## 查看本地镜像

```bash
docker images
```

## 登录仓库

示例：

```bash
docker login --username=xxxxxxxxxxx crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com
```

说明：

- `xxxxxxxxxxx` 替换为阿里云镜像仓库用户名。
- `crpi-...aliyuncs.com` 替换为用户自己仓库的公网地址或专有地址。

## 标记镜像

使用镜像 ID：

```bash
docker tag [images id] crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:[镜像版本]
```

使用本地镜像名：

```bash
docker tag proteinmpnn-1:1.0.0 crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:1.0.0
```

## 上传镜像

```bash
docker push crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:1.0.0
```

## 与 Kit SIF 对齐

如果平台登记的 SIF 是：

```python
SIF = "proteinmpnn-1:1.0.0"
```

那么镜像仓库上传的 tag 和平台后台登记的镜像版本也应为 `1.0.0`。
