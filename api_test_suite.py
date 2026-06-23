"""
FortyGuard API Test Suite — v2 (Rebuilt)
==========================================
Supersedes the original api_test_suite.py. Changes in this version:

  1. env_params / heat_intelligence payloads FIXED to the flat schema
     discovered from the previous run's 422 error messages
     (latitude, longitude, temperature, date — NOT nested location/date_time).
     NOTE: this is a best-guess reconstruction based on "missing field" errors.
     If you still get 422s, READ THE PRINTED ERROR DETAIL — it will tell you
     exactly which field is still missing or wrong, and you can adjust the
     ENV_PARAMS_PAYLOAD / HEAT_INTEL_PAYLOAD templates below accordingly.
  2. Every request now logs response headers (for rate-limit/credit header check).
  3. Every test function is wrapped individually — one failure/exception will
     NOT stop the rest of the suite from running.
  4. Added OpenAPI/Swagger discovery check (no API key needed).
  5. Reduced default repeat counts for the known-broken heatmap endpoint to
     save your time/credits, since it 500s on every call regardless of payload.
  6. Added a final summary printed at the end so you can sanity-check results
     immediately without manually reading the whole log file.

Usage:
    export FORTYGUARD_API_KEY="your_key_here"
    pip install requests
    python api_test_suite_v2.py

Results are logged to results_v2.jsonl (fresh file each run).
"""

import os
import json
import time
import statistics
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = "https://api.fortyguard.com/v1"
ROOT_URL = "https://api.fortyguard.com"
API_KEY = os.environ.get("FORTYGUARD_API_KEY")
LOG_FILE = "results_v2.jsonl"

if not API_KEY:
    raise SystemExit(
        "Set FORTYGUARD_API_KEY as an environment variable before running this script.\n"
        "Example: export FORTYGUARD_API_KEY=\"your_key_here\""
    )

HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

VALID_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [-74.0060, 40.7128],
        [-74.0050, 40.7128],
        [-74.0050, 40.7138],
        [-74.0060, 40.7138],
        [-74.0060, 40.7128],
    ]],
}

VALID_DATE_TIME = {
    "start_date": "2024-07-15",
    "start_time": "14:00",
    "filter_type": 1,
}

# FIXED: flat schema for env_params, reconstructed from 422 "missing field" errors
# in the previous run (latitude, longitude, temperature, date were all flagged
# as missing top-level fields — NOT nested under location/date_time).
ENV_PARAMS_PAYLOAD_3 = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "temperature": 30.0,  # guessed unit: Celsius; adjust if API rejects
    "date": "2024-07-15",
    "parameters": ["heat_index", "humidity", "aqi_pm25"],
}

ENV_PARAMS_PAYLOAD_4 = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "temperature": 30.0,
    "date": "2024-07-15",
    "parameters": ["heat_index", "humidity", "aqi_pm25", "co2"],
}

# FIXED: same flat-schema fix applied to heat_intelligence
HEAT_INTEL_PAYLOAD_BASE = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "temperature": 30.0,
    "date": "2024-07-15",
}


# ---------------------------------------------------------------------------
# Core request/log helpers
# ---------------------------------------------------------------------------

def log_result(test_name, method, url, payload, response, elapsed):
    """Append a structured record (including headers) to the log file."""
    try:
        body = response.json()
    except ValueError:
        body = response.text[:500]

    record = {
        "test": test_name,
        "method": method,
        "url": url,
        "payload": payload,
        "status_code": response.status_code,
        "elapsed_seconds": round(elapsed, 3),
        "response_headers": dict(response.headers),
        "response": body,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"[{test_name}] {method} {url} -> {response.status_code} ({elapsed:.2f}s)")
    return record


