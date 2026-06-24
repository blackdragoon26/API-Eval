# FortyGuard Products Evaluation Report

**Candidate:** Sankalp Jha  
**Position:** DevSecOps and Network Architect  
**Evaluation date:** June 24, 2026  
**Repository:** github.com/blackdragoon26/API-Eval  
**Scope:** FortyGuard Temperature Dashboard(R), Temperature API(R), API documentation, and bounded live API probes

## Executive Summary

FortyGuard has a compelling core product direction: hyperlocal temperature intelligence, asynchronous geospatial processing, a modern dashboard surface, and a developer-friendly credit model where failed tasks are not charged. The API shape is also broadly sensible for heavy spatial workloads: submit a job, receive an `activity_id`, then poll a status endpoint for completion.

The main gaps are not conceptual. They are reliability, validation, and operational developer experience. In live testing on June 24, 2026, a valid `POST /v1/heatmap` request still returned `500 Internal Server Error`, and the same endpoint also returned `500` for an invalid unclosed polygon that should be rejected at the validation layer. The API exposes a useful OpenAPI 3.1 schema at `/openapi.json`, but that schema is not surfaced as an interactive first-class documentation experience in the main docs portal. The docs also contain several mismatches with live behavior, especially around credits usage, environmental parameter customization, response status codes, and documented limits.

The dashboard login experience is polished and responsive, but `/map` redirected to `/login` in a fresh browser session, so a new unauthenticated evaluator cannot inspect the map workflow without dashboard credentials or an existing session. The login page itself presents a clean map-backed first impression, but deeper map usability claims should be treated as previously observed feedback rather than freshly verified in this run.

## Methodology

I used three evidence sources:

1. A bounded Python API probe using the provided evaluation API key, with the key redacted from stored output.
2. Rendered documentation review using Playwright screenshots and text extraction.
3. Visual inspection of dashboard routes at desktop and mobile viewport sizes.

I intentionally avoided destructive or high-volume testing. I did not run a rate-limit flood, credential attacks, or any test intended to degrade the service. The probe focused on normal request paths, validation behavior, status polling, docs accuracy, and operational headers.

Evidence artifacts:

- `evidence/api_probe_2026-06-24.jsonl`
- `evidence/visual_audit_2026-06-24.json`
- `evidence/docs_pages_2026-06-24.json`
- `evidence/limitations_full_text_2026-06-24.txt`
- `evidence/screenshots/`

## What Works Well

1. **Strong async API pattern:** Returning an `activity_id` for heavy geospatial tasks is the right shape. It prevents clients from holding long HTTP connections while expensive spatial or imagery work runs.

2. **Clear core domain value:** The docs communicate a strong product thesis around Large Temperature Models, city-scale heat intelligence, satellite/street imagery segmentation, and environmental parameters.

3. **Credit-on-success model:** The docs state that failed tasks are not charged. This is the right billing posture for an async API, especially while workloads are compute-heavy and can fail for reasons outside the client's control.

4. **OpenAPI availability:** `https://api.fortyguard.com/openapi.json` returns an OpenAPI 3.1.0 schema. This is valuable for SDK generation, Postman import, validation, and automated API testing.

5. **Dashboard login presentation:** The Temperature Dashboard login screen is visually polished, works at both desktop and mobile widths, and makes the product category immediately clear through the map-backed design.

## Key Findings

### 1. Heatmap endpoint reliability is currently blocking the primary workflow

**Evidence:** In the live probe, a valid heatmap submission returned:

```text
POST https://api.fortyguard.com/v1/heatmap -> 500
{"error": true, "message": "Internal server error occurred"}
```

This is the most important issue because heatmap generation appears to be one of the flagship API workflows. If the happy path is failing, it undermines developer trust even if adjacent endpoints work.

**Recommendation:** Treat this as a P0. Add regression tests for a minimal valid polygon, known-good time range, all supported granularities, and both Basic/Premium area limits.

### 2. Geometry validation errors escape as 500s

**Evidence:** An unclosed polygon also returned `500 Internal Server Error`.

