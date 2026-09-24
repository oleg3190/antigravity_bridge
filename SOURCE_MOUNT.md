# Source-mounted development mode

The project directory is mounted into the container at `/app`.
Python source changes therefore do not require a Docker image rebuild.

For source-only changes:
    docker compose restart antigravity-bridge

Rebuild only when Dockerfile/dependencies change:
    docker compose up -d --build

Bridge: http://127.0.0.1:8090
Host SOCKS5: 127.0.0.1:2080
