# Dockerfile 镜像路径分析
Dockerfile: /mnt/data/Dockerfile(1)

## ENV
- CONDA_DIR=/opt/conda
- PATH=/opt/conda/envs/mlfold/bin:$PATH
- PROTEINMPNN_HOME=/opt/ProteinMPNN
- PYTHONPATH=/opt/ProteinMPNN:/app

## WORKDIR
- /app
- /app

## COPY / ADD
- COPY ['Miniconda3-latest-Linux-x86_64.sh'] -> /tmp/miniconda.sh
- COPY ['environment.yml'] -> /app/environment.yml
- COPY ['ProteinMPNN/ProteinMPNN-main'] -> /opt/ProteinMPNN

## 候选镜像内资源根目录
- /opt/conda  (high, ENV CONDA_DIR)
- /opt/ProteinMPNN  (high, ENV PROTEINMPNN_HOME)
- /tmp  (medium, COPY Miniconda3-latest-Linux-x86_64.sh -> /tmp/miniconda.sh)
- /app  (medium, COPY environment.yml -> /app/environment.yml)
- /opt  (low, RUN path check /opt/ProteinMPNN)
