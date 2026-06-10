# SITE_CLAIMS_AUDIT_20260607 — Funnel/privacy/clean-language audit (uitbreiding op 20260604)

> **Datum:** 2026-06-07 (v2: gecorrigeerd na user-review)
> **Worker:** claude-code `think-deep` (ultracode, xhigh) + user-correctie
> **Workspace:** `C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website`
> **Cross-check:** `C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent` (alleen gelezen, niets gewijzigd)
> **Voorganger:** `SITE_CLAIMS_AUDIT_20260604.md` (Benford/64+ bronnen, 152 hits geëlimineerd)
> **v1 van dit rapport** (eerder op 7-juni geschreven) was **niet volledig betrouwbaar** — user-review vond extra hits die de eerste pass miste. Zie sectie 11 voor de correcties.

---

## 1. Aanleiding & context

4-juni-audit heeft de marketing-guardrail + claims-substantiation op orde gebracht voor `Benford's Law` (catch-all) en `64+ bronnen` (alle → "47 databases"). Drie SEO-flag-pagina's bewust niet aangeraakt.

Deze 7-juni-audit richt zich op een **andere risico-categorie** die 4-juni niet dekte:
- **Privacy-guarantee framing** ("absolute anonimiteit is gegarandeerd")
- **Clean / no-risk verdict framing** ("CLEAR", "clean scan", "geen risico")
- **Funnel / score-purchase taal** in CTAs
- **Certificerings-imitaties** ("GDPR Compliant", "AI Confidence Score")
- **Sample-report integriteit** (12 `index-premium.html` samples)

Doel: source-scoped, scenario-range, evidence-closure taal toepassen **zonder de premium-propositie te schenden** en zonder score-purchase of favourable-outcome framing.

## 2. Acceptance criteria (DoD)

| # | Criterium | Status |
|---|-----------|--------|
| 1 | Live surface risico-hits geanalyseerd en geclassificeerd | ✅ (na v1→v2 correctie) |
| 2 | High-confidence safe patches toegepast (source-scoped, scenario-range) | ✅ 5 files, 8 edits |
| 3 | Premium-propositie (€79 / €399 / €19, "47 databases", 11/13 engine consensus) niet verzwakt | ✅ |
| 4 | Geen score-purchase framing geïntroduceerd | ✅ (CTAs onveranderd: "Vraag Premium Rapport Aan") |
| 5 | Geen favourable-outcome framing ("100% safe", "geen risico", "altijd clean") | ✅ |
| 6 | 12 sample-report-*/index-premium.html geverifieerd aanwezig + linked | ✅ (12/12, alleen via `_pages/index.html` accordion) |
| 7 | 4-juni baseline (74 hits in 3 SEO flag files) intact, geen regressie | ✅ |
| 8 | Public surface gate PASS | ✅ |
| 9 | Niets in `duesight-agent` aangeraakt, geen backend-run | ✅ |
| 10 | Geen Docker, geen dev-server gestart | ✅ |

## 3. Risico-categorieën (7-juni scope)

| Categorie | Risico-patroon | Live hits voor fix | Status |
|---|---|---:|---|
| **Privacy-guarantee** | "absolute anonimiteit is gegarandeerd" | 1 (live) + 1 (_pages build) + 1 (website_src) | ✅ gefixt |
| **Certificerings-imitatie** | "GDPR Compliant" | 1 (breach-radar) + 1 (_pages breach-radar) | ✅ user-fixed |
| **Clean / no-risk verdict (header)** | "✓ Breach Exposure Status: CLEAR" | 1 (live) + 1 (_pages) | ✅ gefixt |
| **Clean / no-risk verdict (badge)** | `<span class="badge-clear">CLEAR</span>` | 1 (live) + 1 (_pages) | ✅ user-fixed → "0 MATCHES" |
| **Clean / no-risk verdict (CTA)** | "Een clean breach scan is goed nieuws" | 1 (live) + 1 (_pages) | ✅ gefixt |
| **Clean / no-risk verdict (exposed branch)** | "Breach Exposure Score: N/100" | 1 (live) + 1 (_pages) | ✅ user-fixed → "Breach exposure signal" |
| **Eigendomsketen-garantie** | "volledige eigendomsketens" | 1 (live) + 1 (_pages) | ✅ user-fixed → "eigendoms- en UBO-verificatiepaden" |
| **Patch-typo** | "Forensische data-analyseics" (orig + nieuw) | 1 (live) + 1 (_pages) | ✅ user-fixed → "Forensische data-analyse" |
| **AI-Confidence claim** | "AI Confidence Score" | 1 (live) + 1 (_pages) | ✅ user-fixed → "Bronsterkte-indicatie" / "confidence-indicatie" |
| **Build/source drift** | "Benford's Law" in `_pages/breach-radar.html:600` | 1 | ✅ gefixt (sync) |
| **Score-purchase CTA** | "Bestel Premium Analyse" / "Vraag Premium Rapport Aan" → /#contact | 2 (live) | ✅ onveranderd (verkoopt rapport, niet score) |
| **ISO 27001 / SOC 2 als certificering** | (reeds 4-juni scope) | 0 (live) | ✅ clean |
| **"64+ bronnen"** | (reeds 4-juni scope) | 0 (live) | ✅ clean |

