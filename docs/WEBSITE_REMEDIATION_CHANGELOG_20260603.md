# Website Remediation Changelog - 2026-06-03

**Status:** claim firebreak completed locally; no deploy or push performed.

## Changed Customer-Facing Files

| File | Before | After |
|---|---|---|
| `duesight-track-record.md` | Legacy high-water scores, hit-rate, sole-provider wording and Big-4 comparison. | Replaced with self-assessed buyer-demo replay, fixed layers and explicit limitations. |
| `duesight-linkedin-proof.md` | Legacy score table and auditor comparison. | Replaced with buyer-demo proof note and no benchmark/performance claim. |
| `steinhoff-blind-test.md` | Impossible score-only claim and investment-style language. | Replaced with cutoff-fixed Steinhoff replay summary and allowed-use caveat. |
| `assurance/index.html` | Trust strip suggested formal security certification in preparation. | Replaced with security controls / AI governance wording without certification claim. |
| `index.html` | Security certification labels, Big-4 checklist label and absolute certainty/persona copy. | Replaced with controls roadmap, independent accountant label and source-traceable wording. |
| `trust.html` | Provider/roadmap table exposed certification tokens in customer copy. | Replaced with generic published assurance / external controls audit wording. |
| `dd-checklist/index.html` | Checklist item named specific certification tokens. | Replaced with generic securitycertification / assurance-status wording. |
| `dpa/index.html` | Provider row exposed a certification token. | Replaced with generic published security assurance wording. |
| `rapporten/index.html` | Trust item suggested formal security certification in preparation. | Replaced with security controls documented wording. |
| `sample-hub-gasunie/index.html` | Sample hub trust strip suggested formal security certification in preparation. | Replaced with security controls / AI governance wording. |
| `blog/wat-is-due-diligence/index.html` | Named large advisory firms in comparison table. | Replaced with generic large advisory / specialist DD teams wording. |
| `nis2-check/index.html` | Suggested a specific certification framework. | Replaced with generic security-framework certification wording. |
| `intelligence-hub-template.html` | Template badge exposed certification-aligned wording. | Replaced with security controls documented wording. |

## Verification Notes

- Firebreak grep on the edited customer-facing files returned 0 hits for: `100/100`, `105/110`, `105/100`, `als enige platform`, `PwC`, `KPMG`, `ISO 27001`, `SOC 2`, `Big 4`, `DueSight Score`, `Hit Rate`, `Institutioneel Grade`, `perfect`, `unbeatable`, `100% zekerheid`, `100% Wwft`.
- Broad repo grep still returns ignored/allowed context: backup snapshots, generated company pages with the legal company name `Perfect Pitch Artificial Grass`, source snippets inside sample JSON, and technical glossary text describing perfect-model theory.
- Existing unrelated dirty website changes were left intact and are not part of this remediation scope.
