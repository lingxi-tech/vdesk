#!/bin/bash
# This script is used to update the DeviceIDs, Memory, MemorySwap, and ShmSize of all running docker containers

systemctl stop docker
systemctl stop docker.socket

DIR=/data/docker/containers

gpuid=0
for dir in $DIR/*; do
  if [ -d "$dir" ]; then
    echo "update the hostconfig.json file in $dir"
    # Update the hostconfig.json file to set the DeviceIDs to a specific value increasing by one for each container
    if [ ! -f "$dir/hostconfig.json" ]; then
      echo "hostconfig.json not found in $dir"
      continue
    fi
    cp "$dir/hostconfig.json" "$dir/hostconfig.json.bak"
    sed -i 's/"Count":[0-9]*,//' "$dir/hostconfig.json"
    sed -i "s/\"DeviceIDs\":null,/\"DeviceIDs\":[\"$gpuid\"],/" "$dir/hostconfig.json"
    sed -i 's/"Memory":[0-9]*,/"Memory":34359738368,/' "$dir/hostconfig.json"
    sed -i 's/"MemorySwap":[0-9]*,/"MemorySwap":68719476736,/' "$dir/hostconfig.json"
    sed -i 's/"ShmSize":[0-9]*,/"ShmSize":34359738368,/' "$dir/hostconfig.json"
    gpuid=$((gpuid + 1))
    if [ $gpuid -gt 7 ]; then
      gpuid=0
    fi
    echo "Updated DeviceIDs to $gpuid in $dir/hostconfig.json"
  else
    echo "Skipping $dir, not a directory"
    continue
  fi
done

systemctl start docker.socket
systemctl start docker
