"""Command-line entry: read JSON request from stdin, write JSON report to stdout."""

from __future__ import annotations

import json
import sys

from .orchestrator import process_request


def main() -> int:
    request = json.load(sys.stdin)
    report = process_request(request)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
