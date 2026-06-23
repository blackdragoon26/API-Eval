# FortyGuard Evaluation — Full Technical Test Plan

Goal: produce evaluation feedback sharp enough to stand out — not generic "looks good, minor bugs" feedback, but evidence-backed analysis: actual request/response pairs, a documented bug list, and prioritized recommendations.

---

## 0. Setup (Day 0, ~20 min)

- [ ] Log into dashboard, **immediately change the temporary password**
- [ ] Locate API key (email or dashboard → Profile/API settings)
- [ ] `export FORTYGUARD_API_KEY="..."` in your shell — never hardcode it in a script you might paste somewhere
- [ ] Run `Check API Credits Usage` once to record starting plan + credit balance (you'll diff this after testing to confirm credit-deduction behavior is correct)
- [ ] Skim Known Limitations + Release Notes pages once more — note the exact limits (10mi² Basic / 50mi² Premium, 3 env params Basic, US-only, granularity 60/80/100, filter_type 2 max 23hrs)
- [ ] Set up `api_test_suite.py` (provided separately) — run `pip install requests`

---

## 1. Documentation Audit (do this in parallel with testing, not before)

Go page by page and log **every** inconsistency. Known ones to start with:

| # | Location | Issue |
|---|---|---|
| 1 | Quickstart vs Check Status page | Status values shown as lowercase (`processing`/`succeeded`/`failed`) in Quickstart, but capitalized (`Processing`/`Completed`) in Authentication and Satellite/Check Status examples. **Which is real?** — test confirms. |
| 2 | Satellite endpoint result schema | `"message": "Completed"` at top level, but `"status": "Completed"` nested inside `data` — redundant/inconsistent message vs status field. |
| 3 | Satellite endpoint | Misspelled field `orignal_image` (should be `original_image`) — confirm this isn't a doc typo vs actual API field (if the API itself returns the misspelled key, that's a real API design bug worth flagging). |
| 4 | Heat Intelligence | Docs only show the *streamed PDF download* example — no example of the **submission payload** (what does `analysis` array request body actually look like?). Confirm whether this is documented elsewhere or genuinely missing. |
| 5 | Credits Usage / Free API Key | Endpoints described as forms ("Enter Your API Key", "Enter Your Email") rather than documented as raw HTTP POST with JSON schema like every other endpoint — inconsistent documentation format. Get the actual request schema by inspecting network tab (DevTools) when submitting the form. |
| 6 | Env Params | "Up to 3 parameters per request" (Basic) — but the docs page itself doesn't enumerate the full parameter list/enum names you'd pass (heat index, AQI subcomponents, etc.) in a request schema — confirm from actual endpoint page. |
| 7 | Status endpoint polling | No documented recommended polling interval / backoff guidance, and no max polling timeout documented — worth flagging as missing operational guidance for production users. |

As you test, add a row every time you catch behavior that contradicts the docs, or a doc claim you couldn't verify.

---

## 2. Endpoint-by-Endpoint Functional Tests

For **every** endpoint below: capture (a) the request payload, (b) raw response, (c) status code, (d) whether credits were deducted (check before/after via Credits Usage), (e) latency.

### 2.1 `POST /v1/heatmap`
- [ ] Happy path: small valid polygon (<1mi²), `filter_type=1`, granularity=100
- [ ] Max allowed area for your plan (10mi² Basic / 50mi² Premium) — does it succeed right at the boundary?
- [ ] **1 unit over** the max area — confirm it's rejected with 400, not silently truncated or billed
- [ ] All three `filter_type` values (1, 2, 3) — confirm required/optional fields match docs for each
- [ ] `filter_type=2` with a 23hr range (boundary) and a 24hr range (should fail per docs)
- [ ] All three granularities (60/80/100) — confirm output resolution actually differs
- [ ] Non-US polygon (e.g. somewhere in Canada/Europe) — confirm proper rejection, not silent failure

