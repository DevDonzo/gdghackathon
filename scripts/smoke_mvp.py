from __future__ import annotations

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "http://127.0.0.1:8000"


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    headers["X-RateDrop-Simulated-Call"] = "1"

    request = Request(f"{API_BASE}{path}", data=body, method=method, headers=headers)
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    try:
        health = request_json("/health")
        print("health:", health)

        demo_bills = request_json("/api/demo-bills")
        first_demo = demo_bills["items"][0]
        print("demo bill:", first_demo["id"], first_demo["provider"], first_demo["monthlyTotal"])

        bill = request_json(f"/api/bills/demo/{first_demo['id']}", method="POST")
        print("bill id:", bill["id"])

        negotiation = request_json("/api/negotiations", method="POST", payload={"billId": bill["id"]})
        print("negotiation id:", negotiation["id"])

        started = request_json(f"/api/negotiations/{negotiation['id']}/start", method="POST")
        print("started:", started["status"], started["call"]["mode"])

        deadline = time.time() + 25
        while time.time() < deadline:
            current = request_json(f"/api/negotiations/{negotiation['id']}")
            if current["status"] == "completed":
                transcript = request_json(f"/api/negotiations/{negotiation['id']}/transcript")
                print("completed:", current["result"]["summary"])
                print("turn count:", len(transcript["turns"]))
                return 0
            time.sleep(1.5)

        print("timed out waiting for negotiation completion", file=sys.stderr)
        return 1
    except (HTTPError, URLError, KeyError, TimeoutError) as error:
        print(f"smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
