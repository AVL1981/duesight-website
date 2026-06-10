# Decision List 09 - 2026-06-09

## Purpose

This is the owner/legal/operator decision list for the current launch-readiness state. It is not an instruction for an agent to decide business, legal, payment, or trademark matters.

## Gate Snapshot

| Gate | Status | Blocking decision | Owner |
| --- | --- | --- | --- |
| G2 Payment go-live | Ready for owner go/no-go; runtime/payment readiness remains the live source of truth | Confirm TLS, payment API route, Mollie live mode, SMTP, admin secret, and process supervision before live switch | Arian/operator |
| G4 Counsel sign-off | With counsel | Confirm final legal copy, terms, refund/cancellation wording, and compliance-sensitive claims | Counsel/Arian |
| G5 Operator runbook | Operator work | Confirm who runs launch checks, incident response, refunds, delivery, and customer support | Arian/operator |
| G8 Insurance | Afgesloten via Hiscox | Confirm final policy conditions, coverage scope and exclusions before relying on it commercially | Arian |
| G9 Trademark | Word mark and image mark path open | Decide filing scope, classes, timing, and owner entity | Arian/counsel |
| T4 Snapshot | Operator work | Decide final launch snapshot timing and archive method | Arian/operator |

## Open Decisions

- [BESLISSING] G2: final permission to switch payment flow live.
- [BESLISSING] G4: counsel sign-off received and recorded.
- [BESLISSING] G5: named operator and escalation path.
- [BESLISSING] G8: insurance status accepted or launch risk accepted.
- [BESLISSING] G9: trademark filing route and owner entity.
- [BESLISSING] T4: final pre-launch snapshot method.

## Source Documents

- `docs/PAYMENT_LIVE_READINESS_20260607.md`
- `docs/PUBLIC_SURFACE_GATE_HARDENING_20260609.md`
- `docs/REPAIR_PASS_REPORT_20260609.md`
- `docs/WEBSITE_COMMIT_SPLIT_PLAN_20260609.md`

## Commit Readiness

This file is safe for the finalize documentation commit. It records decisions still owned by Arian, counsel, or the operator.
