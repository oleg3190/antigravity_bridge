SHELL := /bin/bash

COMPOSE := docker compose
SERVICE := antigravity-bridge
IMAGE := antigravity-bridge:3.2.9

.PHONY: help init build rebuild up down restart start stop logs status ps health \
        shell check cpu-check test smoke clean doctor proxy-check workspace

help:
	@echo ""
	@echo "Antigravity Bridge 3.2.7"
	@echo ""
	@echo "  make init          Create .env and workspace"
	@echo "  make build         Build Docker image"
	@echo "  make rebuild       Clean rebuild without cache"
	@echo "  make up            Build and start"
	@echo "  make start         Start existing container"
	@echo "  make stop          Stop container"
	@echo "  make restart       Restart container"
	@echo "  make down          Stop and remove container"
	@echo "  make logs          Follow logs"
	@echo "  make status        Show container status"
	@echo "  make health        Check Bridge health"
	@echo "  make check         Check Python + Antigravity SDK"
	@echo "  make test          Run pytest"
	@echo "  make smoke         Run API smoke test"
	@echo "  make proxy-check   Check SOCKS5 :2080 from host/container"
	@echo "  make workspace     Show workspace information"
	@echo "  make shell         Open shell inside container"
	@echo "  make doctor        Run full diagnostics"
	@echo "  make clean         Remove containers/images"
	@echo ""

init:
	@test -f .env || cp .env.docker.example .env
	@mkdir -p workspace
	@grep -q '^HOST_UID=' .env || echo "HOST_UID=$$(id -u)" >> .env
	@grep -q '^HOST_GID=' .env || echo "HOST_GID=$$(id -g)" >> .env
	@echo "Initialized."
	@echo "Edit .env and set GEMINI_API_KEY if required."

build:
	$(COMPOSE) build --progress=plain

rebuild:
	$(COMPOSE) down
	$(COMPOSE) build --no-cache --progress=plain

up:
	@test -f .env || (echo "ERROR: .env not found. Run 'make init' first."; exit 1)
	@mkdir -p workspace
	@grep -q '^HOST_UID=' .env || echo "HOST_UID=$$(id -u)" >> .env
	@grep -q '^HOST_GID=' .env || echo "HOST_GID=$$(id -g)" >> .env
	$(COMPOSE) up -d --build
	@$(MAKE) health

start:
	$(COMPOSE) start

stop:
	$(COMPOSE) stop

restart:
	$(COMPOSE) restart

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200 $(SERVICE)

status:
	$(COMPOSE) ps

ps: status

health:
	@curl -fsS http://127.0.0.1:8090/health >/dev/null \
		&& echo "OK: Bridge health = healthy" \
		|| (echo "ERROR: Bridge is not healthy"; exit 1)

check:
	@echo "Container memory:"
	@docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' $(SERVICE) 2>/dev/null || true
	$(COMPOSE) exec -T $(SERVICE) python scripts/check_install.py

cpu-check:
	python3 scripts/cpu_check.py

test:
	$(COMPOSE) exec $(SERVICE) pytest -q

smoke:
	docker compose exec -T antigravity-bridge python scripts/smoke_test.py

proxy-check:
	@echo "Host SOCKS5:"
	@ss -lnt 2>/dev/null | grep ':2080' || \
		(echo "ERROR: nothing is listening on TCP :2080"; exit 1)
	@echo ""
	@echo "Testing SOCKS5 -> Docker Registry:"
	@curl --silent --show-error --proxy socks5h://127.0.0.1:2080 \
		-o /dev/null -w 'HTTP status: %{http_code}\n' \
		https://registry-1.docker.io/v2/ || \
		(echo "ERROR: SOCKS5 test failed"; exit 1)

	@echo ""
	@echo "Testing SOCKS5 from Bridge container:"
	@$(COMPOSE) exec $(SERVICE) python -c \
		"import urllib.request; print('HTTP status:', urllib.request.urlopen('https://registry-1.docker.io/v2/', timeout=10).status)" \
		2>&1 | grep -E 'HTTP status:|HTTP Error 401' || true

workspace:
	@echo "Host workspace:"
	@pwd
	@echo ""
	@ls -la workspace 2>/dev/null || true
	@echo ""
	@echo "Container workspace:"
	@$(COMPOSE) exec $(SERVICE) sh -lc 'ls -la /workspace'

shell:
	$(COMPOSE) exec $(SERVICE) bash

doctor:
	@echo "=== Antigravity Bridge Doctor ==="
	@echo ""
	@echo "[1] Docker"
	@docker --version
	@$(COMPOSE) version
	@echo ""
	@echo "[2] Container"
	@$(COMPOSE) ps
	@echo ""
	@echo "[3] Health"
	@$(MAKE) health
	@echo ""
	@echo "[4] SDK"
	@$(MAKE) check
	@echo ""
	@echo "[5] Proxy"
	@$(MAKE) proxy-check
	@echo ""
	@echo "[6] Workspace"
	@$(MAKE) workspace
	@echo ""
	@echo "=== Doctor finished ==="

clean:
	$(COMPOSE) down --remove-orphans
	@echo "Containers stopped/removed."
	@echo "Docker volumes are preserved."
