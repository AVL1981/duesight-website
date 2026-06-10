# Website Worktree Triage - 2026-06-02

## Scope

This note classifies the dirty `duesight-website` worktree before promotion. No public deploy was performed.

Branch: `handoff/max-stack-20260529`
Baseline commit: `6bcfb33b chore(reports): handoff max-stack replay artifacts`

## Decision

Promote only reviewable feature code for the local API app and the contract triage endpoint. Park generated report output, browser artifacts, sample rerenders, and premium/live-looking pages until a separate owner decision.

## PROMOTE

Release-review candidates:

- `app/**/*.py`
  - FastAPI API app.
  - Includes `/health`.
  - Includes `/api/contract/health`.
  - Includes `/api/contract/triage`.
  - Keeps contract triage wired to the canonical agent scanner instead of duplicating logic.
- `tests/test_contract_endpoint.py`
  - Local TestClient coverage for contract health and triage.
- `docs/WEBSITE_WORKTREE_TRIAGE_20260602.md`
  - This classification note.

Important release note: `app/main.py` imports multiple routers and core modules. Promoting only the three contract files would leave a Git checkout unreleasable. The conservative route is to promote the visible API app as one unit, then keep non-code output parked.

## PARK

Do not stage as part of the contract promotion:

- Modified `sample-report-*/*.json`
- Modified `sample-report-*/*.html`
- Modified `index.html`, `trust.html`, glossary/blog pages, `scan_client.js`, and `backtesting/templates/report.html`
- `sample-report-*/index-premium.html`
- `orbit-duesight.html`
- `assets/duesight-*.svg`
- `assets/duesight-*.png`
- `backtesting/report_generator.py`
- `backtesting/scan_server.py`

Reason: these look like demo/report/site rendering work, not required for the contract endpoint release. They may be valuable, but need a separate review because they can affect public claims or live buyer-facing output.

## GENERATED_OUTPUT

Keep out of the feature commit:

- `_tmp-deep-crawl-nlist/`
- `output/`
- `reports/`
- `test-results/`
- `tmp/`
- Browser/smoke profiles already covered by `.gitignore`
- `*.pyc`
- `__pycache__/`

Reason: output is useful as evidence only after a named run note captures what it means. Raw generated folders should not become feature code by accident.

## IGNORE_OR_ARCHIVE

Keep out of Git or archive separately:

- `.env*` files and local config
- Local browser profiles and temporary smoke artifacts
- A/B scratch files such as `antigravity-31-vs-35-*.json`
- Any secret-bearing diagnostic output

## Contract Endpoint Positioning

The endpoint is allowed to be promoted only with this positioning:

- Pre-DD triage only.
- No legal advice.
- No clause review.
- Plain text input only.
- Every health and triage response must include the disclaimer.
- No production deploy in this step.

## Acceptance

- The website worktree now has an explicit classification note.
- The contract endpoint feature code is reviewable as a Git-visible API app.
- Generated output remains documented but unpromoted.
- No public deploy or external action is implied by this note.
