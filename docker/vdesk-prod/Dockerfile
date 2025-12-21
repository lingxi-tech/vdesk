# 使用 NVIDIA CUDA 12.4.1 作为基础镜像
FROM nvidia/cuda:12.4.1-base-ubuntu22.04

# 避免安装过程中交互式提示（如时区设置）
ENV DEBIAN_FRONTEND=noninteractive

# 更新软件包列表并安装 systemd 及一些必要工具
RUN apt-get update && apt-get install -y \
    systemd \
    systemd-sysv \
    dbus \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Docker Engine inside the image (for docker CLI and compose plugin)
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# Optionally add a non-root user to docker group (skip if running as root)
# RUN usermod -aG docker $USER || true

# 复制当前目录下的所有文件到容器内的 /tmp/vdesk 目录
COPY scripts /tmp/vdesk/scripts
COPY web /tmp/vdesk/web

# 设置工作目录
# WORKDIR /tmp/vdesk
# 执行自定义的安装脚本
RUN bash /tmp/vdesk/scripts/deploy_prod.sh

# 初始化 systemd 所需的目录
RUN if [ ! -d /run/systemd/system ]; then mkdir -p /run/systemd/system; fi

# 设置容器的默认启动命令为 systemd
CMD ["/sbin/init"]