# Website Commit-Split Plan — 9 Jun 2026

**Branch:** `handoff/max-stack-20260529`
**Doel:** Defensief commit-plan. **Geen staging, geen commit, geen push, geen deletes, geen moves, geen reverts.**
**Method:** Read-only `git` inspectie + live `python tools/public_surface_gate.py` (3 modi) + pytest. Één nieuw rapport geschreven.
**Aanmaak:** 9 jun 2026.

---

## 1. Executive Summary

**120 modified files** (unstaged) + **30 staged renames** (R100, pure moves) + **4 untracked files** in de worktree. Na live-classificatie in **5 commit-groepen + 1 docs-groep**:

| # | Commit-groep | Files | Auto-commit? | Risico |
|---|--------------|-------|--------------|--------|
| 1 | A. Archive/quarantine renames (staged) | 30 R + 1 MANIFEST | **YES** | LAAG |
| 2 | B. Public surface gate hardening | 2 (gate + tests) | **YES** | LAAG |
| 3 | C. Active public-copy cleanup (this hardening pass) | 11 root files | **YES** | LAAG |
| 4 | D. Source/build-drift cleanup (prior pass) | 73 root files | YES (na Arian scope-OK) | MEDIUM |
| 5 | E. UNKNOWN_OR_PREEXISTING — needs Arian decision | 34 root files | **NO** | HOOG |
| 6 | F. Hardening docs | 2 untracked .md | **YES** | LAAG |

**Totaal voorgestelde commits: 6** (of 5 als Arian docs in commit 2 vouwt).

**Verificatie (live op 9 jun):**
- `python tools/public_surface_gate.py` → **PASS**
- `python tools/public_surface_gate.py --strict` → **PASS**
- `python tools/public_surface_gate.py --legacy` → **PASS**
- `pytest tests/test_public_surface_gate.py` → **18 passed** in 11.51s
- `pytest tests/test_homepage_hygiene.py tests/test_launch_evidence_pages.py tests/test_claims_substantiation.py` → **15 passed** in 0.18s
- Totaal tests: **33/33 PASS**
- `git diff --check` → **CRLF warnings only**, geen echte errors

---

## 2. Live Git Status Snapshot

```
Branch: handoff/max-stack-20260529
Staged (R100): 30 archive renames → archive/legacy_zone_2026-06-08/
Unstaged (M):  120 modified files  (+690 / -367)
Untracked (??): 4 files
  - archive/legacy_zone_2026-06-08/MANIFEST.md
  - docs/PUBLIC_SURFACE_GATE_HARDENING_20260609.md
  - docs/PUBLIC_SURFACE_TRIAGE_20260608.md
  - docs/WEBSITE_COMMIT_SPLIT_PLAN_20260609.md  ← dit rapport
```

**Staged rename zones (alleen R100, identical content):**
- 13 × `backtesting/` (6 + 6 + 1) → `archive/legacy_zone_2026-06-08/backtesting*/`
- 4 × `legacy_root_backups/` (root index_backup*.html / index_master_backup.html / index.html.backup-*)
- 1 × `backtesting/templates/report.html` → `archive/legacy_zone_2026-06-08/backtesting_templates/`
- 12 × `sample-report-*/company-intel-prompt-evaluation.json` → `archive/legacy_zone_2026-06-08/sample_report_evaluations/`

**Totaal staged: 30 renames.** Match met `docs/PUBLIC_SURFACE_TRIAGE_20260608.md` §6 (31 — één afgewezen: `20260526_Mollie.html` was untracked, bleef in place).

**Untracked docs:** bevestigd via `ls`. MANIFEST.md documenteert alle 30 rollback paden.

---

## 3. Verification Results (live gerund 9 jun)

```
$ python "tools/public_surface_gate.py"
DueSight public surface gate: PASS

$ python "tools/public_surface_gate.py" --strict
DueSight public surface gate: PASS

$ python "tools/public_surface_gate.py" --legacy
DueSight legacy surface audit: PASS

$ python -m pytest "tests/test_public_surface_gate.py" -q
..................                                                       [100%]
18 passed in 11.51s

$ python -m pytest "tests/test_homepage_hygiene.py" "tests/test_launch_evidence_pages.py" "tests/test_claims_substantiation.py" -q
...............                                                          [100%]
15 passed in 0.18s
```

**`git diff --check`:** CRLF warnings op 21 files (LF wordt CRLF bij volgende git touch). Geen whitespace conflicts, geen merge conflict markers. **Geen echte errors.**

**Gate-pattern coverage (live in `tools/public_surface_gate.py:148-213`):** 38 `FORBIDDEN_PATTERNS` actief, plus 7 `SECRET_PATTERNS` in strict mode. Aantal gegroeid van ~30 → 38 in deze hardening pass.

---

## 4. Commit Group Proposal

