Backend is a FastAPI app. From the `web/backend` folder run:

1. python3 -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. uvicorn main:app --reload --host 0.0.0.0 --port 8000

APIs:
- GET /api/images
- GET /api/containers
- POST /api/containers
- PUT /api/containers/{name}
- POST /api/containers/{name}/action?action=start|stop|restart|delete

Note: This project calls Docker CLI; ensure Docker is installed and the user has permission.


## Tests

No unit tests are included for the backend in this initial commit. You can add pytest-based tests and run with `pytest` from the `web/backend` folder.
