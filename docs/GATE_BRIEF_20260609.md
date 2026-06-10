# Gate Brief - 2026-06-09

## Purpose

This brief tells the next agent how to treat the final documentation set without reopening public-surface or runtime work.

## Current Verified Baseline

The latest recorded repair pass ended with:

```powershell
python tools\public_surface_gate.py
python tools\public_surface_gate.py --strict
python tools\public_surface_gate.py --legacy
python -m pytest tests\test_public_surface_gate.py -q
python -m pytest tests\test_homepage_hygiene.py tests\test_launch_evidence_pages.py tests\test_claims_substantiation.py -q
git diff --check
```

Recorded status:

- Default gate: PASS.
- Strict gate: PASS.
- Legacy gate: PASS.
- Public surface gate tests: PASS.
- Homepage/launch-evidence/claims tests: PASS.
- Diff check: clean in the final repair baseline.

## Finalize-Scope Checks

For the finalize docs set, run at minimum:

```powershell
git status --short
git diff --check
python tools\public_surface_gate.py
python tools\public_surface_gate.py --strict
python tools\public_surface_gate.py --legacy
```

Run the broader tests again if any public HTML, JS, gate, or test file appears dirty.

## Public Surface Rules

- Do not edit `_pages/`.
- Do not expand public copy in this pass.
- Do not add fixed count claims, named provider/model wording, compliance-status claims, unsupported comparison claims, or source-count marketing.
- Do not rename public slugs or routes inside this finalize docs pass.

## Agent Rules

- Stage only the finalize set named in `docs/SESSION_HANDOFF_FINALIZE_20260609.md`.
- Stop if the live git status has extra changes outside that set.
- Report open [BESLISSING] items at the end.
- Do not push.

## Commit Readiness

This file is safe for the finalize documentation commit. It is a brief for the next agent, not a code or public-copy change.