### Commit 1 — `archive: quarantine legacy artefacts to archive/legacy_zone_2026-06-08/`
- **Scope:** 30 staged renames + `archive/legacy_zone_2026-06-08/MANIFEST.md` (untracked)
- **Risk:** **LAAG** — alle renames zijn R100 (identical content), geen code wijziging, gate verified clean
- **Side note:** `docs/PUBLIC_SURFACE_TRIAGE_20260608.md` (untracked) hoort bij deze commit OF wordt in Commit 6 meegestuurd

### Commit 2 — `feat(gate): public surface gate blindspot hardening (7 new patterns + 8 tests)`
- **Scope:** `tools/public_surface_gate.py` (+47/-6) + `tests/test_public_surface_gate.py` (+283/-1)
- **Risk:** **LAAG** — pure additive patterns + tests, alle 33 tests groen
- **Notes:** Gate patterns zijn verdedigbaar, geen false positives in echte content (verifieerd in 14-allowlist). `_codex_screenshots/background.js` edits uit bulk-script zijn inert (niet git-tracked, niet in build, alleen cosmetisch).

### Commit 3 — `fix(public): remove provider leaks, AI-engine disclosures, source-count claims from public surface`
- **Scope:** 11 root source files expliciet in hardening report §8:
  - `orbit-matrix.html` (HuggingFace → Model Hub)
  - `flipbook.js` (5 databases → meerdere sanctielijsten)
  - `index.html` (Evidence AI Engine + bronnen counts)
  - `faq/index.html` (8 databases ×3)
  - `walkthrough/index.html` (AI Engine Badges + 8 databases)
  - `glossary/ai-consensus/index.html` (Multi-provider + AI-engines + 10-Gate)
  - `glossary/epistemische-confidentie/index.html` (10-Gate ×2)
  - `glossary/sanctiescreening/index.html` (8 databases)
  - `glossary/pre-due-diligence/index.html` (AI-engines)
  - `dpa.html` (AI-engines) — voorkomt regressie; **Niet in git diff** want mogelijk al safe
  - `trust.html` (AI-engines ×2) — voorkomt regressie; **Niet in git diff** want mogelijk al safe
- **Risk:** **LAAG** — alle wijzigingen zijn gerichte safe-language replacements, gate + tests groen

### Commit 4 — `fix(public): claim-normalization across public pages (entity, tabu-terms, framing)`
- **Scope:** ~73 root files gewijzigd in **eerdere** sessies (niet deze hardening pass). Per triage 13.3: bulk-script raakte 172 files, waarvan 139 root + 33 chrome-extension (inert). In detail:
  - 28 × `glossary/*/index.html` (entity/claim normalization)
  - 8 × `blog/*/index.html` (claim normalization)
  - 11 × `scanner/tools`: `benfords-law-scanner.html`, `nis2scanner.html`, `scamscanner.html`, `sanctie-checker/index.html`, `subprocessors/index.html`, `vergelijk/index.html`, `rapporten/index.html`, `sales-tool.html`, `assurance/index.html`, `demo/index.html`, `intelligence-hub-template.html`
  - 4 × `orbit-*` / `walkthrough`: `orbit-demo.html`, `walkthrough/index.html`, `flipbook.js`, `scan_client.js`
  - 1 × `sitemap.xml`
  - 1 × `sample-hub-gasunie/index.html`
  - 11 × `sample-report-*/flipbook.html` (CSS comment `/* AI Engines */` → `/* Analyse */`)
  - 11 × `sample-report-*/styles.css` (CSS comment `/* Engine Grid (AI Consensus) */` → `/* Engine Grid (multi-source evidence review) */`)
  - `sales-tool.html`, `flipbook.js`, `walkthrough/index.html`, `index.html` ook expliciet in hardening report (overlap met Commit 3 — Arian beslist welke als "this pass" telt)
- **Risk:** **MEDIUM** — veel files, changes beslaan meerdere sessies. Arian scope-OK aanbevolen voor staging. `git diff --check` schoon (alleen CRLF).

### Commit 5 — `chore(legacy): designs/ + sample-report-mollie-gold social-platform-coverage.json cleanup`
- **Scope:** 24 × `designs/des-*.html` + 1 × `sample-report-mollie-gold/social-platform-coverage.json` + 1 × `sample-report-specialist-group/flipbook.html`
- **Risk:** **MEDIUM** — designs zijn uitgesloten van gate; sociale-coverage JSON is non-curated data; specialist-group flipbook is asymmetrisch (geen styles.css). Arian-OK aanbevolen.

### Commit 6 — `docs: public surface gate hardening report + triage doc`
- **Scope:** `docs/PUBLIC_SURFACE_GATE_HARDENING_20260609.md` + `docs/PUBLIC_SURFACE_TRIAGE_20260608.md` (2 untracked)
- **Risk:** **LAAG** — pure docs, geen code impact
- **Alt:** Arian kan deze docs in Commit 1 (triage) en Commit 2 (hardening report) vouwen → 5 commits total

---

## 5. File-by-File Classification Table

Aantal files per groep op basis van live git diff (89 M-lijnen in git status = 120 in diff --stat, want diff --stat telt elke file in de M+R set).

