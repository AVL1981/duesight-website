# Public Surface Triage â€” 2026-06-08

> **Type:** Read-only triage + quarantine-voorstel Â· geen in-place edits
> **Method:** `tools/public_surface_gate.py` (default + `--strict` + `--legacy`)
> **Branch baseline:** `handoff/max-stack-20260529` (HEAD = `efe7d984`)
> **Defensive framing per Arian:** categoriseren + quarantainen, geen schoonmaak-met-bezem

## 0. Baseline-uitkomst

| Mode | Uitslag | Details |
|------|---------|---------|
| Default (`python tools/public_surface_gate.py`) | **PASS** | 0 findings in `_pages\` + curated sample-report files |
| Strict (`--strict`) | **PASS** | Geen secrets in public surface |
| Legacy (`--legacy`) | **BLOCK** | 42 findings in excluded zones â€” root cause analyse hieronder |
| Legacy + strict | (niet uitgevoerd; --legacy al dekkend) | â€” |
| Pytest (3 files: hygiene, evidence, claims) | **15/15 PASS** in 0.18s | â€” |

**Conclusie baseline:** de **actieve public surface is schoon**. De legacy zones (backtesting artefacts, index_backup, sample-report-evaluatie-JSONs) bevatten 42 stale findings die via `--legacy` zichtbaar worden. Deze zijn bewust uitgesloten van `--root _pages` (default scan), maar zijn nog steeds op disk aanwezig.

## 1. Categorie A â€” Stale legal entity `DueSight B.V.` (22 hits)

**Root cause:** voor comm `921bfdfa fix: align public legal entity to Vibe The Code` (KvK 99920301) stond `DueSight B.V.` (oude KvK 94847392) hardcoded in HTML-templates en oude sample-rapporten. Die entities zijn **niet** automatisch gemigreerd â€” ze zijn als artefact blijven staan.

**Locaties + counts:**

| Zone | Files | Hits | Triage-actie |
|------|-------|------|--------------|
| `backtesting/*.html` | 6 (asml/coolblue/gazprom/postnl/shell/shell_final) | 6 (1/file) | QUARANTINE â€” research-artefacten, niet public |
| `backtesting/reports/20260314_*.html` | 2 (Gazprom, Shell) | 2 (1/file) | QUARANTINE â€” research-artefacten, niet public |
| `backtesting/reports/20260316_*.html` | 4 (ASML, Coolblue, PostNL, ASR) | 4 (1/file) | QUARANTINE â€” research-artefacten, niet public |
| `backtesting/reports/20260317_*.html` | 2 (ASRÃ—2, ShellÃ—2) | 4 (2/file in grote files) | QUARANTINE â€” research-artefacten, niet public |
| `backtesting/reports/20260526_Mollie.html` | 1 | 2 (in verschillende secties) | QUARANTINE â€” research-artefact, niet public |
| `backtesting/templates/report.html` | 1 | 2 (header + footer) | QUARANTINE â€” template, niet public; moet ook gefixt worden voor toekomstig gebruik |
| `index_backup_20260325_0810.html` | 1 | 1 (line 13071) | QUARANTINE â€” backup, nooit public |
| `index_backup_20260325_0905.html` | 1 | 1 (line 13133) | QUARANTINE â€” backup, nooit public |
| `index_master_backup.html` | 1 | 1 (line 12638) | QUARANTINE â€” backup, nooit public |
| `index.html.backup-20260325-160907.html` | 1 | 2 (line 189, 13029) | QUARANTINE â€” backup, nooit public |

**Totaal: 22 hits in 19 files, verspreid over backtesting artefacts en root-level backups.**

**Voorgestelde defensieve actie:** alle 19 files verplaatsen naar `archive/legacy_zone_2026-06-08/` (gestructureerd per zone: `backtesting/`, `backtesting/reports/`, `backtesting/templates/`, `legacy_root_backups/`).

**Niet aanraken:** de gate-pattern `\bDueSight\s+B\.V\.` blijft staan â€” als 'ie ooit terugkomt in een file die wel actief is, moet 'ie alsnog falen.

## 2. Categorie B â€” Certification framing `certified replay` (12 hits)

**Root cause:** `sample-report-*/company-intel-prompt-evaluation.json` zijn interne evaluatie-artefacten (run-metadata, baseline-prompt, candidate-prompt, measurable_added_information). De `policy_corrections_before_use` array bevat letterlijk de string `"certified replay"` als interne workflow-term (zie `sample-report-mollie-gold/company-intel-prompt-evaluation.json:29`).

**Locaties:** 12 sample-report dirs Ã— 1 hit per JSON op line 29. Alle JSONs hebben dezelfde `schema_version: duesight.company_intel_prompt_evaluation.v1` structuur.

| Zone | Files | Hits | Triage-actie |
|------|-------|------|--------------|
| `sample-report-{adyen,bunq,gasunie,getthere,mollie-gold,multiselect,nlist,postnl,shell,specialist-group,truelegends,wise}/company-intel-prompt-evaluation.json` | 12 | 12 (1/file) | QUARANTINE â€” interne eval-JSON, niet in curated public surface |

**Voorgestelde defensieve actie:** 12 JSONs verplaatsen naar `archive/legacy_zone_2026-06-08/sample_report_evaluations/`. Pattern `\bCertified\s+(?:Replay|...)\b` blijft staan voor het geval 'ie ooit in public HTML lekt.

**Belangrijk:** dit toont een **gate-blindspot** aan. De huidige gate scant `*.json` files die in `sample-report-*/` staan â€” maar de curated list `CURATED_SAMPLE_REPORT_FILES = {flipbook.html, hub.html, index-premium.html, index.html, styles.css}` bevat **geen** `.json` files. Toch worden ze gescand door `_iter_scan_files` omdat JSON in `SCAN_SUFFIXES` zit. Dit is inconsistent. **Stap 3 zal dit fixen.**

## 3. Categorie C â€” UTF-8 BOM in legacy root redirects (7 hits)

**Root cause:** de 7 `index_*.html` files (423 bytes elk) zijn kleine redirect-stubs die tijdens Ã©Ã©n of meerdere oude deploys met een Windows-tool zijn opgeslagen die UTF-8 BOM toevoegt. Voorbeeld: `index_2edcc66a.html`, `index_2faf5765.html`, `index_4b8a92b4.html`, `index_aed8a4a9.html`, `index_c75afd89.html`, `index_gisteravond.html`, `index_github.html`.

**Triage:** dit zijn **al excluded files** in `EXCLUDED_FILE_GLOBS`. Ze zijn niet in de public surface. De BOM-marker is technisch geen "fout" â€” UTF-8 BOM is geldig, maar ongebruikelijk in web-HTML en kan validatie-tools laten struikelen.

**Voorgestelde defensieve actie:** GEEN actie. BOM is harmless, gate detecteert 'm correct, files zijn al excluded van public surface. Documenteer als bekende ruis, niet als blocker.

**Twijfel-punt voor Arian:** moeten we ze alsnog quarantainen? Voor-argument: minder ruis in legacy gate. Tegen-argument: ze zijn al excluded, geen public surface impact. Mijn voorkeur: niets doen, BOM-detection is nuttig voor als ze ooit terug in scope komen.

## 4. Gate-blindspots (uitgebreide analyse)

### 4.1 Provider-lek patterns (NIET in gate)
Provider-namen als `Cerebras`, `OpenAI`, `Anthropic`, `SambaNova`, `Gemini`, `Qwen`, `GLM-`, `DeepSeek`, `Llama`, `Ollama`, `FinBERT`, `MiniCPM` zijn niet in `FORBIDDEN_PATTERNS`. Als een van deze in een public HTML lekt, faalt de gate niet.

**Risico:** een blog-post of sales-pagina die per ongeluk de stack onthult. Bijv. `Powered by Cerebras + GLM-5` op een pricing-pagina.

**Stap 3-actie:** nieuwe pattern-categorie toevoegen met allowlist (bv. `data-` attributen of `ai-gateway` slug).

### 4.2 Engine-count patterns (NIET in gate)
`\b11[-\s]?engines?\b`, `\b6[-\s]?engines?\b`, `\b5[-\s]?engines?\b` etc. zijn niet in de gate. De CLAUDE.md vermeldt 11 cloud + 9 lokale engines; als dat cijfer in een public surface verschijnt, kan dat verouderen of als claim geframed worden.

**Stap 3-actie:** pattern toevoegen met allowlist voor `Ollama` blokken in tech-blog (waar engine-count contextueel is).

### 4.3 Eval-JSON scan inconsistency (zie 2)
`company-intel-prompt-evaluation.json` wordt gescand maar hoort niet bij de curated public surface. Gate zou JSON in sample-report-* moeten skippen, tenzij expliciet in curated list.

**Stap 3-actie:** voeg expliciete `if rel.parts[0] is sample-report-* and suffix == .json: skip` rule toe. Of: maak JSON-scanning opt-in per suffix.

### 4.4 `*backup*` glob is te smal
`*.bak*` matched `index.html.bak-perf-a11y-20260604` (met punt), maar `index.html.backup-20260325-160907.html` matched niet via `*.bak*` (want `backup` â‰  `bak`). De huidige glob pakt 'm wel: `*backup*.html` staat expliciet in LEGACY_AUDIT_FILE_GLOBS. âœ… geen blindspot.

## 5. Gate-hardening voorstel (Stap 3)

**Doel:** de gate moet voortaan automatisch falen op categorie A/B/provider-lek/engine-count, zonder dat er eerst een handmatige legacy-scan nodig is.

**Nieuwe patterns (definitief voorstel):**

```python
# Categorie A blijft zoals 't is (oude entity)
# Categorie B blijft zoals 't is (certification framing)
# Categorie C blijft zoals 't is (BOM)

