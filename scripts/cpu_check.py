#!/usr/bin/env python3
from __future__ import annotations

import json

from bridge.cpu_compat import HarnessCompatibilityError, diagnostic_payload, resolve_harness_env


def main() -> int:
    payload = diagnostic_payload()
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        env = resolve_harness_env()
    except HarnessCompatibilityError as exc:
        print(f"\nCOMPATIBILITY ERROR: {exc}")
        return 2

    if env:
        print(f"\nSelected harness: {env['ANTIGRAVITY_HARNESS_PATH']}")
    else:
        print("\nSelected harness: Google SDK bundled localharness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