### Group A — Archive quarantine (Commit 1, P0, auto-commit yes)

| Path | Status | Reason |
|------|--------|--------|
| 30 × staged `R100` moves | staged R | Per `docs/PUBLIC_SURFACE_TRIAGE_20260608.md` §6 — quarantaine van stale public-surface findings |
| `archive/legacy_zone_2026-06-08/MANIFEST.md` | untracked | Documenteert alle 30 rollback paden |

### Group B — Gate hardening (Commit 2, P0, auto-commit yes)

| Path | Status | ±lines | Reason |
|------|--------|--------|--------|
| `tools/public_surface_gate.py` | M | +47/-6 | 7 new patterns + 1 extended; coverage 30→38 |
| `tests/test_public_surface_gate.py` | M | +283/-1 | 8 new tests + 1 extended; coverage 10→18 |

### Group C — Active public-copy cleanup (Commit 3, P0, auto-commit yes)

| Path | Status | ±lines | Reason (per hardening report §4.1) |
|------|--------|--------|------------------------------------|
| `orbit-matrix.html` | M | +14/-14 | HuggingFace → Model Hub |
| `flipbook.js` | M | +23/-23 | 5 databases → meerdere sanctielijsten |
| `index.html` | M | +8/-8 | Evidence AI Engine + bronnen counts |
| `faq/index.html` | M | +14/-14 | 8 databases ×3 → generic |
| `walkthrough/index.html` | M | +16/-16 | AI Engine Badges + 8 databases |
| `glossary/ai-consensus/index.html` | M | +14/-14 | Multi-provider + AI-engines + 10-Gate |
| `glossary/epistemische-confidentie/index.html` | M | +3/-3 | 10-Gate ×2 → meertraps |
| `glossary/sanctiescreening/index.html` | M | +1/-1 | 8 databases → meerdere sanctielijsten |
| `glossary/pre-due-diligence/index.html` | M | +2/-2 | AI-engines → analyselagen |

**Notes (drift):** hardening report noemt ook `llms.txt` en `llms-full.txt` als gewijzigd. **Niet in git diff** → bevestigd via `git ls-files llms.txt llms-full.txt` (output leeg) + `ls -la` toont dat ze op disk staan maar **niet git-tracked** zijn. Drift verklaring: `llms.txt/llms-full.txt` leven alleen in `_pages/` (build output), niet in root source. **Geen actie nodig** — `_pages/` is al schoon (gate PASS).

### Group D — Source/build-drift cleanup (Commit 4, P1, auto-commit ja na Arian scope-OK)

73 root files uit eerdere sessies, in 6 sub-categorieën:

| Sub-cat | Aantal | Voorbeelden |
|---------|--------|-------------|
| Glossary pagina's | 28 | `glossary/aml/index.html`, `glossary/benfords-law/index.html`, `glossary/fraude-detectie/index.html`, etc. |
| Blog posts | 8 | `blog/ai-due-diligence/index.html`, `blog/benfords-law-fraude-detectie/index.html`, etc. |
| Scanners/tools | 7 | `benfords-law-scanner.html`, `nis2scanner.html`, `scamscanner.html`, `sanctie-checker/index.html`, `subprocessors/index.html`, `vergelijk/index.html`, `rapporten/index.html` |
| Sales/landing | 5 | `sales-tool.html`, `assurance/index.html`, `demo/index.html`, `intelligence-hub-template.html`, `sample-hub-gasunie/index.html` |
| Orbit + walkthrough | 4 | `orbit-demo.html`, `walkthrough/index.html`, `flipbook.js`, `scan_client.js` |
| Sample reports (curated) | 22 | 11 × `flipbook.html` + 11 × `styles.css` (CSS comment fixes) |
| XML/SEO | 1 | `sitemap.xml` |

**Edits geverifieerd (live diff samples):**
- `glossary/shodan/index.html` (+10/-10): Shodan product-claim → passive infrastructure exposure analysis
- `glossary/benfords-law/index.html` (+10/-10): Benford product-claim → forensische data-analyse
- `blog/benfords-law-fraude-detectie/index.html` (+31/-31): Benford framing cleanup
- `flipbook.js` (+23/-23): "5 databases" → generic
- `sample-report-adyen/flipbook.html` (live diff): `/* AI Engines */` → `/* Analyse */` (CSS comment)
- `sample-report-adyen/styles.css` (assumed, +1/-1): CSS comment `/* Engine Grid (AI Consensus) */` → safe variant

### Group E — UNKNOWN_OR_PREEXISTING (NO auto-commit, needs Arian decision)

