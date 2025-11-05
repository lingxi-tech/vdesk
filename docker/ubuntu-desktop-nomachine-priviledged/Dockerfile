ARG BASE_IMAGE=10.233.0.132:8000/gezp/ubuntu-desktop:22.04-cu12.4.1
FROM $BASE_IMAGE

LABEL maintainer="hangdaming"

# handle the priviledges
RUN sed -i "s|#ServerClipboardLimit 0|ServerClipboardLimit 1024 |g" /usr/NX/etc/node.cfg
RUN sed -i "s|#EnableFileTransfer both|EnableFileTransfer client |g" /usr/NX/etc/node.cfg
RUN sed -i "s|#EnableNetworkSharing both|EnableNetworkSharing none |g" /usr/NX/etc/node.cfg
RUN sed -i "/\%sudo/s/ALL$/\/usr\/bin\/apt-get, \/usr\/bin\/systemctl, \/usr\/bin\/apt-add-repository, \/usr\/bin\/add-apt-repository, \/usr\/bin\/apt-add-key, \/usr\/bin\/add-apt-key, \!\/bin\/su/" /etc/sudoers
RUN sed -i "s/root:\$PASSWORD/root:\$ROOTPASSWORD/" /docker_config/entrypoint.sh

EXPOSE 22 4000

ENTRYPOINT ["/docker_config/entrypoint.sh"]