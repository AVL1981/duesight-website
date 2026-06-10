# Change Control Procedure - 2026-06-09

## Purpose

This procedure is the operating rule for the final documentation and launch-readiness pass.

It is intentionally conservative. The goal is to avoid mixing agent work, public-surface changes, runtime changes, and owner-only decisions.

## Hard Boundaries

- No push.
- No deletes.
- No `_pages/` edits.
- No `.gitignore` edits.
- No ARCHITECT-only files.
- No test or scratch files in the finalize commit.
- One writer per repo at a time.
- Agents do not authorize each other's work.
- Unknown or pre-existing dirty state stays out unless proven safe and explicitly in scope.

## Standard Flow

1. Read the handoff fully.
2. Check live git status.
3. Confirm no other agent is writing to the same branch.
4. Stage only the exact documented finalize set.
5. Run the documented checks.
6. Commit only if the staged set and checks match the handoff.
7. Stop before push and report status.

## Required Checks For Finalize Docs

For a docs-only finalize set:

```powershell
git status --short
git diff --check
python tools\public_surface_gate.py
python tools\public_surface_gate.py --strict
python tools\public_surface_gate.py --legacy
```

If public files, payment code, tests, or tools are unexpectedly dirty, stop and report instead of expanding scope.

## Stop Conditions

Stop immediately if:

- another agent is active on the same branch,
- the staged set includes a file outside the handoff,
- `_pages/`, `.gitignore`, ARCHITECT-only files, secrets, backups, or scratch files appear in the staged set,
- a required check fails,
- a decision item is needed to finish safely.

## Commit Readiness

This file is safe for the finalize documentation commit. It is a procedure document only.