## 4. Pre-fix scan (live public surface)

Initiële Grep + `public_surface_gate.py` (vóór user-correctie) hadden **NIET** alle hits gevonden. Totaal live risico-hits gecorrigeerd:

| Bron | Term | Live hit | Door wie gefixt |
|---|---|:---:|:---:|
| index.html:14420 | absolute anonimiteit is gegarandeerd | ✓ | claude |
| _pages/index.html:14391 | absolute anonimiteit is gegarandeerd | ✓ | claude |
| website_src/index.html:14037 | absolute anonimiteit is gegarandeerd | ✓ | claude |
| breach-radar.html:445 | GDPR Compliant | ✓ | user |
| breach-radar.html:578 | CLEAR (badge) | ✓ | user |
| breach-radar.html:588 | Breach Exposure Status: CLEAR | ✓ | claude |
| breach-radar.html:599 | Een clean breach scan is goed nieuws | ✓ | claude |
| breach-radar.html:652 | Breach Exposure Score: N/100 | ✓ | user |
| breach-radar.html:656 | volledige eigendomsketens | ✓ | user |
| breach-radar.html:662 | Forensische data-analyseics (typo) | ✓ | user |
| _pages/breach-radar.html:445 | GDPR Compliant | ✓ | user |
| _pages/breach-radar.html:578 | CLEAR (badge) | ✓ | user |
| _pages/breach-radar.html:600 | Benford's Law (CTA) | ✓ | claude |
| _pages/breach-radar.html:652 | Breach Exposure Score: N/100 | ✓ | user |
| _pages/breach-radar.html:656 | volledige eigendomsketens | ✓ | user |
| _pages/breach-radar.html:662 | Forensische data-analyseics (typo) | ✓ | user |
| sales-tool.html:218 | AI Confidence Score | ✓ | user |
| sales-tool.html:231 | AI Confidence Score | ✓ | user |
| sales-tool.html:255 | AI Confidence Score + bronvermelding | ✓ | user |
| sales-tool.html:340 | AI Confidence Score | ✓ | user |
| _pages/sales-tool.html:218 | AI Confidence Score | ✓ | claude (v2 sync) |
| _pages/sales-tool.html:231 | AI Confidence Score | ✓ | claude (v2 sync) |
| _pages/sales-tool.html:255 | Bronsterkte-indicatie + bronvermelding | ✓ | claude (v2 sync) |
| _pages/sales-tool.html:340 | AI Confidence Score + 6-engine + zeker het systeem | ✓ | claude (v2 sync) |

**Totaal: 24 live-hits → 0 na fix.**

## 5. Patches (8 edits in 5 files)

### 5.1 `index.html:14420-14422` + `_pages/index.html:14391-14393` + `website_src/index.html:14037-14039` — privacy-guarantee (door claude)

**Origineel (verbatim):**
> "Nee, absolute anonimiteit is gegarandeerd. DueSight opereert volledig in stealth mode via passieve OSINT en afgeschermde API's. Het doelbedrijf ontvangt geen enkele notificatie van uw onderzoek."

**Vervangen door:**
> "DueSight gebruikt uitsluitend passieve OSINT via publieke registers en afgeschermde API-toegang; DueSight stuurt zelf geen notificaties naar het doelbedrijf. De geraadpleegde bronnen (KvK, GLEIF, KBO, OpenSanctions e.a.) kunnen in hun eigen auditlogs IP-adressen of query-patronen registreren, zoals bij elke professionele OSINT-werkstroom."

**Reden (source-scoped, evidence-closure):**
- ✅ Bewaart premium-propositie: "DueSight stuurt zelf geen notificaties" = de facto claim die DueSight kan waarmaken
- ✅ Voegt scenario-range toe: "zoals bij elke professionele OSINT-werkstroom"
- ✅ Verwijdert "absolute" + "gegarandeerd" (juridisch kwetsbaar: derden loggen)
- ✅ Bronnen genoemd (KvK/GLEIF/KBO/OpenSanctions) maken de claim controleerbaar

### 5.2 `breach-radar.html:588-593` + `_pages/breach-radar.html:588-593` — clean verdict (door claude)

**Origineel:**
```
✓ Breach Exposure Status: CLEAR
Gecontroleerd tegen 961 breach databases · N records · Bereik: 2007 – 2026 · Bron: HIBP
```

**Vervangen door:**
```
✓ 0 matches in 961 breach databases
Gecontroleerd tegen 961 breach databases · N records · Bereik: 2007 – 2026 · Bron: HIBP. Geen match betekent niet automatisch "geen risico" — enkel geen hit in deze bronnen op dit moment.
```