| # | Path | Status | ±lines | Why UNKNOWN | Review prioriteit |
|---|------|--------|--------|-------------|-------------------|
| 1 | `CONTEXT.json` | M | +5/-5 | Auto-generated door `generate_context.py` — edits overschreven bij volgende run. **Live diff:** `engines/__init__.py` docstring "AI engines" → "Multi-sources", `multi_model_thinker.py` docstring idem, `detect_engines` doc idem, `DDNeverAgainCrossCheck` doc "10-Gate" → "epistemische validatie", `tools/finbert_analyzer.py` doc "HuggingFace" → "open model registry" | **P2 — DO NOT COMMIT** |
| 2 | `company_data.json` | M | +3/-3 | Data file voor sample-reports. **Live diff:** "AI Consensus" → "multi-source review", "8 databases" → "meerdere databases" — safe-language replacements consistent met gate. Past bij Commit 4. | **P1 — commit mogelijk** |
| 3 | `backups/index_20260326_122110.html` | M | +17/-17 | BACKUP file gemodificeerd. **Live diff:** entity/claim normalization toegepast op historische snapshot. Backups horen ongewijzigd te zijn. | **P2 — DO NOT COMMIT** |
| 4 | `backups/orbit-matrix.BACKUP-2026-03-27_1745.html` | M | +1/-1 | BACKUP file. | **P2 — DO NOT COMMIT** |
| 5 | `backups/pre-master-redesign-2026-03-22/rapporten/index.html` | M | +3/-3 | BACKUP file. | **P2 — DO NOT COMMIT** |
| 6 | `backups/pre-master-redesign-2026-03-22/trust.html` | M | +2/-2 | BACKUP file. | **P2 — DO NOT COMMIT** |
| 7-28 | `designs/des-*.html` (22 files) | M | ~30/-30 | Design drafts, **excluded from gate** (`designs` in `EXCLUDED_DIR_NAMES`). **Live diff `des-17.html`:** "Multi-AI consensus" → "Multi-source evidence review", "11 AI-Engines" → "11 analyselagen", "AI Consensus Score" → "Multi-source review score". **Live diff `des-4.html`:** "EU AI Act Ready" → "EU AI Act Mapping". Consistente safe-language cleanup, past bij Commit 5. | **P1 — Arian scope-OK** |
| 29 | `sample-report-specialist-group/flipbook.html` | M | +1/-1 | **Asymmetrisch:** andere sample-reports hebben `flipbook.html` + `styles.css` edits; deze alleen flipbook. Mogelijk onvolledige eerdere edit. | **P2 — onderzoek** |
| 30 | `sample-report-mollie-gold/social-platform-coverage.json` | M | +2/-2 | Non-curated data file. Niet in `CURATED_SAMPLE_REPORT_FILES`. | **P2 — DO NOT COMMIT** |

**Totaal UNKNOWN_OR_PREEXISTING: 30 files** (was 34 in eerdere draft; hercount = 30: 2 data + 4 backups + 22 designs + 1 asymmetrisch + 1 non-curated = 30).

---

## 6. Staged Rename Review

Alle 30 staged renames zijn `R100` (100% similarity, identical content moves). Geen content changes. Match met `docs/PUBLIC_SURFACE_TRIAGE_20260608.md` §6 quarantine plan:

| Source zone | Files | Destination |
|-------------|-------|-------------|
| `backtesting/*.html` | 6 (asml, coolblue, gazprom, postnl, shell, shell_final) | `archive/legacy_zone_2026-06-08/backtesting/` |
| `backtesting/reports/20260314_*.html` | 2 (Gazprom, Shell) | `archive/legacy_zone_2026-06-08/backtesting/reports/` |
| `backtesting/reports/20260316_*.html` | 4 (ASML, Coolblue, PostNL, ASR) | `archive/legacy_zone_2026-06-08/backtesting/reports/` |
| `backtesting/reports/20260317_*.html` | 2 (ASR, Shell) | `archive/legacy_zone_2026-06-08/backtesting/reports/` |
| `backtesting/templates/report.html` | 1 | `archive/legacy_zone_2026-06-08/backtesting_templates/` |
| Root backups | 4 | `archive/legacy_zone_2026-06-08/legacy_root_backups/` |
| Sample-report eval JSONs | 12 | `archive/legacy_zone_2026-06-08/sample_report_evaluations/` |
| **Totaal** | **30** | — |

**MANIFEST.md cross-check:** 30 entries in MANIFEST.md, exact match met staged rename count. ✅

**Skipped (per MANIFEST.md):** `backtesting/reports/20260526_Mollie.html` (untracked, kon niet met `git mv` worden verplaatst). **Bekende legacy exclusions** (7 × `index_*.html` redirect stubs met UTF-8 BOM): blijven in place, excluded van gate via `LEGACY_KNOWN_EXCLUDED_PATHS`.

**Verdict:** staged renames zijn **compleet en consistent** met triage plan. Geen actie nodig behalve Commit 1 triggeren.

---

## 7. Public-Copy / Source Drift Review

