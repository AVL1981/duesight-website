# DueSight — FORENSISCH OVERZICHT & CLAUDE CODE HANDOVER
> Versie: 5.0 FINAL · Datum: 30 maart 2026 · Classificatie: Intern Strategisch
> Gegenereerd door: Claude Opus 4.6 na forensisch onderzoek van chathistorie + codebase

---

## 0. WAT DIT DOCUMENT IS

Dit is het **enige document dat Claude Code nodig heeft** om aan DueSight te werken.
Het bevat ALLES: architectuur, bestanden, beslissingen, bugs, regels, en context.
**Lees het VOLLEDIG voordat je code aanraakt.**

**Stack SSOT (8 jun 2026):** canonieke website/API-stack = `duesight-website\app\`, met runtime entrypoints `app\main.py`, `payment_server.py` en `scan_server.py`. `duesight-monorepo\` is geen actieve website-stack; raak die alleen aan als de taak daar expliciet om vraagt.

---

## 1. WAT IS DUESIGHT

Pre-due-diligence intelligence platform voor M&A, PE en compliance professionals.
Genereert AI-gesynthetiseerde bedrijfsrapporten voor NL/DACH mid-market.

- **Product**: Automated company screening reports
- **Pricing**: €79 Compact / €399 Pre-DD M&A / €19/mnd Monitoring
- **Doelgroep**: M&A boutiques (Marktlink, Oaklins, RSM), PE firms, compliance officers
- **Regio**: Nederland primair + DACH (DE/AT/CH)
- **KvK**: 94092282
- **Founder**: Arian (sole builder), ook eigenaar van GMU (online marketing bureau, Meppel)
- **Concurrent**: DiligenceSquared ($50K/rapport), Bridgetown Research ($19M gefund)
- **DueSight's gat**: NL mid-market pre-DD screening op €79-399, niet €50K

---

## 2. PROJECTLOCATIES — ALTIJD DEZE PADEN

```
WEBSITE + FRONTEND:
C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website\
├── index.html               → Hoofdpagina (~17000 regels, 849KB+)
├── designs/                 → 30+ hero design varianten (des-1.html t/m des-90.html)
├── app/                     → FastAPI backend
│   ├── main.py              → Server entrypoint
│   ├── services/
│   │   ├── ai_gateway.py    → AI model routing (7KB)
│   │   └── ddintel.py       → DD intelligence service (3KB)
│   └── api/routers/
│       ├── scan.py          → Scan endpoint
│       ├── financial.py     → Financial data endpoint
│       ├── shadow.py        → Shadow analysis
│       ├── geo.py           → GEO monitoring
│       └── subsidy.py       → Subsidie checks
├── scan_server.py           → Live scan backend (110KB) ← PRODUCTIE
├── scan_client.js           → Live scan frontend (36KB)
├── sample-report-*/         → 12 voorbeeldrapporten
├── CLAUDE.md                → Agent context doc (DIT UPDATEN)
├── DESIGN_AUDIT.md          → Design audit met scores
└── BUILD_ALL.py             → Design generator + switcher upgrade

AI DD ENGINE (KERN VAN HET PRODUCT):
C:\antigravity\duesight-agent\
├── agents/
│   ├── multi_model_thinker.py    → 11-engine consensus, 3-tier escalatie (44KB) ← HART
│   ├── deep_research_agent.py    → Autonome OSINT + web research (26KB)
│   ├── orchestrator.py           → DD pipeline coordinator (22KB)
│   ├── research_agent.py         → Web research agent (18KB)
│   ├── base_agent.py             → Agent base class (14KB)
│   ├── epistemic_agent.py        → 10-gate validatie (14KB)
│   ├── validation_agent.py       → Output validatie (8KB)
│   └── analysis_agent.py         → Analyse agent (7KB)
├── tools/                        → 16 intelligence modules (330KB totaal)
│   ├── financial_proxies.py      → Altman Z-Score, revenue, EBITDA proxy (56KB)
│   ├── anti_hallucination.py     → Multi-layer fact-check (44KB)
│   ├── vision_analyzer.py        → PDF/document vision parsing (27KB)
│   ├── beast_mode_bridge.py      → Max-depth analyse (26KB)
│   ├── preflight_check.py        → Pre-analyse validatie (22KB)
│   ├── semantic_fact_checker.py   → Semantische cross-verificatie (21KB)
│   ├── data_quality_engine.py    → Data kwaliteitsscoring (21KB)
│   ├── employee_intel.py         → LinkedIn/OSINT employee intel (19KB)
│   ├── escalation_engine.py      → Risk escalatie routing (16KB)
│   ├── serp_checker.py           → SERP positiemonitor (13KB)
│   ├── quantum_security.py       → Quantum-safe crypto checks (13KB)
│   ├── competitive_intel.py      → Concurrent analyse (12KB)
│   ├── tool_result.py            → Result formatting (12KB)
│   ├── legal_intel.py            → Rechtspraak.nl, ECLI (10KB)
│   ├── github_intel.py           → GitHub OSINT (10KB)
│   └── product_reviews.py        → Product reviews intel (8KB)
├── render_report.py              → JSON → HTML rapport renderer (22KB)
├── mkb_enrichment.py             → MKB enrichment pipeline (17KB)
├── api.py                        → REST API (12KB)
├── config.py                     → Configuratie (6KB)
├── main.py                       → Entrypoint (6KB)
├── .env                          → API keys (NOOIT committen)
└── workflows/dd-report.md        → DD rapport workflow spec

