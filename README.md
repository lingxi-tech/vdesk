# working-in-the-cloud

## Requirments

This is a web-based application, which is used to manage the authorization of the cloud resources.


### Backend

The backend should be developed in Python.

#### Create a new container

While creating a new container, the backend shall create a new folder under `<project_root>/containers` with the name specified by the interface, and a template of the docker compose file, which is resides in ./scripts/docker-compose.yml.example under this project, shall be copied to this new folder.

Then the following parameters shall be modified in this docker-compose.yml file with the value retrieved from this interface:
- port, which is the first part of the value of the field `services.my_ws.ports`, the value shall be calculated based on the 6 digits name specified by the interface, the calculation process is: the first digit of the port is mod(digit 1 of `name` + digit 2 of `name`, 6), the last 4 digits is the same as the last 4 digits of `name`
- corresponding image, which is in the docker-compose.yml file, as the value of the field `services.my_ws.image`
- assigned memory size, which is in the docker-compose.yml file, as the value of the field `services.my_ws.deploy.resources.limits.memory`
- assigned cpu number, which is in the docker-compose.yml file, as the value of the field `services.my_ws.deploy.resources.limits.cpus`
- assigned gpu ids, which is in the docker-compose.yml file, as the value of the field `services.my_ws.deploy.resources.reservations.devices.device_ids`

After the modification, a bash command 'docker compose up -d' shall be called to start this new container, the returned value shall be returned to the frontend so that the frontend shall be notified by the result.

#### List the available containers
The backend shall find all the subfolders under `<project_root>/containers` with valid docker-compose.yml file and treat them as available containers, and following information for each container shall be returned by the interface:
- assigned user name, which is the folder name;
- corresponding image, which is in the docker-compose.yml file, as the value of the field `services.my_ws.image`
- assigned memory size, which is in the docker-compose.yml file, as the value of the field `services.my_ws.deploy.resources.limits.memory`
- assigned cpu number, which is in the docker-compose.yml file, as the value of the field `services.my_ws.deploy.resources.limits.cpus`
- assigned gpu ids, which is in the docker-compose.yml file, as the value of the field `services.my_ws.deploy.resources.reservations.devices.device_ids`
- state of the container, which could be gotten via calling `docker ps` and parse the returned value

#### Modify the certain parameters of an available container
The backend shall modify certain parameters of an available container specified by the name retrieved from the interface.


All the output of the command ran in the backend shall be logged to a log file.

### Frontend

The frontend should be developed in Vue.

The frontend shall use the style similar with docker desktop, and it shall have a fancy UI like the modern material style.

The frontend main page shall have the following features:
- It shall list the available docker containers
- For each container, the following fields shall be displayed:
  - assigned user name
  - port
  - corresponding image
  - assigned memory size
  - assigned cpus
  - assigned gpu ids
  - assigned swap size
  - root password
  - state of the container: running, stopped, etc.
- For each container in the available container list, the user shall be able to modify the memory size, gpu ids, swap size, and the root password, after the modification, the container shall restart automatically to apply the modified parameters;
- For each container in the available container list, the user shall be able to delete it;
- For each container in the available container list, the user shall be able to stop it, start it, or restart it;
- The user shall be able to start a new container with following parameters:
  - user name, which is a number of 6 digits;
  - corresponding image, which shall be selected from a list retrieved from the backend;
  - assigned cpu numbers, which shall be number ranging from 1 to 32;
  - assigned memory size, which shall be a number trailed with 'g' or 'm'
  - assigned gpu ids, which shall be an array selected from 0~31 using a multi-selection checkbox;
  - assigned swap size, which shall be a number trailed with 'g' or 'm'


## How to Run

### Backend

See `backend/README.md` for instructions on how to run the backend server.

### Frontend

See `frontend/README.md` for instructions on how to run the frontend application.

**Note:** You need to have Docker installed and running to use this application.