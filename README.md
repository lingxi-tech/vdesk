# working-in-the-cloud

## Requirments

This is a web-based application, which is used to manage the authorization of the cloud resources.

The backend should be developed in Python, and the frontend should be developed in Vue.

The frontend page shall be with the style similar with docker desktop.
- The web page shall list the available docker containers
- For each container, the following fields shall be displayed:
  - assigned user name
  - corresponding image
  - assigned memory size
  - assigned gpu ids
  - assigned swap size
  - root password
  - state of the container: running, stopped, etc.
- For each container, the user shall be able to modify the memory size, gpu ids, swap size, and the root password, the modifications are done via a script file whose usage is as follows:
```bash
update_container <container_name> <key> <value>
```
where \<container_name\> is the assigned user name of the container to be modifed, \<key\> is the parameter name to be modified, including memory_size, swap_size, root_password, and gpu_ids, and \<value\> is the parameter value to be updated.
The script name is `update_container` and resides in the folder \<project_root\>/scripts.
- For each container, the user shall be able to delete it, which means all the data related to this container is also deleted;
- For each container, the user shall be able to stop it, start it, or restart it;
- For each container, the user shall be able to bring up the container or shut down the container;
- The user shall be able to start a new container with specified name, it shall be implemented by calling a script:
```bash
container-management.sh --dir <dir> --command <command>
```
where \<command\> includes:
- reset_compose: reset the configurations in the directory \<dir\>
- update_memory \<size\>: update the memory size in the directory \<dir\>
- update_password \<password\>: update the root password in the directory \<dir\>
- container_up: bring up the container in the directory \<dir\>
- container_down: shut down the container in the directory \<dir\>
- start: start the container in the directory \<dir\>
- stop: stop the container in the directory \<dir\>
- restart: restart the container in the directory \<dir\>
```

- The user shall be able to change the parameter of all the containers. if the forementioned \<dir\> is not specified the parameter of all the containers are changedb by the script `container-management.sh`


All the container information shall be stored in a local database and persisted.


## How to Run

### Backend

See `backend/README.md` for instructions on how to run the backend server.

### Frontend

See `frontend/README.md` for instructions on how to run the frontend application.

**Note:** You need to have Docker installed and running to use this application.