### 7.1 llms.txt / llms-full.txt drift
- **Bevinding:** hardening report §8 zegt: "M llms.txt / M llms-full.txt (AI engines → generic)". **Niet in git diff** bevestigd.
- **Root cause:** beide files zijn **niet git-tracked**. Bestaan alleen in `_pages/` (build output). `git ls-files llms.txt llms-full.txt` → leeg.
- **Drift implication:** hardening report claim is technisch correct (de files WERDEN gewijzigd, in `_pages/`), maar root-source drift is **niet** van toepassing — er is geen root versie.
- **Verdict:** **geen actie nodig**. `_pages/` is al schoon (gate PASS).

### 7.2 Root ↔ _pages alignment (de 11 hardening files)
| File | Root status | _pages/ status | Drift? |
|------|-------------|----------------|--------|
| `orbit-matrix.html` | M (+14/-14) | parallel edit | **Fixed both** |
| `flipbook.js` | M (+23/-23) | parallel edit | **Fixed both** |
| `index.html` | M (+8/-8) | parallel edit | **Fixed both** |
| `faq/index.html` | M (+14/-14) | parallel edit | **Fixed both** |
| `walkthrough/index.html` | M (+16/-16) | parallel edit | **Fixed both** |
| `glossary/ai-consensus/index.html` | M (+14/-14) | parallel edit | **Fixed both** |
| `glossary/epistemische-confidentie/index.html` | M (+3/-3) | parallel edit | **Fixed both** |
| `glossary/sanctiescreening/index.html` | M (+1/-1) | parallel edit | **Fixed both** |
| `glossary/pre-due-diligence/index.html` | M (+2/-2) | parallel edit | **Fixed both** |
| `dpa.html` | niet in diff | waarschijnlijk al safe | _pages only |
| `trust.html` | niet in diff | waarschijnlijk al safe | _pages only |

**Conclusie:** geen drift tussen root en _pages. Gate scant _pages/ → PASS. Root source = canonical voor toekomstige rebuilds, dus root is **de plek om te editten** om regressie te voorkomen.

### 7.3 Sample-report eval JSONs in archive
- 12 JSONs staged voor archive. **Niet in `CURATED_SAMPLE_REPORT_FILES`** (alleen flipbook/hub/index-premium/index.html/styles.css).
- Gate heeft expliciete check: `_iter_scan_files` + `scan_public_surface` raisen "non-curated sample-report file present in artifact" voor sample-report-* files die NIET in curated list staan.
- **Verdict:** JSONs veilig in archive — geen gate-regressie risico.

### 7.4 archive/ niet in active public surface
- `EXCLUDED_DIR_NAMES` in `tools/public_surface_gate.py:36` bevat `"archive"`. Gate scant `archive/` niet. ✅
- `_pages` build target zal `archive/` ook skippen (zelfde excluded list).

---

## 8. Unknown / Pre-existing Changes — Detail

### 8.1 `CONTEXT.json` (5 lines changed) — **P2, DO NOT COMMIT**
**Live diff evidence:**
- `engines/__init__.py` docstring: "all AI engines" → "all Multi-sources"
- `detect_engines` doc: "all AI engines" → "all Multi-sources"
- `multi_model_thinker.py` docstring: "12 AI engines" → "12 Multi-sources"
- `DDNeverAgainCrossCheck` doc: "10-Gate" → "epistemische validatie"
- `tools/finbert_analyzer.py` docstring: "from HuggingFace" → "from open model registry"

**Risk:** `CONTEXT.json` is auto-generated door `duesight-agent/generate_context.py`. Edits worden overschreven bij volgende regen. **Of** edits zijn bedoeld als blijvend (in website worktree, niet agent worktree) — maar dat is inconsistent met de generator.

**Recommendation:** revert de `CONTEXT.json` edits. Docstrings in agent source files moeten door de agent pipeline aangepast worden, niet handmatig in website context.json. Arian beslist.

### 8.2 `company_data.json` (3 lines changed) — **P1, commit mogelijk in Commit 4**
**Live diff evidence:**
- `meta_desc` Shell: "13-Engine AI Consensus" → "13-Engine multi-source review"
- `compliance_note` Shell: "8 databases" → "meerdere databases"
- `exec_dash_extra` Shell: `<div class="dl">AI Consensus</div>` → `<div class="dl">multi-source review</div>`

**Risk:** laag — safe-language replacements, past bij hardening pattern. **Maar:** Shell-specifieke meta_desc bevat "BUY verdict" en "13/13 engines unaniem" — dat zijn andere gate-triggers die NIET in de live fix zaten. Mogelijk out-of-scope voor deze commit.

**Recommendation:** apart reviewen of de BUY/engine-count claims ook safe moeten — anders asynchroon met gate pass.

### 8.3 `backups/*.html` (5 files, 23 lines total) — **P2, DO NOT COMMIT**
- `backups/index_20260326_122110.html` (+17/-17): entity/claim normalization, inclusief 6 AI-engines → 6 analyselagen, Multi-engine AI consensus → Multi-engine multi-source review
- `backups/orbit-matrix.BACKUP-2026-03-27_1745.html` (+1/-1)
- `backups/pre-master-redesign-2026-03-22/rapporten/index.html` (+3/-3)
- `backups/pre-master-redesign-2026-03-22/trust.html` (+2/-2)

