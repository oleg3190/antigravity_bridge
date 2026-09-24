#!/usr/bin/env python3
import importlib
import os
import platform
import shutil
import sys

print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Machine: {platform.machine()}")

for name in ("pip", "setuptools", "wheel", "pytest"):
    try:
        mod = importlib.import_module(name)
        print(f"{name}: {getattr(mod, '__version__', 'installed')}")
    except Exception as exc:
        print(f"{name}: unavailable ({exc.__class__.__name__})")

try:
    dist = importlib.import_module("importlib.metadata")
    try:
        print(f"google-antigravity: {dist.version('google-antigravity')}")
    except Exception as exc:
        print(f"google-antigravity: unavailable ({exc.__class__.__name__})")
except Exception:
    pass

# Import the SDK only. Do not instantiate a client, scan tools, or make network calls.
try:
    import google.antigravity as antigravity  # noqa: F401
    print("Antigravity SDK import: OK")
except Exception as exc:
    print(f"Antigravity SDK import: FAILED: {exc}")
    sys.exit(1)

# Keep this check intentionally lightweight. Listing all built-in tools can load
# substantial SDK state and previously caused exit 137 in constrained containers.
try:
    from google.antigravity import BuiltinTools
    names = [n for n in dir(BuiltinTools) if not n.startswith("_")]
    print(f"BuiltinTools available: {len(names)}")
    if names:
        print("BuiltinTools sample:", names[:20])
except Exception as exc:
    print(f"BuiltinTools: unavailable ({exc.__class__.__name__}: {exc})")
    sys.exit(1)

print("SDK check: OK")
