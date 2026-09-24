from bridge.policy import dangerous_command, is_sensitive_path


def test_sensitive_paths():
    assert is_sensitive_path(".env")
    assert is_sensitive_path(".ssh/id_rsa")
    assert is_sensitive_path("config/credentials.json")
    assert not is_sensitive_path("src/auth.py")


def test_dangerous_commands():
    assert dangerous_command("rm -rf /")
    assert dangerous_command("git reset --hard")
    assert not dangerous_command("pytest -q")
