# LLM Cost Autopilot

Minimal FastAPI service scaffold with environment-based configuration.

## Run locally

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Install the runtime dependencies and start the API:

```powershell
python -m pip install fastapi "uvicorn[standard]" pydantic-settings
python -m uvicorn app.main:app --reload
```

The health endpoint is available at <http://localhost:8000/health>.

## Run with Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The API is exposed on port `8000`.
