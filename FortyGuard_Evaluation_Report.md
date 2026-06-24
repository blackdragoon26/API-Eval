# FortyGuard API Evaluation Report

**Candidate:** Sankalp Jha  
**Position:** DevSecOps and Network Architect  
**Evaluation date:** June 24, 2026  
**Repository:** github.com/blackdragoon26/API-Eval  
**Primary focus:** Temperature API(R), endpoint behavior, async task lifecycle, validation, credit accounting, and documentation accuracy

## Executive Summary

The FortyGuard Temperature API has a solid foundation. When requests are shaped exactly like the public documentation, the main async endpoints submit successfully and complete: Heatmap, Satellite View Segmentation, Street View Segmentation, and Environmental Parameters all returned completed results in my final endpoint audit.

The most important issue is not that the core API is unusable. It is that validation and operational transparency are not yet production-grade. A documented Heatmap `FeatureCollection` request completed successfully, but an intentionally unclosed polygon was also accepted, completed, and appeared in credit usage as a Heatmap Generation task. That is a high-trust issue: invalid geometry should be rejected before job creation and should not consume credits.

The second class of issues is developer experience. The API exposes a useful OpenAPI 3.1 schema, but the public docs do not fully align with live behavior. Credits usage is documented as a form/GET-style page while the real API is a POST body endpoint. Environmental Parameters are described as customizable, but the OpenAPI request schema does not expose a parameter selector. Responses also do not include rate-limit, retry, request-id, or remaining-credit headers, which matters for a credit-based async platform.

## Methodology

I ran a bounded API audit on June 24, 2026 using the evaluation key. The key was passed only through an environment variable and is redacted from all stored evidence. The audit intentionally avoided load testing, credential abuse, or destructive behavior.

Evidence files:

- `final_api_endpoint_audit.py`
- `evidence/final_api_endpoint_audit_2026-06-24.jsonl`
- `evidence/final_api_endpoint_summary_2026-06-24.md`
- `evidence/final_status_followup_2026-06-24.jsonl`
- `evidence/credits_usage_post_followup_2026-06-24.json`

## Endpoint Coverage Summary

| Area | Result | Notes |
|---|---:|---|
| `GET /health` | 200 | Public health check works. |
| `GET /ready` | 200 | Public readiness check works. |
| `GET /openapi.json` | 200 | OpenAPI 3.1 schema is available. |
| `GET /docs` | 404 | Swagger UI is disabled. |
| `GET /redoc` | 200 | ReDoc shell exists, but it should be linked from the main docs if intended for developers. |
| `POST /v1/heatmap` valid `FeatureCollection` | 200 -> Completed | Returned `map_data` FeatureCollection with 180 features plus `stats_data`. |
| `POST /v1/heatmap` unclosed polygon | 200 -> Completed | Bug: invalid geometry was accepted and completed. |
| `POST /v1/satellite` valid request | 200 -> Completed | Returned coordinates, image metadata, `orignal_image`, and segmentation. |
| `POST /v1/streetview` valid request | 200 -> Completed | Returned front street-view segmentation result. |
| `POST /v1/env_params` OpenAPI shape | 200 -> Completed | Returned metadata, one location, environmental parameters, and solar irradiance. |
| `POST /v1/heat_intelligence` invalid category | 422 | Enum validation works. |
| `GET /v1/status/not-a-real-id` | 403 | Should be 404 or a clearer resource-not-found response. |
| `POST /v1/system/fetch-api-key-usage` | 200 | Works, but docs label credits usage as GET/form-style. |

## Main Strengths

1. **Async architecture is appropriate.** Returning an `activity_id` and polling `/v1/status/{activity_id}` is the right pattern for heatmaps, segmentation, and report generation.

2. **Core endpoint set is meaningful.** Heatmap, Satellite, Street View, Environmental Parameters, and Heat Intelligence cover a coherent product surface for urban temperature intelligence.

3. **Main happy paths work when request shape matches docs.** The final audit confirmed completed outputs for Heatmap, Satellite, Street View, and Environmental Parameters.

4. **OpenAPI schema exists.** `/openapi.json` is a strong foundation for Postman import, SDK generation, schema testing, and automated contract checks.

5. **Credit usage API is useful.** The usage endpoint returns plan details, credit totals, and activity breakdowns. This is valuable; it just needs to be documented as a normal API endpoint.

## Critical Findings

### 1. Invalid heatmap geometry is accepted, completed, and charged

The docs state that polygons must be closed and that invalid inputs are rejected. In the final audit, this invalid `FeatureCollection` was submitted:

```text
Polygon coordinates: first coordinate != last coordinate
Endpoint: POST /v1/heatmap
Actual: 200 Heatmap Submitted Successfully
Follow-up status: Completed
Result summary: map_data FeatureCollection, 157 features, stats_data present
```

Credit usage after completion showed `Heatmap Generation` with `count: 2` and `credits: 8440`. In this final run, the only heatmap tasks were the valid polygon and the unclosed polygon, so the invalid geometry appears to have consumed heatmap credits.

**Why this matters:** This is a trust and billing issue. A developer can submit malformed geospatial input, receive a successful activity, get a completed result, and lose credits instead of receiving a clear client-side validation error.

**Recommendation:** Add strict GeoJSON validation before job creation:

- Require `FeatureCollection` or document/support both `FeatureCollection` and raw `Polygon`.
- Validate ring closure, minimum points, self-intersection, area limits, and supported region before enqueueing.
- Return `400` or `422` with `code: invalid_polygon`.
- Never charge credits for validation failures.

### 2. GeoJSON request shape is ambiguous

The public docs use `FeatureCollection`, while some language says "GeoJSON polygon". A common developer interpretation is to pass a raw GeoJSON `Polygon`. Earlier bounded probing showed that a raw `Polygon` payload returned a `500 Internal Server Error`, while the documented `FeatureCollection` shape worked.

**Recommendation:** Make the accepted shape explicit in both docs and OpenAPI. If only `FeatureCollection` is supported, enforce that with schema validation and return `422` for raw `Polygon`. If both are intended, normalize both safely.

### 3. Unknown activity IDs return 403 instead of a not-found response

`GET /v1/status/not-a-real-id` returned:

```json
{"error": true, "status_code": 403, "details": {"message": "Unauthorized access"}}
```

For a request authenticated with a valid API key, this reads as an authorization problem, not a missing task. A `404 Not Found` or `403` with a more precise message such as `activity does not belong to this API key` would be clearer.

### 4. Operational headers are missing

Across the final audit, I did not observe standard operational headers such as:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `Retry-After`
- `X-Credits-Remaining`
- `X-Request-Id` or `X-Correlation-Id`

**Why this matters:** Developers integrating a credit-based async API need to know quota state, retry behavior, and support correlation without making a separate credits call after every request.

### 5. Credits usage docs do not match the real API

The docs sidebar labels "Check API Credits Usage" as `GET`, and the page presents a form. The live OpenAPI and audit show the actual API shape:

```text
POST /v1/system/fetch-api-key-usage
Body: {"api_key": "..."}
```

The endpoint works well, but it should be documented with raw HTTP examples and response schema.

### 6. Environmental Parameters documentation/schema mismatch

The docs say Basic supports "up to 3 customizable environmental parameters per request" and Premium supports all parameters. The OpenAPI request schema does not include a `parameters` selector. A doc-style request containing `location` plus a `parameters` array returned `422`, while the OpenAPI shape completed.

The completed result also contains field names that should be documented more carefully, for example:

- `air_quality:idx`
- `air_quality_pm2p5:idx`
- `cloud_cover_octas`
- `co2_ppm: [-999]`

**Recommendation:** Either expose parameter selection in OpenAPI or remove/clarify "customizable" wording. Also document field naming, units, and sentinel values like `-999`.

### 7. Satellite response contains a spelling/API contract issue

The Satellite result uses `orignal_image` rather than `original_image`. Street View uses `original_image`, so the APIs are inconsistent.

**Recommendation:** Add `original_image`, keep `orignal_image` temporarily for backward compatibility, and mark the typo deprecated.

## Credit Accounting Observation

Before the final audit, the key showed `69,100` used credits. After submitted tasks completed, usage showed `103,440` used credits. The delta was `34,340` credits:

| Activity | Added count | Added credits |
|---|---:|---:|
| Tile Satellite Segmentation | 1 | 14,400 |
| Streetview Segmentation | 1 | 8,600 |
| Heatmap Generation | 2 | 8,440 |
| Environment Parameter Analysis | 1 | 2,900 |

The two heatmap tasks were the valid `FeatureCollection` and the unclosed polygon. This supports the finding that invalid geometry was processed and charged.

## Documentation Improvements

1. Add full raw HTTP docs for `POST /v1/system/fetch-api-key-usage` and custom usage.
2. Link `/openapi.json` from the main documentation and add a Postman import button.
3. Document canonical status values and recommended polling intervals/backoff.
4. Align documented status codes with actual `422` validation behavior, or change implementation to match docs.
5. Document rate limits and include `429`/`Retry-After` examples.
6. Clarify accepted GeoJSON shape for heatmaps.
7. Document units and sentinel values for all environmental fields.
8. Fix `orignal_image` naming.
9. Explain evaluation/free-key credit plans separately from normal Basic/Premium plan limits.

## Missing API Capabilities

- **Webhooks/callbacks:** Long-running tasks currently require polling.
- **Task cancellation:** There is no way to cancel accidental or stuck jobs.
- **Idempotency keys:** Safe retry behavior is important for async POST endpoints.
- **Batch endpoints:** Multi-polygon or multi-location workloads require repeated individual submissions.
- **Request correlation:** A response-level request ID would improve support/debuggability.

## Suggested Ratings

| Area | Suggested rating | Rationale |
|---|---:|---|
| API | 7/10 | Main endpoint happy paths work and complete, but validation, billing safeguards, docs accuracy, and operational headers need work. |
| Dashboard usability | 6/10 | Login/entry experience is polished, but authenticated map workflow needs a separate credentialed review. |
| Overall experience | 7/10 | Strong product foundation with clear climate-tech value; the highest-priority fixes are around API trust and developer operations. |

## Final Takeaway

FortyGuard's API is much closer to usable than the first rough probe suggested. The main endpoints work when called with the documented request shapes. The strongest feedback is therefore sharper: tighten validation before billing, make the OpenAPI contract precise, expose operational headers, document credits/rate limits clearly, and add async production features like webhooks, cancellation, and idempotency.