DATA PIPELINE + BACKTESTING:
C:\antigravity\duesight-agent\ (of backtesting/ in eerdere versies)
- duesight_master.duckdb          → MASTER DATABASE (1.1GB) ← NOOIT VERWIJDEREN
- nightly_data_sync.py            → Dagelijkse sync (~71 min runtime)
- nightly_batch_screen.py         → 15.000 GLEIF + 5.000 ICIJ per nacht
- sanctions_screener.py           → Productie sanctions screener
- duesight_entity_resolution.py   → Splink entity resolution (F1: 95.2%)

SCRIPTS + DATA PIPELINE:
C:\Users\arian\Promptwatch_clone\gego\
├── scripts/                      → 66 scripts (GLEIF, ICIJ, Splink, KVK...)
├── data/                         → 14.500+ bestanden (cache, archives)
└── llms.txt                      → GEO optimalisatie (deploy-ready)

LITELLM PROXY:
C:\Users\arian\Promptwatch_clone\gego\duesight-ccr\
├── litellm-config.yaml           → 15 provider config (v1.82.6 — NIET UPGRADEN)
└── [2 source patches: streaming_iterator.py + handler.py]
```

---

## 3. AI ENGINE ARCHITECTUUR — Multi-Model Thinker v5.5

### 3-Tier Escalatie (DeepMind-gebaseerd)

```
TIER 3 (pre-fetch): Serper live data injectie VOOR alle engines
    ↓
TIER 1 (altijd, parallel):
  • Gemini 3 Flash          — Bull case (optimistisch)
  • Cerebras Qwen3-235B     — GRATIS 24M tok/dag, 2600 tok/s
  • DeepSeek-R1             — Complex reasoning (GRATIS via NVIDIA NIM)
  • GLM-5/4.7               — Juridisch, non-refusal (GRATIS)
  • Qwen3-235B              — Breed, meertalig
  • GPT-4.1/GPT-5           — Via GitHub (gratis preview)
  • MiniMax M2.5/M2.7       — SWE-Bench 80%, $0.30/M tokens
  • Grok 4.1 Fast           — Snel
  • Ollama lokaal (Nemotron-30B + GLM-4.7-Flash) — Privacy-first
    ↓ consensus < 60%?
TIER 2 (escalatie):
  • Gemini 2.5 Pro          — Bear case (adversarial)
  • GPT-OSS-120B via Groq   — MoE perspectief (14.4K req/dag gratis)