def request(method, path, test_name, json_body=None, headers=None, base=BASE_URL):
    """Make an HTTP request and log it. Returns the log record dict, or None on
    a hard network failure (logged separately so the run can continue)."""
    url = f"{base}{path}"
    start = time.time()
    try:
        resp = requests.request(method, url, headers=headers or HEADERS, json=json_body, timeout=60)
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start
        print(f"[{test_name}] {method} {url} -> NETWORK ERROR: {e}")
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps({
                "test": test_name, "method": method, "url": url,
                "payload": json_body, "status_code": None,
                "elapsed_seconds": round(elapsed, 3), "error": str(e),
            }) + "\n")
        return None
    elapsed = time.time() - start
    return log_result(test_name, method, url, json_body, resp, elapsed)


def safe_run(test_fn, *args, **kwargs):
    """Run a test function; on any exception, print the traceback and continue
    rather than aborting the whole suite."""
    try:
        test_fn(*args, **kwargs)
    except Exception:
        print(f"\n!!! Test {test_fn.__name__} raised an exception — continuing anyway !!!")
        traceback.print_exc()
        print()


def poll_status(activity_id, test_name, max_wait=120, interval=3):
    """Poll GET /status/{activity_id} until succeeded/completed/failed or timeout."""
    elapsed_total = 0
    while elapsed_total < max_wait:
        record = request("GET", f"/status/{activity_id}", f"{test_name}_poll")
        if record is None:
            return None
        status = (
            record["response"].get("data", {}).get("status")
            if isinstance(record["response"], dict)
            else None
        )
        if status and status.lower() in ("succeeded", "completed", "failed"):
            return record
        time.sleep(interval)
        elapsed_total += interval
    print(f"[{test_name}] Timed out waiting for completion")
    return None


# ---------------------------------------------------------------------------
# Section 0: OpenAPI / interactive docs discovery (no API key required)
# ---------------------------------------------------------------------------

def test_openapi_discovery():
    """Check whether FastAPI's auto-generated OpenAPI spec / Swagger UI is
    publicly exposed. These don't need an API key."""
    for path in ["/openapi.json", "/docs", "/redoc"]:
        request("GET", path, f"openapi_discovery{path.replace('/', '_')}", base=ROOT_URL)


# ---------------------------------------------------------------------------
# Section 1: Functional happy-path tests
# ---------------------------------------------------------------------------

def test_heatmap_happy_path():
    """NOTE: this endpoint 500'd on every call in the previous run. Kept here
    as a single confirmation check, not repeated — see test_heatmap_repeat_check
    below if you want to re-verify it's still broken."""
    payload = {
        "polygon_aoi": VALID_POLYGON,
        "date_time": VALID_DATE_TIME,
        "granularity": 100,
    }
    record = request("POST", "/heatmap", "heatmap_happy_path", payload)
    if record and isinstance(record["response"], dict):
        activity_id = record["response"].get("data", {}).get("activity_id")
        if activity_id:
            poll_status(activity_id, "heatmap_happy_path")


def test_heatmap_repeat_check(n=2):
    """Small repeat to confirm whether the 500 bug is still present, without
    burning a full 5-10 calls like the original latency/concurrency tests did."""
    payload = {
        "polygon_aoi": VALID_POLYGON,
        "date_time": VALID_DATE_TIME,
        "granularity": 100,
    }
    for i in range(n):
        request("POST", "/heatmap", f"heatmap_repeat_check_{i}", payload)


def test_satellite_happy_path():
    payload = {
        "sat": {"latitude": 41.84632807720175, "longitude": -87.74329628220852},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
    }
    record = request("POST", "/satellite", "satellite_happy_path", payload)
    if record and isinstance(record["response"], dict):
        activity_id = record["response"].get("data", {}).get("activity_id")
        if activity_id:
            poll_status(activity_id, "satellite_happy_path")


def test_env_params_basic_limit():
    """Using the FIXED flat schema. If this still 422s, print the response
    detail and adjust ENV_PARAMS_PAYLOAD_3 / _4 above accordingly."""
    request("POST", "/env_params", "env_params_3_fixed_schema", ENV_PARAMS_PAYLOAD_3)
    request("POST", "/env_params", "env_params_4_fixed_schema", ENV_PARAMS_PAYLOAD_4)


