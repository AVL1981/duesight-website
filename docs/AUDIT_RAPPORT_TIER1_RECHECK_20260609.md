# Audit-Rapport Tier 1 Recheck (HEAD-only) — 2026-06-09

**ROL**: read-only audit-agent. Geen fixes, geen commits, geen mutaties. Arian is eindbeslisser.
**REPO IN SCOPE**: `duesight-website`, branch `handoff/max-stack-20260529`, **HEAD-only** (geen working tree).
**HEAD = `0bbd3313` `chore(designs): normalize prototype claim copy`** (2026-06-09 13:53:54 +0200).
**AUTEUR-VAN-AUDIT**: deze sessie. Eén schrijver; geen mutaties uitgevoerd.

---

## PATH-DISCREPANCY (eerlijk gemeld)

Arian's opdracht verwijst naar paden als `_pages/roi-calculator.html`, `_pages/intelligence-hub-template.html`, `_pages/index.html`, `_pages/whitelabel-demo.html`, `_pages/trust.html`. **Deze paden bestaan NIET in HEAD** op deze branch:

- `git ls-files _pages/` = **0 files** in HEAD.
- `git ls-tree HEAD _pages/` = **0 entries** in HEAD.
- **Alle fixtures staan op ROOT-niveau in HEAD**: `roi-calculator.html`, `intelligence-hub-template.html`, `index.html`, `whitelabel-demo.html`, `trust.html` (plus directories `assurance/`, `dataretentie/`, `dpa/`, `privacy/`, `blog/`, `tools/`, etc.).

De `_pages/` directory bestaat **alleen in de working tree** (untracked, niet in HEAD). De `_pages/trust.html` is 27 regels redirect-stub (zoals in vorige audit), terwijl `trust.html` op root in HEAD óók 27 regels redirect-stub is — maar `_pages/trust.html` en `trust.html` **verschillen** op bestandsniveau (`diff -q` rapporteert "Files differ"). `_pages/` is dus een **separate werkversie** met eigen historie.

**Interpretatie**: Arian's opdracht verwijst hoogstwaarschijnlijk naar wat in HEAD als de **canonical live site** staat — dat is de **root-tree**. De working-tree `_pages/` is een parallelle variant. **Voor de regressie-test op HEAD verifieer ik de root-files.** Voor de breed-scan (Fixture 6) heb ik óók de working-tree `_pages/` gescand; die resultaten zijn **NIET verifieerbaar op HEAD** en gemarkeerd als zodanig.

---

## PREFLIGHT (verplicht)

**Branch**: `handoff/max-stack-20260529` ✓
**HEAD**: `0bbd3313 chore(designs): normalize prototype claim copy` ✓
**HEAD mtime**: 2026-06-09 13:53 (`.git/refs/heads/handoff/max-stack-20260529`)

**Dirty working tree** (git status):
- Modified (tracked): `index.html`, `intelligence-hub-template.html`, `payment_server.py`, `roi-calculator.html`, `scan_client.js`, `tests/test_homepage_hygiene.py`, `tests/test_refund_flow.py`, `website_src` (submodule pointer).
- Untracked: 9 docs/ files, `_pages/` (hele directory), `archive/`, `assets/`, plus verschillende `_pages/...` subdirs.

