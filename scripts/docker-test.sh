#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker build --progress=plain -t antigravity-bridge:3.2.7 .
