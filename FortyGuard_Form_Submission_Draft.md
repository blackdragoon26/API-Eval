# FortyGuard Google Form Submission Draft

## Full Name

Sankalp Jha

## Email Address

sankalp.jha9643@gmail.com

## Position Applied For

DevSecOps and Network Architect

## How much time did you spend reviewing the dashboard?

More than 30 minutes

## What was your first impression of the dashboard?

The product direction is strong. FortyGuard is not just exposing generic weather data; it is packaging hyperlocal temperature intelligence, heatmaps, imagery segmentation, environmental parameters, and reports into one operational platform. The dashboard/login experience also feels polished and visually aligned with a map-based climate-tech product.

For the API specifically, my first impression improved after testing with the exact `FeatureCollection` shape used in the docs. The main async endpoints do submit and complete. The bigger concern is validation and operational trust: malformed geospatial input can still be accepted as a successful heatmap job, and the API does not expose enough rate-limit, request-id, retry, or remaining-credit telemetry in response headers.

## What did you like most?

The async `activity_id` model is the strongest part of the API design. It is the right architecture for heavy workloads like heatmap generation, satellite segmentation, street-view segmentation, and report generation.

I also liked that the core endpoint set is coherent. In my final endpoint audit, documented requests for Heatmap, Satellite View Segmentation, Street View Segmentation, and Environmental Parameters all completed successfully. The OpenAPI 3.1 schema at `/openapi.json` is also a major plus because it can support Postman import, SDK generation, schema validation, and automated testing.

## What did you dislike most? (This is important)

The biggest issue is validation before billing. A valid documented heatmap request completed successfully, but an intentionally unclosed polygon was also accepted, completed, and appeared in credit usage as a Heatmap Generation task. Invalid geometry should be rejected before job creation and should not consume credits.

The second issue is operational transparency. For a credit-based async API, every authenticated response should ideally include a request/correlation ID, rate-limit state, retry guidance where relevant, and remaining-credit information. Right now developers need to call a separate credits endpoint to understand usage state.

## Did you encounter any bugs, issues, or confusing behavior?

Yes. Main findings from my endpoint audit:

- `POST /v1/heatmap` with the documented `FeatureCollection` shape works and completes.
- However, `POST /v1/heatmap` with an unclosed polygon also returned `200`, completed, and was counted under Heatmap Generation credits. This should be a `400` or `422` validation error with no credit charge.
- A raw GeoJSON `Polygon` payload, which is a plausible interpretation of "GeoJSON polygon," returned `500` in earlier probing. The docs should clearly require `FeatureCollection`, or the API should support both shapes safely.
- `GET /v1/status/not-a-real-id` returned `403 Unauthorized access`; for a valid API key and nonexistent activity, `404 Not Found` or a clearer ownership/not-found message would be better.
- No standard rate-limit, retry, request-id, or remaining-credit headers were observed.
- The Credits Usage page is labeled as `GET`/form-style in the docs, but the actual API is `POST /v1/system/fetch-api-key-usage` with an `api_key` JSON body.
- Environmental Parameters are described as customizable, but the OpenAPI request schema does not expose a `parameters` selector. A request using a `parameters` array returned `422`.
- Environmental output field names and sentinel values need clearer documentation, for example `air_quality:idx`, `air_quality_pm2p5:idx`, and `-999` values.
- Satellite results use `orignal_image`, while Street View uses `original_image`. This typo should be corrected with backward compatibility.

## If you were responsible for improving this dashboard, what would be your top 3 recommendations?

1. Add a guided first-run workflow from dashboard to API. Let users create their first heatmap, see the equivalent API request, and understand the resulting `activity_id`, status, credits, and output layers.

2. Add stronger job transparency in the dashboard. Every analysis should show validation status, submitted geometry, job state, expected wait time, credit impact, and final output/export actions.

3. Add direct export and developer handoff. Let users export CSV/GeoJSON/PDF and copy the exact API request used to reproduce the dashboard result.

## Rate the dashboard usability

6

## Rate the API

7

## Did you identify any API design issues or missing endpoints?

Yes.

- Missing webhook/callback support for long-running async jobs.
- Missing task cancellation endpoint for accidental or stuck jobs.
- Missing idempotency-key support for safe retries on async POST endpoints.
- Missing batch/multi-location endpoints for enterprise workloads.
- Missing operational headers such as request ID, rate-limit state, retry guidance, and remaining credits.
- Unknown activity IDs return `403`, which is ambiguous for clients.
- Heatmap geometry validation should happen before job creation and billing.
- Credits usage exists as an endpoint, but it is not documented as cleanly as the analysis endpoints.

## Upload any supporting files, reports, screenshots, or presentations.

Suggested upload: `output/pdf/FortyGuard_Evaluation_Report.pdf`

## Do you have any improvement for documentation API?

Yes. I would improve the API documentation in these areas:

- Make `/openapi.json` a first-class link and add a Postman import button.
- Add raw HTTP/cURL/Python/JavaScript examples for every endpoint, including credits usage.
- Fix the Credits Usage docs: the actual API is `POST /v1/system/fetch-api-key-usage`, not a simple GET page.
- Clearly define accepted heatmap GeoJSON shape: `FeatureCollection` vs raw `Polygon`.
- Document geometry validation rules and show invalid-geometry examples.
- Document canonical status values and recommended polling interval/backoff.
- Document rate limits, `429`, and `Retry-After`.
- Document all environmental parameter units and sentinel values like `-999`.
- Clarify whether environmental parameters are selectable/customizable; if yes, expose the selector in OpenAPI.
- Fix naming consistency such as `orignal_image` vs `original_image`.
- Include example error envelopes with stable machine-readable error codes.

## Rate the overall experience

7

## Additional comments

Overall, FortyGuard has a strong technical foundation. The main endpoints work when called with the documented request shapes, and the async model is appropriate for the product. The biggest improvements I would prioritize are validation-before-billing, clearer API contracts, better operational headers, and stronger async production features like webhooks, cancellation, and idempotency keys. Those changes would make the platform feel much more enterprise-ready.
