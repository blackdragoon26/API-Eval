"""
FortyGuard final API endpoint audit.

This is a bounded, hiring-evaluation-style probe, not a load test.

Usage:
    export FORTYGUARD_API_KEY="..."
    python final_api_endpoint_audit.py

Outputs:
    evidence/final_api_endpoint_audit_2026-06-24.jsonl
    evidence/final_api_endpoint_summary_2026-06-24.md

The API key is never written to output files. Large Base64/image/PDF payloads are
redacted so the evidence remains shareable.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE = "https://api.fortyguard.com"
API = f"{BASE}/v1"
RUN_DATE = "2026-06-24"
OUT_DIR = Path("evidence")
JSONL = OUT_DIR / f"final_api_endpoint_audit_{RUN_DATE}.jsonl"
SUMMARY = OUT_DIR / f"final_api_endpoint_summary_{RUN_DATE}.md"

API_KEY = os.environ.get("FORTYGUARD_API_KEY")
if not API_KEY:
    raise SystemExit("Set FORTYGUARD_API_KEY before running this script.")

HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}
SECRET_RE = re.compile(re.escape(API_KEY))


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            if key.lower() in {"api-key", "authorization", "x-api-key"}:
                cleaned[key] = "<redacted>"
            else:
                cleaned[key] = redact(child)
        return cleaned
    if isinstance(value, list):
        if value and all(isinstance(item, str) and len(item) > 500 for item in value):
            return [f"<redacted large string list: {len(value)} item(s)>"]
        return [redact(item) for item in value]
    if isinstance(value, str):
        value = SECRET_RE.sub("<redacted api key>", value)
        if len(value) > 500 and re.fullmatch(r"[A-Za-z0-9+/=\n\r]+", value):
            return f"<redacted large base64/string: {len(value)} chars>"
        if len(value) > 2500:
            return value[:2500] + "... <truncated>"
        return value
    return value


def compact_openapi(body: Any) -> Any:
    if not isinstance(body, dict):
        return body
    paths = sorted(body.get("paths", {}).keys())
    schemas = sorted(body.get("components", {}).get("schemas", {}).keys())
    return {
        "openapi": body.get("openapi"),
        "info": body.get("info"),
        "path_count": len(paths),
        "paths": paths,
        "schemas": schemas,
    }


def selected_headers(headers: dict[str, str]) -> dict[str, str]:
    interesting = {}
    for key, value in headers.items():
        lower = key.lower()
        if (
            lower in {"content-type", "content-length", "cache-control", "etag"}
            or "ratelimit" in lower
            or "retry-after" in lower
            or "credit" in lower
            or lower in {"x-request-id", "x-correlation-id", "traceparent"}
        ):
            interesting[key] = value
    return interesting


def request(
    name: str,
    method: str,
    url: str,
    *,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    raw_body: str | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    started = time.time()
    kwargs: dict[str, Any] = {"timeout": timeout, "headers": headers or HEADERS}
    if raw_body is not None:
        kwargs["data"] = raw_body
    elif json_body is not None:
        kwargs["json"] = json_body

    try:
        response = requests.request(method, url, **kwargs)
        elapsed = round(time.time() - started, 3)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text[:1000]
        elif "pdf" in content_type.lower() or response.content[:4] == b"%PDF":
            body = f"<redacted binary/pdf: {len(response.content)} bytes>"
        else:
            body = response.text[:1000]
        if name == "openapi_json":
            body = compact_openapi(body)
        record = {
            "test": name,
            "method": method,
            "url": url,
            "request": redact(json_body if json_body is not None else raw_body),
            "status_code": response.status_code,
            "elapsed_seconds": elapsed,
            "headers": selected_headers(dict(response.headers)),
            "response": redact(body),
        }
    except requests.RequestException as exc:
        record = {
            "test": name,
            "method": method,
            "url": url,
            "request": redact(json_body if json_body is not None else raw_body),
            "status_code": None,
            "elapsed_seconds": round(time.time() - started, 3),
            "error": str(exc),
        }

    with JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    print(f"{name:35} {method:4} {record.get('status_code')} {record['elapsed_seconds']}s")
    return record


def status_from(record: dict[str, Any]) -> str | None:
    body = record.get("response")
    if not isinstance(body, dict):
        return None
    data = body.get("data")
    if isinstance(data, dict):
        status = data.get("status")
        if isinstance(status, str):
            return status
    return None


def activity_id_from(record: dict[str, Any]) -> str | None:
    body = record.get("response")
    if not isinstance(body, dict):
        return None
    data = body.get("data")
    if isinstance(data, dict):
        activity_id = data.get("activity_id")
        if isinstance(activity_id, str):
            return activity_id
    return None


def poll(activity_id: str, prefix: str, *, polls: int = 4, interval: int = 3) -> list[dict[str, Any]]:
    results = []
    for index in range(1, polls + 1):
        time.sleep(interval)
        record = request(f"{prefix}_poll_{index}", "GET", f"{API}/status/{activity_id}", headers={"api-key": API_KEY})
        results.append(record)
        status = status_from(record)
        if status and status.lower() in {"completed", "succeeded", "failed"}:
            break
    return results


VALID_DATE_TIME = {"start_date": "2024-07-15", "start_time": "14:00", "filter_type": 1}

HEATMAP_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-74.0170, 40.7050],
                        [-74.0030, 40.7050],
                        [-74.0030, 40.7180],
                        [-74.0170, 40.7180],
                        [-74.0170, 40.7050],
                    ]
                ],
            },
        }
    ],
}

UNCLOSED_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-74.0170, 40.7050],
                        [-74.0030, 40.7050],
                        [-74.0030, 40.7180],
                        [-74.0100, 40.7200],
                    ]
                ],
            },
        }
    ],
}


def response_brief(record: dict[str, Any]) -> str:
    body = record.get("response")
    if isinstance(body, dict):
        if "message" in body:
            return str(body["message"])
        if "details" in body:
            return json.dumps(body["details"], ensure_ascii=True)[:120]
        if "detail" in body:
            return json.dumps(body["detail"], ensure_ascii=True)[:140]
    if isinstance(body, str):
        return body[:120]
    return ""


def write_summary(records: list[dict[str, Any]]) -> None:
    by_name = {record["test"]: record for record in records}

    def row(name: str, expected: str, note: str = "") -> str:
        record = by_name.get(name)
        if not record:
            return f"| `{name}` | {expected} | not run | | {note} |"
        actual = record.get("status_code")
        brief = response_brief(record).replace("|", "\\|")
        return f"| `{name}` | {expected} | {actual} | {brief} | {note} |"

    rate_headers = sorted(
        {
            header
            for record in records
            for header in record.get("headers", {})
            if "ratelimit" in header.lower()
            or "retry-after" in header.lower()
            or "credit" in header.lower()
            or header.lower() in {"x-request-id", "x-correlation-id"}
        }
    )

    lines = [
        "# FortyGuard Final API Endpoint Audit",
        "",
        f"Run date: {RUN_DATE}",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This pass focuses on API endpoint behavior and main functionality. It is intentionally bounded and does not perform load testing or destructive testing. The API key is redacted from all evidence.",
        "",
        "## Endpoint Results",
        "",
        "| Test | Expected | Actual HTTP | Response brief | Notes |",
        "|---|---:|---:|---|---|",
        row("health", "200", "Public health check."),
        row("ready", "200", "Public readiness check."),
        row("openapi_json", "200", "OpenAPI 3.1 schema available."),
        row("swagger_docs_disabled", "404", "FastAPI Swagger UI disabled."),
        row("redoc", "200", "ReDoc shell available, but browser rendering may depend on CDN."),
        row("credits_usage_before", "200", "Credit/plan usage endpoint works but is a POST body API."),
        row("missing_api_key", "401/403", "Clear auth validation."),
        row("malformed_json", "400/422", "Malformed body validation."),
        row("heatmap_docs_featurecollection", "200 submit or clear 4xx", "Docs-style FeatureCollection happy path."),
        row("heatmap_unclosed_featurecollection", "400/422", "Geometry should be rejected before job execution."),
        row("heatmap_invalid_granularity", "400/422", "Enum validation."),
        row("satellite_submit", "200 submit", "Premium endpoint happy path."),
        row("satellite_invalid_latitude", "400/422", "Coordinate validation."),
        row("streetview_submit", "200 submit", "Premium endpoint happy path."),
        row("streetview_missing_back_view", "400/422", "Required field validation."),
        row("env_params_submit", "200 submit", "OpenAPI-correct schema."),
        row("env_params_doc_style_parameters", "200 or documented 4xx", "Docs/customization mismatch check."),
        row("heat_intelligence_invalid_category", "400/422", "Analysis enum validation."),
        row("heat_intelligence_empty_analysis", "400/422", "Array min length validation."),
        row("garbage_activity_id", "404 preferred", "Unknown activity id behavior."),
        row("credits_usage_after", "200", "Allows before/after credit inspection."),
        "",
        "## Operational Headers",
        "",
        "Observed quota/retry/request-id headers: "
        + (", ".join(f"`{header}`" for header in rate_headers) if rate_headers else "None observed."),
        "",
        "## Evidence",
        "",
        f"- Raw sanitized JSONL: `{JSONL}`",
        f"- Summary: `{SUMMARY}`",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    JSONL.write_text("", encoding="utf-8")

    records: list[dict[str, Any]] = []

    def add(record: dict[str, Any]) -> dict[str, Any]:
        records.append(record)
        return record

    add(request("health", "GET", f"{BASE}/health", headers={}))
    add(request("ready", "GET", f"{BASE}/ready", headers={}))
    add(request("openapi_json", "GET", f"{BASE}/openapi.json", headers={}))
    add(request("swagger_docs_disabled", "GET", f"{BASE}/docs", headers={}))
    add(request("redoc", "GET", f"{BASE}/redoc", headers={}))

    add(
        request(
            "credits_usage_before",
            "POST",
            f"{API}/system/fetch-api-key-usage",
            json_body={"api_key": API_KEY},
            headers={"Content-Type": "application/json"},
        )
    )

    add(
        request(
            "missing_api_key",
            "POST",
            f"{API}/heatmap",
            json_body={"polygon_aoi": HEATMAP_FEATURE_COLLECTION, "date_time": VALID_DATE_TIME, "granularity": 100},
            headers={"Content-Type": "application/json"},
        )
    )
    add(
        request(
            "malformed_json",
            "POST",
            f"{API}/heatmap",
            raw_body='{"polygon_aoi": ',
            headers={"api-key": API_KEY, "Content-Type": "application/json"},
        )
    )

    add(
        request(
            "heatmap_docs_featurecollection",
            "POST",
            f"{API}/heatmap",
            json_body={"polygon_aoi": HEATMAP_FEATURE_COLLECTION, "date_time": VALID_DATE_TIME, "granularity": 100},
        )
    )
    add(
        request(
            "heatmap_unclosed_featurecollection",
            "POST",
            f"{API}/heatmap",
            json_body={"polygon_aoi": UNCLOSED_FEATURE_COLLECTION, "date_time": VALID_DATE_TIME, "granularity": 100},
        )
    )
    add(
        request(
            "heatmap_invalid_granularity",
            "POST",
            f"{API}/heatmap",
            json_body={"polygon_aoi": HEATMAP_FEATURE_COLLECTION, "date_time": VALID_DATE_TIME, "granularity": 75},
        )
    )

    satellite = add(
        request(
            "satellite_submit",
            "POST",
            f"{API}/satellite",
            json_body={
                "sat": {"latitude": 41.84632807720175, "longitude": -87.74329628220852},
                "date_time": VALID_DATE_TIME,
                "granularity": 80,
            },
        )
    )
    add(
        request(
            "satellite_invalid_latitude",
            "POST",
            f"{API}/satellite",
            json_body={
                "sat": {"latitude": 200, "longitude": -87.74329628220852},
                "date_time": VALID_DATE_TIME,
                "granularity": 80,
            },
        )
    )
    satellite_id = activity_id_from(satellite)
    if satellite_id:
        records.extend(poll(satellite_id, "satellite", polls=4, interval=3))

    streetview = add(
        request(
            "streetview_submit",
            "POST",
            f"{API}/streetview",
            json_body={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "vertical_angle": 10.0,
                "horizontal_angle": 90.0,
                "back_view": False,
            },
        )
    )
    add(
        request(
            "streetview_missing_back_view",
            "POST",
            f"{API}/streetview",
            json_body={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "vertical_angle": 10.0,
                "horizontal_angle": 90.0,
            },
        )
    )
    streetview_id = activity_id_from(streetview)
    if streetview_id:
        records.extend(poll(streetview_id, "streetview", polls=3, interval=3))

    env_params = add(
        request(
            "env_params_submit",
            "POST",
            f"{API}/env_params",
            json_body={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "temperature": 30.0,
                "date_time": VALID_DATE_TIME,
            },
        )
    )
    add(
        request(
            "env_params_doc_style_parameters",
            "POST",
            f"{API}/env_params",
            json_body={
                "location": {"latitude": 40.7128, "longitude": -74.0060},
                "date_time": VALID_DATE_TIME,
                "parameters": ["heat_index", "humidity", "aqi_pm25"],
            },
        )
    )
    env_params_id = activity_id_from(env_params)
    if env_params_id:
        records.extend(poll(env_params_id, "env_params", polls=3, interval=3))

    add(
        request(
            "heat_intelligence_invalid_category",
            "POST",
            f"{API}/heat_intelligence",
            json_body={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "temperature": 30.0,
                "date": "2024-07-15",
                "analysis": ["weather"],
            },
        )
    )
    add(
        request(
            "heat_intelligence_empty_analysis",
            "POST",
            f"{API}/heat_intelligence",
            json_body={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "temperature": 30.0,
                "date": "2024-07-15",
                "analysis": [],
            },
        )
    )

    add(request("garbage_activity_id", "GET", f"{API}/status/not-a-real-id", headers={"api-key": API_KEY}))

    add(
        request(
            "credits_usage_after",
            "POST",
            f"{API}/system/fetch-api-key-usage",
            json_body={"api_key": API_KEY},
            headers={"Content-Type": "application/json"},
        )
    )

    write_summary(records)
    print(f"\nWrote {JSONL}")
    print(f"Wrote {SUMMARY}")


if __name__ == "__main__":
    main()
