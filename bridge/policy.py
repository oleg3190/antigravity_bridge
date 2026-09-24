from __future__ import annotations

import re
from pathlib import PurePosixPath


SENSITIVE_PARTS = {
    ".env",
    ".git",
    ".ssh",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "secrets",
}


def is_sensitive_path(path: str) -> bool:
    p = PurePosixPath(path.replace("\\", "/"))
    for part in p.parts:
        if part in SENSITIVE_PARTS:
            return True
    return bool(re.search(r"(^|/)(.*secret.*|.*credential.*)$", str(p), re.I))


DANGEROUS_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-rf\s+/", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-fdx?\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=", re.I),
    re.compile(r"\bcurl\b.*\|\s*(sh|bash)\b", re.I),
    re.compile(r"\bwget\b.*\|\s*(sh|bash)\b", re.I),
]


def dangerous_command(command: str) -> bool:
    return any(rx.search(command) for rx in DANGEROUS_COMMAND_PATTERNS)


def validate_diff_paths(changed_files: list[str]) -> None:
    bad = [p for p in changed_files if is_sensitive_path(p)]
    if bad:
        raise PermissionError(f"Refusing sensitive paths in diff: {bad}")
