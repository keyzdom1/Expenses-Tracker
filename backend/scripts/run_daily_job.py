"""Trigger the API's idempotent daily job from a cron runner.

Usage (Render Cron Job, GitHub Actions, Task Scheduler):

    API_BASE_URL=https://your-api.onrender.com \
    CRON_SECRET=... \
    python scripts/run_daily_job.py

Only the standard library is used, so no dependencies are needed beyond the
API itself. The job is idempotent: running it more than once per day is safe.
"""

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
CRON_SECRET = os.environ.get("CRON_SECRET", "")


def main() -> int:
    if not API_BASE_URL:
        print("API_BASE_URL is required.", file=sys.stderr)
        return 2
    if not CRON_SECRET:
        print("CRON_SECRET is required.", file=sys.stderr)
        return 2

    request = urllib.request.Request(
        f"{API_BASE_URL}/api/v1/jobs/run",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Cron-Secret": CRON_SECRET,
            "User-Agent": "expense-tracker-daily-job",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Could not reach the API: {exc.reason}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return 0

    print(json.dumps(payload.get("data", payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
