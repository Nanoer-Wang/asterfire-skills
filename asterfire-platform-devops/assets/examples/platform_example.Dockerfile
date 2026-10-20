# 指定基础镜像
FROM m.daocloud.io/docker.io/python:3.12.12-slim

# 设置环境变量
ENV PATH=/app/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# 复制本地文件到容器中
COPY local_file.txt /app/local_file.txt
COPY requirements.txt /app/requirements.txt

# 容器构建时执行的命令
RUN apt-get update && apt-get install -y python3 python3-pip \
    && if ! command -v python >/dev/null 2>&1; then ln -s "$(command -v python3)" /usr/local/bin/python; fi \
    && python -m pip install -r /app/requirements.txt \
    && python -m pip install "adam-community==1.2.5" \
    && rm -rf /var/lib/apt/lists/*

RUN command -v bash \
    && command -v python \
    && python --version \
    && python -c "import adam_community; print('Asterfire runtime ready')"

# 设置工作目录
WORKDIR /app

# 容器运行时默认执行的命令
CMD ["bash"]

# 容器元数据
LABEL Author="Your Name" \
      Version="1.0.0" \
      Description="Your application description"
