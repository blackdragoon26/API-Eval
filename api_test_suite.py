"""
FortyGuard API Test Suite
==========================
Run this yourself with your own API key set as an environment variable.
Never hardcode your key in this file or paste it anywhere you don't control.

Usage:
    export FORTYGUARD_API_KEY="your_key_here"
    python api_test_suite.py

This script logs every request/response pair to results.jsonl so you have
a clean evidence trail for your feedback write-up (Section 3 of the plan).
"""

import os
import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = "https://api.fortyguard.com/v1"
API_KEY = os.environ.get("FORTYGUARD_API_KEY")
LOG_FILE = "results.jsonl"

if not API_KEY:
    raise SystemExit(
        "Set FORTYGUARD_API_KEY as an environment variable before running this script."
    )

HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}

# A small, valid NYC polygon for happy-path tests (~well under 1 mi^2)
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


def log_result(test_name, method, url, payload, response, elapsed):
    """Append a structured record of the request/response to the log file."""
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
        "response": body,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"[{test_name}] {method} {url} -> {response.status_code} ({elapsed:.2f}s)")
    return record


def request(method, path, test_name, json_body=None, headers=None):
    url = f"{BASE_URL}{path}"
    start = time.time()
    resp = requests.request(method, url, headers=headers or HEADERS, json=json_body, timeout=60)
    elapsed = time.time() - start
    return log_result(test_name, method, url, json_body, resp, elapsed)


def poll_status(activity_id, test_name, max_wait=120, interval=3):
    """Poll GET /status/{activity_id} until succeeded/failed or timeout."""
    elapsed_total = 0
    while elapsed_total < max_wait:
        record = request("GET", f"/status/{activity_id}", f"{test_name}_poll")
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
# Section 2: Functional happy-path tests
# ---------------------------------------------------------------------------

def test_heatmap_happy_path():
    payload = {
        "polygon_aoi": VALID_POLYGON,
        "date_time": VALID_DATE_TIME,
        "granularity": 100,
    }
    record = request("POST", "/heatmap", "heatmap_happy_path", payload)
    activity_id = (
        record["response"].get("data", {}).get("activity_id")
        if isinstance(record["response"], dict)
        else None
    )
    if activity_id:
        poll_status(activity_id, "heatmap_happy_path")


def test_satellite_happy_path():
    payload = {
        "sat": {"latitude": 41.84632807720175, "longitude": -87.74329628220852},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
    }
    record = request("POST", "/satellite", "satellite_happy_path", payload)
    activity_id = (
        record["response"].get("data", {}).get("activity_id")
        if isinstance(record["response"], dict)
        else None
    )
    if activity_id:
        poll_status(activity_id, "satellite_happy_path")


def test_env_params_basic_limit():
    # 3 params -> should succeed on Basic; adjust param names once confirmed from docs/dashboard
    payload = {
        "location": {"latitude": 40.7128, "longitude": -74.0060},
        "date_time": VALID_DATE_TIME,
        "parameters": ["heat_index", "humidity", "aqi_pm25"],
    }
    request("POST", "/env_params", "env_params_3_basic", payload)

    # 4 params -> should be rejected on Basic plan
    payload_4 = dict(payload)
    payload_4["parameters"] = ["heat_index", "humidity", "aqi_pm25", "co2"]
    request("POST", "/env_params", "env_params_4_should_fail_on_basic", payload_4)


# ---------------------------------------------------------------------------
# Section 3: Validation / error-handling matrix
# ---------------------------------------------------------------------------

