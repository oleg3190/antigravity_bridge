#!/usr/bin/env python3
import json, os, sys, time, urllib.error, urllib.request

BASE = os.getenv("BRIDGE_URL", "http://127.0.0.1:8090")
payload = {
    "task": "Создай файл antigravity_smoke_test.txt в текущем workspace с текстом ANTIGRAVITY_OK. Проверь существование файла. Не изменяй другие файлы.",
    "workspace": "/workspace",
    "run_tests": False,
}
req = urllib.request.Request(BASE + "/v1/jobs", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        job = json.load(r)
except Exception as e:
    print(f"ERROR: cannot submit smoke job: {e}")
    sys.exit(2)
job_id = job["id"]
print(f"Job: {job_id}")
for _ in range(90):
    with urllib.request.urlopen(BASE + f"/v1/jobs/{job_id}", timeout=10) as r:
        job = json.load(r)
    status = job["status"]
    print(f"status={status}")
    if status in {"succeeded", "failed", "test_failed", "canceled"}:
        if status != "succeeded":
            print(json.dumps(job, ensure_ascii=False, indent=2))
            sys.exit(1)
        result = job.get("result") or {}
        if "antigravity_smoke_test.txt" not in result.get("changed_files", []):
            print("ERROR: smoke job succeeded but changed file was not reported")
            sys.exit(1)
        print("SMOKE OK")
        sys.exit(0)
    time.sleep(1)
print("ERROR: smoke test timed out")
sys.exit(2)
