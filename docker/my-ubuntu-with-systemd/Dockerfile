# 使用 Ubuntu 22.04 作为基础镜像
FROM ubuntu:22.04

# 避免安装过程中交互式提示（如时区设置）
ENV DEBIAN_FRONTEND=noninteractive

# 更新软件包列表并安装 systemd 及一些必要工具
RUN apt-get update && apt-get install -y \
    systemd \
    systemd-sysv \
    dbus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 初始化 systemd 所需的目录
RUN if [ ! -d /run/systemd/system ]; then mkdir -p /run/systemd/system; fi

# 设置容器的默认启动命令为 systemd
CMD ["/sbin/init"]