"""CLI entry: read JSON request from stdin, write JSON report to stdout."""

import json
import sys

from .pipeline import run


def main() -> int:
    raw = sys.stdin.buffer.read()
    request = json.loads(raw.decode("utf-8-sig"))
    report = run(request)
    sys.stdout.buffer.write(
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
