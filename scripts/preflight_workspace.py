#!/usr/bin/env python3
import argparse, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("workspace")
args = p.parse_args()

ws = Path(args.workspace).resolve()
if not ws.exists():
    print(f"ERROR: workspace does not exist: {ws}")
    raise SystemExit(2)
if not ws.is_dir():
    print(f"ERROR: workspace is not a directory: {ws}")
    raise SystemExit(2)

if (ws / ".git").exists():
    print(f"OK: Git workspace: {ws}")
else:
    print(f"OK: non-Git workspace: {ws}")
    print("Git is required only for Git diff/rollback operations.")
