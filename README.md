# FortyGuard API Evaluation

This repo contains my FortyGuard hiring evaluation work: final form answers, a short uploadable report, endpoint audit scripts, and sanitized evidence from the API/docs/dashboard pass.


## Main Finding

The core API workflows work when called with the documented request shapes. Heatmap, Satellite View Segmentation, Street View Segmentation, and Environmental Parameters all completed during the final endpoint audit.

The strongest issue is validation-before-billing: an intentionally unclosed heatmap polygon was accepted, completed, and appeared in Heatmap Generation credit usage. Invalid geometry should fail before job creation and should not consume credits.

## Rerun the API Audit

```bash
export FORTYGUARD_API_KEY="..."
python scripts/final_api_endpoint_audit.py
```

The script writes sanitized output under `evidence/api/` and redacts the API key plus large image/PDF payloads.

`scripts/api_test_suite.py` is kept as a compatibility wrapper for anyone expecting that filename.