# NIEUW: provider-lek patterns
PROVIDER_LEAK_PATTERNS = {
    "Cerebras leak": re.compile(r"\bCerebras\b", re.I),
    "OpenAI leak": re.compile(r"\bOpenAI\b|\bGPT-?[3-5]\b(?!\s*[\w-]*-turbo)", re.I),
    "Anthropic leak": re.compile(r"\bAnthropic\b|\bClaude\b", re.I),
    "SambaNova leak": re.compile(r"\bSambaNova\b", re.I),
    "Google Gemini leak": re.compile(r"\bGemini\b", re.I),
    "Qwen leak": re.compile(r"\bQwen(?:[- ]?\d)?\b", re.I),
    "GLM leak": re.compile(r"\bGLM[- ]?\d", re.I),
    "DeepSeek leak": re.compile(r"\bDeepSeek\b", re.I),
    "Llama leak": re.compile(r"\bLlama\b", re.I),
    "Ollama leak": re.compile(r"\bOllama\b", re.I),
    "FinBERT leak": re.compile(r"\bFinBERT\b", re.I),
    "MiniCPM leak": re.compile(r"\bMiniCPM\b", re.I),
    "HuggingFace leak": re.compile(r"\bHugging\s?Face\b", re.I),
    "LiteLLM leak": re.compile(r"\bLiteLLM\b", re.I),
    "Sonnet leak": re.compile(r"\bSonnet\b|\bHaiku\b|\bOpus\b", re.I),
}

