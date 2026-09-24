from __future__ import annotations

from pathlib import Path

import pytest

from bridge.cpu_compat import (
    CPUInfo,
    HarnessCompatibilityError,
    diagnostic_payload,
    resolve_harness_env,
)


def cpu(*flags: str) -> CPUInfo:
    return CPUInfo(
        architecture="x86_64",
        model="Intel test CPU",
        flags=frozenset(flags),
    )


def test_legacy_x86_is_detected_without_avx():
    info = cpu("sse4_1", "sse4_2")

    assert info.legacy_x86 is True
    assert info.supports_avx is False
    assert info.supports_aes is False


def test_explicit_harness_overrides_cpu_check(monkeypatch, tmp_path: Path):
    binary = tmp_path / "localharness"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("ANTIGRAVITY_HARNESS_PATH", str(binary))

    result = resolve_harness_env(cpu())

    assert result == {"ANTIGRAVITY_HARNESS_PATH": str(binary)}


def test_legacy_harness_is_selected_for_old_cpu(monkeypatch, tmp_path: Path):
    binary = tmp_path / "localharness-legacy"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.delenv("ANTIGRAVITY_HARNESS_PATH", raising=False)
    monkeypatch.setenv("ANTIGRAVITY_LEGACY_HARNESS_PATH", str(binary))

    result = resolve_harness_env(cpu())

    assert result == {"ANTIGRAVITY_HARNESS_PATH": str(binary)}


def test_old_cpu_without_legacy_binary_fails_clearly(monkeypatch):
    monkeypatch.delenv("ANTIGRAVITY_HARNESS_PATH", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_LEGACY_HARNESS_PATH", raising=False)

    with pytest.raises(HarnessCompatibilityError, match="without AVX"):
        resolve_harness_env(cpu())


def test_non_avx_flag_can_be_reported_without_hiding_aes():
    info = cpu("avx", "avx2", "aes", "pclmulqdq")
    payload = diagnostic_payload(info)

    assert payload["legacy_x86"] is False
    assert payload["features"] == {
        "avx": True,
        "avx2": True,
        "aes": True,
        "pclmulqdq": True,
    }