Expected behavior is a client-side validation error such as `400 Bad Request` or `422 Unprocessable Entity`, with a specific message like `polygon must be closed`.

**Recommendation:** Validate GeoJSON shape before enqueueing the job. Return a structured error envelope with a stable machine-readable code, for example:

```json
{
  "error": {
    "code": "invalid_polygon",
    "message": "Polygon ring must be closed: first and last coordinates must match.",
    "doc_url": "https://docs-api.fortyguard.com/docs/create-heatmap"
  }
}
```

### 3. Error codes are inconsistent with docs and REST expectations

Examples:

| Test case | Expected | Actual | Notes |
|---|---:|---:|---|
| Missing `api-key` header | 401 or 403 | 401 | Good, clear message. |
| Invalid latitude `200` | 400 per docs, or 422 | 422 | Technically acceptable, but docs say 400. |
| Invalid granularity `75` | 400 per docs, or 422 | 422 | Useful validation detail, but docs mismatch. |
| Malformed date `07-15-2024` | 400 per docs, or 422 | 422 | Useful validation detail, but docs mismatch. |
| Unclosed polygon | 400/422 | 500 | Server-side bug. |
| Unknown `activity_id` | 404 | 403 | Looks like auth failure instead of missing resource. |

**Recommendation:** Standardize the error model and document it. The current mix of custom `error/details` objects and FastAPI `detail` validation arrays is workable internally but uneven for external developers.

### 4. Operational headers are missing

Across the live probe, responses did not include:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `Retry-After`
- `X-Credits-Remaining`
- `X-Request-Id` or equivalent correlation header

This matters because FortyGuard uses credit-based billing and async processing. Developers should not need a separate usage call after every operation just to understand remaining quota.

**Recommendation:** Add lightweight operational headers to all authenticated responses. At minimum, return remaining cycle credits, request ID, and rate-limit state. Return `Retry-After` with any `429 Too Many Requests` response.

### 5. Credits usage docs do not match the actual API shape

The docs sidebar labels "Check API Credits Usage" as `GET`, and the page presents a form. The OpenAPI schema and live probe show the underlying endpoint is:

```text
POST /v1/system/fetch-api-key-usage
Body: {"api_key": "..."}
```

The endpoint works and returns useful plan/credit/activity data, but this should be documented as a normal HTTP endpoint with request/response schema, not only as a UI form.

**Recommendation:** Add a raw cURL/Python/JavaScript example for credit usage, and reconcile the sidebar method label with the actual POST endpoint.

### 6. Environmental parameter customization is unclear

The docs state that Basic allows "up to 3 customizable environmental parameters per request" and Premium gives full access. However, the live OpenAPI schema for `EnvParamsRequest` requires only:

```text
latitude, longitude, temperature, date_time
```

It does not expose a `parameters` selector. A doc-style request with a `parameters` array was rejected with `422` because the expected top-level fields were missing.

**Recommendation:** If parameter selection is supported, expose it in the OpenAPI schema. If the endpoint always returns a fixed set, update the docs to remove "customizable" wording or explain plan-level filtering clearly.

### 7. The API exposes useful OpenAPI/ReDoc assets but not as an integrated DX path

`/openapi.json` is public and useful. `/redoc` exists, while `/docs` returns `404`. The main docs site is visually clean and includes code examples, but it does not provide an in-page "Try it" workflow with the user's API key.

**Recommendation:** Link the OpenAPI spec from the docs navigation, provide a Postman import button, and consider an authenticated "Try it" panel for safe endpoints. This would reduce time-to-first-successful-call.

### 8. Dashboard map route is auth-gated in a fresh browser session

Directly visiting `https://dashboard.fortyguard.com/map` redirected to `https://dashboard.fortyguard.com/login` on both desktop and mobile. The login page is responsive and polished, but a fresh evaluator cannot inspect the map workflow without dashboard credentials.

**Recommendation:** For hiring/evaluation flows, include either dashboard credentials in the access email or a dedicated demo mode. If `/map` is intentionally protected, the redirect is correct, but the candidate journey should make the required login path unambiguous.

