#!/usr/bin/env bash
set -euo pipefail

IMAGE="${ANTIGRAVITY_IMAGE:-ghcr.io/oleg3190/antigravity_bridge:3.2.9}"

: "${GEMINI_API_KEY:?Set GEMINI_API_KEY before starting the container}"

mkdir -p "${WORKSPACE_DIR:-$PWD/workspace}"

exec docker run --rm \
  --name antigravity-bridge \
  --init \
  --publish "${BRIDGE_PORT:-8090}:8090" \
  --env GEMINI_API_KEY \
  --env GOOGLE_GENAI_USE_VERTEXAI \
  --env GOOGLE_CLOUD_PROJECT \
  --env GOOGLE_CLOUD_LOCATION \
  --env ANTIGRAVITY_HARNESS_PATH \
  --env ANTIGRAVITY_LEGACY_HARNESS_PATH \
  --volume "$(cd "${WORKSPACE_DIR:-$PWD/workspace}" && pwd):/workspace" \
  --volume "${BRIDGE_DATA_DIR:-$PWD/.bridge-data}:/data" \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m \
  "$IMAGE"