```

### KRITIEKE ARCHITECTUURBESLISSINGEN
- **Parallel → Consensus is FOUT** (17x error amplificatie, DeepMind dec 2025)
- **TODO**: Migreren naar Sequential Debate (analyse → kritiek → synthese)
- **Serper probleem**: Pre-fetch deelt factbasis → diversiteit verdwijnt
- **TODO**: Herpositioneer Serper naar post-Tier-1 verificatielaag

### NLP Prefilter Stack (lokaal, €0, RTX GPU)
```
ProsusAI/finbert           → Financial sentiment
FinBERT-ESG-9cat           → CSRD/ESG compliance classificatie
FinBERT-FLS                → Forward-Looking Statements detectie
LegalBERT                  → Juridische NER en tagging
Twitter-RoBERTa            → Social media paniek/sentiment
Fin-ModernBERT             → RAG embeddings (document ranking)
FinBERT2 (ValueSimplex)    → Upgrade: +15.6% betere embeddings ← GEPLANNED
SaulLM-7B                  → Juridische redenering (past op 1× RTX 5060 Ti)
```

### Quality Gates
```
Epistemic Agent            → 10-gate validator
Anti-Hallucination Layer   → Multi-layer fact-check, cross-source
Beast Mode Quality Patterns → Max-depth analyse
Data Quality Engine        → Scoring per databron
Checkpoint/Resume          → Crash recovery
```

---

## 4. DATA BRONNEN — 64+ Institutionele Bronnen

### Master Database (DuckDB, 1.1GB)

| Bron | Type | Refresh | Kosten |
|------|------|---------|--------|
| KvK Handelsregister | NL bedrijven | Werkdagen | €/query |
| GLEIF Global LEI Index | LEI + ownership (L1/L2) | Dagelijks | Gratis (CC0) |
| ICIJ Offshore Leaks | Panama/Pandora Papers | Maandelijks | Gratis |
| OpenSanctions | OFAC/EU/UN/FATF sancties + PEP | Dagelijks | Gratis |
| Rechtspraak.nl | ECLI uitspraken | Dagelijks | Gratis |
| Staatscourant SRU | Faillissementen | Dagelijks | Gratis |
| Wayback CDX | Website tijdlijn (historische claims) | On-demand | Gratis |
| Companies House | UK bedrijven | Dagelijks | Gratis |
| INSEE SIRENE | Franse bedrijven | Maandelijks | Gratis |
| CBS/Statline | Nederlandse statistieken | Maandelijks | Gratis |
| Bundesanzeiger | Duitse publicaties | Dagelijks | Gratis |
| NVD/CISA CVE | Cybersecurity kwetsbaarheden | Dagelijks | Gratis |
| GDELT | Wereldwijd nieuws monitoring | Real-time | Gratis |
| Shodan | Internet-exposed services | On-demand | Freemium |

### 4-Tier Intelligence Pipeline

```
TIER 1: Legal/Sanctions
  ├── OFAC/EU/UN sanctiescreening
  ├── ICIJ Panama/Pandora Papers cross-check
  ├── PEP (Politically Exposed Persons) detectie
  ├── UBO-structuur mapping (GLEIF L1/L2)
  └── Rechtspraak.nl ECLI faillissement/fraude

TIER 2: Financial Integrity
  ├── KvK XBRL jaarrekening analyse
  ├── Benford's Law chi² test (fraudedetectie)
  ├── Altman Z-Score (faillissementskans)
  ├── Revenue/EBITDA proxy berekening
  ├── CBS benchmark vergelijking
  └── Isolation Forest ML anomalie detectie (F1: 95.2%)

TIER 3: Cybersecurity / NIS2
  ├── NVD/CISA CVE Scanner
  ├── Digital Footprint Analyzer
  ├── GitHub Intel (public repos)
  ├── SecurityHeaders check
  └── EUVD (gepland)

TIER 4: Operational Context
  ├── Wikidata Entity Resolution
  ├── Google Places Verification
  ├── Wayback Machine Profiler (historische claims)
  ├── Job Intel Extractor (vacatures = groei/krimp signal)
  ├── GDELT News Monitor
  └── Product Reviews analyse
