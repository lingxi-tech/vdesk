#!/bin/bash
# this script is used to update certain parameters of all the running container

DIR=/data/docker/containers

# stop the docker service in case the configuration files been modified automatically during the edition
systemctl stop docker
systemctl stop docker.socket

# change all the host mount folder from /mnt/workspace to /data/workspace
for dir in $DIR/*; do
  if [ -d "$dir" ]; then
    echo "Updating volume mounts in container directory: $dir"

    if [ -f "$dir/hostconfig.json" ]; then
      cp "$dir/hostconfig.json" "$dir/hostconfig.json.bak"
      sed -i 's/mnt\/workspace/data\/workspace/g' "$dir/hostconfig.json"
    else
      echo "Warning: hostconfig.json not found in $dir"
    fi

    if [ -f "$dir/config.v2.json" ]; then
      cp "$dir/config.v2.json" "$dir/config.v2.json.bak"
      sed -i 's/mnt\/workspace/data\/workspace/g' "$dir/config.v2.json"
    else
      echo "Warning: config.v2.json not found in $dir"
    fi
    echo "Completed volume mount updates in $dir"
  else
    echo "Skipping $dir, not a directory"
  fi
done

# restart the docker service
systemctl start docker.socket
systemctl start docker
