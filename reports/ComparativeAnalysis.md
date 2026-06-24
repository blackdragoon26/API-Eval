<img width="512" height="110" alt="image" src="https://github.com/user-attachments/assets/822db016-1b32-40e9-a765-9176a6e70b5d" />

# FortyGuard Comparative Analysis - Engineering Notes

**Candidate:** [Sankalp Jha](https://github.com/blackdragoon26)  
**Position:** Software Engineer Intern 
**Date:** June 24, 2026  
**Repository:** [github.com/blackdragoon26/API-Eval ](https://github.com/blackdragoon26/API-Eval) <br>
**Scope:** Temperature API, async job behavior, validation, credit accounting, docs accuracy, and a light dashboard/docs visual pass

## Summary

The API has the right base design for its domain: async jobs, geospatial inputs, imagery analysis, environmental data, and reports. Compared with mature developer platforms, the gaps are not around product idea. They are around validation, billing trust, error semantics, observability, and documentation precision.

The final endpoint audit corrected the rough early read: Heatmap works with the documented `FeatureCollection` request. The more useful finding is that an unclosed polygon was also accepted, completed, and charged. That is the issue I would lead with.

## Compared With Mature API Platforms

Stripe/Twilio-style APIs set expectations around:

- Stable error envelopes with machine-readable codes
- Idempotency keys for retries
- Request IDs on every response
- Clear rate-limit and retry headers
- Copy/paste examples for each endpoint
- Public OpenAPI/Postman flows

FortyGuard has API-key auth, an async task model, and OpenAPI 3.1. The next step is turning that foundation into an integration experience developers can trust without guessing.

## Compared With Metered/Usage-Based APIs

For credit-based APIs, developers need quick visibility into:

- Remaining credits
- Whether a failed/invalid request was charged
- Rate-limit state
- Retry timing
- Correlation IDs for support

FortyGuard has a working credits usage endpoint, which is good. The weak spot is that normal endpoint responses do not expose credit/rate-limit/request-id headers, and invalid heatmap geometry appeared to consume credits.

## Compared With Weather/Geospatial APIs

FortyGuard's differentiator is stronger than generic weather lookup. The endpoint set points to urban heat intelligence: heatmaps, segmentation, environmental parameters, and property/city reports.

The domain-specific improvements are:

- Strict GeoJSON validation before job creation
- Clear `FeatureCollection` vs raw `Polygon` contract
- Units and sentinel values for every environmental output
- Exportable GeoJSON/CSV/PDF artifacts
- Batch jobs for multiple areas or locations

## Strongest Findings

1. Documented Heatmap `FeatureCollection` requests work and complete.
2. Invalid unclosed Heatmap polygons also complete and appear charged.
3. Unknown activity IDs return ambiguous `403` responses.
4. Credits usage works but is documented as a form-style/GET flow instead of a normal `POST` API.
5. Environmental Parameters docs imply customization that the OpenAPI schema does not expose.
6. Satellite uses `orignal_image`; Street View uses `original_image`.
7. Operational headers are missing for request ID, rate limits, retry guidance, and remaining credits.

## Recommendation Priority

1. Fix validation-before-billing for Heatmap.
2. Standardize error/status behavior.
3. Document the live API contract exactly.
4. Add request IDs, rate-limit headers, retry headers, and remaining-credit headers.
5. Add webhooks, cancellation, idempotency, batch submission, and job history.

## Final Position

FortyGuard's product thesis is strong. The engineering work I would prioritize is not a redesign; it is hardening the contract so developers can integrate confidently and users can trust the credit model.
