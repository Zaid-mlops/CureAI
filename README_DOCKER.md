Quick Docker Compose for local development (Gunicorn + Uvicorn workers + Ollama)

Steps:

1. Build and start services:

```powershell
# from project root
docker compose up --build
```

2. Visit the web UI:

- App: http://localhost/ (if `nginx` included) or http://localhost:8000/
- Health: http://localhost:8000/health

Notes:
- `model` service uses `ollama/ollama:latest` as a placeholder. Replace with your actual model runtime or image.
- The `web` service runs Gunicorn with `uvicorn.workers.UvicornWorker` serving the ASGI-wrapped Flask app (`app:asgi_app`).
- If exposing publicly, terminate TLS at `nginx` or a proper load balancer and secure the host.
- To skip `nginx`, remove or comment the `nginx` service in `docker-compose.yml` and access port `8000` directly.

Environment variables:
- `OLLAMA_URL` is set in `docker-compose.yml` to point to the `model` service.

Production note:
- This compose setup is for local/dev usage. For production, run containers on a host with proper TLS, process supervision, and monitoring.
