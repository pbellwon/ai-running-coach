# Sprint 29 — Adaptive Planning

The dashboard can accept or reject an adaptation proposal and restore that
decision from the database when the page is reopened, including in a new browser.
Acceptance records the athlete's choice; training-plan edits are still manual.

## Decision identity and retries

`GET /adaptive-plan?target_date=YYYY-MM-DD` includes `proposal.proposal_id` and a
nullable `athlete_decision`. The ID covers the date, original workout title/type,
proposed decision/type/distance/duration, and approval requirement. Changes to
explanatory text alone do not reset a decision. A changed workout proposal gets
a new ID and requires a new response.

Send that ID with the existing `POST /adaptive-plan/decision` fields. The API
checks the current proposal before saving and returns HTTP 409 if it changed.
An answered proposal is final: retries and competing responses return the first
saved decision. A unique database index also protects concurrent requests.

Historical records have no proposal ID and remain preserved. They are not
assigned to a newly generated proposal because their exact original volume and
workout title were not recorded. Legacy POST requests without an ID remain
compatible but do not mark a current proposal as answered.

The UI disables both buttons during saving and after a confirmed response,
supports retry after an unsuccessful request, and asks for a refresh after a
stale-proposal conflict. It shows proposal warnings before the decision.

## Deploy in this order

1. Back up the production database using the normal operational procedure.
2. With the intended database configured, run from `backend/`:

   ```sh
   .venv/bin/python -m app.scripts.add_adaptation_decision_records_table
   ```

   This repeatable migration creates a missing table or adds the nullable
   `proposal_id` column and its unique index to the existing table. It supports
   SQLite and PostgreSQL. It keeps existing decision rows unchanged. Use the
   deployed Python executable in environments without `.venv`.
3. Deploy the backend, then check that `/adaptive-plan` returns `proposal_id` and
   `athlete_decision` for a configured training date.
4. Deploy Firebase Hosting using the repository's `firebase.json` and the
   authorized Firebase account: `firebase deploy --only hosting`.
5. On a real proposal, check accept/reject, confirmation, and the persisted
   status after a browser reload. Recording a real athlete response is an
   intentional production action; use a suitable test proposal/account.

The frontend requires the updated backend to persist decisions. During a staged
deployment against an older backend it displays an unavailable message and
leaves the buttons disabled. JS and CSS cache versions are bumped to 5.

## Local validation

From `backend/`, with dependencies and pytest/httpx installed:

```sh
.venv/bin/python -m app.scripts.add_adaptation_decision_records_table
.venv/bin/python -m pytest -q
```

Browser tests require Node.js 20+, the backend `.venv`, and Chromium. From the
repository root:

```sh
npm ci --prefix tests/frontend
npm test --prefix tests/frontend
```

Chromium defaults to `/usr/bin/chromium`; set `CHROMIUM_PATH` for another
installation. Tests start a local server on port 18765 with a temporary SQLite
database and deterministic training inputs. All production API URLs are
intercepted and served by the local fixture. The real adaptive decision API and
database persistence are exercised. No production data or external integrations
are used. Tests cover both choices, reopening in a new browser context, changed
proposals, failed requests, retries, and double-click protection.

Validated locally: 206 backend tests and 5 browser tests passed. Production
migration, backend/frontend deployment, and the production click/reload check
remain outstanding. Sprint 29 should be closed after those checks pass.
