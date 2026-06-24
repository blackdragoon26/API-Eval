# FortyGuard API Evaluation

This repo contains my FortyGuard hiring evaluation work: final form answers, a short uploadable report, endpoint audit scripts, and sanitized evidence from the API/docs/dashboard pass.

## What to Submit

Use this PDF for the Google Form upload:

`output/pdf/FortyGuard_Evaluation_Report.pdf`

Use this file for copy/paste form answers:

`reports/FortyGuard_Form_Submission_Draft.md`

## Repo Layout

```text
reports/                  Final writeups and earlier planning notes
scripts/                  API audit scripts
scripts/legacy/           Older exploratory polling script
evidence/api/             Final sanitized API audit evidence
evidence/docs/            Captured docs text
evidence/visual/          Dashboard/docs screenshots and visual notes
evidence/old-runs/        Earlier probe outputs kept for traceability
output/pdf/               Upload-ready PDF
forty/                    Local Python virtualenv used during testing
```

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
