#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys


def fail(message: str) -> None:
    print(f"verify-ssh-host-key: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    try:
        query = json.load(sys.stdin)
        host = query["host"]
        expected = query["host_key"].strip()
        algorithm, encoded = expected.split()
        base64.b64decode(encoded, validate=True)
    except (KeyError, TypeError, ValueError) as error:
        fail(f"invalid query: {error}")

    result = subprocess.run(
        ["ssh-keyscan", "-T", "5", "-t", algorithm, host],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        fail(f"ssh-keyscan failed for {host}: {result.stderr.strip()}")

    observed = {
        " ".join(line.split()[1:3])
        for line in result.stdout.splitlines()
        if line and not line.startswith("#") and len(line.split()) >= 3
    }
    if expected not in observed:
        fail(f"the pinned {algorithm} key does not match {host}")

    fingerprint = base64.b64encode(
        hashlib.sha256(base64.b64decode(encoded)).digest()
    ).decode("ascii").rstrip("=")
    json.dump({"algorithm": algorithm, "fingerprint": f"SHA256:{fingerprint}"}, sys.stdout)


if __name__ == "__main__":
    main()
