ARG BASE_IMAGE=10.233.0.132:8000/hdm/ubuntu-desktop-nomachine-priviledged:22.04-cu12.4.1
FROM $BASE_IMAGE

LABEL maintainer="hangdaming"

ENV DEBIAN_FRONTEND=noninteractive

# in case the deb file could not be downloaded during the build
COPY ./ros2-apt-source_1.1.0.jammy_all.deb /tmp/ros2-apt-source.deb

# install ros-humble-desktop
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9
RUN apt install -y software-properties-common && add-apt-repository universe && apt update
# RUN export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
# RUN curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb" # If using Ubuntu derivates use $UBUNTU_CODENAME
RUN apt install -y /tmp/ros2-apt-source.deb
RUN apt update
RUN apt install -y ros-humble-desktop

EXPOSE 22 4000

ENTRYPOINT ["/docker_config/entrypoint.sh"]