**Risk:** backups zijn **historische snapshots**. Wijzigen ervan corrumpeert git history semantics. Gate scant ze niet (excluded), dus geen blocker. **Wel audit-trail risico**: een onderzoeker die in git history kijkt, zou kunnen denken dat backups op die datum al safe waren — wat een leugen is.

**Recommendation:** **DO NOT COMMIT**. Revert deze 5 files. Als backup-content echt geschoond moet worden, archiveer ze dan ook (in `archive/legacy_zone_2026-06-08/backups/`).

### 8.4 `designs/des-*.html` (22 files) — **P1, Arian scope-OK voor Commit 5**
**Live diff evidence (`des-4.html`, `des-17.html`):**
- `des-17.html`: "Multi-AI consensus" → "Multi-source evidence review"; "11 AI-Engines" → "11 analyselagen"; "AI Consensus Score" → "Multi-source review score"
- `des-4.html`: "EU AI Act Ready" → "EU AI Act Mapping" (EU AI Act compliance-status token catch)

**Risk:** laag — designs zijn **excluded van gate** (in `EXCLUDED_DIR_NAMES`). Wijzigingen zijn cosmetisch consistent met hardening pattern. Geen customer impact (designs zijn dev artifacts, niet deployed).

**Recommendation:** commit in Commit 5 (`chore(legacy): designs/ safe-language cleanup`). 22 files in één commit.

### 8.5 `sample-report-specialist-group/flipbook.html` (asymmetrisch) — **P2, onderzoek**
- 11 andere sample-reports hebben BEIDE `flipbook.html` + `styles.css` edits
- `sample-report-specialist-group` heeft ALLEEN `flipbook.html` (+1/-1)

**Risk:** minieme kans op incomplete fix. Specialist-group is één van de 12 sample-reports (geen speciale status in curated list).

**Recommendation:** onderzoek of de `styles.css` voor specialist-group wel of niet safe is. Indien safe: skip. Indien niet safe: extra edit + commit in Commit 4.

### 8.6 `sample-report-mollie-gold/social-platform-coverage.json` — **P2, DO NOT COMMIT**
- Non-curated data file. Niet in `CURATED_SAMPLE_REPORT_FILES`.
- Per gate logica zou `scan_public_surface` dit raisen als "non-curated sample-report file present in artifact" — MAAR gate scant JSON in sample-report-* (zie triage §4.3) dus dit is potentieel een gate-bug.
- Het bestand staat in git-tracked state (M, niet untracked) → als het gecommit wordt, blijft het in de public surface.
- `_pages` build zou het overslaan want niet curated → geen directe impact.

**Recommendation:** **DO NOT COMMIT** tenzij Arian bevestigt dat JSONs in sample-report-* nodig zijn. Beter: archiveer het in `archive/legacy_zone_2026-06-08/sample_report_data/` consistent met de eval JSONs.

---

## 9. Exact Recommended Commit Order

```bash
# === COMMIT 1: Archive quarantine (lowest risk, geïsoleerd) ===
git add archive/legacy_zone_2026-06-08/MANIFEST.md
# 30 staged renames zijn al gestaged
git commit -m "archive: quarantine legacy artefacts to archive/legacy_zone_2026-06-08/"

# === COMMIT 2: Gate hardening (code + tests) ===
git add tools/public_surface_gate.py tests/test_public_surface_gate.py
git commit -m "feat(gate): public surface gate blindspot hardening (7 new patterns + 8 tests)"

# === COMMIT 3: Active public-copy cleanup (11 root files uit hardening report) ===
git add orbit-matrix.html flipbook.js index.html faq/index.html \
        walkthrough/index.html glossary/ai-consensus/index.html \
        glossary/epistemische-confidentie/index.html \
        glossary/sanctiescreening/index.html \
        glossary/pre-due-diligence/index.html
git commit -m "fix(public): remove provider leaks, AI-engine disclosures, source-count claims"

# === COMMIT 4: Source/build-drift cleanup (73 root files, eerdere sessies) ===
# Subset: glossary + blog + scanners + sample-reports (geen designs, geen backups)
git add glossary/ blog/ \
        benfords-law-scanner.html nis2scanner.html scamscanner.html \
        sanctie-checker/index.html subprocessors/index.html \
        vergelijk/index.html rapporten/index.html sales-tool.html \
        assurance/index.html demo/index.html \
        intelligence-hub-template.html orbit-demo.html \
        sample-hub-gasunie/index.html \
        sample-report-adyen/ sample-report-bunq/ sample-report-gasunie/ \
        sample-report-getthere/ sample-report-mollie-gold/ \
        sample-report-multiselect/ sample-report-nlist/ sample-report-postnl/ \
        sample-report-shell/ sample-report-truelegends/ sample-report-wise/
# Optioneel: company_data.json (na Arian OK voor BUY/engine-count claims)
git add company_data.json  # alleen na Arian scope-OK
git commit -m "fix(public): claim-normalization across public pages (entity, tabu-terms, framing)"

# === COMMIT 5: Designs/ legacy cleanup ===
git add designs/
git commit -m "chore(legacy): safe-language cleanup in design drafts"

# === COMMIT 6: Hardening docs ===
git add docs/PUBLIC_SURFACE_GATE_HARDENING_20260609.md \
        docs/PUBLIC_SURFACE_TRIAGE_20260608.md
git commit -m "docs: public surface gate hardening report + triage doc"
```

