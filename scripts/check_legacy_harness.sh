#!/usr/bin/env bash
set -euo pipefail

VERSION="0.1.6"
EXPECTED_SHA256="e1eabba26db6f7cee27861365393f65dcb567f83db2aac7382adac0372e8d093"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> Download google-antigravity==$VERSION"
python -m pip download   --no-deps   --only-binary=:all:   --dest "$WORKDIR"   "google-antigravity==$VERSION"

WHEEL="$(find "$WORKDIR" -maxdepth 1 -type f -name 'google_antigravity-*.whl' -print -quit)"
test -n "$WHEEL"

ACTUAL_SHA256="$(sha256sum "$WHEEL" | awk '{print $1}')"
echo "wheel: $WHEEL"
echo "sha256: $ACTUAL_SHA256"
test "$ACTUAL_SHA256" = "$EXPECTED_SHA256"

HARNESS="$WORKDIR/localharness-legacy"
unzip -p "$WHEEL" google/antigravity/bin/localharness > "$HARNESS"
chmod +x "$HARNESS"

echo
echo "==> Harness file"
file "$HARNESS"

echo
echo "==> Go build metadata"
GO_METADATA="$(go version -m "$HARNESS" 2>&1 || true)"
printf '%s\n' "$GO_METADATA"

if grep -Eq 'GOAMD64=v[234]' <<<"$GO_METADATA"; then
  echo "ERROR: localharness explicitly requires GOAMD64 >= v2"
  exit 1
fi

if grep -Eq 'GOAMD64=v1' <<<"$GO_METADATA"; then
  echo "PASS: localharness explicitly reports GOAMD64=v1"
else
  echo "INFO: GOAMD64 is not present in build metadata; continuing with runtime/static checks"
fi

echo
echo "==> Static instruction scan (diagnostic)"
OBJSCAN="$(objdump -d "$HARNESS" 2>/dev/null || true)"
AVX_HITS="$(grep -E $'\\t(vmov|vadd|vsub|vmul|vdiv|vsqrt|vpx|vpand|vpor|vpunpck|vpack|vperm|vblend|vextract|vinsert|vpbroadcast|vpshuf|vptest|vzeroupper|vzeroall|vgather|vscatter|vfm|vfnm)' <<<"$OBJSCAN" | head -20 || true)"
AES_HITS="$(grep -E $'\\t(aes[a-z0-9]*)' <<<"$OBJSCAN" | head -20 || true)"
PCLMUL_HITS="$(grep -E $'\\t(pclmul[a-z0-9]*)' <<<"$OBJSCAN" | head -20 || true)"

if test -n "$AVX_HITS" || test -n "$AES_HITS" || test -n "$PCLMUL_HITS"; then
  echo "INFO: optional/vector instructions are present in disassembly:"
  test -z "$AVX_HITS" || printf '%s\n' "$AVX_HITS"
  test -z "$AES_HITS" || printf '%s\n' "$AES_HITS"
  test -z "$PCLMUL_HITS" || printf '%s\n' "$PCLMUL_HITS"
else
  echo "PASS: no obvious AVX/AES/PCLMUL mnemonics found in disassembly"
fi

echo
echo "==> Runtime smoke test on a legacy x86-64 CPU profile"
if ! command -v qemu-x86_64 >/dev/null 2>&1; then
  echo "qemu-x86_64 is required for the legacy CPU smoke test"
  exit 1
fi

qemu-x86_64 -cpu help | grep -q '^x86-64\|^core2duo' || true

set +e
timeout 8s qemu-x86_64 -cpu core2duo "$HARNESS" --help >"$WORKDIR/harness-help.log" 2>&1
RC=$?
set -e

cat "$WORKDIR/harness-help.log"

if grep -Eiq 'illegal instruction|SIGILL|invalid opcode' "$WORKDIR/harness-help.log"; then
  echo "ERROR: legacy CPU smoke test hit an illegal-instruction failure"
  exit 1
fi

if test "$RC" -eq 132; then
  echo "ERROR: localharness exited with SIGILL (132) on qemu core2duo"
  exit 1
fi

if test "$RC" -eq 126 || test "$RC" -eq 127; then
  echo "ERROR: localharness could not be executed (exit $RC)"
  exit 1
fi

echo "PASS: legacy CPU smoke test did not hit SIGILL"