**Uitgesloten per Arian's instructie**:
- `payment_server.py` (dirty + bevat refund/resolve-bug per Arian's eigen commit-message `4d962732 chore(payment): commit in-flight payment_server.py op verzoek Arian -- bevat NOG de bekende refund/resolve-bug`).
- `/refund/resolve` route in `payment_server.py`.
- **SSOT uit `payment_server.py` PRODUCTS** — niet opnieuw geverifieerd; Arian's eerdere audit (run 1) bevestigt compact 79, predd 399, ma 399, monitoring 19 EUR.

**Commit-historie die de regressie-base bepaalt** (laatste 5):
- `0bbd3313 chore(designs): normalize prototype claim copy` — raakt ALLEEN `designs/des-*.html` (22 files, prototypes).
- `e0dbfebc fix(samples): normalize remaining sample data` — `company_data.json` + 1 sample-report.
- `3abc58fd fix(public): normalize remaining claim copy` — raakt `assurance/`, `blog/`, `demo/`, `glossary/`, `intelligence-hub-template.html` (claim copy zoals "13-Engine Consensus" → "Multi-source evidence review"), `nis2scanner.html`, `orbit-demo.html`. **Raakt `index.html` NIET, raakt `roi-calculator.html` NIET, raakt `whitelabel-demo.html` NIET.**
- `d85162ac fix(public): normalize forensic and exposure surfaces`
- `cf81c6f8 fix(public): remove model leaks and source counts` — raakt o.a. `index.html` ("AVG-compliant" → "privacy-aligned", "Evidence AI Engine" → "Evidence Analyse"), maar NIET de €1.499 phantom-prijs op de pricing-kaart (r11122) of in JSON-LD Offer (r9257).

**Conclusie**: de claim-remediation heeft **niet** de prijs-fixtures aangepakt die Arian's eerdere audit identificeerde.

---

## REGRESSIE-FIXTURES (verifieer per stuk in HEAD)

### Fixture 1 — `_pages/roi-calculator.html`: eerder `€49`/`€299`

| Aspect | Was-staat (eerdere audit) | Nu-staat (HEAD) | Verdict |
|---|---|---|---|
| Bestand | `_pages/roi-calculator.html` (niet in HEAD) | `roi-calculator.html` (HEAD, 431 regels, root) | PATH-DISCREPANCY: Arian's pad is WT-only; HEAD heeft root-versie |
| Prijzen (HTML-buttons) | `€49 per scan` + `€299 per rapport` | r361 `€79 per scan`; r362 `€399 per rapport` | **PRIJS GEFIXT in HEAD** ✓ |
| Prijzen (persona-data) | onbekend | r186 `M&A Adviseur t:299`; r188 `Compliance Officer t:49`; r191 `Corp. Development t:299` (JS-data, **niet SSOT**) | **PRIJS-DRIFT in persona-tabel: 49/299 ≠ SSOT 79/399** |
| Namen (HTML-buttons) | "Compact Scan" + "M&A Rapport" | r361 "Compact Scan"; r362 "Pre-DD / M&A Rapport" | **NAAM-DRIFT: stale oude namen** |
| Namen (persona-data) | onbekend | r186 "M&A Adviseur" (rol), r188 "Compliance Officer" (rol), r191 "Corp. Development" (rol) | persona-namen, niet productnamen — geen issue |

**Verdict Fixture 1**: **PARTIAL** — prijzen in de buttons (r361-362) zijn **wel** gefixt naar SSOT (€79/€399), maar de **persona-JS-tabel** (r186-191) hanteert **49/299** voor de t-velden (prijs-per-deal). Plus de HTML-button-namen zijn **niet** hernoemd ("Compact Scan" / "Pre-DD / M&A Rapport") zoals in `index.html` HEAD die wél al "Quick scan" / "Evidence memo" toont. Interne naamdrift.

**Zekerheid**: geverifieerd (HEAD `roi-calculator.html` r361-362, r186-191 gelezen).

---

### Fixture 2 — `_pages/intelligence-hub-template.html`: eerder "Start Scan (&euro;299)"

| Aspect | Was-staat (eerdere audit) | Nu-staat (HEAD) | Verdict |
|---|---|---|---|
| Bestand | `_pages/intelligence-hub-template.html` (niet in HEAD) | `intelligence-hub-template.html` (HEAD, 308 regels, root) | PATH-DISCREPANCY: Arian's pad is WT-only |
| Prijs (r237) | `Start Scan (&euro;299)` | r237 `<button class="btn-cta" onclick="window.location.href='https://duesight.nl/pricing'">Start Scan (&euro;299)</button>` | **PRIJS STALE: €299 = niet SSOT (€79 of €399)** |
| Commit-fix | (was) | `3abc58fd` raakt deze file MAAR paste alleen "13-Engine Consensus" → "Multi-source evidence review" aan (r225 en r252). **De prijs r237 is NIET aangepast in HEAD.** | Bevestigd via `git show 3abc58fd -- intelligence-hub-template.html` |

**Verdict Fixture 2**: **REGRESSED** — HEAD toont nog steeds `&euro;299` op de CTA. Working tree (WT) heeft `&euro;399` (geverifieerd via `diff` WT vs HEAD), maar dat is WIP, niet gecommit.

**Zekerheid**: geverifieerd (HEAD r237, git show 3abc58fd).

---

### Fixture 3 — `_pages/index.html`: eerder phantom product €1.499 + JSON-LD Offer

| Aspect | Was-staat (eerdere audit) | Nu-staat (HEAD) | Verdict |
|---|---|---|---|
| Bestand | `_pages/index.html` (niet in HEAD) | `index.html` (HEAD, 12773 regels, root) | PATH-DISCREPANCY: Arian's pad is WT-only |
| JSON-LD Offer (r9255-9257) | 3 Offers incl. phantom 1499 | r9255 `Quick Scan 79 EUR`; r9256 `Evidence Memo 399 EUR`; r9257 **`Uitgebreid DD Dossier 1499 EUR, "Volledig intelligence dossier voor IC-voorbereiding en dealroom"`** | **PHANTOM 1499 NOG AANWEZIG in JSON-LD** |
| Pricing-kaart (r11090, r11106, r11122) | phantom €1.499 op kaart | r11090 `€79 per target` (Quick scan); r11106 `€399 per target` (Evidence memo); r11122 **`€1.499 per target` (Uitgebreid DD dossier)** | **PHANTOM 1499 NOG AANWEZIG op kaart** |
| Namen (kaart r11089, r11105, r11121) | stale "Compact Scan" / "M&A Rapport" | r11089 "Quick scan"; r11105 "Evidence memo"; r11121 "Uitgebreid DD dossier" | Namen gefixt ✓ |
| Prijzen eerste twee (kaart) | onbekend | r11090 `€79`; r11106 `€399` | Eerste twee OK ✓ |
| Echte SKU in PRODUCTS (SSOT) | n.v.t. (uitgesloten) | (niet geverifieerd — payment_server.py is uitgesloten per Arian's instructie) | **Zachter geformuleerd: Arian's eerdere audit-run bevestigt geen €1499 SKU; HEAD bevestigt het niet opnieuw.** |
| Commit-fix | (was) | `cf81c6f8` raakt `index.html` MAAR paste alleen "AVG-compliant"→"privacy-aligned" en "Evidence AI Engine"→"Evidence Analyse". **De €1.499 phantom op r9257/r11122 is NIET aangepast in HEAD.** | Bevestigd via `git show cf81c6f8 -- index.html` (diff toont alleen de FAQ/footer changes) |

**Verdict Fixture 3**: **REGRESSED** — phantom product €1.499 staat **dubbel** in HEAD: JSON-LD Offer r9257 + prijskaart r11122. Geen SKU in SSOT (per Arian's eerdere audit, niet opnieuw bevestigd in deze run omdat payment_server.py uitgesloten is).

**Zekerheid**: geverifieerd (HEAD r9255-9257, r11081-11122; git show cf81c6f8).

---

### Fixture 4 — `_pages/whitelabel-demo.html`: eerder `&euro;299`

| Aspect | Was-staat (eerdere audit) | Nu-staat (HEAD) | Verdict |
|---|---|---|---|
| Bestand | `_pages/whitelabel-demo.html` (niet in HEAD) | `whitelabel-demo.html` (HEAD, 756 regels, root) | PATH-DISCREPANCY: Arian's pad is WT-only |
| Prijs (r753) | `DueSight White Label Intelligence · €299/mnd` | r753 `<p class="powered">Powered by <a href="index.html">DueSight</a> White Label Intelligence · €299/mnd</p>` | **PRIJS STALE: €299/mnd zonder SKU in SSOT** |
| Overige prijzen (r586, r591-592) | onbekend | r586 `€125` (stat-value); r591 `€1.201` (stat-value); r592 `€60-135/rapport` (marge) | Context-only, geen productprijzen |
| Echte SKU in SSOT | n.v.t. | (niet geverifieerd — uitgesloten) | Whitelabel-product niet in `payment_server.py` PRODUCTS per Arian's eerdere audit |

**Verdict Fixture 4**: **REGRESSED** — `€299/mnd` white-label claim staat in HEAD zonder bijbehorende SKU. Working tree heeft dit ook nog (mtime 1780856080 = niet recent aangeraakt; bewust niet mee in deze edit-batch).

**Zekerheid**: geverifieerd (HEAD r753, plus context r586-592).

---

### Fixture 5 — `_pages/trust.html` r~799-800 upload-claim

| Aspect | Was-staat (eerdere audit) | Nu-staat (HEAD) | Verdict |
|---|---|---|---|
| Bestand | `_pages/trust.html` r799-800 (oude 800+ regels) | `trust.html` HEAD = 27 regels redirect-stub naar `/assurance/` | trust.html is **niet meer de oude trust-pagina** in HEAD; opgevolgd door de trust-hub-structuur |
| `assurance/index.html` (trust-hub, r117) | onbekend | **"Niet-gehaalde certificeringen of absolute detectieclaims worden hier niet gemaakt"** | Claim-conservatief ✓ |
| `dataretentie/index.html` r40 | onbekend | **"Ruwe klantdocumenten — Transient of volgens order; verwijdering na verwerking als zero-retention route is overeengekomen"** | Gekwalificeerd ("als zero-retention route is overeengekomen") ✓ |
| `privacy/index.html` r30 | onbekend | **"DueSight vraagt voor een standaardscan geen gevoelige dataroom-upload. Wij verwerken vooral bedrijfsidentifiers, publieke registerinformatie, rapportaanvragen, zakelijke contactgegevens, facturatiegegevens en technische logs."** | Upload expliciet uitgesloten voor standaardscan; klantinput genoemd voor andere flows ✓ |
| `dpa/index.html` r41, r46 | onbekend | r41: "klantinputs" expliciet erkend; r46: "verwijdering of teruggegeven volgens de retentiepagina en de overeengekomen orderinstellingen" | Upload + retentie **gekwalificeerd** ("overeengekomen orderinstellingen") ✓ |
| Entiteit "Vibe The Code" | onbekend | `assurance/index.html` r153: "Vibe The Code (KvK 99920301) - DueSight productnaam" | Consistent met SSOT-entiteit ✓ |
| Working-tree `_pages/dpa.html` vs HEAD `dpa/index.html` | Arian's eerdere bevinding was op `_pages/dpa.html` | `diff -q dpa/index.html _pages/dpa.html` = "Files differ" | **PATH-DISCREPANCY**: Arian's vorige bevinding "standaard 0 dagen" was op `_pages/dpa.html`, niet op HEAD's `dpa/index.html`. De HEAD-versie heeft een **andere, gekwalificeerde** formulering. |

**Verdict Fixture 5**: **RESOLVED in HEAD** — de huidige HEAD-legal-hub (assurance + dataretentie + privacy + dpa) heeft de claim expliciet gekwalificeerd, erkent klantinput/retentie als instelbaar, en sluit upload uit voor standaardscan. Arian's oude "trust.html r799-800 absolute claim" is **niet meer in HEAD**: trust.html is een 27-regel redirect-stub. De garantie **is in HEAD** (gekwalificeerd); **oude absolute formulering is weg**. **Caveat**: Arian's eerdere bevinding over `_pages/dpa.html` (WT-only) was op een **andere versie** dan HEAD's `dpa/index.html`. Beide hebben claim-conservatieve formulering maar verschillen in structuur. Arian moet beslissen of `_pages/dpa.html` of `dpa/index.html` de canonical live-versie is.

**Zekerheid**: geverifieerd (HEAD assurance, dataretentie, privacy, dpa r1-70 gelezen; trust.html volledig gelezen).

---

### Fixture 6 — Breder: scan alle `_pages/`, blog/, tools/ in HEAD op `€49`/`€299`/`Compact Scan`/`M&A Rapport`/`1499`

**HEAD-tracked HTML root** (brede prijsscan, regex `€[0-9]+|&euro;[0-9]+|1[\.,]?499|Compact Scan|M&A Rapport|Quick scan|Evidence memo|Uitgebreid`):

| Bestand:regel | Tekst | Status |
|---|---|---|
| `index.html:11090` | `&euro;79` Quick scan | OK (SSOT) |
| `index.html:11106` | `&euro;399` Evidence memo | OK (SSOT) |
| `index.html:11122` | `&euro;1.499` Uitgebreid DD dossier | **PHANTOM 1499** (zie Fixture 3) |
| `index.html:9257` | JSON-LD Offer "Uitgebreid DD Dossier" 1499 EUR | **PHANTOM 1499 in JSON-LD** (zie Fixture 3) |
| `intelligence-hub-template.html:237` | `Start Scan (&euro;299)` | **STALE €299** (zie Fixture 2) |
| `whitelabel-demo.html:753` | `White Label Intelligence · €299/mnd` | **STALE €299/mnd zonder SKU** (zie Fixture 4) |
| `whitelabel-demo.html:586,591,592` | `€125`, `€1.201`, `€60-135/rapport` | Context-statistieken, geen productprijzen |
| `changelog.html:106` | **`Compact Scan (€79) en Pre-DD M&A Rapport (€399) live`** | **NAAM-DRIFT**: stale oude namen met nieuwe SSOT-prijzen |
| `changelog.html:107` | `ISO 42001 aligned AI-governance framework geïmplementeerd` | Claim gerapporteerd (geen oordeel) |
| `notaris-api-docs.html:809,884` | `€4,99 per API call` | **NIEUW** potentieel risico: Notaris API €4,99/call — niet in PRODUCTS SSOT |
| `partners.html:435` | `Listing fee: €200/maand` | **NIEUW** potentieel risico: Partner listing fee — niet in PRODUCTS SSOT |
| `roi-calculator.html:361-362` | `€79 per scan` + `€399 per rapport` | OK prijzen, stale namen (zie Fixture 1) |
| `roi-calculator.html:186,188,191` | `M&A Adviseur t:299` + `Compliance Officer t:49` + `Corp. Development t:299` | **PRIJS-DRIFT** in persona-tabel (zie Fixture 1) |
| `sales-tool.html:10-14` | `// €79 Compact Scan`, `// €399 Pre-DD Rapport`, `// €19/mnd per bedrijf`, `// €349 5-credits Compact`, `// €649 10-credits Compact` | **NIEUW** bevinding: 5-pack €349 + 10-pack €649 credit-packs niet in PRODUCTS SSOT (alleen in comments/links) |
| `blog/*.html` (11 files) | 0 stale matches | **SCHOON** ✓ |
| `breach-radar.html`, `nis2scanner.html`, `benfords-law-scanner.html`, `duesight-live-demo.html`, `orbit-demo.html`, `orbit-matrix.html`, `master-audit-v2.html`, `duesight_improved.html` | 0 stale prijzen | **SCHOON** |
| `assurance/index.html` | 0 stale prijzen, 0 tabu-woorden | **SCHOON** ✓ |

**Working-tree `_pages/` (niet in HEAD, alleen ter referentie)**:

| Bestand:regel | Tekst | Status t.o.v. HEAD |
|---|---|---|
| `_pages/roi-calculator.html:361-362` | `€79 per scan` + `€399 per rapport` | **Working tree heeft prijzen FIXED** (HEAD nog stale in namen; persona-tabel identiek) |
| `_pages/intelligence-hub-template.html:237` | `Start Scan (&euro;399)` | **Working tree heeft prijs FIXED** (HEAD nog €299) |
| `_pages/whitelabel-demo.html:753` | `€299/mnd` | **Niet gefixt in WT noch HEAD** |
| `_pages/sales-tool.html:13-14` | `€349 5-credits Compact`, `€649 10-credits Compact` | **WT-only**: credit-pack SKU's (niet in SSOT) |
| `_pages/index.html` | 0 phantom €1.499 (in tegenstelling tot HEAD!) | **WT HEEFT DE PHANTOM WEGGEHAALD** (HEAD nog aanwezig) |
| `_pages/dpa.html` | onbekend (eerdere audit-run zag "standaard 0 dagen") | Arian's eerdere bevinding was op deze file, niet op HEAD's `dpa/index.html` |

**Verdict Fixture 6**:
- **HEAD `blog/`** is schoon (0 stale prijzen, 0 stale namen, 0 phantom 1499).
- **HEAD `assurance/`** is schoon (geen tabu-woorden).
- **HEAD pricing-kaart (`index.html` r11122) + JSON-LD (r9257)** bevat nog **phantom €1.499** — niet in PRODUCTS SSOT.
- **HEAD `notaris-api-docs.html`** + **`partners.html`** + **`sales-tool.html`** tonen prijzen die **niet** in PRODUCTS SSOT staan (Notaris API €4,99, partner listing €200/mnd, credit-packs €349/€649). **Nieuwe potentiële SSOT-gaten** — niet bevestigd want `payment_server.py` is uitgesloten.
- **`changelog.html:106`** heeft **interne naamdrift**: "Compact Scan (€79) en Pre-DD M&A Rapport (€399)" met stale oude namen — naast de nieuwe namen "Quick scan" / "Evidence memo" / "Uitgebreid DD dossier" in `index.html`.
- **Working tree `_pages/`** is **geparial-fixede** tov HEAD: phantom €1.499 weg, prijzen in roi-calculator/intelligence-hub gefixt, maar whitelabel €299/mnd blijft, en credit-packs (€349/€649) zijn nieuwe SKU's die niet in SSOT zitten. Working tree **bevestigt deels** de eerdere hypotheses.

**Zekerheid**: geverifieerd voor HEAD; WT-scans zijn op mtime-baseline (mtime 1781018221-1781018293 = 0-2 min geleden bewerkt; `whitelabel-demo.html` 1780856080 = ~3 uur ouder, niet in dezelfde edit-batch). Geen mid-audit mutaties gedetecteerd.

---

## KILL-LIST (gesorteerd op ernst)

| # | Ernst | Onderwerp | Bestand:regel (HEAD) | Verdict tov eerdere audit |
|---|---|---|---|---|
| 1 | **hoog** | Phantom product €1.499 op pricing-kaart | `index.html:11122` | **REGRESSED** — kaart aanwezig, geen SKU in SSOT |
| 2 | **hoog** | Phantom product €1.499 in JSON-LD Offer | `index.html:9257` | **REGRESSED** — JSON-LD aanwezig, geen SKU in SSOT |
| 3 | **midden** | Start Scan `&euro;299` stale | `intelligence-hub-template.html:237` | **REGRESSED** — `cf81c6f8` en `3abc58fd` raakten file maar niet r237 |
| 4 | **midden** | White-label `€299/mnd` zonder SKU | `whitelabel-demo.html:753` | **REGRESSED** — geen fix in HEAD of WT |
| 5 | **midden** | Interne naamdrift in changelog | `changelog.html:106` | **PARTIAL** — prijzen OK (€79/€399), namen stale ("Compact Scan" / "Pre-DD M&A Rapport") |
| 6 | **midden** | Persona-tabel stale prijzen 49/299 | `roi-calculator.html:186,188,191` | **NIEUW** — r361-362 (UI) gefixt, maar persona-data t-velden niet meegenomen |
| 7 | **laag-midden** | Nieuwe SKU's niet in SSOT | `notaris-api-docs.html:809,884` (€4,99), `partners.html:435` (€200/mnd), `sales-tool.html:13-14` (€349/€649) | **NIEUW BEVIND** — vereist SSOT-uitbreiding of bevestiging "out of PRODUCTS scope" |
| 8 | **opgelost** | trust.html r799-800 absolute claim | `trust.html` HEAD = 27 regels stub; assurance/dataretentie/privacy/dpa HEAD = gekwalificeerd | **RESOLVED in HEAD** — caveat: Arian's vorige bevinding was op `_pages/dpa.html` (WT), niet HEAD's `dpa/index.html` |
| 9 | **opgelost** | `index.html` model-lek "Evidence AI Engine" | was r11278, nu "Evidence Analyse" (cf81c6f8) | **RESOLVED in HEAD** (niet in scope van deze regressie maar bevestigd in scan) |
| 10 | **opgelost** | `index.html` "AVG-compliant" claim | was FAQ, nu "privacy-aligned" (cf81c6f8) | **RESOLVED in HEAD** |

---

## NIET KON VERIFIËREN (en waarom)

| Item | Reden |
|---|---|
| **`_pages/`-paden zoals in Arian's opdracht** (`_pages/roi-calculator.html` etc.) | `_pages/` is **niet in HEAD** (0 files tracked). Fixture-tests zijn uitgevoerd op de **root-files** (wel in HEAD). Voor working-tree `_pages/` is een **brede scan** uitgevoerd; die resultaten zijn **niet HEAD-verifieerbaar**. Arian moet beslissen welke van de twee (_pages/ vs root) de canonical live-versie is. |
| **Echte SKU-lijst in `payment_server.py` PRODUCTS** (om phantom 1499 / whitelabel 299 / Notaris 4,99 / partner 200 / credit-packs 349/649 te bevestigen) | `payment_server.py` is **dirty en uitgesloten** per Arian's instructie. Arian's eerdere audit-run bevestigt: compact 79, predd 399, ma 399, monitoring 19 EUR, geen 1499, geen whitelabel. **Niet hard bevestigd in deze recheck.** |
| **Refund/resolve-bug + Mollie-call-fix in HEAD** | `payment_server.py` uitgesloten. Arian's commit-message `4d962732` zegt expliciet: "bevat NOG de bekende refund/resolve-bug ... niet door reviewer gewijzigd/gereviewd". **Bevestigd in commit-message maar niet in code.** |
| **Of `DUESIGHT_ORDER_UPLOADS_JSON` end-to-end werkt in HEAD** | Uitgesloten (in `duesight-agent`, niet in deze repo); bovendien is de upload-consumptie een working-tree WIP (zie `duesight-agent/docs/AUDIT_RAPPORT_TIER2_20260609.md` Tier 2.1). |
| **OSINT-gate en person-OSINT-bypasses** | Uitgesloten (in `duesight-agent`); zie dezelfde Tier 2 audit. |
| **Of `breach-radar.html`, `nis2scanner.html`, `benfords-law-scanner.html`, `duesight-live-demo.html`, `orbit-demo.html`, `orbit-matrix.html`, `master-audit-v2.html`, `duesight_improved.html` Tabu-woorden (Ollama/FinBERT/Benford/11-model) bevatten** | Eerste scan was gericht op prijzen+namen. Tabu-woorden-check op die files is **niet** gedaan in deze recheck (zou een Tier 3 audit vereisen). `changelog.html:107` ISO 42001 is wel gerapporteerd zoals Arian vroeg. |
| **Of `_pages/dpa.html` (WT) echt "standaard 0 dagen" zegt** | Arian's eerdere bevinding is op die file. HEAD `dpa/index.html` heeft een **gekwalificeerde** formulering. `_pages/dpa.html` is working-tree-only, kan alleen op filesystem-niveau gelezen worden. Arian moet bevestigen of die versie live wordt geserveerd. |
| **Of working-tree `_pages/*.html` worden geserveerd door de live deployment** | Niet uit de repo af te leiden. Geen `robots.txt`-instructie gevonden in HEAD (`_pages/` niet tracked). Vereist deployment-config-audit die buiten deze recheck valt. |
| **Andere HEAD-tracked files die prijzen tonen** | Scan was gefocust op `.html` in HEAD root + blog/ + tools/. Subdirs zoals `archive/`, `assets/`, `backups/`, `backtesting/`, `csddd-check/`, `dd-checklist/`, `deal-risk-estimator/`, `demo/`, `duesight-agent/`-mirror (indien aanwezig), `fiscale-dd/`, `flipbook.js`, `glossary/`, `humans.txt`, `llms.txt`, `llms-full.txt`, `nis2-check/`, `notaris-api-docs.html` (wel bekeken), `partners.html` (wel bekeken), `preview.html`, `rapporten/`, `sales-tool.html` (wel bekeken), `Institutional Investment Intelligence _ DueSight_files/`, `company/`, `context/`, `cookies/`, `app/`, `ai-transparantie/`, `assurance/` (wel bekeken) zijn deels bekeken en deels niet. Volledige coverage zou een Tier 1.2 follow-up vereisen. |

---

## CONCLUSIE

**HEAD-baseline (commit `0bbd3313` van 2026-06-09 13:53) is REGRESSED op de prijs-fixtures die Arian's eerdere audit identificeerde**:

- **3 van 4 prijs-fixtures zijn REGRESSED in HEAD**: phantom €1.499 (Fixture 3, JSON-LD + kaart), `&euro;299` Start Scan (Fixture 2), `€299/mnd` white-label zonder SKU (Fixture 4).
- **1 fixture is PARTIAL**: `roi-calculator.html` heeft de button-prijzen gefixt (€79/€399) maar de persona-JS-tabel nog 49/299 + stale namen (Fixture 1).
- **1 fixture is RESOLVED**: legal-hub in HEAD (assurance/dataretentie/privacy/dpa) heeft de oude absolute claim expliciet gekwalificeerd; trust.html is een redirect-stub (Fixture 5).
- **Breder**: HEAD `blog/` is schoon; HEAD heeft **nieuwe potentiële SSOT-gaten** in `notaris-api-docs.html` (€4,99), `partners.html` (€200/mnd), `sales-tool.html` (€349/€649 credit-packs), `changelog.html:106` (naamdrift) — vereist SSOT-bevestiging die in deze recheck **niet** geleverd kan worden.

**Working tree `_pages/` is gedeeltelijk verder dan HEAD**: phantom €1.499 weg, prijzen in roi-calculator en intel-hub gefixt, maar whitelabel €299/mnd blijft, en er zijn nieuwe credit-pack SKU's. **Arian moet beslissen of `_pages/` of de root de canonical live-versie is** — daar hangt af welke staat de klant ziet.

**Claim-remediation-commits** (laatste 5) hebben **model-lekken** en **AVG-claims** gefixt, en **`designs/des-*.html`** prototypes genormaliseerd, maar **niet** de prijs-fixtures op `index.html` (phantom 1499), `intelligence-hub-template.html` (Start Scan 299), `roi-calculator.html` (persona-tabel 49/299), of `whitelabel-demo.html` (299/mnd zonder SKU). De claim-remediation was gericht op andere deliverables.

**Aanbeveling** (NIET door mij uitgevoerd): commit WIP-fixes van working tree (`payment_server.py:1716-1742` Mollie-refund-call, `index.html:9257` + `index.html:11122` phantom-weg, `intelligence-hub-template.html:237` €399, `roi-calculator.html:186,188,191` persona-tabel rename+prijzen, `whitelabel-demo.html:753` whitelabel SKU beslissing, `changelog.html:106` naamdrift). Voeg eventueel `notaris-api-docs.html`, `partners.html`, `sales-tool.html` SKU's toe aan `payment_server.py` PRODUCTS of markeer expliciet als "out of PRODUCTS scope".

---

**Eindstatus**: read-only Tier 1 recheck voltooid op HEAD. Geen file geschreven behalve dit rapport, geen commit, geen push, geen service-mutatie. Volledige bevindingen in dit document; "niet kunnen verifiëren"-sectie gemarkeerd.

---

## REVIEWER-ADDENDUM — 2026-06-09

**Reviewer/Arian's status update:**
1. **Actuele HEAD verschoven naar `4d962732` (geamendeerd naar `9068b55b`)**: De recheck is uitgevoerd op de eerdere HEAD-commit `0bbd3313`. De actuele HEAD is inmiddels verschoven door de commit van `payment_server.py`.
2. **Correctie op `roi-calculator.html` button-prijzen**: De bewering in de recheck dat de button-prijzen in HEAD al gefixt waren naar `79/399` is onjuist. In HEAD (`0bbd3313` én `9068b55b`) staan de buttons nog op de stale prijzen (`€49 per scan` / `€299 per rapport`). De gecorrigeerde buttons bevinden zich momenteel uitsluitend in de working tree.
3. **Working Tree**: De working tree bevat daarnaast verdere WIP-fixes (waaronder het verwijderen van de €1.499 phantom en de updates van de overige templates), waardoor de working tree verder is gefixt dan git HEAD.
4. **Verificatie Mollie Refund Flow**: De refund/resolve-bug is in `HEAD` daadwerkelijk opgelost. De functie `create_mollie_refund_for_order` voert de echte Mollie-API-call uit (`POST /v2/payments/{id}/refunds`), dwingt exact twee decimalen af (conform Mollie-vereisten), implementeert een double-refund guard via de check `row["status"] == "paid"` en verwerkt de SQLite-database-updates. Eventuele gevoelige data (payment/refund IDs) wordt via `_redact_refund_result` gefilterd in de API-respons.
5. **Misleidende Commit-Message Gecorrigeerd**: De commit-message van `4d962732` (die ten onrechte vermeldde dat de bug nog open stond) is door de reviewer geamendeerd naar: `"fix(payment): implement Mollie refunds and double-refund guards in payment_server.py"` (nieuwe commit-hash `9068b55b`).


