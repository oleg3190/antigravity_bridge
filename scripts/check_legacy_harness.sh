#!/usr/bin/env bash
set -euo pipefail

# Ordered newest -> oldest. 0.1.6 is included because CI must prove that it
# is NOT compatible with the target CPU before falling back further.
CANDIDATES=("0.1.6" "0.1.5" "0.1.4" "0.1.3" "0.1.2")
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1"
    exit 1
  }
}

require_cmd python
require_cmd qemu-x86_64
require_cmd unzip
require_cmd go

compatible_version=""
compatible_harness=""

for VERSION in "${CANDIDATES[@]}"; do
  echo
  echo "============================================================"
  echo "==> Checking google-antigravity==$VERSION"
  echo "============================================================"

  CANDIDATE_DIR="$WORKDIR/$VERSION"
  mkdir -p "$CANDIDATE_DIR"

  if ! python -m pip download       --no-deps       --only-binary=:all:       --dest "$CANDIDATE_DIR"       "google-antigravity==$VERSION"; then
    echo "INFO: version $VERSION is unavailable for this runner; continuing"
    continue
  fi

  WHEEL="$(find "$CANDIDATE_DIR" -maxdepth 1 -type f -name 'google_antigravity-*.whl' -print -quit)"
  if test -z "$WHEEL"; then
    echo "INFO: no wheel found for $VERSION; continuing"
    continue
  fi

  echo "wheel: $WHEEL"
  sha256sum "$WHEEL"

  HARNESS="$CANDIDATE_DIR/localharness"
  unzip -p "$WHEEL" google/antigravity/bin/localharness > "$HARNESS"
  chmod +x "$HARNESS"

  echo "-- file"
  file "$HARNESS"

  echo "-- Go build metadata"
  go version -m "$HARNESS" 2>&1 || true

  echo "-- embedded CPU diagnostics"
  strings "$HARNESS" |
    grep -Eio 'compiled with (aes|avx|avx2|pclmul)[^[:cntrl:]]*|GOAMD64=v[1234]' |
    sort -u |
    head -20 || true

  echo "-- runtime smoke test: QEMU Nehalem CPU (SSE4.2, no AES)"
  LOG="$CANDIDATE_DIR/runtime.log"
  set +e
  timeout 8s qemu-x86_64 -cpu Nehalem "$HARNESS" --help >"$LOG" 2>&1
  RC=$?
  set -e

  cat "$LOG"

  if test "$RC" -eq 132 || grep -Eiq 'illegal instruction|SIGILL|invalid opcode|sigill-fail-fast|compiled with (aes|avx|avx2|pclmul)' "$LOG"; then
    echo "RESULT: $VERSION is NOT compatible with the legacy CPU profile"
    continue
  fi

  if test "$RC" -eq 126 || test "$RC" -eq 127; then
    echo "ERROR: harness $VERSION could not be executed"
    exit 1
  fi

  compatible_version="$VERSION"
  compatible_harness="$HARNESS"
  echo "RESULT: $VERSION is compatible with the legacy CPU profile"
  break
done

if test -z "$compatible_version"; then
  echo
  echo "ERROR: no compatible legacy localharness found in candidates:"
  printf '  %s\n' "${CANDIDATES[@]}"
  exit 1
fi

echo
echo "============================================================"
echo "PASS: compatible legacy localharness found"
echo "version: $compatible_version"
echo "path: $compatible_harness"
echo "sha256: $(sha256sum "$compatible_harness" | awk '{print $1}')"
echo "============================================================"

echo
echo "==> Static instruction diagnostics for selected harness"
# This is intentionally informational: Go may contain optional CPU-specific
# implementations that are guarded at runtime. The decisive test above is
# actual startup under a CPU profile without AES/AVX.
OBJSCAN="$(timeout 90s objdump -d "$compatible_harness" 2>/dev/null || true)"
AVX_HITS="$(grep -E $'\\t(vmov|vadd|vsub|vmul|vdiv|vsqrt|vpx|vpand|vpor|vpunpck|vpack|vperm|vblend|vextract|vinsert|vpbroadcast|vpshuf|vptest|vzeroupper|vzeroall|vgather|vscatter|vfm|vfnm)' <<<"$OBJSCAN" | head -10 || true)"
AES_HITS="$(grep -E $'\\t(aes[a-z0-9]*)' <<<"$OBJSCAN" | head -10 || true)"
PCLMUL_HITS="$(grep -E $'\\t(pclmul[a-z0-9]*)' <<<"$OBJSCAN" | head -10 || true)"

test -z "$AVX_HITS" || printf 'AVX-like instructions (diagnostic):\n%s\n' "$AVX_HITS"
test -z "$AES_HITS" || printf 'AES instructions (diagnostic):\n%s\n' "$AES_HITS"
test -z "$PCLMUL_HITS" || printf 'PCLMUL instructions (diagnostic):\n%s\n' "$PCLMUL_HITS"
echo "Selected harness static scan complete."