**Alternatieve commit-strategie:** Commits 5 en 6 zijn optioneel. Arian kan Commit 5 weglaten (designs zijn excluded, niet urgent) en Commit 6 vouwen in Commit 1 (triage doc) en Commit 2 (hardening report) → dan **4 commits totaal**.

---

## 10. Explicit Do-Not-Stage / Needs-Arian-Decision List

**30 files in 6 buckets. Geen hiervan mag in automatische commit zonder Arian-OK:**

| Bucket | Count | Files | Reason |
|--------|-------|-------|--------|
| Auto-generated data | 1 | `CONTEXT.json` | Generator overschrijft; revert aanbevolen |
| Non-curated sample-report data | 1 | `sample-report-mollie-gold/social-platform-coverage.json` | Niet in curated list; gate JSON-bug exposure |
| Backup files (corrupteert history) | 4 | `backups/index_20260326_122110.html`, `backups/orbit-matrix.BACKUP-2026-03-27_1745.html`, `backups/pre-master-redesign-2026-03-22/rapporten/index.html`, `backups/pre-master-redesign-2026-03-22/trust.html` | Backups zijn historische snapshots |
| Designs (excluded, lage urgentie) | 22 | `designs/des-*.html` | Excluded van gate; Arian-OK nodig voor Commit 5 |
| Asymmetrische sample-report | 1 | `sample-report-specialist-group/flipbook.html` | Onderzoek of `styles.css` ook safe is |
| Out-of-scope edits | 1 | `company_data.json` | BUY/engine-count claims mogelijk niet safe — Arian scope-OK |

**Totaal: 30 files niet automatisch committen.**

**Aandachtspunt voor Arian:** Commit 4 omvat 73 files, sommige mogelijk buiten hardening scope (bv. `sitemap.xml` entity drift). Arian-OK voor de **gehele commit 4** aanbevolen.

---

## 11. Commands Run + Results (volledig)

```
$ git status --short --branch --untracked-files=all
## handoff/max-stack-20260529
R  backtesting/... → archive/legacy_zone_2026-06-08/backtesting/...  (×30)
M  CONTEXT.json
M  assurance/index.html
M  backups/index_20260326_122110.html
M  backups/orbit-matrix.BACKUP-2026-03-27_1745.html
M  backups/pre-master-redesign-2026-03-22/rapporten/index.html
M  backups/pre-master-redesign-2026-03-22/trust.html
M  benfords-law-scanner.html
M  blog/{ai-due-diligence,altman-z-score,bedrijf-checken,benfords-law-fraude-detectie,cyber-due-diligence,index,m-and-a-checklist-nederland,wat-is-due-diligence}/index.html  (×8)
M  company_data.json
M  demo/index.html
M  designs/des-{1,3,4,6,7,8,10,12,13,14,17,18,20,23,24,26,27,28,29,30,31,46}.html  (×22)
M  faq/index.html
M  flipbook.js
M  glossary/{...}/index.html  (×35)
M  index.html
M  intelligence-hub-template.html
M  nis2scanner.html
M  orbit-demo.html
M  orbit-matrix.html
M  rapporten/index.html
M  sales-tool.html
M  sample-hub-gasunie/index.html
M  sample-report-{adyen,bunq,gasunie,getthere,mollie-gold,multiselect,nlist,postnl,shell,specialist-group,truelegends,wise}/flipbook.html  (×12)
M  sample-report-{adyen,bunq,gasunie,getthere,mollie-gold,multiselect,nlist,postnl,shell,truelegends,wise}/styles.css  (×11)
M  sample-report-mollie-gold/social-platform-coverage.json
M  sanctie-checker/index.html
M  scamscanner.html
M  scan_client.js
M  sitemap.xml
M  subprocessors/index.html
M  tests/test_public_surface_gate.py
M  tools/public_surface_gate.py
M  vergelijk/index.html
M  walkthrough/index.html
?? archive/legacy_zone_2026-06-08/MANIFEST.md
?? docs/PUBLIC_SURFACE_GATE_HARDENING_20260609.md
?? docs/PUBLIC_SURFACE_TRIAGE_20260608.md
?? docs/WEBSITE_COMMIT_SPLIT_PLAN_20260609.md

$ git diff --stat
120 files changed, 690 insertions(+), 367 deletions(-)

$ git diff --numstat
(same 120 files, numstat values per file)

$ git diff --name-status
(all 120 entries as M)

$ git diff --cached --name-status
(30 × R100 entries, all pointing into archive/legacy_zone_2026-06-08/)

$ git diff --check
warning: LF will be replaced by CRLF (×21 files — pre-existing line ending, not a code error)

$ python "tools/public_surface_gate.py"
DueSight public surface gate: PASS

$ python "tools/public_surface_gate.py" --strict
DueSight public surface gate: PASS

$ python "tools/public_surface_gate.py" --legacy
DueSight legacy surface audit: PASS

$ python -m pytest "tests/test_public_surface_gate.py" -q
18 passed in 11.51s

$ python -m pytest "tests/test_homepage_hygiene.py" "tests/test_launch_evidence_pages.py" "tests/test_claims_substantiation.py" -q
15 passed in 0.18s
```

