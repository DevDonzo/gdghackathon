from __future__ import annotations

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "http://127.0.0.1:8000"


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    headers["X-RateDrop-Simulated-Call"] = "1"

    request = Request(f"{API_BASE}{path}", data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        payload = error.read().decode("utf-8")
        return error.code, json.loads(payload)


def expect_status(path: str, expected: int, method: str = "GET", payload: dict | None = None) -> dict:
    status, data = request_json(path, method=method, payload=payload)
    if status != expected:
        raise RuntimeError(f"{method} {path} returned {status}, expected {expected}: {data}")
    return data


def main() -> int:
    try:
        print("health:", expect_status("/health", 200))
        print("invalid bill id:", expect_status("/api/bills/not-an-id", 400))
        print("invalid negotiation id:", expect_status("/api/negotiations/not-an-id", 400))
        print("invalid create payload:", expect_status("/api/negotiations", 400, method="POST", payload={"wrong": "shape"}))

        demo_bills = expect_status("/api/demo-bills", 200)
        first_demo = demo_bills["items"][0]
        print("demo bill:", first_demo["id"], first_demo["provider"], first_demo["monthlyTotal"])

        bill = expect_status(f"/api/bills/demo/{first_demo['id']}", 200, method="POST")
        print("bill id:", bill["id"])

        negotiation = expect_status("/api/negotiations", 200, method="POST", payload={"billId": bill["id"]})
        print("negotiation id:", negotiation["id"])

        first_start = expect_status(f"/api/negotiations/{negotiation['id']}/start", 200, method="POST")
        second_start = expect_status(f"/api/negotiations/{negotiation['id']}/start", 200, method="POST")
        print("first start:", first_start["status"], first_start["call"]["mode"])
        print("second start:", second_start["status"], second_start["call"]["mode"])

        deadline = time.time() + 30
        while time.time() < deadline:
            current = expect_status(f"/api/negotiations/{negotiation['id']}", 200)
            if current["status"] == "completed":
                transcript = expect_status(f"/api/negotiations/{negotiation['id']}/transcript", 200)
                turn_count = len(transcript["turns"])
                if turn_count != 8:
                    raise RuntimeError(f"Expected 8 transcript turns, got {turn_count}.")
                print("completed:", current["result"]["summary"])
                print("turn count:", turn_count)
                return 0
            time.sleep(1.5)

        raise RuntimeError("Timed out waiting for negotiation completion.")
    except (URLError, KeyError, TimeoutError, RuntimeError, ValueError) as error:
        print(f"backend sanity check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
