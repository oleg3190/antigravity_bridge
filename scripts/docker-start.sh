#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  cp .env.docker.example .env
  echo "Created .env from .env.docker.example"
  echo "Set GEMINI_API_KEY (or Vertex settings) in .env, then run this script again."
  exit 1
fi

mkdir -p workspace

docker compose build --progress=plain
docker compose up -d

echo
echo "Antigravity Bridge 3.2.7 is starting on http://127.0.0.1:8090"
echo "Health: curl http://127.0.0.1:8090/health"
echo "Logs:   docker compose logs -f antigravity-bridge"