### 2.2 `POST /v1/satellite` (Premium only)
- [ ] Happy path per the documented example
- [ ] If you're on Basic: confirm you get a clean 403/plan-restriction error, not a 500 or vague 400
- [ ] All three `filter_type` values
- [ ] All three granularities
- [ ] Check `orignal_image`/`segmentation.image_content` — are they valid Base64? Decode and render to confirm they're real images, not placeholder/empty strings (the example response shows `""` — is that just doc redaction or an actual bug in some cases?)

### 2.3 `POST /v1/streetview`
- [ ] Happy path
- [ ] Front-only vs front+back view (per release notes, "optional back" view) — confirm exact parameter name/shape (docs you have don't show this endpoint's full schema — flag if genuinely undocumented)
- [ ] Location with no available street-level imagery (rural/remote coordinate) — does it fail gracefully?

### 2.4 `POST /v1/heat_intelligence` (Premium only)
- [ ] Happy path with all 5 analysis categories: `["geographic","environmental","urban","events","anthropogenic"]`
- [ ] Single category only
- [ ] Invalid category string (e.g. `"weather"`) — confirm 400 with clear message
- [ ] Empty array `[]` — confirm behavior is sane (error, not silent success)
- [ ] Confirm streamed PDF download actually works with the documented `stream=True` snippet — open the resulting PDF, confirm it's a real, complete report

### 2.5 `POST /v1/env_params`
- [ ] Basic plan: exactly 3 parameters → success
- [ ] Basic plan: 4 parameters → confirm proper rejection (not silently capped to 3)
- [ ] Premium: full parameter list in one request
- [ ] Invalid parameter name → 400 with useful message naming which one is bad
- [ ] Confirm units returned for each parameter (e.g. is temperature °C or °F? is irradiance in W/m²?) — **docs don't state units anywhere**, flag this

### 2.6 `GET /v1/status/{activity_id}`
- [ ] Valid in-progress ID → confirm "Processing"/"processing" (resolve the casing question here)
- [ ] Valid completed ID → confirm full result payload matches documented schema exactly
- [ ] Nonexistent/garbage activity_id → expect 404, check what actually comes back
- [ ] Activity ID belonging to a *different* endpoint type queried correctly — does the response shape change appropriately?
- [ ] A `failed` task — intentionally trigger one (e.g. malformed-but-accepted payload that fails downstream) and confirm credits are NOT deducted

### 2.7 Credits / Free Key endpoints
- [ ] `Check API Credits Usage` with valid key → confirm matches dashboard exactly
- [ ] With invalid/garbage key → confirm clean error, not stack trace or vague 500
- [ ] Inspect via browser DevTools what the *actual* underlying request looks like (method, URL, body) since docs only show a form UI — note if there's no documented JSON API for this at all

---

## 3. Validation & Error-Handling Matrix (this is the section that will make your feedback stand out)

Build a table like this and fill it in with real results:

| Test case | Endpoint | Expected (per docs) | Actual | Credits charged? | Notes |
|---|---|---|---|---|---|
| Missing `api-key` header | any | 401/403 | ? | ? | |
| Malformed JSON body | any | 400 | ? | ? | |
| `latitude=200` | heatmap | 400 | ? | ? | |
| `longitude=-200` | heatmap | 400 | ? | ? | |
| Polygon not closed (first ≠ last coord) | heatmap | 400 | ? | ? | |
| Polygon with only 2 points (invalid geometry) | heatmap | 400 | ? | ? | |
| `granularity=75` (not in 60/80/100) | heatmap | 400 | ? | ? | |
| `filter_type=4` (invalid) | any with date_time | 400 | ? | ? | |
| `start_date` malformed (e.g. `07-15-2024`) | any | 400 | ? | ? | |
| `start_time` without `filter_type=1/2` | any | ? | ? | ? | undocumented behavior |
| Extremely large polygon (100s of mi²) | heatmap | 400 | ? | ? | does it hang/timeout instead of fast-failing? |
| Duplicate/rapid-fire requests (10 in 1 sec) | any | rate limit? | ? | ? | docs don't mention rate limits at all — flag this gap |
| SQL/script injection string in any text field | any | 400, sanitized | ? | ? | basic robustness check, not an attack — just confirm no reflected/stored issue |
| Oversized payload (huge polygon coordinate array) | heatmap | 400/413 | ? | ? | |
| Wrong `Content-Type` header | any | 400/415 | ? | ? | |

