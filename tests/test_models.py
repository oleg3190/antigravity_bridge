from bridge.models import CreateJobRequest


def test_request():
    req = CreateJobRequest(
        task="fix tests",
        workspace="/tmp/repo",
        run_tests=False,
    )
    assert req.task == "fix tests"