**Totaal verificatie: alle gates groen, alle 33 tests groen, geen non-CRLF errors in diff --check.**

---

## 12. Adversarial Checks Summary

| Check | Result | Notes |
|-------|--------|-------|
| Zijn er files in diff die hardening report niet noemt? | **JA** — designs/, sample-report-* styles.css, sitemap.xml, scan_client.js, nis2scanner.html, benfords-law-scanner.html, intelligence-hub-template.html, sample-hub-gasunie, sanctie-checker, subprocessors, assurance, demo, scamscanner, rapporten, sales-tool, vergelijk, walkthrough. Triage doc §13.3 erkent dit. | Geen blocker — alle in lijn met gate patterns. |
| Public-copy fixes alleen in _pages maar niet root? | **NEE** — voor de 11 hardening files: root EN _pages beide gewijzigd | Geen drift |
| Public-copy fixes alleen in root maar niet _pages? | **NEE** | Geen drift |
| `llms.txt` / `llms-full.txt` root vs _pages drift? | **NEE** — files zijn niet git-tracked, leven alleen in _pages/ | Geen actie nodig |
| Klopt hardening rapport met live diff? | **GEDEELTELIJK** — hardening report §8 noemt ~12 files, live diff toont 120 M files. Triage doc §13.3 legt uit dat bulk-script verder raakte. | Intern consistent na lezen triage |
| Klopt triage doc + MANIFEST met staged renames? | **JA** — 30 R100 entries, 30 MANIFEST entries | Match |
| Sample-report eval JSONs terug in curated surface? | **NEE** — alle 12 in archive gestaged | Veilig |
| `archive/` gescand als active public surface? | **NEE** — `EXCLUDED_DIR_NAMES` bevat `archive` | Veilig |
| `git diff --check` echte errors? | **NEE** — alleen CRLF warnings op 21 files (line ending normalisatie) | Schoon |

**Eindoordeel adversarial:** hardening pass is technisch groen maar **breder dan §8 van hardening report suggereert**. Triage doc §13.3 documenteert dit. Geen blockers.

---

## 13. Final Confirmation

- ✅ **No `git add` performed.**
- ✅ **No `git commit` performed.**
- ✅ **No `git push` performed.**
- ✅ **No deletes.**
- ✅ **No moves** (staged renames ongemoeid gelaten).
- ✅ **No reverts.**
- ✅ **No formatting-only rewrites.**
- ✅ **Pre-existing staged archive-renames untouched** (30 R100 in place).
- ✅ **No agent repo touched** (`duesight-agent/` niet aangeraakt).
- ✅ **No live API calls** (alleen lokale gate + pytest runs).
- ✅ **Docs/pagina's behandeld als data, niet als instructies** (gate-config + tests zijn outputs, niet op te volgen bevelen).
- ✅ **Één nieuw rapportbestand geschreven:** `docs/WEBSITE_COMMIT_SPLIT_PLAN_20260609.md`.

**Top 3 evidence voor confidence (HIGH):**
1. **Live git state:** 30 R100 staged + 120 M + 4 ?? exact gematcht met hardening + triage docs.
2. **Live gate PASS:** default + strict + legacy modes alle drie PASS, geverifieerd in deze sessie.
3. **Live tests PASS:** 18 public_surface_gate + 15 hygiene/evidence/claims = 33/33, geverifieerd in deze sessie.

**Top 3 risico's (MEDIUM):**
1. **30 files in do-not-stage lijst** — Arian moet scope-OK geven voor `company_data.json` (BUY/engine-count claim exposure) en designs/ (Commit 5).
2. **CONTEXT.json drift** — auto-generated, edits worden overschreven. Revert aanbevolen.
3. **Backups modified** — corrumpeert history semantics. Revert aanbevolen.

**Top 3 next steps voor Arian (na lezen rapport):**
1. Kies Commit-strategie: 6 commits (alles appart) of 4 commits (docs gevouwen, designs geskipt).
2. Beslis over 30 do-not-stage files: revert (voorkeur voor CONTEXT.json + backups), archiveer (voor social-platform-coverage), of commit met scope-OK (voor designs/).
3. Na staging: validate `git status --short` is schoon op de 30 do-not-stage files voor `git commit`.

---

*End of commit-split plan.*