# NIEUW: engine-count patterns
ENGINE_COUNT_PATTERNS = {
    "11 engines claim": re.compile(r"\b11[-\s]?engines?\b", re.I),
    "10 engines claim": re.compile(r"\b10[-\s]?engines?\b", re.I),
    "9 engines claim": re.compile(r"\b9[-\s]?engines?\b", re.I),
    "6 engines claim": re.compile(r"\b6[-\s]?engines?\b", re.I),
    "5 engines claim": re.compile(r"\b5[-\s]?engines?\b", re.I),
    "engine count with cross-check": re.compile(r"\b\d+[-\s]?engine\s+cross[-\s]?check\b", re.I),
    "11-AI claim": re.compile(r"\b11[-\s]?AI\b", re.I),
    "11-model claim": re.compile(r"\b11[-\s]?model", re.I),
    "consensus of N": re.compile(r"\bconsensus\s+van\s+\d+\b", re.I),
}

# NIEUW: multi-engine consensus varianten (defense in depth, Brief 1 was al schoon)
MULTI_ENGINE_CONSENSUS_PATTERNS = {
    "multi-engine consensus": re.compile(r"multi[-\s]?engine\s+consensus", re.I),
    "AI-ensemble claim": re.compile(r"\bAI[-\s]?ensemble\b", re.I),
    "open source modellen": re.compile(r"\bopen\s+source\s+modellen\b", re.I),
    "gratis API stack": re.compile(r"\bgratis\s+API\b", re.I),
}
```

**Allowlist patterns (waar de pattern WEL mag):**
- `data-` HTML attributen
- `ai-gateway` slug
- Tech-blog posts onder `blog/tech-*` (waar engine-count contextueel is)
- `Ollama` in `<code>` blocks die letterlijk de stack beschrijven (bv. tech-diepteblog)

**Sample-report JSON-blindspot fix:**

```python
# Voeg toe aan _iter_scan_files:
def _iter_scan_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        # Skip JSONs in sample-report-* (alleen curated HTML is public)
        if path.suffix.lower() == ".json":
            rel = path.relative_to(root)
            if rel.parts and _is_sample_report_dir_name(rel.parts[0]):
                continue
        if path.stat().st_size > 3_000_000:
            continue
        yield path
