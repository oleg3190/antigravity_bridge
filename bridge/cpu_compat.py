from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


class HarnessCompatibilityError(RuntimeError):
    """Raised when the selected Antigravity harness cannot run on this CPU."""


@dataclass(frozen=True)
class CPUInfo:
    architecture: str
    model: str
    flags: frozenset[str]

    @property
    def is_x86_64(self) -> bool:
        return self.architecture in {"x86_64", "amd64"}

    @property
    def supports_avx(self) -> bool:
        return "avx" in self.flags

    @property
    def supports_avx2(self) -> bool:
        return "avx2" in self.flags

    @property
    def supports_aes(self) -> bool:
        return "aes" in self.flags

    @property
    def supports_pclmulqdq(self) -> bool:
        return "pclmulqdq" in self.flags

    @property
    def legacy_x86(self) -> bool:
        """Old x86-64 CPUs such as Westmere/Arrandale without AVX."""
        return self.is_x86_64 and not self.supports_avx


def _read_proc_cpuinfo() -> str:
    try:
        return Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _parse_cpuinfo(text: str) -> CPUInfo:
    model = ""
    flags: set[str] = set()

    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key in {"model name", "hardware"} and not model:
            model = value
        elif key in {"flags", "features"}:
            flags.update(value.split())

    return CPUInfo(
        architecture=platform.machine().lower(),
        model=model or "unknown",
        flags=frozenset(flags),
    )


def get_cpu_info() -> CPUInfo:
    return _parse_cpuinfo(_read_proc_cpuinfo())


def _validated_binary(path: str | None) -> str | None:
    if not path:
        return None

    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise HarnessCompatibilityError(
            f"Configured Antigravity harness does not exist: {candidate}"
        )
    if not os.access(candidate, os.X_OK):
        raise HarnessCompatibilityError(
            f"Configured Antigravity harness is not executable: {candidate}"
        )
    return str(candidate)


def resolve_harness_env(cpu: CPUInfo | None = None) -> dict[str, str]:
    """Resolve an optional external harness without mutating global os.environ.

    Priority:
      1. ANTIGRAVITY_HARNESS_PATH — explicit override for every CPU.
      2. ANTIGRAVITY_LEGACY_HARNESS_PATH — automatic fallback on x86-64
         machines without AVX.
      3. No override — let the Google SDK use its bundled harness.
    """
    cpu = cpu or get_cpu_info()

    explicit = _validated_binary(os.getenv("ANTIGRAVITY_HARNESS_PATH"))
    if explicit:
        return {"ANTIGRAVITY_HARNESS_PATH": explicit}

    if cpu.legacy_x86:
        legacy = _validated_binary(os.getenv("ANTIGRAVITY_LEGACY_HARNESS_PATH"))
        if legacy:
            return {"ANTIGRAVITY_HARNESS_PATH": legacy}

        raise HarnessCompatibilityError(
            "The host CPU is an old x86-64 processor without AVX, while the "
            "bundled Google Antigravity localharness may require newer CPU "
            "instructions. Set ANTIGRAVITY_HARNESS_PATH to a compatible "
            "localharness binary, or ANTIGRAVITY_LEGACY_HARNESS_PATH to the "
            "legacy binary used for automatic fallback. "
            f"Detected CPU: {cpu.model}; flags: "
            f"avx={cpu.supports_avx}, aes={cpu.supports_aes}, "
            f"pclmulqdq={cpu.supports_pclmulqdq}."
        )

    return {}


def diagnostic_payload(cpu: CPUInfo | None = None) -> dict[str, object]:
    cpu = cpu or get_cpu_info()
    return {
        "architecture": cpu.architecture,
        "model": cpu.model,
        "legacy_x86": cpu.legacy_x86,
        "features": {
            "avx": cpu.supports_avx,
            "avx2": cpu.supports_avx2,
            "aes": cpu.supports_aes,
            "pclmulqdq": cpu.supports_pclmulqdq,
        },
        "explicit_harness_path": bool(os.getenv("ANTIGRAVITY_HARNESS_PATH")),
        "legacy_harness_path": os.getenv("ANTIGRAVITY_LEGACY_HARNESS_PATH", ""),
    }
