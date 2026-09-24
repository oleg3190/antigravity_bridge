import pytest


def test_sdk_public_imports():
    try:
        from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, types
    except ModuleNotFoundError:
        pytest.skip("google-antigravity is not installed in the local test environment")
    assert Agent is not None
    assert LocalAgentConfig is not None
    assert CapabilitiesConfig is not None
    assert types is not None