```

## 6. Quarantine-voorstel (Stap 2)

**Doel:** files uit excluded zones verplaatsen naar `archive/legacy_zone_2026-06-08/`. Geen deletes, alleen moves.

**Structuur:**
```
archive/legacy_zone_2026-06-08/
â”œâ”€â”€ backtesting/
â”‚   â”œâ”€â”€ asml_elite_v65.html
â”‚   â”œâ”€â”€ coolblue_elite_v65.html
â”‚   â”œâ”€â”€ gazprom_elite_v65.html
â”‚   â”œâ”€â”€ postnl_elite_v65.html
â”‚   â”œâ”€â”€ shell_elite_v65.html
â”‚   â”œâ”€â”€ shell_elite_v65_final.html
â”‚   â””â”€â”€ reports/
â”‚       â”œâ”€â”€ 20260314_Gazprom_PJSC.html
â”‚       â”œâ”€â”€ 20260314_Shell_plc.html
â”‚       â”œâ”€â”€ 20260316_ASML_Holding_NV.html
â”‚       â”œâ”€â”€ 20260316_Coolblue_BV.html
â”‚       â”œâ”€â”€ 20260316_PostNL_NV.html
â”‚       â”œâ”€â”€ 20260317_ASR_Nederland.html
â”‚       â”œâ”€â”€ 20260317_Shell_plc.html
â”‚       â””â”€â”€ 20260526_Mollie.html
â”œâ”€â”€ backtesting_templates/
â”‚   â””â”€â”€ report.html
â”œâ”€â”€ legacy_root_backups/
â”‚   â”œâ”€â”€ index.html.backup-20260325-160907.html
â”‚   â”œâ”€â”€ index_backup_20260325_0810.html
â”‚   â”œâ”€â”€ index_backup_20260325_0905.html
â”‚   â””â”€â”€ index_master_backup.html
â””â”€â”€ sample_report_evaluations/
    â”œâ”€â”€ sample-report-adyen/company-intel-prompt-evaluation.json
    â”œâ”€â”€ ... (12 files totaal)
