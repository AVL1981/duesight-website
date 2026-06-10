# DueSight Max-Stack Handoff - 2026-05-29

## Status

All 12 sample reports have a fresh max-stack company-intel replay artifact set and public HTML render after the 2026-05-29 cleanup.

Final audit:

- Path: `C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website\max-stack-all12-completion-audit.json`
- Result: `all_12_strict_pass_retained0_with_dq_deep_crawl_and_public_hygiene = true`
- Public HTML forbidden hits: `[]`
- Cross-target NLIST/TSG leakage: `[]`
- Each report has 11 provider routes recorded:
  - `deep_research_crawl`
  - `minimax_search`
  - `minimax_highspeed_a`
  - `minimax_highspeed_b`
  - `glm_direct`
  - `local_xortron`
  - `hermes_deepseek`
  - `nvidia_nim_nemotron`
  - `antigravity_codeassist`
  - `claude_code`
  - `codex_cli`

## User Question Checked

Claim checked:

> If Claude Code Desktop CLI or Gemini runs true deep research, it can produce hundreds of URLs; why does the current run not?

Verdict:

- Architecturally correct: the old provider path was mostly one prompt to one answer, so it behaved like single-shot synthesis/review.
- Not fully proven for this local Claude CLI: `claude --help` did not expose a literal `deep-research` subcommand in this install. Existing DueSight `claude_code` route uses `claude -p`, so it is not a guaranteed iterative deep-research crawler.
- Correct fix: add a DueSight-native iterative discovery provider instead of depending on a model CLI to behave like a crawler.

Implemented fix:

- Added first-class `deep_research_crawl` provider in `duesight-agent\tools\max_deep_research_runner.py`.
- Provider runs the DueSight query plan as many small public-source discovery calls.
- Provider crawls the target-owned public domain routes before model synthesis.
- Provider writes `deep-research-crawl.json`.
- Discovered source URLs are fed into the downstream AI provider prompt context.

## Code Changes

### `duesight-agent\tools\max_deep_research_runner.py`

Key changes:

- Added `deep_crawl` / `deep_research_crawl` provider.
- Added target-site crawl with same-domain public route limits.
- Added entity relevance filtering to reduce ambiguous-name noise.
- Raised source URL cap through `DUESIGHT_PROVIDER_SOURCE_URL_LIMIT`.
- Made `deep_research_crawl` a required anti-hallucination signal.
- Changed G7 to source URL depth.
- Tightened raw-error regex so normal limitation language is not falsely blocked.
- Removed accidental global `The Specialist Group` term from MiniMax search query.

### `duesight-agent\tools\sample_report_max_company_intel_replay.py`

Default providers now include:

```text
deep_crawl,minimax_search,minimax_a,minimax_b,glm,xortron,hermes_deepseek,nim,antigravity,claude,codex
```

### `duesight-website\tools\sample_report_certified_renderer.py`

Key fixes:

- Removed NLIST/TSG findings as default basis for every report.
- NLIST-specific commercial findings now only apply to `sample-report-nlist`.
- Generic targets now get target-specific context/findings.
- Specialist Group gets its own platform/acquisition context.
- Public context-strength copy no longer claims unrelated targets are linked to TSG.
- Extended dossier lead text changed from `concrete NLIST-bevindingen` to `target-specifieke bevindingen`.

### `duesight-website\sample-report-specialist-group\pipeline-manifest.json`

Key fix:

- Target domain corrected from inactive `specialistgroup.nl` to public `thespecialistgroup.com`.
- This fixed the failed Specialist Group deep crawl.

## Specialist Group Rerun

Before fix:

- `crawl_urls = 0`
- `crawl_queries = 1`
- Target domain was `specialistgroup.nl`, which does not resolve.

After fix:

- Run ID: `max-research-the-specialist-group-b.v.-20260529T105301Z`
- Total URLs: `106`
- Deep crawl URLs: `77`
- Crawl queries attempted: `24`
- Target site pages checked: `60`
- Providers executed: `11`
- Retained providers: `[]`
- Anti-hallucination gate: `PASS`

## Final Audit Snapshot

Scores after final render/audit:

| Report | Score | URLs | Deep crawl URLs | Gate |
|---|---:|---:|---:|---|
| adyen | 70 | 113 | 78 | PASS |
| bunq | 71 | 106 | 70 | PASS |
| gasunie | 71 | 118 | 84 | PASS |
| getthere | 67 | 61 | 15 | PASS |
| mollie-gold | 71 | 96 | 55 | PASS |
| multiselect | 64 | 85 | 34 | PASS |
| nlist | 71 | 72 | 39 | PASS |
| postnl | 71 | 109 | 84 | PASS |
| shell | 70 | 125 | 83 | PASS |
| specialist-group | 64 | 106 | 77 | PASS |
| truelegends | 66 | 57 | 22 | PASS |
| wise | 70 | 101 | 65 | PASS |

## Reproduction Commands

Specialist Group rerun:

```powershell
$env:DUESIGHT_ANTIGRAVITY_MODEL='gemini31_flash'
$env:DUESIGHT_GLM_MAX_ATTEMPTS='1'
$env:DUESIGHT_HERMES_DEEPSEEK_MODEL='deepseek-chat'
$env:DUESIGHT_DEEP_CRAWL_MAX_QUERIES='24'
$env:DUESIGHT_DEEP_CRAWL_PER_QUERY_TIMEOUT='12'
$env:DUESIGHT_DEEP_CRAWL_SITE_PAGES='60'
$env:DUESIGHT_DEEP_CRAWL_SOURCE_URL_LIMIT='320'
python "C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent\tools\sample_report_max_company_intel_replay.py" --reports specialist-group --providers deep_crawl,minimax_search,minimax_a,minimax_b,glm,xortron,hermes_deepseek,nim,antigravity,claude,codex --provider-timeout 180 --step-timeout 1800 --render-timeout 240 --render --force --continue-on-error
```

Render all public reports:

```powershell
python "C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website\tools\sample_report_certified_renderer.py"
```

Read final audit:

```powershell
Get-Content -Raw "C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website\max-stack-all12-completion-audit.json"
```

## Remaining Product Truth

The sample reports now prove max-stack replay and source discovery, but not 100% official diligence closure. Data-quality gaps remain honest official-proof gates:

- `finance_source` requires official annual account/XBRL/PDF, seller P&L or licensed provider document with source hash.
- `ownership_ubo` requires lawful UBO extract, shareholder register, current registry extract or licensed ownership graph/provider evidence with source hash.
- AI/model providers enrich, cross-check and prioritize; they are not primary legal or finance sources.

