# FortyGuard Google Form Submission Draft

Use this as the copy/paste version for the form. I kept it direct, technical, and fair: strong product signal, but clear about the issues that matter.

## Full Name

Sankalp Jha

## Email Address

sankalp.jha9643@gmail.com

## Position Applied For

DevSecOps and Network Architect

## How much time did you spend reviewing the dashboard?

More than 30 minutes

## What was your first impression of the dashboard?

The product feels serious and differentiated. It is not just another weather dashboard; it is trying to turn hyperlocal temperature data, satellite/street-level imagery, environmental parameters, and report generation into one operational workflow. The map-first direction makes sense for this type of climate-tech product.

The first-run experience could be clearer, though. As a new evaluator, I could see the product direction, but I still had to infer what the first useful action should be, what layer/result I was looking at, and how dashboard actions map back to API jobs and credits.

## What did you like most?

The async `activity_id` model is the strongest part of the API. Heatmaps, segmentation, environmental analysis, and PDF reports are expensive geo/computation tasks, so submitting a job and polling status is the right shape.

I also liked that the main endpoint set is coherent. In my final audit, documented requests for Heatmap, Satellite View Segmentation, Street View Segmentation, and Environmental Parameters all completed successfully. The hidden OpenAPI spec at `/openapi.json` is useful too because it can support Postman imports, SDK generation, and contract tests.

## What did you dislike most? (This is important)

The biggest issue is the gap between "accepted" and "valid." A documented Heatmap `FeatureCollection` worked, which is good. But an intentionally unclosed polygon was also accepted, completed, and appeared in credit usage as a Heatmap Generation task. Invalid geometry should fail before job creation and should never consume credits.

The second issue is operational visibility. For a credit-based async API, responses should expose request IDs, rate-limit state, retry guidance, and remaining credits. Right now a developer has to make a separate credits call to understand usage state, and support/debugging would be harder without a correlation ID.

## Did you encounter any bugs, issues, or confusing behavior?

Yes. The main findings from my endpoint audit were:

- `POST /v1/heatmap` works with the documented GeoJSON `FeatureCollection` request shape.
- The same heatmap endpoint also accepted an unclosed polygon, completed it, and counted it under Heatmap Generation credits. This should be a `400` or `422` with no charge.
- A raw GeoJSON `Polygon` is an easy mistake to make because the docs use language like "GeoJSON polygon." Earlier probing showed that raw `Polygon` input can return `500`, while `FeatureCollection` works. The contract should be explicit.
- `GET /v1/status/not-a-real-id` returned `403 Unauthorized access`. With a valid API key, a nonexistent activity should be `404 Not Found` or a clearer ownership/not-found response.
- I did not observe `X-RateLimit-*`, `Retry-After`, `X-Credits-Remaining`, `X-Request-Id`, or `X-Correlation-Id` headers.
- The Credits Usage docs look like a `GET`/form-style flow, but the real API is `POST /v1/system/fetch-api-key-usage` with an `api_key` JSON body.
- Environmental Parameters are described as customizable, but the OpenAPI schema does not expose a `parameters` selector. A request using a `parameters` array returned `422`.
- Environmental output needs clearer field documentation, especially units and sentinel values like `-999`.
- Satellite results use `orignal_image`, while Street View uses `original_image`. That typo should be fixed with backward compatibility.

## If you were responsible for improving this dashboard, what would be your top 3 recommendations?

1. Build a guided first heatmap workflow. Give a new user a clear path from drawing/selecting an area to seeing the output, cost, status, and equivalent API request.

2. Add a job transparency panel. Each dashboard analysis should show submitted geometry, validation result, current status, expected wait, credit impact, output summary, and error details if it fails.

3. Add export and developer handoff. Users should be able to export CSV/GeoJSON/PDF and copy the exact API request that produced the result. That would connect the dashboard experience to real implementation work.

## Rate the dashboard usability

6

## Rate the API

7

## Did you identify any API design issues or missing endpoints?

Yes.

- Missing webhook/callback support for long-running jobs.
- Missing task cancellation for accidental or stuck jobs.
- Missing idempotency keys for safe retries on async `POST` endpoints.
- Missing batch/multi-area endpoints for enterprise workloads.
- Missing job history/list endpoint to inspect past activities without storing every `activity_id` client-side.
- Missing operational headers for request ID, rate limit, retry guidance, and remaining credits.
- Heatmap geometry validation should run before job creation and billing.
- Credits usage exists, but it should be documented as a normal API endpoint with request/response examples.

## Upload any supporting files, reports, screenshots, or presentations.

Upload this file:

`output/pdf/FortyGuard_Evaluation_Report.pdf`

If they allow only one file, use the PDF. It includes the endpoint audit summary, strongest findings, and recommendations.

## Do you have any improvement for documentation API?

Yes. I would improve the API docs in these specific ways:

- Link `/openapi.json` directly from the docs and add a Postman import option.
- Add raw HTTP, cURL, Python, and JavaScript examples for every endpoint, including credits usage.
- Fix the Credits Usage documentation. The working API is `POST /v1/system/fetch-api-key-usage`, not a simple `GET` page.
- State the exact accepted Heatmap GeoJSON shape: `FeatureCollection`, raw `Polygon`, or both.
- Add invalid-geometry examples and explain what is rejected before billing.
- Document canonical status values and recommended polling/backoff.
- Document rate limits, `429`, and `Retry-After`.
- Document all Environmental Parameters units and sentinel values such as `-999`.
- Clarify whether environmental parameters are actually selectable/customizable; if yes, expose that selector in OpenAPI.
- Fix naming consistency such as `orignal_image` vs `original_image`.
- Add standard error examples with stable machine-readable codes.

## Rate the overall experience

7

## Additional comments

I liked the core idea and the API direction. The product has a real use case: turning urban heat and environmental context into something teams can query, visualize, and operationalize. The main endpoints work when called with the documented shapes.

The biggest improvements I would prioritize are validation-before-billing, clearer API contracts, operational headers, and better async workflow features like webhooks, cancellation, idempotency, and job history. Those changes would make the platform feel much more reliable for production integrations.