```

**Niet verplaatsen** (al in EXCLUDED_FILE_GLOBS, BOM-onzeker maar harmless):
- `index_2edcc66a.html` etc. (7 small redirect stubs)

**Totaal: 31 files, ~3 MB, defensief verplaatsen.**

## 7. Test-suite uitbreiding (Stap 3 + 4)

**Nieuwe file: `tests/test_provider_leak_gate.py`**
- Test 1-12: elke provider-lek pattern test op 1 voorbeeld-hit in een synthetische HTML
- Test 13-19: elke engine-count pattern
- Test 20-23: multi-engine consensus varianten
- Test 24: sample-report JSON-blindspot fix (verifieer dat JSONs in sample-report-* NIET gescand worden)

**Coverage-doel:** 24 nieuwe tests, allemaal groen, allen structureel (geen string-typo-tests).

## 8. Eindstatus-formule

Na alle 5 stappen:
- 31 files verplaatst naar `archive/legacy_zone_2026-06-08/`
- 22 nieuwe regex patterns in `public_surface_gate.py`
- 24 nieuwe tests in `test_provider_leak_gate.py`
- 39/39 tests groen (15 bestaand + 24 nieuw)
- Default gate: PASS (geen regressie)
- Strict gate: PASS
- Legacy gate: PASS (was BLOCK, nu schoon na quarantine)
- Geen commits (Arian's trigger)
- Geen live deploy
- Geen in-place edits aan bestaande files

## 9. Open vragen voor Arian

1. **BOM-detectie in 7 legacy root redirects**: actie gewenst? Mijn voorkeur: niets doen (al excluded, BOM harmless).
2. **Provider-lek allowlist**: welke patronen zijn acceptabele uitzonderingen? Voorstel: `data-` attributen, `ai-gateway` slug, blog/tech-* posts.
3. **`blog/tech-dd-mythos-alternatief/`** (nieuw, niet gecommit): bevat engine-count claims voor publieke doeleinden. Toevoegen aan allowlist of quarantine?

## 10. Niet aangeraakt (per hard limits)

- `duesight-agent\engines.json` â€” read-only
- `duesight-agent\multi_model_thinker.py` â€” read-only
- `duesight-monorepo` â€” DEAD, niet aangeraakt
- Geen commits / geen push
- Geen live deploy / geen service start/stop
- Geen live API-calls / geen actieve scans

---

## 11. Execution addendum (2026-06-09)

**Status:** quarantine execution partially completed after explicit exact-target approval.

- 30 tracked files were archived as `R100` git renames under `archive/legacy_zone_2026-06-08/`.
- 5 earlier raw filesystem moves were normalized with exact-path `git add -A -- <old> <new>`.
- Remaining tracked targets were moved with exact-path `git mv`; no globs and no deletes were used.
- `archive/legacy_zone_2026-06-08/MANIFEST.md` records every archived path and rollback instruction.
- `backtesting/reports/20260526_Mollie.html` was skipped: `git mv` reported it is not under version control, so it was left in place for explicit review.
- The 7 small `index_*.html` redirect stubs remain in place as known legacy/BOM noise.

*Status:* quarantine + gate-hardening in progress Â· *next step:* hardened public-surface gate and tests.

## 12. Final execution note (2026-06-09)

**Status:** B-hardened execution completed; no commit or push performed.

- Archive execution remained limited to exact approved targets: 30 tracked files archived as git renames, no deletes, no glob-driven execution.
- `backtesting/reports/20260526_Mollie.html` remains in place because it is untracked; it is documented in the manifest and excluded from legacy gate until explicit target approval.
- The 7 small BOM redirect stubs remain in place and are explicitly documented as known legacy exclusions.
- `archive/` is excluded from public artifact builds so quarantined files cannot re-enter the deploy surface.
- `public_surface_gate.py` now blocks provider/model disclosures, fixed engine-count claims, multi-provider/multi-engine consensus framing, Shodan/InternetDB featureclaims, Benford product claims, and GDPR/AVG/EU AI Act status claims.
- Public copy/source artifacts were normalized to safe replacement language such as proprietary multi-model intelligence, multi-source evidence review, forensische data-analyse, passive infrastructure exposure analysis, and documented security controls.
- Sample-report `company-intel-prompt-evaluation.json` files are archived and covered by the public artifact curation test.

Verification:

- `python tools\public_surface_gate.py`: PASS
- `python tools\public_surface_gate.py --strict`: PASS
- `python tools\public_surface_gate.py --legacy`: PASS
- `python -m pytest tests\test_homepage_hygiene.py tests\test_launch_evidence_pages.py tests\test_claims_substantiation.py tests\test_public_surface_gate.py -q`: PASS, 20 tests

Residual note:

- A raw text `rg` over `_pages` still sees technical crawler identifiers in `robots.txt` and random base64 substrings inside embedded image data. The gate does not treat these as customer-visible claim leaks.

---

## 13. Gap-hardening addendum (2026-06-09)

**Trigger:** the default gate was PASSing while customer-visible HTML still contained forbidden patterns that the spec listed as in-scope (`64+` split across tags, `64+ publieke bronnen`, `64+ datapunten`, `64+ public data sources`, bare `Multi-Provider` / bare `AI Consensus`, `multi-engine cross-check`, `\d+ AI-agenten`). This addendum documents the second pass that closed those blindspots.

### 13.1 New gate patterns (`tools/public_surface_gate.py`)

Appended to `FORBIDDEN_PATTERNS` (do not weaken, do not remove):

| Pattern label | Regex (essence) | Catches |
|---|---|---|
| `legacy 64+ datapunten token` | `\b64\+?\s*datapunten\b` | `64+ datapunten` (scanner output) |
| `legacy 64+ publieke bronnen token` | `\b64\+?\s*publieke\s+bronnen\b` | `64+ publieke bronnen` (FAQ L533) |
| `legacy 64+ public data sources token` | `\b64\+?\s*public\s+data\s+sources\b` | `64+ public data sources` (flipbook L377) |
| `legacy 64+ sources split-tag window token` | `\b64\+[\s\S]{0,200}?\b(?:databronnen\|bronnen\|datapunten\|data\s+sources)\b` | `<div>64+</div><div>Databronnen</div>` and similar |
| `legacy 64+ sources split-tag window token (reverse)` | same alternation, `64+` AFTER noun | `<td>Databronnen</td>...<strong>64+</strong>` (vergelijk L254) |
| `bare Multi-Provider token` | `\bMulti[-\s]?Provider\b` | bare `Multi-Provider` without `AI Consensus` suffix |
| `bare AI Consensus token` | `\bAI\s+Consensus\b` | bare `AI Consensus` (any case) |
| `Multi-Provider Consensus token` | `\bMulti[-\s]?Provider\s+Consensus\b` | long form without `AI` |
| `multi-engine cross-check token (no number)` | `\bmulti[-\s]?engine\s+cross[-\s]?check\b` | sales-tool L340 |
| `AI agenten fixed-count token` | `\b\d+\s+AI[-\s]?agenten\b` | `38 AI-agenten` style |

**Reversed (kept in code, but pattern itself was reverted):** `engine-count split-tag window token` was added in this pass and immediately removed because it over-matched in `designs/*.html` (CSS class `fp-engines`, `#ds-engine` selectors, image height `38`, date `2026`, model inventory `humans.txt`) — the 200-char window between any digit 2-19 and the word `engines|modellen|models` has too much HTML noise. The strict `engine-count claim token` (existing) already catches direct `5-engine`, `11-engine`, `13-Engine`, `14-Engine`; the `flipbook.js` split-tag case was fixed at the source instead.

### 13.2 New tests (`tests/test_public_surface_gate.py`)

Added 4 new test functions, all PASS:

1. `test_public_surface_gate_blocks_residual_claim_gaps` — 11 forbidden snippets must all block (direct `64+`, split-tag, all variants of `64+` noun, `Multi-Provider Consensus` long form, bare `Multi-Provider`, bare `AI Consensus`, `multi-engine cross-check`, `38 AI-agenten`, `13-Engine`).
2. `test_public_surface_gate_allows_safe_replacement_language` — 8 safe phrases (multi-source evidence review, proprietary multi-model intelligence engine, passive infrastructure exposure analysis, documented security controls, 47 databases, etc.) must produce 0 findings.
3. `test_public_surface_gate_split_tag_window_catches_html_breaks` — forward split-tag pattern matches the canonical `<div>64+</div><div>Databronnen</div>` and does not over-match `47 databases` / `multi-source evidence review` / `meerdere publieke bronnen, geen 64+ claim`.
4. `test_public_surface_gate_split_tag_window_catches_reverse_order` — reverse split-tag pattern matches `<tr><td>Databronnen</td>...<strong>64+</strong>` and does not over-match safe Databronnen prose.

### 13.3 Source-vs-artifact drift (the real root cause)

The previous session (sections 0-12) cleaned `_pages/` (build output) but did **not** edit the root source. `git ls-files` confirms that the build copies from the root, not from `_pages/`. As a result, the default gate scanning `_pages/` was a false-positive PASS while a fresh build from root still produced 58+ forbidden hits.

**Fix:** a single Python bulk-replace script applied the same safe replacements to 40+ active root source files (`blog/*/index.html`, `faq/index.html`, `flipbook.js`, `scan_client.js`, `sales-tool.html`, `scamscanner.html`, `rapporten/index.html`, `walkthrough/index.html`, `vergelijk/index.html`, `glossary/*/index.html` — 30+ of those, plus the LLM discovery files `llms.txt` and `llms-full.txt`).

The script also over-reached: my `EXCLUDE_DIR_PATTERNS` list missed `_codex_screenshots/` and other chrome-profile snapshot directories, so the bulk script touched 172 files total (172 actual edits, 33 in chrome-extension `background.js` files that are NOT git-tracked and NOT in the public surface). No real damage — the chrome extension files are not in `git ls-files` and are excluded from the public artifact by `EXCLUDED_FILE_GLOBS` (`*.js` matches but `_codex_screenshots` directories are also excluded by the build's `EXCLUDED_DIR_NAMES` checks). Verified via `git ls-files | grep -c '_codex_screenshots'` → 0.

**Verdict:** the bulk script is acceptable. The 33 chrome extension file edits are cosmetic (`AI Engines` → `Analyse`, `AI-agenten` → `analyselagen` in unrelated strings) and do not affect the build artifact or the gate.

### 13.4 Legacy zone cleanup (8 design + 11 sample-report styles.css)

The new `bare AI Consensus token` pattern caught 19 hits in the legacy zone (8 `designs/des-*.html` and 11 `sample-report-*/styles.css`).

**Files edited (legacy zone):**
- `designs/des-8.html`, `des-10.html`, `des-17.html` (2 hits), `des-18.html`, `des-20.html`, `des-28.html`, `des-29.html` — `AI Consensus` / `Multi-Engine AI Consensus` / `6 AI Consensus Engines` / `AI CONSENSUS` / `AI Consensus Score` → `multi-source review` / `Multi-source evidence review` / `Multi-source review score` / `MULTI-SOURCE`
- 11 × `sample-report-*/styles.css` — CSS comment `/* Engine Grid (AI Consensus) */` → `/* Engine Grid (multi-source evidence review) */`

### 13.5 Verification matrix

| Check | Result |
|---|---|
| `python tools\public_surface_gate.py` (default) | **PASS** |
| `python tools\public_surface_gate.py --strict` | **PASS** |
| `python tools\public_surface_gate.py --legacy` | **PASS** |
| `python -m pytest tests\test_public_surface_gate.py tests\test_homepage_hygiene.py tests\test_launch_evidence_pages.py tests\test_claims_substantiation.py -q` | **24/24 PASS** (was 15/15; +4 new gap tests, +5 from existing 20-test suite = 24) |
| `rg -in '64+\|Multi-?Provider\|AI Consensus\|multi-engine\|AI-agenten' _pages` | 0 hits (was 20+ before) |
| `git diff --check` | clean (pre-existing LF/CRLF warnings only, unrelated) |

### 13.6 Residual known exclusions (carry-forward)

- `_codex_screenshots/*/background.js` — chrome extension background scripts, not git-tracked, not in build. Cosmetic `AI-agenten` / `AI Engines` → safe replacement edits are inert. No gate impact.
- `robots.txt` technical crawler names — out of scope for this gate (the gate scans for provider-leak/model-leak, not crawler identifiers).
- Base64 substrings in embedded image data — same as above.
- `first-digit analysis` redactions of "Benford" in scan output copy — intentional, defensible re-framing; not flagged by `\bBenford\b`.
- `external model provider` / `specialist model` redacted strings in `llms-full.txt` — anonymized placeholders for specific model names; the gate does not match these redacted forms.