**Reden:** "CLEAR" = favourable-outcome verdict → vervangen door feitelijke observatie "0 matches". "Geen risico" expliciet weerlegd.

### 5.3 `breach-radar.html:599-603` + `_pages/breach-radar.html:599-603` — clean framing (door claude)

**Origineel:** "Een clean breach scan is goed nieuws..."

**Vervangen door:** "Geen datalekken gevonden in onze 961 HIBP-bronnen is een geruststellende eerste indicator, maar geen volledige due diligence..."

**Reden:** "clean breach scan" → feit ("geen datalekken gevonden in 961 HIBP-bronnen"). "goed nieuws" → "geruststellende eerste indicator".

### 5.4 `breach-radar.html:445` + `_pages/breach-radar.html:445` — GDPR Compliant (door user)

**Origineel:** "🇪🇺 GDPR Compliant" (trust-badge)

**Vervangen door:** "🇪🇺 Privacy-by-design workflow"

**Reden:** "Compliant" suggereert certificering; DueSight heeft geen GDPR-certificering. "Privacy-by-design" = technische architectuurbeschrijving, geen claim.

### 5.5 `breach-radar.html:578` + `_pages/breach-radar.html:578` — CLEAR badge (door user)

**Origineel:** `<span class="result-badge badge-clear">CLEAR</span>`

**Vervangen door:** `<span class="result-badge badge-clear">0 MATCHES</span>`

**Reden:** "CLEAR" = favourable-outcome verdict; "0 MATCHES" = feitelijke observatie. CSS-klasse `badge-clear` blijft (visueel groen), alleen de tekst verandert.

### 5.6 `breach-radar.html:652` + `_pages/breach-radar.html:652` — Breach Exposure Score (door user)

**Origineel:** `⚠️ Breach Exposure Score: ${Math.min(100, matches.length * 25)}/100`

**Vervangen door:** `⚠️ Breach exposure signal: ${matches.length} matched breach${matches.length > 1 ? 'es' : ''}`

**Reden:** "Score" suggereert een gevalideerde, schaalbare risico-maat; "signal" is een feitelijke observatie van het aantal matches. Geen "/100" die een schaalbare verdict suggereert.

### 5.7 `breach-radar.html:656` + `_pages/breach-radar.html:656` — eigendomsketen (door user)

**Origineel:** "...en **volledige eigendomsketens**."

**Vervangen door:** "...en **eigendoms- en UBO-verificatiepaden**."

**Reden:** "volledige eigendomsketens" = garantie dat alle UBO-lagen volledig in kaart zijn gebracht; "verificatiepaden" = scenario-range (sommige lagen kunnen onvolledig zijn door datakwaliteit, jurisdictie, etc.).

### 5.8 `breach-radar.html:662` + `_pages/breach-radar.html:662` — typo (door user)

**Origineel:** "...Forensische data-analyseics, en AI deep research..." (letterlijke typo: samengetrokken "forensische data-analyse" + "ics")

**Vervangen door:** "...Forensische data-analyse, en AI deep research door 8 providers."

**Reden:** Typo + ontbrekende bron-noot. "Forensische data-analyse" = 4-juni-vocabulair; "8 providers" = eerlijke bron-noot (was "13-Engine" in backtesting/sjablonen, onjuist voor breach-radar).

### 5.9 `sales-tool.html` × 4 + `_pages/sales-tool.html` × 4 — AI Confidence Score (door user + claude-sync)

**Origineel (4×):**
- L218: `<span class="check-y">✓</span> AI Confidence Score`
- L231: `<span class="check-n">✗</span> AI Confidence Score`
- L255: `<span class="check-y">✓</span> AI Confidence Score + bronvermelding`
- L340: `De AI Confidence Score geeft per sectie aan hoe zeker het systeem is. En de 6-engine cross-check valideert bevindingen over meerdere onafhankelijke bronnen.`

**Vervangen door:**
- L218: `<span class="check-y">✓</span> Bronsterkte-indicatie`
- L231: `<span class="check-n">✗</span> Bronsterkte-indicatie`
- L255: `<span class="check-y">✓</span> Bronsterkte-indicatie + bronvermelding`
- L340: `De confidence-indicatie geeft per sectie aan hoe sterk de bronbasis is. De multi-engine cross-check valideert bevindingen over meerdere onafhankelijke analyselagen.`

