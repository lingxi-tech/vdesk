# working-in-the-cloud

## Requirments

This is a web-based application, which is used to manage the authorization of the cloud resources.

The backend should be developed in Python, and the frontend should be developed in Vue.

From the frontend web-ui, user can:
- create a new docker container and assigned to a user
- delete a docker container
- start a docker container
- stop a docker container
- restart a docker container
- get the logs of a docker container
- get the status of a docker container
- get the list of all docker containers
- get the list of all users
- create a new user
- delete a user
- get the list of all users

In the backend, the forementioned 10 operations should be implemented by calling a bash script.
The script is already implemented, and the backend should be developed to call the script. it is container-management.sh, which is located in the project fould. Its usage is as follows:
```bash
            echo "Usage: $0 [--help | -h] [--command | -c <command>]"
            echo "This script sets up a container management environment using Docker and Docker Compose."
            echo "Options:"
            echo "  --help, -h        Show this help message"
            echo "  --command, -c     Specify a command to run, supported commands are:"
            echo "    reset_compose:                    reset the docker-compose.yml file using the example file"
            echo "    update_memory <size>:             update the memory size in docker-compose.yml"
            echo "    update_password <password>:       update the root password in docker-compose.yml"
            echo "    change_image <image_name>:        change the image name in docker-compose.yml"
            echo "    container_up:                     bring up the containers in specified folder"
            echo "    container_down:                   take down the containers in specified folder"
            echo "    container_start:                  start the containers in specified folder"
            echo "    container_stop:                   stop the containers in specified folder"
            echo "    container_restart:                restart the containers in specified folder"
            echo "  --username, -u    Specify a username to work for, default is 'ALL'"
            echo "  --dir, -d         Specify a folder as the working directory (default is current directory)"
```

User can also change the parameters of a running container, such as the memory size, the root password, and the allocated gpus.
This feature can be done by calling the script update_container.sh or myupdate.sh, which is already implemented.

## How to Run

### Backend

See `backend/README.md` for instructions on how to run the backend server.

### Frontend

See `frontend/README.md` for instructions on how to run the frontend application.

**Note:** You need to have Docker installed and running to use this application.