from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any


subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)


def encode_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


async def publish(negotiation_id: str, event: str, payload: dict[str, Any]) -> None:
    message = encode_sse(event, payload)
    for queue in list(subscribers[negotiation_id]):
        await queue.put(message)


def subscribe(negotiation_id: str) -> asyncio.Queue[str]:
    queue: asyncio.Queue[str] = asyncio.Queue()
    subscribers[negotiation_id].add(queue)
    return queue


def unsubscribe(negotiation_id: str, queue: asyncio.Queue[str]) -> None:
    subscribers[negotiation_id].discard(queue)
    if not subscribers[negotiation_id]:
        subscribers.pop(negotiation_id, None)