def test_heat_intelligence_happy_path():
    payload = dict(HEAT_INTEL_PAYLOAD_BASE)
    payload["analysis"] = ["geographic", "environmental"]
    request("POST", "/heat_intelligence", "heat_intelligence_fixed_schema", payload)


# ---------------------------------------------------------------------------
# Section 2: Validation / error-handling matrix
# ---------------------------------------------------------------------------

def test_validation_matrix():
    # Missing API key
    bad_headers = {"Content-Type": "application/json"}
    request("POST", "/heatmap", "missing_api_key",
            {"polygon_aoi": VALID_POLYGON, "date_time": VALID_DATE_TIME, "granularity": 100},
            headers=bad_headers)

    # Invalid latitude / longitude
    request("POST", "/satellite", "invalid_latitude_200",
            {"sat": {"latitude": 200, "longitude": -87.74},
             "date_time": VALID_DATE_TIME, "granularity": 80})

    request("POST", "/satellite", "invalid_longitude_-200",
            {"sat": {"latitude": 41.84, "longitude": -200},
             "date_time": VALID_DATE_TIME, "granularity": 80})

    # Non-closed polygon (first != last coordinate)
    bad_polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-74.0060, 40.7128],
            [-74.0050, 40.7128],
            [-74.0050, 40.7138],
            [-74.0040, 40.7148],
        ]],
    }
    request("POST", "/heatmap", "polygon_not_closed",
            {"polygon_aoi": bad_polygon, "date_time": VALID_DATE_TIME, "granularity": 100})

    # Invalid granularity / filter_type
    request("POST", "/heatmap", "invalid_granularity_75",
            {"polygon_aoi": VALID_POLYGON, "date_time": VALID_DATE_TIME, "granularity": 75})

    bad_filter = dict(VALID_DATE_TIME)
    bad_filter["filter_type"] = 4
    request("POST", "/heatmap", "invalid_filter_type_4",
            {"polygon_aoi": VALID_POLYGON, "date_time": bad_filter, "granularity": 100})

    # Malformed date
    bad_date = dict(VALID_DATE_TIME)
    bad_date["start_date"] = "07-15-2024"
    request("POST", "/heatmap", "malformed_date_format",
            {"polygon_aoi": VALID_POLYGON, "date_time": bad_date, "granularity": 100})

    # filter_type=2 spanning across two days (already confirmed rejected last run)
    over_range = {
        "start_date": "2024-07-15", "start_time": "00:00",
        "end_time": "23:59", "filter_type": 2, "end_date": "2024-07-16",
    }
    request("POST", "/heatmap", "filter_type2_over_23h",
            {"polygon_aoi": VALID_POLYGON, "date_time": over_range, "granularity": 100})

    # Non-US coordinates (Paris) — confirm again whether geofence is enforced
    request("POST", "/satellite", "non_us_coordinates_recheck",
            {"sat": {"latitude": 48.8566, "longitude": 2.3522},
             "date_time": VALID_DATE_TIME, "granularity": 80})

    # Garbage activity_id — confirm 403 vs 404 behavior again
    request("GET", "/status/not-a-real-id", "garbage_activity_id_recheck")

    # heat_intelligence: empty / invalid analysis array, using FIXED schema
    empty_analysis = dict(HEAT_INTEL_PAYLOAD_BASE)
    empty_analysis["analysis"] = []
    request("POST", "/heat_intelligence", "empty_analysis_array_fixed", empty_analysis)

    invalid_analysis = dict(HEAT_INTEL_PAYLOAD_BASE)
    invalid_analysis["analysis"] = ["weather"]
    request("POST", "/heat_intelligence", "invalid_analysis_category_fixed", invalid_analysis)

    # Injection-string robustness check (not an attack, just input sanitization check)
    injection_payload = {
        "sat": {"latitude": 41.84, "longitude": -87.74},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
        "label": "'; DROP TABLE activities; --",
    }
    request("POST", "/satellite", "injection_string_field", injection_payload)