**Reden:**
- "AI Confidence Score" = "AI is zeker" suggestie → "Bronsterkte-indicatie" / "confidence-indicatie" = bron-gebaseerde observatie
- "6-engine cross-check" → "multi-engine cross-check" (geen specifiek getal dat op andere pagina's wordt tegengesproken)
- "zeker het systeem is" → "sterk de bronbasis is" (input-based niet output-based)
- "meerdere onafhankelijke bronnen" → "meerdere onafhankelijke analyselagen" (eerlijker: het zijn engines die elkaar checken, niet bronnen)

### 5.10 `_pages/breach-radar.html:600` — Benford CTA sync (door claude)

**Origineel:** "...sanctiescreening, eigendomsanalyse, **Benford's Law**, cyber exposure..."

**Vervangen door:** "...sanctiescreening, eigendomsanalyse, **forensische data-analyse**, cyber exposure..."

**Reden:** 4-juni-audit fixed de live `breach-radar.html` maar miste de `_pages/` build-versie. Sync om build-consistentie te bewaren.

## 6. Sample report integriteit (12/12)

**Verificatie: alle 12 sample-report-*/index-premium.html aanwezig:**

```
sample-report-adyen/index-premium.html          ✓
sample-report-bunq/index-premium.html           ✓
sample-report-gasunie/index-premium.html        ✓
sample-report-getthere/index-premium.html       ✓
sample-report-mollie-gold/index-premium.html    ✓
sample-report-multiselect/index-premium.html    ✓
sample-report-nlist/index-premium.html          ✓
sample-report-postnl/index-premium.html         ✓
sample-report-shell/index-premium.html          ✓
sample-report-specialist-group/index-premium.html ✓
sample-report-truelegends/index-premium.html    ✓
sample-report-wise/index-premium.html           ✓
```

**Linking:**
- ✅ `_pages/index.html:13011-13073` — sample-report-accordion met 12 cards (Kort/Hub + Uitgebreid/Index-Premium + Flipbook)
- ⚠️ Live `index.html` heeft **geen** sample-report-accordion (alleen `_pages/` build-versie)
- ⚠️ `duesight_improved.html:10219-10373` heeft de accordion ook (7-jun 15:09 build, nog niet gedeployed)

## 7. Risico-hits na fix (live public surface)

| Term | Live hits | Status |
|---|---:|---|
| `absolute anonimiteit is gegarandeerd` | 0 | ✅ gefixt (11× in uitgesloten `index_*.html` backups) |
| `GDPR Compliant` (live) | 0 | ✅ user-fixed |
| `CLEAR` (live) | 0 | ✅ user-fixed |
| `Breach Exposure Score` (live) | 0 | ✅ user-fixed |
| `Een clean breach scan` | 0 | ✅ gefixt |
| `volledige eigendomsketens` (live) | 0 | ✅ user-fixed |
| `Forensische data-analyseics` | 0 | ✅ user-fixed |
| `AI Confidence Score` (live) | 0 | ✅ user-fixed |
| `Benford's Law` in CTA sync (live) | 0 | ✅ gefixt |
| **Totaal nieuwe live hits na fix** | **0** | **CLEAN** |

## 8. Resterende rode vlaggen (FYI, niet in scope of al uitgesloten)

1. **Build/source drift in uitgesloten bestanden:**
   - `index_4b8a92b4.html:9909, 12512, 12647, 12685, 12830, 12965, 13003` — 7× "AI Confidence Score" (backup, 4-juni-uitgesloten)
   - `sample-hub-gasunie/index.html:285` — "🇪🇺 GDPR Compliant" (4-juni-uitgesloten)
   - `sample-report-adyen/eigen_bedrijf_rendered.html:440`, `sample-report-gasunie/eigen_bedrijf_rendered.html:443`, `sample-report-gasunie/eigen_bedrijf_template.html:409` — "🇪🇺 GDPR Compliant" (rendered output, 4-juni-uitgesloten)

2. **`website_src/index.html:14421`** "Benford's Law" (vergelijkings-tekst). Niet aangeraakt — niet onder "DueSight past ... toe" patroon. **Bron-onderzoek: 1 regel.**

3. **Live `index.html` heeft geen sample-report-accordion** — alleen `_pages/` en `duesight_improved.html`. Orphan-risk.

4. **`breach-radar.html:602, 665`** CTAs linken naar `https://duesight.nl/#contact`. Geen score-purchase (verkoopt rapport, niet score), maar funnel-stap "rapport kopen" niet expliciet.

5. **"11 AI-engines" vs "6-engine cross-check" inconsistentie** in 4 design-varianten vs `sales-tool.html`. Positonerings-onzuiverheid, niet risk. (User-fixed "6-engine" → "multi-engine" in v2 sync.)

## 9. Harde grenzen — bevestigd

| Grens | Status |
|---|---|
| Strikt in `duesight-website` gebleven | ✅ Alleen 5 files in `duesight-website` aangeraakt |
| Niets in `duesight-agent` | ✅ (verifieerbaar: geen agent-file in deze sessie gewijzigd) |
| Geen backend-run / benchmark gestart | ✅ |
| Geen Docker gebruikt | ✅ |
| Geen dev-server gestart (geen 8000/8090/8099) | ✅ |
| Geen kill van backend-daemons | ✅ |
| Premium-propositie niet verzwakt | ✅ "11/13 engine consensus", "47 databases", "€79/€399/€19" onveranderd |
| Geen score-purchase framing geïntroduceerd | ✅ CTAs onveranderd (verkopen rapport, niet score) |
| Geen favourable-outcome framing ("altijd clean", "100% safe") | ✅ Verwijderd |
| Geen nieuwe backups aangemaakt | ✅ (per CLAUDE.md regel #10) |
| HTML-structuur intact (geen tag-balance breuk) | ✅ Inline edits alleen in `<p>`/`<div>`/`<li>`/`<span>` tekst |
| Public surface gate PASS | ✅ |
| 4-juni baseline 74 hits intact | ✅ |

## 10. Reproduceerbaarheid

```powershell
# Baseline herbevestigen
cd "C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website"
powershell -ExecutionPolicy Bypass -File tools/claims_audit_20260604/scan_claims.ps1
# → 9251 files, 74 hits, ~16s (4-juni baseline intact)

python tools/public_surface_gate.py
# → DueSight public surface gate: PASS

# Gerichte risico-scan (deze 7-juni-specifiek) — handmatige grep, GEEN geautomatiseerde tool
# (Zie sectie 11 voor waarom public_surface_gate.py alleen NIET voldoende is)
```

## 11. Audit-betrouwbaarheid: les uit v1→v2 correctie

**V1 van dit rapport (eerder op 7-juni) was NIET volledig betrouwbaar.** De eerste pass miste:

1. **`GDPR Compliant` in breach-radar.html** — niet in initiële Grep-pattern (alleen "100%/gegarandeerd/clean/no-risk" gescand). "GDPR Compliant" is een certificerings-imitatie, viel buiten de eerste regex-set.

2. **`CLEAR` als `<span class="badge-clear">` badge** — eerste Grep zocht "CLEAR" als los woord, maar de badge was verpakt in HTML + CSS-klasse. Gemist.

3. **`Breach Exposure Score: N/100` in showExposed branch** — eerste Grep las alleen `breach-radar.html:580-605` (showClean branch). De showExposed branch (regels 607-668) had een tweede "Score: " patroon dat niet gelezen werd. Les: **bij het lezen van een file voor patches, lees de hele file, niet alleen de regel-range rond de bekende hit**.

4. **`volledige eigendomsketens`** in showExposed branch — zelfde reden als #3. Niet in eerste Grep-pattern ("eigendomsketens" zat niet in mijn initiële regex-set).

5. **`Forensische data-analyseics` typo** in showExposed — `_pages/breach-radar.html:600` had de Benford-sync, maar de showExposed CTA op regel 662 had een ander tekstblok dat ik niet had gelezen. Les: **bij sync tussen live en `_pages/`, grep beide files op alle bekende risico-termen, niet alleen de sync-doelregel**.

6. **`AI Confidence Score` in sales-tool.html** — hele file `sales-tool.html` is niet door initiële scan gegaan. Les: **risk-audit moet elke public-facing file tenminste één keer openen of op een brede risk-terms-set scannen**.

7. **`public_surface_gate.py` is te smal** — geen regex op `GDPR`, `CLEAR`, `Score:`, `eigendomsketens`, `Confidence`. De gate geeft PASS maar laat risico-hits door. Les: **gate is gate, niet scan — handmatige gerichte scan aanvullend vereist**.

8. **Patch-typo `Forensische data-analyseics`** was al in de originele code (showExposed branch). Bij mijn eerste patch in showClean heb ik dit niet aangeraakt; pas bij user-fix in showExposed werd dit opgemerkt en gecorrigeerd. Les: **bij audits, eerst origineel + build parallel lezen voor de volledige context, niet alleen de bekende hit-regel**.

### Consequentie voor toekomstige audits

- **Vóór elke audit-run:** stel een **brede risk-terms-set** samen (≥ 20 patronen), niet alleen de categorieën uit de directe prompt
- **Tijdens scan:** elke gematchte file volledig lezen, niet alleen de match-regel
- **Na patches:** altijd handmatige gerichte grep aanvullend op geautomatiseerde gates
- **Bij sync tussen live en `_pages/`:** altijd beide files naast elkaar op alle risico-termen scannen

Dit is een **feedback-gedreven verbetering**, niet een eenmalige fout. De volgende audit-pass moet deze les meenemen.

## 12. Eindstand

| Metric | Voor 7-juni | Na 7-juni (v2) |
|---|---:|---:|
| Live publieke risico-hits | 11 unieke termen × N files = 24 | 0 |
| ISO 27001 / SOC 2 (live) | 0 | 0 |
| 64+ bronnen (live) | 0 | 0 |
| Benford product-claims (live) | 0 | 0 |
| Files aangeraakt in deze audit | — | 5 |
| Edits | — | 8 |
| 4-juni baseline (74 hits in 3 flag files) | 74 | 74 (intact) |
| Public surface gate | PASS | PASS |
| Sample reports aanwezig | 12/12 | 12/12 |

**Acceptatiecriteria: 10/10 voldaan.** 24 live risico-hits geëlimineerd via source-scoped, scenario-range, evidence-closure herformulering. Premium-propositie onveranderd. Geen score-purchase of favourable-outcome framing geïntroduceerd. 4-juni-baseline (74 hits in 3 flag files) intact. Public surface gate PASS.

**v2-correctie:** Initiële audit (v1) was onvolledig — user vond 6 extra risico-termen in breach-radar.html + sales-tool.html die v1 miste. v2 reflecteert de complete fix (deels door claude, deels door user) en documenteert de audit-betrouwbaarheidsles in sectie 11.

**Open follow-ups (FYI, Arian-besluit):**
- `public_surface_gate.py` uitbreiden met regex-set voor `GDPR Compliant`, `CLEAR`, `Score:`, `eigendomsketens`, `Confidence`
- `duesight-agent/tools/_verify_premium.py` bestaat inmiddels en valideert de 12 premium samples; een website-side wrapper is optioneel.
- Uitgesloten artifacts zoals `sample-hub-gasunie/` en `sample-report-*/eigen_bedrijf_*.html` hebben nog GDPR Compliant / CLEAR hits; technisch aanwezig maar buiten public-surface gate.
- Live `index.html` heeft geen sample-report-accordion (alleen `_pages/` en `duesight_improved.html`)
- `breach-radar.html` CTAs linken naar `/#contact` (geen score-purchase, maar funnel-stap "rapport kopen" niet expliciet)

— Einde rapport (v2) —

## 13. Codex follow-up (v3, 2026-06-07)

De open follow-up rond `public_surface_gate.py` is uitgevoerd en opnieuw geverifieerd.

Extra gate-dekking toegevoegd:
- `GDPR Compliant` / `GDPR-compliant`
- `EU AI Act compliant`
- clean verdicts zoals `CLEAR`, `ALL CLEAR`, `Breach Exposure Status: CLEAR`
- `Breach Exposure Score`
- `clean breach scan`
- `absolute anonimiteit is gegarandeerd`
- `volledige eigendomsketens`
- `AI Confidence Score`, `DueSight Confidence Score`, `DueSight Confidence Index`, `Confidence Score`
- `Compliance Grade`
- outcome-framing zoals `BUY`, `BUY/HOLD/ABSTAIN`, `Consensus: BUY`
- `6-engine cross-check`
- legacy `64+ bronnen/databronnen/sources`
- `Benford's Law forensics/forensiek`

Extra fixes na v2:
- resterende `64+` en `Confidence Score` tokens opgeschoond in `_pages`, live kernbestanden en `website_src`.
- `walkthrough/index.html` en `_pages/walkthrough/index.html` aangepast van `BUY` naar `REVIEW`-risicoroute.
- `faq/index.html` typo `Forensische data-analyseics` en neveneffecten zoals `forensische data-analyse Forensics` gecorrigeerd.
- UTF-8 BOMs verwijderd die door bulk-rewrite op aangeraakte bestanden waren gezet.
- `website_src/` source-drift meegenomen; uitgesloten backups/backtesting blijven apart gemarkeerd en zijn niet public-surface-ready.

Verificatie na v3:
```powershell
python tools/public_surface_gate.py --strict
# DueSight public surface gate: PASS

python -m py_compile tools/public_surface_gate.py
# PASS

cd "C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent"
python tools\_verify_premium.py
# T4 CHECKLIST: PASS
```

Een aanvullende brede grep op live/source-kernbestanden gaf 0 hits op de nieuwe risk-term set. Resterende hits zitten uitsluitend in uitgesloten legacy-zones zoals `backtesting/`, oude `index_*` backups, `designs/` en enkele niet-live `sample-report-*` artifacts.
Aanvulling v3-links: de sample-report links in `index.html`, `_pages/index.html` en `website_src/index.html` zijn gesynct van `sample-report-*/index.html` naar `sample-report-*/index-premium.html`. `rg "sample-report-[a-z0-9-]+/index\.html" index.html _pages\index.html website_src\index.html` geeft 0 hits; er zijn 38 `index-premium.html` links aanwezig over live, `_pages` en source.

## 14. Codex follow-up (v4, 2026-06-07)

De legacy-follow-up uit v3 is omgezet naar een reproduceerbare gate-modus:

```powershell
python tools\public_surface_gate.py --legacy
# DueSight legacy surface audit: BLOCK
```

De gewone public gate blijft groen:

```powershell
python tools\public_surface_gate.py --strict
# DueSight public surface gate: PASS
```

Extra hardening in `tools/public_surface_gate.py`:
- UTF-8 BOM detectie toegevoegd voor gescande files.
- Typografische regex-karakters vervangen door ASCII-safe `\u2014` / `\u2019` escapes.
- `--legacy` scant nu repo-root legacy-zones: `backtesting/`, `designs/`, `sample-report-*` en oude `index_*` / backup-indexbestanden.

Legacy audit eindstand:
- Totaal: 616 findings.
- `backtesting`: 150.
- `backup-index`: 441.
- `designs`: 5.
- `sample-report-*`: 20.

Top legacy-labels:
- `legacy 64 plus sources token`: 142.
- `AI confidence score token`: 87.
- `raw tracker script`: 87.
- `buy verdict token`: 54.
- `ISO 27001 claim token`: 38.
- `clean verdict badge text`: 41.
- `SOC 2 claim token`: 31.

Interpretatie: live/public surface is schoon, maar legacy-zones zijn aantoonbaar niet publicatieklaar. Voor elke deploy die `backtesting/`, `designs/`, oude index-backups of raw `sample-report-*` artifacts raakt, moet `python tools\public_surface_gate.py --legacy` eerst PASS worden of de files moeten uitgesloten blijven.

Aanvulling v4 sample-links: de gelinkte sample HTML's (`hub.html`, `flipbook.html`, `index.html`, `index-premium.html`) zijn apart gescand op de 7-juni risk-term set. Resultaat: 0 hits. De resterende `sample-report-*` legacy-findings zitten in raw logs, JSON of niet-premium/static artifacts, niet in de homepage-gelinkte sample HTML's.

## 15. Codex follow-up (v5, 2026-06-07)

Reviewer-vraag: is er vanaf de live-surface een link die een legacy-zone binnenleidt?

Antwoord: ja, `sample-report-*` is deels publiek bedoeld. De oplossing is niet "alles legacy houden", maar een curated include.

**Build-fix:**
- `build_public_artifact()` include nu uit `sample-report-*` alleen:
  - `hub.html`
  - `flipbook.html`
  - `index.html`
  - `index-premium.html`
  - `styles.css`
- Alle overige raw/sample-report artifacts blijven uitgesloten.
- `_pages` wordt bij build-from-root niet meer als nested public artifact meegekopieerd.
- Oude root build/backups zoals `index_github.html`, `index_gisteravond.html`, `index_master_backup.html` blijven uitgesloten.

**Link-fix:**
- `rapporten/index.html` + `_pages/rapporten/index.html`: alle zichtbare `Uitgebreid` links gaan nu naar `index-premium.html`.
- `whitelabel-demo.html`, `_pages/whitelabel-demo.html`, `website_src/whitelabel-demo.html`: `Bekijk Rapport` links gaan naar `sample-report-*/index-premium.html`.
- Root-level `whitelabel-demo.html` gebruikte foutief `../sample-report-*`; dat is gecorrigeerd naar `sample-report-*`.

**Temp-build bewijs:**
```powershell
python tools\public_surface_gate.py --root _tmp_public_artifact --build-from . --strict
# DueSight public surface gate: PASS
```

Aanvullende checks op het temp-artifact:
- 12 `sample-report-*` directories aanwezig.
- 0 non-curated files in die sample-report directories.
- 0 missende sample-report links.

**Regressiechecks na v5:**
- `python tools\public_surface_gate.py --strict` -> PASS.
- Gelinkte sample HTML risk grep -> 0 hits.
- `python tools\_verify_premium.py` -> T4 CHECKLIST PASS.
- `scan_claims.ps1` -> 9251 files, 74 hits.
- `scan_claims.ps1` exclude is verbreed van `_tmp-*` naar `_tmp*`, zodat temp-builds de 4-juni baseline niet vervuilen.

Interpretatie v5: public/live claims zijn schoon, sample-report links werken in een built artifact, en raw legacy blijft buiten public deploy. `--legacy` blijft terecht BLOCK op 616 niet-live findings.

## 16. Codex follow-up (v6, 2026-06-07)

Aanvullende reviewer-vondst na v5: de curated sample include maakte de gelinkte sample HTML's publiek genoeg om ook hun eigen claim-taal streng te behandelen. De eerdere brede grep miste generieke sample-framing zoals `Certified sample replay`, `SCORE 70/100`, `Pipeline score`, `Evidence score`, `score model`, `GOLD Report`, `INVEST` en `5-Engine Unanimous Consensus`.

Doorgevoerde fixes:

- Alle 48 curated sample HTML's (`index.html`, `hub.html`, `flipbook.html`, `index-premium.html` over 12 samples) genormaliseerd:
  - `Certified` / `certification` sample-framing -> `Curated` / `evidence review`.
  - `Score` / `SCORE` / `Pipeline score` / `Evidence score` -> `bronsterkte-indicatie`, `bronsterkte` of `Evidence model`.
  - `scoremodel` / `sample_report_score_model` -> evidence-model naming.
- `flipbook.js` en `_pages/flipbook.js` statisch geneutraliseerd:
  - `GOLD Report`, `GOLD TIER`, `AI VERDICT`, `INVEST`, `5-Engine Unanimous Consensus`, `strong investment profile` verwijderd uit public source.
- `faq/index.html` en `_pages/faq/index.html`:
  - `dashboard met score, verdict` -> `dashboard met bronsterkte-indicatie, reviewstatus`.
  - `_pages` Benford-rest -> `forensische data-analyse`.
- `duesight_improved.html`:
  - `pipeline-certified` -> `pipeline-curated`.
  - `Get There ICT Solutions B.V.` -> `Get There ICT professionals`.
- `public_surface_gate.py` uitgebreid met gerichte guards voor:
  - public sample score-framing;
  - uppercase score-verdict markup;
  - favourable-outcome sample tokens;
  - sample certification-framing.

Verificatie na v6:

- `python tools\public_surface_gate.py --strict` -> PASS.
- `python -m py_compile tools\public_surface_gate.py` -> PASS.
- Temp public artifact build vanaf repo-root -> PASS.
- Built artifact: 12 `sample-report-*` directories, 0 non-curated sample files, 0 missende sample-report links.
- Gerichte sample/flipbook/FAQ grep op oude framing tokens -> 0 hits.
- `python tools\_verify_premium.py` -> PASS, 12/12.
- 4-juni baseline `scan_claims.ps1` -> 9251 files, 74 hits.
- Temp artifact na verificatie verwijderd.

Legacy-status na v6:

- `scan_legacy_surface(strict=False)` telt nu 694 findings. Dat is hoger dan v5 doordat de gate strenger is geworden, niet doordat de public surface is verslechterd.
- Sample-report legacy totaal: 90 findings in uitgesloten raw/non-curated sample artifacts. De curated sample HTML's zijn via de temp public artifact bewezen schoon.

Interpretatie v6: public deploypad is nu zowel structureel werkend als claim-governance schoon. De legacy-zones blijven rood en mogen niet ongefilterd gepubliceerd worden.

## 17. Codex follow-up (v7, 2026-06-07)

Aanvullende reviewer-vondst na v6: de GetThere/Get There naamfix was niet alleen een kaart-label. De publiek gelinkte GetThere rapporten moesten entity-hygiëne afdwingen:

- DD-rapporten gebruiken de juridische naam: `Get There ICT Solutions B.V.`.
- Marketingkaarten gebruiken de handelsnaam: `Get There ICT professionals`.
- Driftvarianten `GetThere B.V.`, `Get There B.V.` en `GetThere Group` mogen niet meer in public/customer-facing output staan.

Doorgevoerd:

- `premium_report_render.py` leest voor `sample-report-getthere` de identity split uit `kvk_verified_data.json` en normaliseert oude slug/spacing-aliassen naar de juridische naam.
- `sample-report-getthere/{index.html,hub.html,flipbook.html,index-premium.html}` opgeschoond:
  - juridische naam in rapportcontext;
  - geen `GetThere B.V.`, `Get There B.V.`, `Getthere B.V.` of `GetThere Group`;
  - oude `BUY`/`CLEAR`/certificering/AI-confidence/Benford-restanten in de curated public files verwijderd of geneutraliseerd.
- Public marketing cards in `index.html`, `_pages/index.html`, `rapporten/index.html`, `_pages/rapporten/index.html`, `website_src/index.html` gebruiken `Get There ICT professionals`.
- `public_surface_gate.py` uitgebreid met:
  - Get There entity-drift guard;
  - `AI Visibility Score` guard;
  - build-exclude voor `sample-hub-*`;
  - build-exclude voor `*.backup*`.
- `_pages/sample-hub-gasunie/` verwijderd uit de public artifact, omdat die legacy hub niet bij de curated sample-report deploy hoort.
- `tools/_verify_premium.py` checkt nu expliciet dat GetThere premium de legal/trade/KvK split toont en geen oude driftvariant lekt.

Verificatie na v7:

- `python tools\public_surface_gate.py --strict` -> PASS.
- `python tools\public_surface_gate.py --root _tmp_public_artifact --build-from . --strict` -> PASS.
- Built artifact: 12 `sample-report-*` directories, 0 `sample-hub-*` directories, 0 backup files, 0 non-curated sample files.
- `python tools\_verify_premium.py` -> PASS, 12/12, `GetThere identity split : PASS`.
- Gerichte grep op `GetThere B.V.`, `Get There B.V.`, `Getthere B.V.`, `GetThere Group`, `BUY`, `CLEAR`, `INVEST`, `ISO 27001`, `AI Visibility Score`, `Confidence Score`, `Certified`, `GOLD`, `5-Engine` in GetThere curated files -> 0 hits.
- 4-juni baseline `scan_claims.ps1` -> 9251 files, 74 hits.
- `git diff --check` op gewijzigde public files -> geen whitespace errors (alleen bestaande CRLF-waarschuwingen voor enkele HTML/Python files).

Interpretatie v7: de curated public deploy is nu ook entity-governance schoon voor Get There. De juridische/handelsnaam-split is reproduceerbaar geborgd in renderer, gate en premium-verifier.
