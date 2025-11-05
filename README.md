# working-in-the-cloud

This is a web-based application, which is used to manage the authorization of the cloud resources.

## How to Run

### Clone the code
First, clone this repo to local.

```bash
git clone http://github.com/..
cd vdesk
```

### Prepare the docker images


#### Install docker engine
For Ubuntu:
```bash
sudo apt update
sudo apt install apt-transport-https ca-certificates curl gnupg-agent software-properties-common

# Add GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add apt sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update the software package again
sudo apt update

sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER

```

#### Create nescessary docker images for the remote desktop
Here we create the docker image for hosting the remote desktop. This image is based on the image gezp/ubuntu-desktop:22.04-cu12.4.1(https://github.com/gezp/docker-ubuntu-desktop).
```bash
cd docker/ubuntu-desktop-nomachine-cuda
docker build -t ubuntu-desktop-nomachine-cuda:22.04-cu12.4.1 .
cd ../..

cd docker/ros2-humble-cu12.4.1-nomachine-priviledged
docker build -t ros2-humble-cu12.4.1-nomachine-priviledged:1.0 .
cd ../..
```

Now there are two images created:
- ubuntu-desktop-nomachine-cuda:22.04-cu12.4.1
- ros2-humble-cu12.4.1-nomachine-priviledged:1.0

These two images can be used to create the remote desktop containers. and it shall be selected from the frontend when creating a new container.


#### Create a docker-in-docker container for the backend to call docker CLI
The backend calls docker CLI to manage the containers, so we need to create a docker-in-docker container and mount the docker socket to this container.

```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock -v .:/data -p 5173:5173 -p 8000:8000 --name my-dood-container -it ubuntu:22.04 /bin/bash
```

In the container, install docker cli:
```bash
apt update
apt install apt-transport-https ca-certificates curl gnupg-agent software-properties-common lsb-release -y
# Add GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
# Add apt sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
# Update the software package again
apt update
apt install docker-ce-cli -y
```

### Backend

See `backend/README.md` for instructions on how to run the backend server.

### Frontend

See `frontend/README.md` for instructions on how to run the frontend application.

**Note:** You need to have Docker installed and running to use this application.