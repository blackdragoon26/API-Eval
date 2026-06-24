# FortyGuard Final API Endpoint Audit

Run date: 2026-06-24
Generated at: 2026-06-24T11:47:07.810381+00:00

This pass focuses on API endpoint behavior and main functionality. It is intentionally bounded and does not perform load testing or destructive testing. The API key is redacted from all evidence.

## Endpoint Results

| Test | Expected | Actual HTTP | Response brief | Notes |
|---|---:|---:|---|---|
| `health` | 200 | 200 | API is healthy | Public health check. |
| `ready` | 200 | 200 | Service is ready | Public readiness check. |
| `openapi_json` | 200 | 200 |  | OpenAPI 3.1 schema available. |
| `swagger_docs_disabled` | 404 | 404 | "Not Found" | FastAPI Swagger UI disabled. |
| `redoc` | 200 | 200 | 
    <!DOCTYPE html>
    <html>
    <head>
    <title>FastAPI - ReDoc</title>
    <!-- needed for adaptive design -->
   | ReDoc shell available, but browser rendering may depend on CDN. |
| `credits_usage_before` | 200 | 200 |  | Credit/plan usage endpoint works but is a POST body API. |
| `missing_api_key` | 401/403 | 401 | {"message": "API key is required in request headers"} | Clear auth validation. |
| `malformed_json` | 400/422 | 422 | [{"type": "json_invalid", "loc": ["body", 16], "msg": "JSON decode error", "input": {}, "ctx": {"error": "Expecting value"}}] | Malformed body validation. |
| `heatmap_docs_featurecollection` | 200 submit or clear 4xx | 200 | Heatmap Submitted Successfully | Docs-style FeatureCollection happy path. |
| `heatmap_unclosed_featurecollection` | 400/422 | 200 | Heatmap Submitted Successfully | Geometry should be rejected before job execution. |
| `heatmap_invalid_granularity` | 400/422 | 422 | [{"type": "literal_error", "loc": ["body", "granularity"], "msg": "Input should be 60, 80 or 100", "input": 75, "ctx": {"expected": "60, 80  | Enum validation. |
| `satellite_submit` | 200 submit | 200 | Satellite Segmentation Submitted Successfully | Premium endpoint happy path. |
| `satellite_invalid_latitude` | 400/422 | 422 | [{"type": "less_than_equal", "loc": ["body", "sat", "latitude"], "msg": "Input should be less than or equal to 90", "input": 200, "ctx": {"l | Coordinate validation. |
| `streetview_submit` | 200 submit | 200 | Street View Segmentation Submitted Successfully | Premium endpoint happy path. |
| `streetview_missing_back_view` | 400/422 | 422 | [{"type": "missing", "loc": ["body", "back_view"], "msg": "Field required", "input": {"latitude": 40.7128, "longitude": -74.006, "vertical_a | Required field validation. |
| `env_params_submit` | 200 submit | 200 | Environment Parameters Analysis Submitted Successfully | OpenAPI-correct schema. |
| `env_params_doc_style_parameters` | 200 or documented 4xx | 422 | [{"type": "missing", "loc": ["body", "latitude"], "msg": "Field required", "input": {"location": {"latitude": 40.7128, "longitude": -74.006} | Docs/customization mismatch check. |
| `heat_intelligence_invalid_category` | 400/422 | 422 | [{"type": "literal_error", "loc": ["body", "analysis", 0], "msg": "Input should be 'geographic', 'environmental', 'urban', 'events' or 'anth | Analysis enum validation. |
| `heat_intelligence_empty_analysis` | 400/422 | 422 | [{"type": "too_short", "loc": ["body", "analysis"], "msg": "List should have at least 1 item after validation, not 0", "input": [], "ctx": { | Array min length validation. |
| `garbage_activity_id` | 404 preferred | 403 | {"message": "Unauthorized access"} | Unknown activity id behavior. |
| `credits_usage_after` | 200 | 200 |  | Allows before/after credit inspection. |

## Operational Headers

Observed quota/retry/request-id headers: None observed.

## Follow-Up Completion Check

After the bounded polling window, I re-checked the already-created activity IDs without submitting new work:

| Source test | Final status | Result summary |
|---|---:|---|
| `heatmap_docs_featurecollection` | Completed | `map_data` FeatureCollection with 180 features; `stats_data` present. |
| `heatmap_unclosed_featurecollection` | Completed | `map_data` FeatureCollection with 157 features; `stats_data` present. |
| `satellite_submit` | Completed | Coordinates, `orignal_image`, image year, segmentation metadata. |
| `streetview_submit` | Completed | Coordinates and front street-view segmentation output. |
| `env_params_submit` | Completed | Metadata, one location, environmental parameter arrays, solar irradiance. |

## Credit Accounting After Completion

Credit usage moved from `69,100` used credits before the final audit to `103,440` after the submitted tasks completed, a delta of `34,340`.

| Activity | Added count | Added credits |
|---|---:|---:|
| Tile Satellite Segmentation | 1 | 14,400 |
| Streetview Segmentation | 1 | 8,600 |
| Heatmap Generation | 2 | 8,440 |
| Environment Parameter Analysis | 1 | 2,900 |

The two heatmap tasks in this run were the valid FeatureCollection and the unclosed polygon. This supports the finding that invalid geometry was processed and charged.

## Evidence

- Raw sanitized JSONL: `evidence/final_api_endpoint_audit_2026-06-24.jsonl`
- Summary: `evidence/final_api_endpoint_summary_2026-06-24.md`
