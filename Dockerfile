FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip && python -m pip install google-antigravity==0.1.16 fastapi uvicorn pydantic python-dotenv
EXPOSE 8090
CMD ["python","-m","uvicorn","bridge.main:app","--host","0.0.0.0","--port","8090"]
