# This script is used to patch a Docker container to use a specific data directory.
#!/bin/bash
# Check if the container name is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <container_name>"
  exit 1
fi

# # Change the ownership of the /data directory to the ubuntu user
# docker exec $1 chown -R ubuntu:ubuntu /data

# # kill all processes running as ubuntu user
# docker exec $1 pkill -u ubuntu
# # change the home directory of the ubuntu user to /data
# docker exec $1 usermod -d /data -m ubuntu

# Copy the .bashrc and .profile files from /etc/skel to the home directory of the $USER user
docker exec $1 cp /etc/skel/.bashrc /etc/skel/.profile /home/ubuntu/
docker exec $1 chown ubuntu:ubuntu /home/ubuntu/.bashrc /home/ubuntu/.profile
docker exec $1 chown ubuntu:ubuntu /home/ubuntu
docker exec $1 sed -i "/\%sudo/s/\!\/bin\/su/\/usr\/bin\/dpkg, \!\/bin\/su/" /etc/sudoers
