FROM registry.cn-hangzhou.aliyuncs.com/sidereus-ai/python:3.12.12-slim

RUN rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian trixie main" > /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian trixie-updates main" >> /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security trixie-security main" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH

COPY Miniconda3-latest-Linux-x86_64.sh /tmp/miniconda.sh
RUN bash /tmp/miniconda.sh -b -p $CONDA_DIR \
    && rm /tmp/miniconda.sh \
    && conda clean -afy

RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

WORKDIR /app
COPY environment.yml /app/environment.yml
RUN conda env create -f /app/environment.yml \
    && conda clean -afy

ENV PATH=/opt/conda/envs/mlfold/bin:$PATH

COPY ProteinMPNN/ProteinMPNN-main /opt/ProteinMPNN
ENV PROTEINMPNN_HOME=/opt/ProteinMPNN
ENV PYTHONPATH=/opt/ProteinMPNN:/app:$PYTHONPATH

RUN python --version \
    && which python \
    && ls -lah /opt/ProteinMPNN \
    && test -f /opt/ProteinMPNN/protein_mpnn_run.py

WORKDIR /app
CMD ["bash"]

LABEL Author="wangming_base" \
      Version="1.0.1" \
      Description="Asterfire Kit image with Conda environment and local ProteinMPNN project"
