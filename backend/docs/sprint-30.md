# Sprint 30 — Weekly Coach Review

## Behavior

A read-only weekly coach review combines the existing plan/session matching,
execution reviews, athlete feedback, recovery snapshots, and fatigue trends.
It provides an explained assessment rather than only weekly statistics. No
training plans are changed and no new OpenAI calls or credentials are required.

The dashboard has a **Weekly Coach Review / Tygodniowy przegląd trenera** card
below recent workouts. It defaults to the last completed Monday–Sunday week.
Previous/next navigation, the current week, and returning to the last completed
week are supported. Current/future workouts without an execution remain pending;
only past dates can have missing executions. Future weeks are rejected.

The card shows:

- Planned, executed, paired, missing, and pending training counts.
- Running distance, total training duration, and quality/strength session counts.
- `on_target`, `too_hard`, `too_easy`, and `insufficient_evidence` assessments.
- Recovery coverage, average sleep, recovery-day statuses, and end-of-period
  HRV/resting-HR/sleep trends from the existing five-day trend engine.
- Strengths, points needing attention, and suggestions for the following week,
  with supporting evidence for each finding.
- An expandable seven-day plan/execution table, including assessment evidence
  and warnings, plus explicit limitations of the overall assessment.
- Empty, loading, and retry states; failure does not block the rest of the dashboard.

## API

`GET /review/week` defaults to the last completed calendar week.
`GET /review/week?week_start=YYYY-MM-DD` selects a Monday.

Responses include `week_start`, `week_end`, `as_of_date`, `current_week_start`,
`period_status` (`completed` / `in_progress`), `status` (`ready` /
`no_execution_data`), `summary`, `days`, `training_distribution`, `recovery`, and
`coach`. Each executed session has an `execution_review` produced by the existing
workout execution review engine with its matched plan and stored feedback.
The established `/review/week-test` statistics endpoint remains available.

Malformed dates return 422, a non-Monday/future week returns 400, and unavailable
upstream data returns 502 with a generic retry message. Internal exception details
and credential values are not returned.

## Calculations and limits

- Use all workouts in the selected calendar week, not only the three recent
  sessions shown on the dashboard. Warm-up/main/cooldown grouping uses the existing
  logical-session builder. Multiple sessions on a day retain one-to-one matching;
  a single planned workout cannot supply two confident execution assessments.
- Current-week data is bounded by the current date, consistent with `/today`.
  Calendar dates follow the backend's existing date convention; they are not
  rolling seven-day windows. A current-day workout without execution is pending.
- Confidence below 0.5 does not support claims about repeated excessive load.
  Two confident `too_hard` assessments trigger a review of recovery before the
  next quality workout. One difficult session alone does not establish fatigue.
- Recovery metrics use historical baselines from the existing snapshot service.
  Recovery trends use at most the last five days **inside the selected week**;
  missing days are not filled. Empty wellness rows are not treated as healthy
  observations. Missing baselines, sparse or absent end-of-week recovery data,
  and absent subjective feedback qualify the findings.
- Missing execution records may reflect incomplete imports. The review explicitly
  recommends checking synchronization before concluding that a workout was skipped.
- `too_hard`/`too_easy` describe the executed stimulus relative to the plan; they
  are not fitness measurements. Advice remains a user decision.
- The current imported plan is used; this does not introduce immutable historical
  plan versions or advance to Sprint 32's structured workout adjustments.

## Validation

Verified locally: **227 backend tests and 11 browser tests passed**, including
the existing Sprint 29 regressions. Production deployment is still outstanding.

From `backend/`, using the existing environment:

```sh
.venv/bin/python -m pytest -q
```

From the repository root, with Node 20+ and Chromium:

```sh
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

Set `CHROMIUM_PATH` if Chromium is not at `/usr/bin/chromium`. The existing backend
`.venv` is required by the browser fixture. It starts a local server with a fresh
temporary SQLite database. Deterministic plan inputs feed the real weekly API,
matching, workout assessment, and recovery/coaching engines. Production API URLs
are intercepted and fulfilled locally; tests never contact production.

Backend coverage includes complete/current/empty weeks, year boundaries, all three
execution categories, low-confidence assessments, subjective feedback, missing
baselines and data, future activities, more than three sessions, one-to-one and
composite matching, running plus strength, invalid requests, and safe error messages.
Browser coverage adds evidence expansion, navigation, empty/retry states, mobile
layout, stale-response protection, and the existing Sprint 29 decision regressions.

## Deploy

No database migration or new dependencies/secrets are needed for Sprint 30.
Merge the review branch into `main`, then deploy backend **before** frontend.
From a clean checkout of the merged code:

```sh
gcloud run deploy pacemind-backend --source backend --region=europe-central2 --project=pacemind-503211
npx --yes firebase-tools deploy --only hosting --project=pacemind-503211
```

The new frontend requires `/review/week`; during a staged deploy against an old
backend it shows a recoverable weekly error while the other cards remain usable.
JS/CSS versions are bumped to 6; `weekly-review.js` is a new hosted static asset.

After deployment, check the default past week, expand the daily comparison and
finding evidence, navigate to the current week, and confirm pending workouts are
not called missed. Check a week with no records too. Production behavior and
external Google Sheets access must be validated after deployment; local fixture
tests alone do not establish those integration results.