```

### Entity Resolution
- **Splink** probabilistisch matching framework
- **DuckDB** backend (past bij bestaande infra)
- **3-fase proces**: LEI anchor → probabilistic → L2 ownership
- **F1: 95.2%** op 1.47M NL bedrijven test set
- **GLEIF als primaire anchor** (CC0, gratis, universeel EU)
- **WAARSCHUWING**: m/u-parameters driften zonder labeled feedback

### Nightly Sync (nightly_data_sync.py, ~71 min)
1. OpenSanctions delta (kritiek, eerst)
2. GLEIF delta refresh
3. ICIJ check op nieuwe releases
4. KVK incrementeel
5. Rechtspraak.nl ECLI
6. Staatscourant faillissementen

**BUGS**: Geen Slack alert bij failure → stil falen → stale data.
**BUGS**: Geen idempotentie in nightly_batch_screen.py → crash = herstart vanaf nul.

---

## 5. HARDWARE

```
CPU:   Intel Core Ultra 9 285K (met NPU voor inference)
RAM:   64 GB DDR5
GPU 0: NVIDIA RTX 5060 Ti 16GB (MiniCPM-V vision, primaire inference)
GPU 1: NVIDIA RTX 5060 Ti 16GB (backup inference)
```

**GPU WAARSCHUWING**: RTX 5060 Ti = Blackwell arch (sm_120).
FP8 via vLLM heeft bekende bugs. Gebruik AWQ of BF16/INT8.

---

## 6. WEBSITE STRUCTUUR

### Dev Toolbar (index.html)
Fixed positie top-left, bevat:
- **RES**: Viewport preview (4K, 2K, FHD, Laptop, iPad, Phone)
- **DES**: Design switcher (1-90 met paging, ◀◀ ◀ × [1-10] ▶ ▶▶)
- **NAV**: Navigation thema's (A, B, C, D, E)

### Design Systeem
- 30+ hero designs in `/designs/des-N.html` (standalone HTML met canvas animaties)
- DES-switcher: iframe overlay (`#ds-design-overlay`) over de hele pagina
- Script: `<script id="ds-design-switcher">` (regel ~16750)
- BUILD_ALL.py genereert ontbrekende designs + upgraded switcher

### Key Scripts in index.html
```
Regel ~16500: ds-viewport-toggle (RES strip)
Regel ~16700: ds-design-switcher (DES 1-90)
Regel ~16830: ds-nav-theme-toggle (NAV A/B/C/D/E)
Regel ~16900: Flip-card click handler
Regel ~16920: Vanta.js init (thema E)
Regel ~17000: KVK Autofill Widget (Overheid.io + OpenKVK)
```

### SEO Assets
- 641 company SEO pages in `/company/` (Adidas, Siemens, Shell, etc.)
- 8 blog artikelen in `/blog/`
- 30 glossary termen in `/glossary/`
- `sitemap.xml`, `robots.txt`, `llms.txt` (GEO optimalisatie)

---

## 7. PRIVACY & COMPLIANCE REGELS (ABSOLUUT)

```
CLOUD OK (publieke data):          CLOUD VERBODEN (privé):
├── Webzoekopdrachten              ├── KVK queries met bedrijfsnaam
├── Publieke OSINT                 ├── ICIJ match resultaten
├── SE Ranking data                ├── GLEIF L2 ownership graphs
├── GEO monitoring                 ├── Klantdata in rapporten
└── Algemene code generatie        └── Rechtspraak ECLI persoonsnamen
```

Privacy-gevoelige data → ALLEEN via Ollama lokaal. NOOIT cloud-API.

### Trust Badges (juridisch gevalideerd)
- ✅ "Zero Data Retention" — eigen technische claim
- ✅ "AVG Art. 25 Privacy by Design" — eigen verklaring (geen certificering)
- ✅ "TLS 1.3 + AES-256" — verifieerbare technische claim
- ✅ "6/11-Engine Cross-Check" — eigen productclaim
- ⚠️ "EU AI Act Ready" → herformuleren naar "EU AI Act Aligned"
- ⚠️ "NIS2-aligned" → OK zolang geen certificeringsclaim
- ❌ NOOIT ISO 27001 claimen zonder daadwerkelijke certificering

---

## 8. LITELLM PROXY (CCR)

```
Config: C:\Users\arian\Promptwatch_clone\gego\duesight-ccr\litellm-config.yaml
Versie: v1.82.6 — NIET UPGRADEN (twee source patches)
Patches: streaming_iterator.py + handler.py (None response/stream bugs)
ZAI: Native zai/ prefix
OpenRouter spend: $12.67/$50

Providers (15):
├── Cerebras    → Llama 4 Scout (GRATIS 24M tok/dag)
├── MiniMax M2.5 → $0.30/M input, 200K context
├── OpenRouter  → qwen3-coder:free, gemini-2.5-flash:free
├── Ollama      → Lokaal, privacy-first
├── NVIDIA NIM  → Kimi K2.5 (requires reasoning_content fallback)
├── ZAI         → Via native prefix
└── [9 meer providers]

Open bug: Claude Code sends image blocks → ZAI/Cerebras reject "Invalid API parameter" error 1210
```

---

## 9. BEKENDE BUGS & TODO's

