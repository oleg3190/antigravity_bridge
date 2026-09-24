# Antigravity Bridge v3.2

Native Google Antigravity SDK integration for a reliable coding-agent bridge.

## What changed from v3

- No custom HTTP client for Antigravity.
- Uses `google-antigravity` public Python SDK (`Agent`, `LocalAgentConfig`, `CapabilitiesConfig`, policies).
- Lets Antigravity own the agent/tool loop.
- Uses Git worktrees for transactional workspace isolation.
- Uses SDK tool allowlisting plus policy guardrails.
- Captures streaming text, thoughts/tool-call metadata, usage and final result.
- Git diff is the source of truth for changed code; the model's prose is not.
- Optional structured finish schema.
- SDK retry/budget configuration is used instead of a duplicate HTTP retry layer.
- FastAPI/OpenAI-compatible bridge remains a thin outer API.


## Recommended: Docker

The bridge is designed to run in a container so the host Python version does not matter.
The image uses Python 3.11, installs the official `google-antigravity` wheel from PyPI,
runs the SDK import check, and runs the test suite during the image build.

### Requirements

- Docker Engine
- Docker Compose plugin (`docker compose`)
- Gemini API key, or Vertex/Gemini Enterprise credentials

### Start

```bash
cp .env.docker.example .env
nano .env
mkdir -p workspace
docker compose build
docker compose up -d
```

Check:

```bash
curl http://127.0.0.1:8090/health
docker compose logs -f antigravity-bridge
```

### Run a repository

Put a Git repository under:

```text
./workspace/my-repo
```

The bridge sees it as:

```text
/workspace/my-repo
```

Example:

```bash
curl -X POST http://127.0.0.1:8090/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "task": "Inspect the repository, fix the failing tests, and make the smallest safe change.",
    "workspace": "/workspace/my-repo",
    "run_tests": true,
    "test_command": ["pytest", "-q"]
  }'
```

Stop:

```bash
docker compose down
```

Run tests in the image:

```bash
./scripts/docker-test.sh
```

### Security

Do not mount your home directory or `/` into the container. Only mount a dedicated
workspace root. The compose service drops Linux capabilities and enables
`no-new-privileges`. Antigravity policies and the Git worktree provide additional
application-level isolation. The SDK documentation explicitly warns that its OS
sandbox may be unavailable on some environments, so it is not treated as the only
security boundary.

## Install

This project supports editable installation even with older pip/setuptools combinations.

Recommended clean install:

```bash
cd antigravity_bridge_v3_2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

The repository includes both `pyproject.toml` and a minimal `setup.py` compatibility shim. Modern pip uses the PEP 660 build path; older tooling can fall back to the legacy setuptools path. Setuptools documents this compatibility approach.

The official Antigravity SDK itself must come from PyPI because its platform wheel contains the compiled runtime binary.

or:

```bash
pip install google-antigravity
```

For Gemini API key mode:

```bash
export GEMINI_API_KEY="..."
```

For Vertex/Enterprise with ADC:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=True
export GOOGLE_CLOUD_PROJECT="..."
export GOOGLE_CLOUD_LOCATION="us-central1"
gcloud auth application-default login
```

The SDK docs state that `Agent` manages lifecycle, tool wiring and policy defaults, and that it is read-only by default; write tools are enabled through `CapabilitiesConfig`. 

## Run

```bash
uvicorn bridge.main:app --host 127.0.0.1 --port 8090
```

Submit:

```bash
curl -X POST http://127.0.0.1:8090/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"task":"Fix the failing tests in this repository","workspace":"/path/to/repo"}'
```

Then:

```bash
curl http://127.0.0.1:8090/v1/jobs/<job_id>
```

Streaming:

```bash
curl -N http://127.0.0.1:8090/v1/jobs/<job_id>/events
```

## Safety model

1. Git worktree isolates the task.
2. Antigravity `enabled_tools` controls what the model can see.
3. Antigravity policies provide runtime guardrails.
4. `run_command` is restricted by command policy.
5. Secrets are not injected into prompts.
6. The resulting Git diff is validated before it can be applied.
7. Tests run after the agent turn as an independent verification step.

The SDK's OS sandbox is optional defense-in-depth and is not treated as the only security boundary.

## Important

The exact public SDK surface can evolve while Antigravity is preview software. This project intentionally imports public interfaces only and performs a startup SDK compatibility check.


## If `pip install -e .` still says setup.py is missing

You are almost certainly invoking a different/old pip than the Python interpreter you intend to use. Check:

```bash
python3 --version
python3 -m pip --version
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -e .
```

Prefer `python3 -m pip` over a bare `pip` so pip belongs to the same interpreter.


## Docker build troubleshooting

The image installs the development extra with:

```bash
python -m pip install -e ".[dev]"
```

because the image runs `pytest` as a build-time verification step. If you see a failure at the final Docker step, rerun:

```bash
docker compose build --no-cache --progress=plain
```

and inspect the last 30 lines. The final command is intentionally split into separate `RUN` layers so dependency failures, SDK import failures and test failures are distinguishable.


## Docker-first setup (v3.2.7)

The Docker image uses Python 3.11 and installs the Antigravity SDK inside the container, so the host Python version does not matter.

### 1. Configure

```bash
cp .env.docker.example .env
```

Set `GEMINI_API_KEY` or the required Vertex/Enterprise variables.

### 2. Build

```bash
docker compose build --progress=plain
```

The build installs the application and test dependencies separately, runs `scripts/check_install.py`, and runs `pytest -q`. A failed SDK import or test stops the image build.

### 3. Start

```bash
mkdir -p workspace
docker compose up -d
```

### 4. Check

```bash
curl http://127.0.0.1:8090/health
docker compose logs -f antigravity-bridge
```

### 5. Stop

```bash
docker compose down
```

Only `./workspace` is mounted into the container. Do not mount your home directory or `/`.

### Host proxy on port 2080

If the host proxy listens on `127.0.0.1:2080`, Docker containers must address it as `host.docker.internal:2080`.

Add to `.env`:

```env
HTTP_PROXY=http://host.docker.internal:2080
HTTPS_PROXY=http://host.docker.internal:2080
ALL_PROXY=http://host.docker.internal:2080
NO_PROXY=localhost,127.0.0.1
```

Then recreate the container:

```bash
docker compose down
docker compose up -d --build
```

Check from inside the container:

```bash
docker compose exec antigravity-bridge sh -lc 'env | grep -i proxy'
```

The compose file maps `host.docker.internal` to the Docker host with `host-gateway`, which is required on Linux.

## v3.2.7

- Docker uses Python 3.11.
- Runtime supports a host-local SOCKS5 proxy on `127.0.0.1:2080`.
- Docker build does not depend on the runtime proxy.
- Container uses host networking so a proxy bound to host loopback is reachable.
- The workspace is no longer required to be a Git repository for every task.
- Git is required only where Git diff/rollback state is needed.

```bash
docker compose down
docker compose build --no-cache --progress=plain
docker compose up -d
curl http://127.0.0.1:8090/health
```
# antigravity_bridge