# ---------------------------------------------------------------------------
# Section 3: Performance / concurrency (reduced defaults to save time/credits)
# ---------------------------------------------------------------------------

def test_latency_distribution(n=3):
    """Uses /satellite (known working) instead of /heatmap (known broken) so
    this actually measures real latency rather than just 500-error round-trips."""
    latencies = []
    for i in range(n):
        payload = {
            "sat": {"latitude": 41.84632807720175, "longitude": -87.74329628220852},
            "date_time": VALID_DATE_TIME,
            "granularity": 80,
        }
        record = request("POST", "/satellite", f"latency_run_{i}", payload)
        if record:
            latencies.append(record["elapsed_seconds"])
    if latencies:
        print(f"\nLatency over {len(latencies)} runs (satellite) — min: {min(latencies):.2f}s, "
              f"median: {statistics.median(latencies):.2f}s, max: {max(latencies):.2f}s")


def test_concurrent_requests(n=3):
    """Also switched to /satellite since /heatmap is known broken — concurrency
    behavior on a working endpoint is the more informative test."""
    payload = {
        "sat": {"latitude": 41.84632807720175, "longitude": -87.74329628220852},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
    }

    def submit(i):
        return request("POST", "/satellite", f"concurrent_{i}", payload)

    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(submit, i) for i in range(n)]
        results = [f.result() for f in as_completed(futures)]

    statuses = [r["status_code"] for r in results if r]
    print(f"\nConcurrent submission status codes (satellite): {statuses}")


# ---------------------------------------------------------------------------
# Run everything
# ---------------------------------------------------------------------------

def print_summary():
    """Read back the log file and print a quick sanity-check summary so you
    don't have to manually scan results_v2.jsonl right away."""
    if not os.path.exists(LOG_FILE):
        print("No log file found.")
        return

    with open(LOG_FILE) as f:
        records = [json.loads(line) for line in f if line.strip()]

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    heatmap_calls = [r for r in records if "heatmap" in r["test"] and r.get("status_code")]
    heatmap_500s = [r for r in heatmap_calls if r["status_code"] == 500]
    if heatmap_calls:
        print(f"Heatmap calls: {len(heatmap_calls)} total, {len(heatmap_500s)} returned 500 "
              f"({'STILL BROKEN' if len(heatmap_500s) == len(heatmap_calls) else 'partially working'})")

    rate_limit_headers_found = []
    for r in records:
        headers = r.get("response_headers", {})
        for h in headers:
            if "ratelimit" in h.lower() or "credit" in h.lower() or "retry-after" in h.lower():
                rate_limit_headers_found.append(h)
    if rate_limit_headers_found:
        print(f"Rate-limit/credit headers found: {set(rate_limit_headers_found)}")
    else:
        print("Rate-limit/credit headers found: NONE across any request")

    openapi_checks = [r for r in records if "openapi_discovery" in r["test"]]
    for r in openapi_checks:
        print(f"  {r['url']} -> {r['status_code']}")

    error_count = sum(1 for r in records if r.get("status_code") is None)
    if error_count:
        print(f"\nNetwork-level errors during run: {error_count} (see log for details)")

    print(f"\nFull details in: {LOG_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    open(LOG_FILE, "w").close()  # fresh log each run

    print("=== Section 0: OpenAPI / docs discovery ===")
    safe_run(test_openapi_discovery)

    print("\n=== Section 1: Functional happy-path tests ===")
    safe_run(test_heatmap_happy_path)
    safe_run(test_heatmap_repeat_check, n=2)
    safe_run(test_satellite_happy_path)
    safe_run(test_env_params_basic_limit)
    safe_run(test_heat_intelligence_happy_path)

    print("\n=== Section 2: Validation / error-handling matrix ===")
    safe_run(test_validation_matrix)

    print("\n=== Section 3: Performance checks ===")
    safe_run(test_latency_distribution, n=3)
    safe_run(test_concurrent_requests, n=3)

    print_summary()