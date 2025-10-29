#!/bin/bash

# This script sets up a container management environment using Docker and Docker Compose.
# Usage: ./container-management.sh [--help | -h]
#        ./container-management.sh [--dir | -d <working_dir>] [--command | -c <command>] [--username | -u <username>]

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi
# Check if Docker Compose is installed
#if ! command -v docker-compose &> /dev/null; then
#    echo "Docker Compose is not installed. Please install Docker Compose first."
#    exit 1
#fi

USERNAME="ALL"
DOCKER_IMAGE="10.233.0.132:8000/hdm/ros2-humble-cu12.4.1-nomachine-priviledged:1.0"
# set the ROOTPASSWORD to a random password
ROOTPASSWORD=$(openssl rand -base64 12)
MESSAGE="docker container for user"

ROOT_DIR=$(pwd)
WORKING_DIR="$ROOT_DIR"

# command parsing
# -h or --help to display help message
# -c or --command to specify a command to run
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
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
            exit 0
            ;;
        --dir|-d)
            if [[ -z "$2" ]]; then
                echo "Error: No directory specified after --dir/-d."
                exit 1
            fi
            WORKING_DIR="$2"
            if [[ ! -d "$WORKING_DIR" ]]; then
                echo "Error: The specified directory '$WORKING_DIR' does not exist."
                exit 1
            fi
            cd "$WORKING_DIR" || exit 1
            shift 2
            ;;
        --message|-m)
            if [[ -z "$2" ]]; then
                echo "Error: No message specified after --message/-m."
                exit 1
            fi
            MESSAGE="$2"
            shift 2
            ;;
        --command|-c)
            if [[ -z "$2" ]]; then
                echo "Error: No command specified after --command/-c."
                exit 1
            fi
            COMMAND="$2"
            shift 2
            ;;
        --username|-u)
            if [[ -z "$2" ]]; then
                echo "Error: No username specified after --username/-u."
                exit 1
            fi
            USERNAME="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Use --help or -h for usage information."
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# find if $USERNAME is a subfolder in the current directory
if [[ "$USERNAME" != "ALL" && ! -d "$USERNAME" ]]; then
    echo "The specified username directory '$USERNAME' does not exist. Create it first."
    mkdir -p "$USERNAME"
    cp -r ${ROOT_DIR}/docker-compose.yml.example "$USERNAME/docker-compose.yml"
    # change the next line after "port:" in the docker-compose.yml file to $USERNAME
    # get the last 4 characters of the username and use them as the port
    if [[ ${#USERNAME} -ge 4 ]]; then
        PORT="1${USERNAME: -4}"
    else
        PORT="1$(printf "%04d" "$RANDOM")"  # Generate a random 4-digit port if username is too short
    fi
    sed -i "/ports:/{n;s/[0-9]*:/$PORT:/}" "$USERNAME/docker-compose.yml"
    sed -i "s/ROOTPASSWORD=.*/ROOTPASSWORD=$ROOTPASSWORD/" "$USERNAME/docker-compose.yml"
    # set the image to the latest docker image
    sed -i "s|image:.*|image: $DOCKER_IMAGE|" "$USERNAME/docker-compose.yml"
    echo $MESSAGE > $USERNAME/readme.md
fi

# go through all the subfolders within the current directory
gpuid=0
for dir in */; do
    # Check if the directory contains a docker-compose.yaml or a docker-compose.yml file
    dir=${dir%/}  # Remove trailing slash
    #echo "Processing directory: $dir"
    if [[ ! -d "$dir" ]]; then
        #echo "Skipping $dir, not a directory."
        continue
    fi
    if [[ $dir == ".." || $dir == "." ]]; then
        #echo "Skipping $dir, it's a special directory."
        continue
    fi
    if [[ "$USERNAME" != "ALL" && "$dir" != "$USERNAME" ]]; then
        #echo "Skipping $dir, it's not the specified username directory."
        continue
    fi
    echo "Processing directory: $dir"
    case "$COMMAND" in
        reset_compose)
            echo "Resetting docker-compose for $USERNAME in $dir"
            # Here you would typically reset the docker-compose file to its default state
            # For demonstration, we will just copy the example file
            if [[ -f "$ROOT_DIR/docker-compose.yml.example" ]]; then
                cp -r "$ROOT_DIR/docker-compose.yml.example" "$dir/docker-compose.yml"
                # change the next line after "port:" in the docker-compose.yml file to $USERNAME
                # get the last 4 characters of the username and use them as the port
                if [[ ${#dir} -ge 4 ]]; then
                    PORT="1${dir: -4}"
                else
                    PORT="1$(printf "%04d" "$RANDOM")"  # Generate a random 4-digit port if username is too short
                fi
                sed -i "/ports:/{n;s/[0-9]*:/$PORT:/}" "$dir/docker-compose.yml"
                sed -i "s/ROOTPASSWORD=.*/ROOTPASSWORD=$ROOTPASSWORD/" "$dir/docker-compose.yml"
                # set the image to the latest docker image
                sed -i "s|image:.*|image: $DOCKER_IMAGE|" "$dir/docker-compose.yml"
                # update the device id for the gpu assignment
                sed -i "s/device_ids: \[\"0\"\]/device_ids: [\"$gpuid\"]/" "$dir/docker-compose.yml" 
                gpuid=$((gpuid + 1))
                if [ $gpuid -gt 7 ]; then
                    gpuid=0
                fi
                echo $MESSAGE > $dir/readme.md
            else
                echo "No example docker-compose file found in $ROOT_DIR."
            fi
            ;;
        update_memory)
            if [[ -z "$1" ]]; then
                echo "No memory limit specified after update_memory, using default 16GB."
                MEMORY_LIMIT="16g"
            else
                MEMORY_LIMIT="$1"
            fi
            # multiply the memory limit by 2 to convert it to shm_size
            # remove the last character if it is 'g' or 'm'
            SHM_LIMIT=${MEMORY_LIMIT,,}  # Convert to lowercase
            if [[ "$MEMORY_LIMIT" == *g ]]; then
                SHM_LIMIT=${MEMORY_LIMIT%g}  # Remove 'g'
                SHM_LIMIT_UNIT="g"
            elif [[ "$MEMORY_LIMIT" == *m ]]; then
                SHM_LIMIT=${MEMORY_LIMIT%m}  # Remove 'm'
                SHM_LIMIT_UNIT="m"
            fi
            SHM_LIMIT=$(echo "$SHM_LIMIT * 2" | bc)
            SHM_LIMIT="${SHM_LIMIT}${SHM_LIMIT_UNIT:-g}"  # Default to 'g' if no unit specified
            echo "Updating memory limit for $USERNAME in $dir to $MEMORY_LIMIT"
            if [[ -f "$dir/docker-compose.yml" ]]; then
                line_num=$(grep -n 'memory:' "$dir/docker-compose.yml" | sed -n "1p" | cut -d: -f1)
                sed -i "${line_num}s/memory:.*/memory: $MEMORY_LIMIT/" "$dir/docker-compose.yml"
                sed -i "s/shm_size:.*/shm_size: \"$SHM_LIMIT\"/" "$dir/docker-compose.yml"
            elif [[ -f "$dir/docker-compose.yaml" ]]; then
                line_num=$(grep -n 'memory:' "$dir/docker-compose.yaml" | sed -n "1p" | cut -d: -f1)
                sed -i "${line_num}s/memory:.*/memory: $MEMORY_LIMIT/" "$dir/docker-compose.yaml"
                sed -i "s/shm_size:.*/shm_size: "$SHM_LIMIT"/" "$dir/docker-compose.yaml"
            else
                echo "No docker compose file found in $dir."
            fi
            shift 1
            ;;
        update_password)
            if [[ -z "$1" ]]; then
                echo "No new password specified after update_password, use a random one."
            else
                ROOTPASSWORD="$1"
            fi
            echo "Updating password for $USERNAME in $dir to $ROOTPASSWORD"
            # Here you would typically update the password in a file or database
            # For demonstration, we will just echo it
            # use sed to replace the content after the key word "ROOTPASSWORD=" in a file
            if [[ -f "$dir/docker-compose.yml" ]]; then
                sed -i "s/ROOTPASSWORD=.*/ROOTPASSWORD=$ROOTPASSWORD/" "$dir/docker-compose.yml"
            elif [[ -f "$dir/docker-compose.yaml" ]]; then
                sed -i "s/ROOTPASSWORD=.*/ROOTPASSWORD=$ROOTPASSWORD/" "$dir/docker-compose.yaml"
            else
                echo "No docker compose file found in $dir."
            fi
            shift 1
            ;;
        change_image)
            if [[ -z "$1" ]]; then
                echo "No new image specified after change_image, use the default one."
            else
                DOCKER_IMAGE="$1"
            fi
            echo "Changing Docker image for $USERNAME in $dir to $DOCKER_IMAGE"
            # Here you would typically change the Docker image in a file or configuration
            # For demonstration, we will just echo it
            if [[ -f "$dir/docker-compose.yml" ]]; then
                sed -i "s|image:.*|image: $DOCKER_IMAGE|" "$dir/docker-compose.yml"
            elif [[ -f "$dir/docker-compose.yaml" ]]; then
                sed -i "s|image:.*|image: $DOCKER_IMAGE|" "$dir/docker-compose.yaml"
            else
                echo "No docker compose file found in $dir."
            fi
            shift 2
            ;;
        container_up)
            echo "bring up container for $USERNAME in $dir"
            # Here you would typically start the Docker container
            if [[ -f "$dir/docker-compose.yml" || -f "$dir/docker-compose.yaml" ]]; then
                echo "Starting Docker Compose for $dir"
                # Navigate to the directory and start Docker Compose
                (cd "$dir" && docker compose up -d)
                # get the docker container id just started
                CONTAINER_ID=$(docker ps -lq)
                ${ROOT_DIR}/patches.sh ${CONTAINER_ID}
            else
                echo "No docker-compose.yml or docker-compose.yaml found in $dir, skipping."
            fi
            ;;
        container_down)
            echo "shutdown container for $USERNAME in $dir"
            # Here you would typically stop the Docker container
            if [[ -f "$dir/docker-compose.yml" || -f "$dir/docker-compose.yaml" ]]; then
                echo "Stopping Docker Compose for $dir"
                # Navigate to the directory and stop Docker Compose
                (cd "$dir" && docker compose down)
            else
                echo "No docker-compose.yml or docker-compose.yaml found in $dir, skipping."
            fi
            ;;
        container_start)
            echo "Starting container for $USERNAME in $dir"
            # Here you would typically start the Docker container
            if [[ -f "$dir/docker-compose.yml" || -f "$dir/docker-compose.yaml" ]]; then
                echo "Starting Docker Compose for $dir"
                # Navigate to the directory and start Docker Compose
                (cd "$dir" && docker compose start)
            else
                echo "No docker-compose.yml or docker-compose.yaml found in $dir, skipping."
            fi
            ;;
        container_stop)
            echo "Stopping container for $USERNAME in $dir"
            # Here you would typically stop the Docker container
            if [[ -f "$dir/docker-compose.yml" || -f "$dir/docker-compose.yaml" ]]; then
                echo "Stopping Docker Compose for $dir"
                # Navigate to the directory and stop Docker Compose
                (cd "$dir" && docker compose stop)
            else
                echo "No docker-compose.yml or docker-compose.yaml found in $dir, skipping."
            fi
            ;;
        container_restart)
            echo "Restarting container for $USERNAME in $dir"
            # Here you would typically restart the Docker container
            if [[ -f "$dir/docker-compose.yml" || -f "$dir/docker-compose.yaml" ]]; then
                echo "Restarting Docker Compose for $dir"
                # Navigate to the directory and restart Docker Compose
                (cd "$dir" && docker compose restart)
            else
                echo "No docker-compose.yml or docker-compose.yaml found in $dir, skipping."
            fi
            ;;
        *)
            echo "unrecognized command $COMMAND"
            ;;
    esac
done
