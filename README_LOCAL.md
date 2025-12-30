Local run instructions (no Docker)

Overview
- This project runs a Flask frontend (`/`) that posts to `/chat`, which calls a local model runtime (Ollama or similar) via `OLLAMA_URL`.
- By default the app expects the model server at `http://localhost:11434/api/generate` (this is the Ollama default used in the code).

Steps to run locally
1. Install Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Install and run your model runtime (Ollama) locally
- Install Ollama per your OS (follow Ollama docs) and start it.
- Load or pull the model you intend to use (for example `gemma:3.1b`) according to your model runtime instructions.
- Verify the model server is reachable at `http://localhost:11434`.

If you don't have Ollama but have another local model server, ensure it exposes a compatible HTTP API and update `OLLAMA_URL` env variable accordingly.

3. Run the web app
- On Windows (recommended): use `waitress` (WSGI)

```powershell
# serve the WSGI Flask app
waitress-serve --listen=0.0.0.0:8000 app:app
```

- On Linux / macOS: use Gunicorn + Uvicorn workers (ASGI)

```bash
# runs the ASGI-wrapped Flask app (app:asgi_app)
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 app:asgi_app
```

4. Open the frontend
- Visit http://127.0.0.1:8000/ in your browser and use the chat UI.

Environment variables
- `OLLAMA_URL` — set to your model runtime endpoint if not running on `localhost:11434` (e.g., `setx OLLAMA_URL "http://127.0.0.1:11434/api/generate"` on Windows or `export OLLAMA_URL=...` on Linux/macOS).
- `FLASK_DEBUG`, `FLASK_RUN_PORT`, `FLASK_RUN_HOST` are supported by the app.
 - `MEDICAL_ONLY` — when `1` (default) the server will refuse non-medical queries and only answer medical science questions. Set to `0` to disable this guard.
 - `MEDICAL_CLASSIFY` — when `1` (default) the server will first ask the model to classify whether a prompt is medical (YES/NO). This costs an extra model call but reduces false positives/negatives. Set to `0` to disable.
 - `CLASSIFIER_MODEL` — model name used for the classification call (defaults to `gemma:3.1b`). You can point this to a lighter model if available.

Verify Ollama is reachable (PowerShell)
```powershell
# Simple test: send a small generate request to your Ollama endpoint
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:11434/api/generate -Body (ConvertTo-Json @{ model = 'gemma:3.1b'; prompt = 'Hello'; stream = $false }) -ContentType 'application/json'
```

If the endpoint is running you'll get a response (or an error about missing model). If the request fails, ensure Ollama is installed and running; consult your Ollama install docs.

Notes
- If you run the model runtime on the same machine, keep it separate from the web process for resource isolation.
- If you need help installing or starting Ollama (or want specific commands), tell me your OS and whether Ollama is already installed and I will provide exact commands.
