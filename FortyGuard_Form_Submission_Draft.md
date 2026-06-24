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

The product makes a strong first impression visually. The dashboard login screen is polished, responsive, and immediately communicates a map-based temperature intelligence product. The broader platform concept is also compelling: FortyGuard is clearly trying to turn hyperlocal temperature data into something operationally useful rather than just another weather visualization.

That said, in a fresh browser session, directly opening `/map` redirected me to `/login`, so I could not fully re-check the authenticated map workflow without dashboard credentials. Based on the available experience and prior exploration, I would make the first-run journey more guided so a new evaluator knows exactly how to create the first heatmap, interpret the layers, and move from visual exploration to API-backed analysis.

## What did you like most?

I liked the underlying API architecture the most. The `activity_id` submission and status polling model is a good fit for heavy geospatial and imagery workloads because clients are not forced to hold long-running HTTP requests open. I also liked the credit-on-success model described in the docs. For a compute-heavy API, not charging failed tasks is a trust-building design choice.

Another positive is that the platform exposes an OpenAPI 3.1 schema at `/openapi.json`. That is very useful for Postman import, schema validation, SDK generation, and automated testing. The public docs are also visually clean and easy to scan.

## What did you dislike most? (This is important)

The biggest issue is reliability around the primary heatmap workflow. In my live probe, a valid `POST /v1/heatmap` request returned `500 Internal Server Error`, and an invalid unclosed polygon also returned `500` instead of a clear validation error. For an API whose core value depends on heatmap generation, the happy path failing is a serious blocker.

The second issue is operational transparency. Responses did not include standard rate-limit, retry, request-id, or remaining-credit headers, even though the product is credit-based and asynchronous. Developers currently need a separate credits usage call to understand quota state, and the docs do not give enough guidance on polling intervals, retry behavior, or expected completion windows.

## Did you encounter any bugs, issues, or confusing behavior?

Yes. Key findings from my automated and visual checks:

- `POST /v1/heatmap` returned `500 Internal Server Error` for a valid minimal polygon request.
- `POST /v1/heatmap` with an unclosed polygon also returned `500` instead of a validation response such as `400` or `422`.
- `GET /v1/status/not-a-real-id` returned `403 Forbidden`, which reads like an authorization issue even though the resource simply does not exist. A `404` would be clearer.
- Several validation errors return FastAPI-style `422` responses, while the docs often state `400 Bad Request`. The actual behavior is reasonable in some cases, but the docs and API should agree.
- The "Check API Credits Usage" docs page is labeled as `GET` and presented as a form, but the OpenAPI schema shows the real underlying endpoint as `POST /v1/system/fetch-api-key-usage`.
- The Environmental Parameters docs mention customizable parameters, but the current OpenAPI request schema does not expose a `parameters` selector.
- The satellite result schema uses `orignal_image`, which appears to be a misspelling of `original_image`.
- The Known Limitations page says requests outside current constraints should return clean client errors, but at least one geometry validation issue surfaced as a server error.
- Direct access to `https://dashboard.fortyguard.com/map` redirected to login in a fresh browser session, so evaluation access should make dashboard credentials or demo access very explicit.

## If you were responsible for improving this dashboard, what would be your top 3 recommendations?

1. Fix the first-run workflow and onboarding. Add a guided "Create your first heatmap" flow that explains area selection, date/time selection, layer meaning, and status/result interpretation. The goal should be a successful first map within a few minutes.

2. Make the dashboard more transparent about job state and data lineage. For every submitted analysis, show the `activity_id`, status, expected wait time, credit impact, selected inputs, and any validation issues in plain language.

3. Add direct export and developer handoff actions. Once a heatmap or analysis is visible, let users export CSV/GeoJSON/PDF and copy the equivalent API request. That would connect the dashboard experience to real engineering workflows.

## Rate the dashboard usability

6

## Rate the API

5

## Did you identify any API design issues or missing endpoints?

Yes. The API has a strong async foundation, but several production-grade pieces are missing or inconsistent:

- No webhook/callback option for long-running tasks, so clients must poll `/v1/status/{activity_id}`.
- No task cancellation endpoint for stuck or accidental jobs.
- No idempotency key support for async POST requests, which makes safe retries harder and can create duplicate jobs.
- No batch endpoint for submitting multiple polygons or locations efficiently.
- No standard rate-limit, retry, request-id, or remaining-credit headers.
- Inconsistent status/error behavior across endpoints, including `500` for geometry validation and `403` for unknown activity IDs.
- Credits usage is available through a useful endpoint, but it is not documented in the same raw HTTP style as the main analysis endpoints.

## Upload any supporting files, reports, screenshots, or presentations.

Suggested upload: `output/pdf/FortyGuard_Evaluation_Report.pdf`

## Do you have any improvement for documentation API?

Yes. The docs are visually clean, but I would improve them in these specific ways:

- Promote `/openapi.json` as a first-class resource and add a Postman import button.
- Add an interactive "Try it" experience or at least copy-ready cURL, Python, and JavaScript snippets for every endpoint.
- Align documented status codes with actual behavior (`400` vs `422`, `403` vs `404`, etc.).
- Document recommended polling intervals, exponential backoff, timeout guidance, and whether polling is rate-limited.
- Add standard error envelope examples with stable machine-readable error codes.
- Fix the credits usage page so the raw `POST /v1/system/fetch-api-key-usage` schema is documented.
- Clarify Environmental Parameters customization, because the docs mention customizable parameters but the OpenAPI schema does not show a parameter selector.
- Standardize field names, especially `orignal_image` vs `original_image`.
- Document rate-limit values and response headers. The release notes mention rate limits, but the Known Limitations page did not show concrete `429`, `Retry-After`, or request-limit guidance in my review.
- State units and sentinel values consistently for environmental and solar fields.

## Rate the overall experience

6

## Additional comments

Overall, FortyGuard feels like a strong technical product with a clear climate-tech use case and a good async API foundation. My main recommendation is to focus less on adding new endpoints immediately and more on reliability, validation quality, documentation accuracy, and operational developer experience. If the heatmap happy path is stable, errors are predictable, and developers can see credits/rate-limit state without extra calls, the platform will feel much more enterprise-ready.

I kept my testing bounded and non-destructive. The attached report includes the methodology, screenshots, and sanitized evidence from the API probes.
