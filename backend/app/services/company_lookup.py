from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.core.config import get_settings


PHONE_PATTERN = re.compile(
    r"(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}|1[\s.-]?8\d{2}[\s.-]?\d{3}[\s.-]?\d{4}",
    re.IGNORECASE,
)


def lookup_company_contact(issue_context: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    settings = get_settings()
    company = issue_context.get("companyName") or "service provider"
    query = build_company_contact_query(issue_context)

    if not settings.tavily_api_key:
        return {
            "status": "disabled",
            "provider": "tavily",
            "companyName": company,
            "query": query,
            "phoneNumber": None,
            "confidence": 0.0,
            "sourceUrls": [],
            "sourceTitles": [],
            "error": "Set TAVILY_API_KEY to enable real company phone lookup.",
        }

    try:
        response = tavily_search(query, settings.tavily_api_key, timeout=timeout)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        return {
            "status": "failed",
            "provider": "tavily",
            "companyName": company,
            "query": query,
            "phoneNumber": None,
            "confidence": 0.0,
            "sourceUrls": [],
            "sourceTitles": [],
            "error": str(error),
        }

    return contact_lookup_from_tavily(company, query, response)


def build_company_contact_query(issue_context: dict[str, Any]) -> str:
    company = issue_context.get("companyName") or "service provider"
    task_type = str(issue_context.get("taskType") or "support").replace("_", " ")
    problem = issue_context.get("problemSummary") or issue_context.get("desiredOutcome") or ""
    return f"{company} official customer service phone number {task_type} {problem}".strip()


def tavily_search(query: str, api_key: str, timeout: int = 10) -> dict[str, Any]:
    payload = {
        "query": query,
        "search_depth": "basic",
        "include_answer": "basic",
        "max_results": 5,
    }
    request = Request(
        "https://api.tavily.com/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def contact_lookup_from_tavily(company: str, query: str, response: dict[str, Any]) -> dict[str, Any]:
    results = response.get("results") or []
    candidates = extract_phone_candidates(response)
    phone = candidates[0] if candidates else None
    source_urls = [str(item.get("url")) for item in results if item.get("url")][:5]
    source_titles = [str(item.get("title")) for item in results if item.get("title")][:5]
    confidence = _confidence(phone, source_urls)

    return {
        "status": "found" if phone else "not_found",
        "provider": "tavily",
        "companyName": company,
        "query": query,
        "phoneNumber": phone,
        "confidence": confidence,
        "sourceUrls": source_urls,
        "sourceTitles": source_titles,
        "answer": response.get("answer"),
        "error": None if phone else "No phone number found in Tavily answer or top results.",
    }


def extract_phone_candidates(response: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    _append_phone_matches(str(response.get("answer") or ""), candidates, seen)
    for result in response.get("results") or []:
        _append_phone_matches(str(result.get("title") or ""), candidates, seen)
        _append_phone_matches(str(result.get("content") or ""), candidates, seen)
        _append_phone_matches(str(result.get("url") or ""), candidates, seen)
    return candidates


def _append_phone_matches(text: str, candidates: list[str], seen: set[str]) -> None:
    for raw in PHONE_PATTERN.findall(text):
        normalized = normalize_phone(raw)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"+1{digits}"


def _confidence(phone: str | None, urls: list[str]) -> float:
    if not phone:
        return 0.0
    officialish = any(domain in url.lower() for url in urls for domain in [".com", ".ca", ".org"])
    return 0.82 if officialish else 0.64
