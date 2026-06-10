# Public Surface Gate Hardening — 9 Jun 2026

**Branch:** `handoff/max-stack-20260529`
**Scope:** Gate pattern additions + public-copy cleanup for blindspots
**No commit/push.**

---

## 1. Executive Summary

The public-surface gate now covers the blindspot families from the hardening brief: provider/model disclosures, engine/source-count claims, consensus claims, Shodan/InternetDB featureclaims, Benford product framing, and GDPR/AVG/EU AI Act compliance-status framing. Public copy was cleaned in `_pages/` and aligned in the corresponding root source files where needed; root `llms-full.txt` was also corrected after review so Shodan/Benford wording cannot re-enter on rebuild.

**Verification:**
| Mode | Before | After |
|------|--------|-------|
| Default (`python tools/public_surface_gate.py`) | PASS | **PASS** |
| Strict (`--strict`) | PASS | **PASS** |
| Legacy (`--legacy`) | PASS | **PASS** |
| Gate tests | 10 passed | **18 passed** |
| Hygiene/evidence/claims tests | 15 passed | **15 passed** |

---

## 2. Pattern Families Covered

| # | Pattern Family | Catches | Safe wording / exception |
|---|----------------|---------|-------------------------|
| 1 | `provider/model disclosure token` | OpenAI/Anthropic/Claude/Gemini/GPT/DeepSeek/Llama/Mistral/Qwen/Ollama/Cerebras/SambaNova/FinBERT/GLM/MiniCPM/Hugging Face/LiteLLM style leaks | generic provider-neutral language |
| 2 | `engine-count claim token` + `AI-engines disclosure token` | `11 engines`, `5-engine`, `AI-engines`, `AI engines`, model-count framing | "meerdere analyselagen", "proprietary multi-model intelligence engine" |
| 3 | Source-count / `64+` source patterns | `64+ bronnen`, `64+ datapunten`, split-tag `64+ ... Databronnen`, `27 bronnen`, `N bronnen` | "meerdere bronnen", "meerdere databronnen" |
| 4 | `fixed-count databases token` | `8 databases`, `5 databases`, `N databases` | `47 databases` remains explicitly allowed |
| 5 | Gate-count claims | `10-Gate`, `5-Gate`, `N Gate` | "meertraps validatie" |
| 6 | Consensus claims | `Multi-Provider AI Consensus`, bare `AI Consensus`, `multi-engine consensus`, `consensus-stack`, `dual-model AI` | "multi-source evidence review", "analyselaag" |
| 7 | `Shodan/InternetDB featureclaim token` | Shodan / InternetDB public featureclaims | "passive infrastructure exposure analysis" |
| 8 | Benford product framing | Benford / Benford's public product-claim wording | "first-digit analysis", "forensische data-analyse" |
| 9 | Compliance-status framing | GDPR/AVG compliant/conform/ready; EU AI Act compliant/conform/ready; ISO/SOC claims remain blocked | "documented security controls" |

**Existing patterns unchanged** — all 30+ existing forbidden patterns remain in place.

---

## 3. Allowlist / Safe Replacements

The following language is explicitly tested to NOT trigger the gate:

```
proprietary multi-model intelligence engine
multi-source evidence review
forensische data-analyse
passive infrastructure exposure analysis
documented security controls
47 databases
meerdere analyselagen
meerdere sanctielijsten
uitgebreide sanctiedekking
Geautomatiseerde sanctiescreening
public-source based pre-diligence
bronherleidbare publieke bronnen
meerdere databronnen
meerdere bronnen
```

---

## 4. Public-Copy Changes

### 4.1 _pages/ (deploy surface) — files modified

| File | Change | Before → After |
|------|--------|---------------|
| `orbit-matrix.html` | HuggingFace → Model Hub (name + favicon URL) | `{name:'HuggingFace',...` → `{name:'Model Hub',...` |
| `flipbook.js` | "5 databases" → generic | `across 5 databases` → `across meerdere sanctielijsten` |
| `index.html` | "Evidence AI Engine" badge → generic | `Evidence AI Engine` → `Evidence Review` |
| `index.html` | "27 bronnen" / "24 bronnen" → generic | `uit 27 bronnen` → `uit meerdere bronnen` |
| `faq/index.html` | "8 databases" (×3) → generic | `8 databases` → `meerdere sanctielijsten` / `Geautomatiseerde sanctiescreening` / `Geavanceerde sanctiescreening met AI-ondersteuning` |
| `walkthrough/index.html` | "AI Engine Badges" (×2) + "8 databases" | → `Analyse Badges` / `uitgebreide screening` |
| `glossary/ai-consensus/index.html` | "Multi-provider" + "AI-engines" + "consensus-stack" + "10-Gate" | → "Multi-source" + "analyselagen" + "analyselaag" + "meertraps" |
| `glossary/epistemische-confidentie/index.html` | "10-Gate systeem" (×2) | → "meertrags validatiesysteem" / "meertrags epistemisch systeem" |
| `glossary/sanctiescreening/index.html` | "8 databases met F1=96.2%" | → "meerdere sanctielijsten met hoge nauwkeurigheid" |
| `glossary/pre-due-diligence/index.html` | "meerdere AI-engines" | → "meerdere analyselagen" |
| `trust.html` | "AI-engines" (×2) | → "analyselagen" |
| `dpa.html` | "AI-engines" | → "Analyselagen" |
| `llms.txt` | "AI engines" | → context-appropriate safe language |
| `llms-full.txt` | "AI engines" + "10-Gate" + Shodan/Benford residuals | → context-appropriate safe language |

