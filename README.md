# working-in-the-cloud

This is a web-based application, which is used to manage the authorization of the cloud resources.

## Preparations

### Clone the code
First, clone this repo to local.

```bash
git clone https://github.com/lingxi-tech/vdesk
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
cd docker/my-ubuntu-with-systemd
docker build -t my-ubuntu-with-systemd:latest .
cd ../..

docker run -d \
  -v /var/run/docker.sock:/docker.sock \
  -e DOCKER_HOST=unix:///docker.sock \
  -v .:/data -p 5173:5173 -p 8000:8000 \
  --name vdesk-admin-container \
  --privileged \
  my-ubuntu-with-systemd:latest /usr/sbin/init
docker exec -it vdesk-admin-container /bin/bash
```

where `-v /var/run/docker.sock:/docker.sock` and `-e DOCKER_HOST=unix:///docker.sock` is used to mount the docker socket to this container, so that the backend running in this container can call docker CLI to manage the containers on the host.

`-v .:/data` is used to mount the current project folder to `/data` in the container, so that the backend can access the project files.

`-p 5173:5173` is used to expose the frontend dev server port.

`-p 8000:8000` is used to expose the backend server port. 

#### Work inside the container

##### Install docker engine inside the container
In the container, install docker:
```bash
apt update
apt install apt-transport-https ca-certificates curl gnupg-agent software-properties-common

# Add GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add apt sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update the software package again
apt update

apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# usermod -aG docker $USER
```

##### Run the backend and frontend for development
Open two terminal sessions to run the backend and frontend respectively.
In the first terminal, run the backend:
```bash
cd /data/web/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# set the environment variable for the registry URL
export VDESK_REGISTRY_URL=""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
In the second terminal, run the frontend:
```bash
cd /data/web/frontend
npm install
npm run dev
```


##### Production deployment

A helper script is included at `scripts/deploy_prod.sh` to install and configure the application on a Debian/Ubuntu server. The script will:
- copy the repository to `/opt/vdesk` (use sudo)
- create a Python virtualenv and install backend requirements
- build frontend production assets (npm)
- create a systemd service `vdesk-backend` that runs uvicorn bound to 127.0.0.1:8000
- configure nginx to serve the frontend `dist/` and reverse-proxy `/api` to the backend

Important: the script makes changes to system configuration (systemd, nginx) and must be run as root. Review the script before running.

Quick deploy steps (on a clean Debian/Ubuntu server):

1. Copy or checkout the repository on the server and run the deploy script as root from the repo root:

```bash
sudo bash scripts/deploy_prod.sh
```

2. After the script completes:
- Backend will be available via systemd service `vdesk-backend` listening on 127.0.0.1:8000
- Nginx will serve the frontend on port 5173 and proxy /api to the backend

Notes and post-deploy tasks:
- SSL: the script does not configure TLS. For production you must add HTTPS (recommended via Let's Encrypt). Configure nginx to listen on 443 and set up certificates.
- Docker: the backend manages containers by calling the host docker CLI. Ensure the backend process has access to the Docker socket (e.g. run on the host or run inside a container with `/var/run/docker.sock` mounted and proper permissions).
- Users: a default admin user is created on first backend run with username `admin` and password `admin`. Change this immediately using the web UI change-password endpoint or by running:

```bash
# as root on the server
python3 -m venv /opt/vdesk/venv
source /opt/vdesk/venv/bin/activate
python -c "from web.backend.main import set_user_password; set_user_password('admin', 'NEW_PASSWORD')"
```

- Custom domain: update the nginx `server_name` and firewall rules accordingly.

## Access the remote desktop

### Create the remote desktop container
The remote desktop containers can be created from the frontend application. When creating a new container, select the image from the dropdown list. The available images are:
- ubuntu-desktop-nomachine-cuda:22.04-cu12.4.1
- ros2-humble-cu12.4.1-nomachine-priviledged:1.0

While entering the name of the new container, you must use a 6-digit string. And the NoMachine port of the new container will be calculated from this 6-digit string and displayed on the UI.

### Get the NoMachine client
Download and install NoMachine client from https://www.nomachine.com/download

### Connect to the remote desktop
1. Open NoMachine client
2. Click "New" to create a new connection
3. In the "Host" field, enter the IP address of the host machine where the docker containers are running.
4. In the "Port" field, enter the port number mapped to the container's NoMachine port (please refer to the port displayed on the frontend when creating the container).
5. Click "Connect"
6. Enter the username and password for the remote desktop (default username: ubuntu, password: ubuntu)
7. Click "OK" to connect to the remote desktop

## Users and Authentication
This application includes user authentication functionality. User credentials are stored in the `users.json` file in the backend directory. Passwords are hashed using bcrypt for security.