### Kritiek
1. **Nightly sync geen alerting** → stil falen → stale data in rapporten
2. **Nightly batch geen idempotentie** → crash = herstart vanaf nul
3. **Serper als pre-fetch** → alle engines delen factbasis (diversiteitsverlies)
4. **Parallel consensus 17x error amplificatie** → migreer naar Sequential Debate
5. **Splink parameter drift** → hertraining nodig bij 10+ klanten

### Website
6. **index.html 849KB+** → performance issues
7. **DES-4, DES-5** → multi-section pagina's, geen hero sections
8. **DES-8, DES-9** → te kaal, minimale visuele impact
9. **Mogelijk duplicate `#logo-reveal`** in index.html
10. **`#final-cta-removed`** → lege div met 240px padding (verwijderen)

### LiteLLM
11. **Image blocks → ZAI/Cerebras error 1210**
12. **Kimi K2.5** → requires `additional_drop_params: ["output_config", "thinking"]`

---

## 10. REGELS VOOR AGENTS

1. **NOOIT** index.html backup maken zonder reden (10+ backups bestaan al)
2. **ALTIJD** via localhost:8000 testen na wijzigingen
3. **NOOIT** orbit-matrix of flip-card animaties breken
4. **ALTIJD** DueSight branding consistent houden
5. **NOOIT** externe dependencies toevoegen (alles via CDN)
6. **NOOIT** API keys hardcoden
7. **ALTIJD** privacy boundary respecteren (sectie 7)
8. **BIJ TWIJFEL**: Lees DESIGN_AUDIT.md voor design context
9. **HUIDIGE PRIORITEIT**: EERSTE BETALENDE KLANT
10. **Stop met data-lagen toevoegen** — de stack is klaar

---

## 11. MODEL SELECTIE PER TAAK

| Taak | Model | Reden |
|------|-------|-------|
| DD rapport genereren | Cerebras Scout | Gratis, 2600 tok/s |
| Complexe reasoning/ECLI | MiniMax M2.5 | 80.2% SWE, 20x goedkoper |
| Privacy-gevoelige data | Ollama Nemotron | Lokaal, geen cloud |
| PDF/jaarrekening parsing | MiniCPM-V lokaal | Vision, lokaal |
| Website code schrijven | Antigravity + Gemini | Best voor frontend |
| Pipeline debugging | Claude Sonnet/Code | Beste self-correction |
| Entity resolution | Ollama Qwen3.5 | Lokaal, data blijft hier |
| Juridisch (non-refusal) | GLM-5/GLM-4.7 | Beste voor gevoelige legal content |

---

## 12. QUICK REFERENCE COMMANDS

```bash
# Rapport genereren:
python generate_shell_report.py --company "Bedrijfsnaam" --kvk "12345678"

# Entity resolution:
python duesight_entity_resolution.py --company "Naam"

# Nightly sync handmatig:
python nightly_data_sync.py

# Sanctions screener:
python sanctions_screener.py --name "Naam"

# Live scan backend:
python scan_server.py

# Website dev server:
cd duesight-website && python -m http.server 8000

# CCR starten:
ccr code  # of: cc-cerebras / cc-local / cc-litellm

# Design generator:
python BUILD_ALL.py  # Genereert ontbrekende designs + upgraded switcher
```

---

## 13. WAT MAAKT DUESIGHT UNIEK

Dit is geen standaard SaaS. Dit zijn de technische onderscheiders:

1. **11-engine multi-model consensus** — geen enkel ander platform draait 11 onafhankelijke AI-engines met adversarial cross-validatie
2. **ICIJ Panama/Pandora Papers × OpenSanctions × Rechtspraak.nl** in één output — nergens anders gecombineerd
3. **Benford's Law chi² test** op financiële data — forensische fraudedetectie
4. **Isolation Forest ML** (F1: 95.2%) op 1.47M NL bedrijven
5. **Zero data retention** — geen cloud storage van klantdata, alles volatiel
6. **€5-15/mnd infra** — 8 van 11 engines gratis, rest <$1/rapport
7. **Splink entity resolution** met GLEIF LEI anchoring over 7 EU-landen
8. **NLP prefilter op lokale GPU** — FinBERT, LegalBERT, ESG-BERT reduceren API kosten 60-80%
9. **45M+ bedrijfsrecords** uit 7 Europese landen in DuckDB
10. **Epistemic Agent met 10-gate validatie** — wetenschappelijk onderbouwde kwaliteitsgarantie