### 4.2 Root source files — same changes applied

All root source files (canonical source for builds) received the same replacements to prevent future rebuild drift.

---

## 5. Tests Added/Changed

| Test | Purpose |
|------|---------|
| `test_public_surface_gate_blocks_new_provider_leaks` | MiniCPM, HuggingFace, Hugging Face, LiteLLM caught |
| `test_public_surface_gate_blocks_ai_engines_disclosure` | "AI-engines", "AI engines", "AI engine" caught |
| `test_public_surface_gate_blocks_source_count_bronnen` | "27 bronnen", "24 bronnen", "N bronnen" caught |
| `test_public_surface_gate_blocks_fixed_count_databases` | "8 databases", "15 databases" caught |
| `test_public_surface_gate_allows_47_databases` | "47 databases" explicitly NOT caught |
| `test_public_surface_gate_blocks_gate_count_claims` | "10-Gate", "5-Gate", "N Gate" caught |
| `test_public_surface_gate_blocks_consensus_stack` | "consensus-stack" caught |
| `test_public_surface_gate_blocks_dual_model_ai` | "dual-model AI" caught |
| `test_public_surface_gate_hardened_safe_replacements_all` | All 14 safe phrases explicitly NOT caught |

**Test count: 10 → 18** (8 new tests)

---

## 6. Gate Output — Default / Strict / Legacy

```
$ python tools/public_surface_gate.py
DueSight public surface gate: PASS

$ python tools/public_surface_gate.py --strict
DueSight public surface gate: PASS

$ python tools/public_surface_gate.py --legacy
DueSight legacy surface audit: PASS
```

---

## 7. Residual rg Hits + Acceptability

| Pattern | Remaining in _pages/ | Status |
|---------|---------------------|--------|
| `Benford` in code blocks | `blog/benfords-law-fraude-detectie/` code examples (`benford_expected(digit)`) | **Acceptable** — code identifier, not product claim |
| `47 databases` | Verified wording in `index.html`, `faq/`, etc. | **Acceptable** — explicit allowlist |
| `meerdere bronnen` | Sample report descriptions | **Acceptable** — non-fixed generic |
| Various `meerdere analyselagen` | Safe replacement language | **Acceptable** — designed safe language |
| Legacy designs/ `AI-Engines` | Only in `designs/` (excluded from default/strict) | **Acceptable** — legacy design drafts |
| Sample reports `5-Gate` in `eigen_bedrijf_*.html` | Legacy scan only | **Acceptable** — non-curated files |

---

## 8. Git Status (Exact)

```
Branch: handoff/max-stack-20260529
Pre-existing staged: 30 archive renames + many modified HTML/gate files
This session changes:
  M tools/public_surface_gate.py       (+53 lines: 7 new patterns + 1 extended)
  M tests/test_public_surface_gate.py  (+284 lines: 8 new tests)
  M orbit-matrix.html                  (HuggingFace → Model Hub)
  M flipbook.js                        (5 databases → meerdere sanctielijsten)
  M index.html                         (AI Engine + bronnen counts)
  M faq/index.html                     (8 databases → generic)
  M walkthrough/index.html             (AI Engine Badges + 8 databases)
  M glossary/ai-consensus/index.html   (Multi-provider + AI-engines + 10-Gate)
  M glossary/epistemische-confidentie/index.html  (10-Gate)
  M glossary/sanctiescreening/index.html          (8 databases)
  M glossary/pre-due-diligence/index.html         (AI-engines)
  M llms.txt                           (AI engines → generic)
  M llms-full.txt                      (AI engines + 10-Gate + Shodan/Benford → generic)
  + _pages/ copies of all above
```

`git diff --check`: CRLF warnings only, no errors.

---

## 9. No Commit/Push Confirmation

- **No `git add` performed.**
- **No `git commit` performed.**
- **No `git push` performed.**
- **No deletes or mass moves.**
- **No archive/quarantine work.**
- **No app/runtime/payment code modified.** Gate code and tests were intentionally modified.
- **Pre-existing staged archive-renames untouched.**

---

*End of hardening report.*