def test_validation_matrix():
    # Missing API key
    bad_headers = {"Content-Type": "application/json"}
    request("POST", "/heatmap", "missing_api_key",
            {"polygon_aoi": VALID_POLYGON, "date_time": VALID_DATE_TIME, "granularity": 100},
            headers=bad_headers)

    # Invalid latitude
    bad_lat_payload = {
        "sat": {"latitude": 200, "longitude": -87.74},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
    }
    request("POST", "/satellite", "invalid_latitude_200", bad_lat_payload)

    # Invalid longitude
    bad_lng_payload = {
        "sat": {"latitude": 41.84, "longitude": -200},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
    }
    request("POST", "/satellite", "invalid_longitude_-200", bad_lng_payload)

    # Non-closed polygon (first != last coordinate)
    bad_polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-74.0060, 40.7128],
            [-74.0050, 40.7128],
            [-74.0050, 40.7138],
            [-74.0040, 40.7148],  # not closing back to start
        ]],
    }
    request("POST", "/heatmap", "polygon_not_closed",
            {"polygon_aoi": bad_polygon, "date_time": VALID_DATE_TIME, "granularity": 100})

    # Invalid granularity
    request("POST", "/heatmap", "invalid_granularity_75",
            {"polygon_aoi": VALID_POLYGON, "date_time": VALID_DATE_TIME, "granularity": 75})

    # Invalid filter_type
    bad_filter = dict(VALID_DATE_TIME)
    bad_filter["filter_type"] = 4
    request("POST", "/heatmap", "invalid_filter_type_4",
            {"polygon_aoi": VALID_POLYGON, "date_time": bad_filter, "granularity": 100})

    # Malformed date
    bad_date = dict(VALID_DATE_TIME)
    bad_date["start_date"] = "07-15-2024"
    request("POST", "/heatmap", "malformed_date_format",
            {"polygon_aoi": VALID_POLYGON, "date_time": bad_date, "granularity": 100})

    # filter_type=2 range over 23 hours
    over_range = {
        "start_date": "2024-07-15",
        "start_time": "00:00",
        "end_time": "23:59",
        "filter_type": 2,
    }
    # Push past 23h by spanning into a second day's worth via end_date if accepted
    over_range_2 = dict(over_range)
    over_range_2["end_date"] = "2024-07-16"
    request("POST", "/heatmap", "filter_type2_over_23h",
            {"polygon_aoi": VALID_POLYGON, "date_time": over_range_2, "granularity": 100})

    # Non-US coordinates (e.g. somewhere in France)
    non_us_payload = {
        "sat": {"latitude": 48.8566, "longitude": 2.3522},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
    }
    request("POST", "/satellite", "non_us_coordinates", non_us_payload)

    # Garbage activity_id
    request("GET", "/status/not-a-real-id", "garbage_activity_id")

    # Empty heat_intelligence analysis array
    request("POST", "/heat_intelligence", "empty_analysis_array",
            {"location": {"latitude": 40.7128, "longitude": -74.0060},
             "date_time": VALID_DATE_TIME, "analysis": []})

    # Invalid analysis category
    request("POST", "/heat_intelligence", "invalid_analysis_category",
            {"location": {"latitude": 40.7128, "longitude": -74.0060},
             "date_time": VALID_DATE_TIME, "analysis": ["weather"]})

    # Basic injection-string robustness check (not an attack, just input sanitization check)
    injection_payload = {
        "sat": {"latitude": 41.84, "longitude": -87.74},
        "date_time": VALID_DATE_TIME,
        "granularity": 80,
        "label": "'; DROP TABLE activities; --",
    }
    request("POST", "/satellite", "injection_string_field", injection_payload)


# ---------------------------------------------------------------------------
# Section 4: Performance / concurrency
# ---------------------------------------------------------------------------

def test_latency_distribution(n=10):
    latencies = []
    for i in range(n):
        payload = {
            "polygon_aoi": VALID_POLYGON,
            "date_time": VALID_DATE_TIME,
            "granularity": 100,
        }
        record = request("POST", "/heatmap", f"latency_run_{i}", payload)
        latencies.append(record["elapsed_seconds"])
    print(f"\nLatency over {n} runs — min: {min(latencies):.2f}s, "
          f"median: {statistics.median(latencies):.2f}s, max: {max(latencies):.2f}s")


def test_concurrent_requests(n=5):
    payload = {
        "polygon_aoi": VALID_POLYGON,
        "date_time": VALID_DATE_TIME,
        "granularity": 100,
    }

    def submit(i):
        return request("POST", "/heatmap", f"concurrent_{i}", payload)

    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(submit, i) for i in range(n)]
        results = [f.result() for f in as_completed(futures)]

    statuses = [r["status_code"] for r in results]
    print(f"\nConcurrent submission status codes: {statuses}")


# ---------------------------------------------------------------------------
# Run everything
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    open(LOG_FILE, "w").close()  # fresh log each run

    print("=== Functional happy-path tests ===")
    test_heatmap_happy_path()
    test_satellite_happy_path()
    test_env_params_basic_limit()

    print("\n=== Validation / error-handling matrix ===")
    test_validation_matrix()

    print("\n=== Performance checks ===")
    test_latency_distribution(n=5)  # lower n by default to conserve credits; raise if you have budget
    test_concurrent_requests(n=5)

    print(f"\nAll requests logged to {LOG_FILE}. Review it to fill in the Section 3 table.")