## Dashboard UX Notes

Fresh-session visual checks:

- Desktop login screenshot: `evidence/screenshots/dashboard_map_desktop.png`
- Mobile login screenshot: `evidence/screenshots/dashboard_map_mobile.png`

Observed strengths:

- Strong first-viewport brand presence.
- Map-backed background communicates the product domain quickly.
- Mobile layout remains readable and centered.
- Standard login options are present: email/password, forgot password, Google sign-in, sign-up.

Limitations of this run:

- I could not verify authenticated map controls, heatmap creation, data export, dashboard performance, or time-slider behavior because dashboard credentials were not available in the workspace.
- The final dashboard feedback should therefore distinguish between the visually verified login experience and previously observed in-dashboard behavior.

## Documentation Audit

High-value documentation improvements:

1. **Expose the raw HTTP schema for credits usage.** The current docs show a form but not the actual `POST /v1/system/fetch-api-key-usage` shape.

2. **Clarify plan credits for evaluation/free keys.** The docs list Premium as 5,000,000 monthly credits, while the live evaluation key returned Premium access with 1,000,000 available credits. That may be correct for a one-time/evaluation key, but the distinction should be explicit.

3. **Document rate limits with real values.** Release notes mention rate limits, but the Known Limitations page did not contain `429`, `Retry-After`, or concrete request limits in the captured full text.

4. **Standardize status values.** Docs and live responses use capitalized `Processing` and `Completed`, while client examples lower-case values before comparison. That is fine as defensive client code, but the canonical API enum should be stated once.

5. **Fix spelling in the satellite schema.** The satellite docs and result use `orignal_image`; this should be `original_image`. If backwards compatibility matters, keep both temporarily and deprecate the misspelled key.

6. **Add polling guidance.** Recommend initial delay, polling interval, exponential backoff, max wait, timeout behavior, and whether polling itself is rate-limited or charged.

7. **Add units everywhere.** Heat Intelligence and Environmental Parameters do mention some Celsius units, but all returned environmental and solar fields should consistently document units and sentinel values.

## API Design Recommendations

1. **Add webhook callbacks for async jobs.** Polling is acceptable for quickstarts, but production integrations need a `webhook_url` callback with signed events for completed/failed tasks.

2. **Add task cancellation.** A `DELETE /v1/status/{activity_id}` or `POST /v1/tasks/{activity_id}/cancel` endpoint would let developers stop stuck or accidental jobs.

3. **Add idempotency keys.** Async POST endpoints should support an `Idempotency-Key` header so retries do not create duplicate billable tasks.

4. **Add batch submission.** Batch heatmaps or multi-point environmental requests would reduce client overhead for enterprise workloads.

5. **Add standard error envelopes.** Use stable `code`, human `message`, `request_id`, and optional `doc_url`.

6. **Return operational headers.** Credits, rate limits, request ID, cache hints where applicable, and `Retry-After`.

7. **Document caching behavior.** For historical or slow-changing temperature data, `Cache-Control` and `ETag` guidance would help clients reduce cost and API load.

## Suggested Ratings

| Area | Suggested rating | Rationale |
|---|---:|---|
| Dashboard usability | 6/10 | Polished login and clear product branding, but authenticated map workflow could not be freshly verified and prior first-run observations suggest onboarding gaps. |
| API | 5/10 | Strong async architecture and useful OpenAPI schema, but the primary heatmap happy path returning 500 is a serious reliability issue. |
| Overall experience | 6/10 | Strong product potential and good foundations, but reliability, docs accuracy, and operational transparency need tightening before production-grade developer trust. |

## Final Takeaway

FortyGuard feels like a technically ambitious platform with a real product thesis. The improvements that would most increase trust are not cosmetic: fix the heatmap happy path, validate geospatial inputs before job submission, standardize the error model, expose rate/credit telemetry in headers, and turn the hidden OpenAPI schema into a first-class developer experience. Once those are addressed, the product will feel much more enterprise-ready.
