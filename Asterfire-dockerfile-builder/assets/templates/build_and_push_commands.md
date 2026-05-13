# Docker build / tag / push commands

## 1. 构建镜像

```bash
docker build -t <local_image_name>:<image_version> .
```

## 2. 查看镜像名称和 ID

```bash
docker images
```

## 3. 登录阿里云镜像仓库

下面只是示例，实际使用时需要替换为用户自己的阿里云镜像仓库网络地址和用户名：

```bash
docker login --username=xxxxxxxxxxx crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com
```

## 4. 标记镜像

```bash
docker tag [images id] crpi-3v2rl4y9u3xihgef.cn-hangzhou.personal.cr.aliyuncs.com/mlfold/proteinmpnn-1:[镜像版本]
```

或者：

```bash
docker tag <local_image_name>:<image_version> <registry>/<namespace>/<repo>:<image_version>
```

## 5. 上传镜像

```bash
docker push <registry>/<namespace>/<repo>:<image_version>
```