This table alone, filled with real evidence, is more valuable than 90% of what other applicants will submit.

---

## 4. Performance & Reliability

- [ ] Time-to-completion for heatmap at granularity 60 vs 80 vs 100 — does finer granularity meaningfully increase latency?
- [ ] Submit 5 heatmap requests concurrently (use `concurrent.futures` in the test script) — do they all process correctly, or does anything get dropped/corrupted?
- [ ] Poll a long-running task (Heat Intelligence) every 2s vs every 10s — any difference in behavior, any indication of being rate-limited on polling itself?
- [ ] Note typical latency distribution (min/median/max) across ~10 identical requests

---

## 5. Dashboard UX Audit

Go through deliberately, not casually — they explicitly score this 1–10.

- [ ] First-run experience: is there onboarding, or are you dropped into an empty map with no guidance?
- [ ] Create a heatmap from the dashboard UI itself — does the workflow match what the API quickstart implies? Time it (they literally ask "how much time did you spend").
- [ ] Test "Map Controls," "Heatmap Information," "Analytics," "Heat Intelligence," "Map Comparison" — note anything unlabeled, broken, or dead-end
- [ ] Try resizing the browser window / mobile width — is it responsive?
- [ ] Toggle Map ↔ Satellite — confirm no broken tiles or state loss
- [ ] Check "Settings" and "Profile" — is changing your password actually straightforward (you should've just done this)?
- [ ] Note load time for the initial heatmap render — does the page feel instant or sluggish?
- [ ] Try an invalid/edge action deliberately (e.g. zoom to an area with no data, search a nonexistent address in "Go to...") — does it fail gracefully?

---

## 6. Writing the Feedback (mapping directly to their form fields)

Use this structure so every form field has a strong, specific answer ready before you open the form:

1. **First impression** — 2–3 honest sentences. Specific > generic ("clean visual design, but the dashboard gives no onboarding and the API docs have inconsistent status-value casing across pages" beats "looks nice and modern").
2. **What you liked most** — pick 2 concrete things (e.g. async activity_id + status polling model is clean and standard; credit-only-on-success billing model is fair and well-documented).
3. **What you disliked most** — lead with your single best-evidenced bug, not a vague complaint.
4. **Bugs/confusing behavior** — pull directly from your Section 3 table; list 3–5 with exact repro steps.
5. **Top 3 recommendations** — prioritize impact:
   - e.g. (1) Fix status-casing inconsistency across docs, (2) Document rate limits, polling backoff guidance, and parameter units explicitly, (3) Add a JSON-schema-documented version of the Credits/Free-Key endpoints instead of form-only.
6. **API design issues / missing endpoints** — candidates: no DELETE/cancel-activity endpoint, no webhook/callback option for long-running tasks (forces polling), no bulk/batch submission endpoint, `orignal_image` typo.
7. **Documentation improvements** — units for env params, explicit Heat Intelligence request schema, rate-limit docs, consistent status casing, recommended polling interval.
8. **Ratings** — give honest numbers and **justify each one in one sentence** in the comments field; specific reasoning reads far better than a bare number.

---

## 7. Suggested Timeline

| Phase | Time |
|---|---|
| Setup + credential rotation | 20 min |
| Functional endpoint testing (Section 2) | 90–120 min |
| Validation/error matrix (Section 3) | 60–90 min |
| Performance checks (Section 4) | 30 min |
| Dashboard audit (Section 5) | 30–45 min |
| Write-up (Section 6) | 45–60 min |
| **Total** | **~5–6 hours** |

If you're short on time, prioritize: Section 3 (error matrix) > Section 1 (doc audit) > Section 2 (functional) > Section 5 (dashboard) > Section 4 (performance). The error-handling matrix is the highest-signal, lowest-effort section for standing out.

---

## 8. Before You Submit

- [ ] Double check you're not pasting your raw API key or password anywhere in the feedback form/screenshots
- [ ] Attach the filled Section 3 table as a screenshot or short doc — visual evidence is persuasive
- [ ] Keep tone constructive and specific — confident technical critique, not complaints