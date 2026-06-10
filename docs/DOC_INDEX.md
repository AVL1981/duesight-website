# DueSight Document Index

| Veld | Waarde |
|------|--------|
| Status | ACTIEF |
| Laatst bijgewerkt | 2026-05-22 |
| Doel | Documentcontrole: wat is leidend, ondersteunend of archief |

---

## Statuslabels

| Label | Betekenis |
|-------|-----------|
| CANONICAL | Leidend document. |
| ACTIVE | Actief ondersteunend document. |
| NEEDS_RECONCILE | Bevat waarde, maar conflicteert of is ouder. |
| ARCHIVE | Historisch/bewaren, niet gebruiken voor besluiten. |
| GENERATED | Output/data; alleen gebruiken met verificatie. |

---

## Canonical Set

| Document | Status | Rol |
|----------|--------|-----|
| `DUESIGHT_KOMPAS.md` | CANONICAL | Master truth en besluitregels. |
| `TASK_REGISTER.md` | CANONICAL | Actuele taakstatus, audit-ID, owner, bewijs. |
| `LAUNCH_GATE.md` | CANONICAL | Go/no-go criteria. |
| `PROJECT_MAP.md` | CANONICAL | Systeemkaart. |
| `DOC_INDEX.md` | CANONICAL | Documentcontrole. |
| `GAP_AUDIT_360_20260511.md` | ACTIVE | Primaire risico-audit. |
| `GAP_CLOSURE_PLAN_20260511.md` | ACTIVE / NEEDS_RECONCILE | AI-delegatieplanning; volgorde/status uitlijnen op Kompas. |
| `EVIDENCE_PACK.md` | ACTIVE | Bewijslog; ondersteunend aan G7, niet leidend boven Task Register. |
| `CLOSURE_AUDIT_20260521.md` | ACTIVE | Closure truth table: reconcile van eerdere Codex/Hermes/Claude sessies naar `MITIGATED`, `OPEN`, `CLOSED` of `ACCEPTED_RISK` per taak en gate. |
| `LEGAL_DOC_LINK_AUDIT_20260521.md` | ACTIVE | T10 legal-surface audit: TOS/privacy/DPA/SLA/retention/incident vindbaarheid, canonical links en resterende legal-review gaps. |
| `LAUNCH_LEGAL_MONITORING_GATE_20260522.md` | ACTIVE | Bankrekening-scheiding plus legal/payment/monitoring dry-run bewijs voor launch gates. |
| `MONITORING_LAUNCH_SMOKE_20260522.md` | ACTIVE | T9/T12/G5 launch monitoring smoke: ES, Yente, Premium API, Ollama en source-health bewijs. |
| `PROCESS_MANAGER_PERSISTENCE_AUDIT_20260522.md` | ACTIVE | User-logon persistence bewijs voor `DueSight-LaunchStack`; reboot/no-login service proof blijft open. |
| `HOMEPAGE_BROWSER_SMOKE_20260522.md` | ACTIVE | T6/G6 browser-smoke bewijs: desktop/mobile screenshots, legal routes, checkout modal en frontend guards. |
| `D6_TAKEOVER_RUNBOOK.md` | ACTIVE | Solo-founder/takeover runbook; ondersteunt T13. |
| `CLAIMS_SUBSTANTIATION_MATRIX.md` | ACTIVE | Single source of truth voor publieke claims, bewijsstatus en toegestane claimtaal. |
| `INFRA_360_AUDIT_20260512.md` | ACTIVE | Aanvullende infrastructuur-audit: services, poorten, MCP/tooling, API-contracten, fixes en open runtimepunten. |
| `API_SOURCE_RELIABILITY_AUDIT_20260512.md` | ACTIVE | Bron/API-betrouwbaarheidsmatrix: live public checks, keyed/provider-readiness, datacontracten en open source-readiness acties. |
| `FULL_STACK_LIVE_TEST_AUDIT_20260512.md` | ACTIVE | Live evidence voor AI stacks, keyed API-bronnen, Mollie test-mode, lokale services en kritieke module/script fixes. |
| `KEYED_PROVIDER_TEST_MODE_AUDIT_20260512.md` | ACTIVE | Expliciete testmodus-validatie voor keyed providers: AI, search, sanctions/cyber/company/enrichment, GitHub en Mollie. |
| `PRODUCT_PROPOSITION_10_20260512.md` | ACTIVE | Canonieke 10/10 productpositionering: ICP, homepageboodschap, productpakking, claimdiscipline en scorecard. |
| `COMPETITIVE_INTELLIGENCE_SCOREPLEX_20260512.md` | ACTIVE | Concurrentiedossier Scoreplex: overlap, differentiatie, sample-report correctie en positioneringsguardrails. |
| `SCOREPLEX_WEBSITE_AUDIT_20260512.md` | ACTIVE | Passieve website/stack/claim-audit van Scoreplex: publieke tech-stack, productmodules, security-hygiene, funnel en DueSight-tegenzet. |
| `POSITIONING_360_STRATEGY_20260512.md` | ACTIVE / STRATEGIC | Categorie-strategie: DueSight niet als generiek AI due-diligence platform positioneren, maar als Deal Risk Intelligence / Target Integrity Memo voor outside-in target assessment. |
| `IP_EVIDENCE_POSITION_SCOREPLEX_20260520.md` | ACTIVE / STRATEGIC | Gelaagde IP- en bewijspositie voor DueSight tegenover Scoreplex: i-DEPOT, merk/submerken, bedrijfsgeheimen, copyright, database/evidence layer, patent-scan en vervolgcommand voor andere chats. |
| `DUESIGHT_IP_EVIDENCE_PACK_20260520.md` | ACTIVE / STRATEGIC | Productieklare IP Evidence Pack manifest: bewijsrug, annexlijst, BOIP/trademark/trade-secret status en handoff voor counsel. |
| `BOIP_IDEPOT_INPUT_DUESIGHT_20260520.md` | ACTIVE / LEGAL-PREP | i-DEPOT indieningstekst, annexstructuur, filing hygiene en post-filing receipt-template. |
| `TRADEMARK_CLEARANCE_CHECKLIST_DUESIGHT_20260520.md` | ACTIVE / LEGAL-PREP | Merkonderzoek checklist voor DueSight, logo/device mark en submerken zoals Target Integrity Memo en Evidence Ledger. |
| `TRADE_SECRET_REGISTER_20260520.md` | ACTIVE / INTERNAL-CONTROL | Bedrijfsgeheimenregister: protectable know-how, secrecy classification, public abstractions en reasonable-measures checklist. |
| `DUESIGHT_10_SCORECARD_20260512.md` | ACTIVE / STRATEGIC | Objectieve 10/10 meetlat voor positionering, product, website, AI-stack, benchmarks, bronnen, compliance, delivery en operations. |
| `PREMIUM_DATA_STACK_20260512.md` | ACTIVE / STRATEGIC | Budget-onbeperkte data/API/toolingstrategie: welke premium bronnen, graph tooling en productfeatures DueSight extreem sterker maken. |
| `DATA_STACK_ROI_MATRIX_20260512.md` | ACTIVE / STRATEGIC | Budget-efficiency matrix met actuele prijsankers, beste ROI-stack, koopvolgorde en dure-bronnen guardrails. |
| `TIER0_COMPETITIVE_ADVANTAGE_AUDIT_20260512.md` | ACTIVE / STRATEGIC | Tier0 audit en roadmap: canonieke deterministic finance core, false-positive budget, gap-mining, monitor/evidence requirements en benchmark-claim discipline. |
| `TIER0_FALSE_POSITIVE_SPRINT_20260512.md` | ACTIVE | Uitgevoerde Tier0 false-positive sprint: AES inventory turnover, Lockheed CAGR, regressietests, verificatie en resterende full-run acties. |
| `FINANCE_CLOUD_SUBSCRIPTION_ELITE_20260512.md` | ACTIVE | FinanceBench cloud-subscription sprint: MiniMax native highspeed dual, GLM direct, Codex GPT-5.5 CLI auth, nieuwe preset, smoke evidence en open full-run acties. |
| `FINANCEBENCH_OFFICIAL_CLAIM_AUDIT_20260514.md` | ACTIVE | Official-rule audit voor FinanceBench claims: public sample n=150 versus full 10,231 benchmark, veilige claimtaal en vervolgroute. |
| `CASEHOLD_REPRO_AND_RECORD_PLAN_20260513.md` | ACTIVE | CaseHOLD record/repro plan, claim boundaries, local verified track, Monte Carlo/Tier0/NLP wiring audit, and autonomous local improvement loop. |
| `CASEHOLD_TIER0_TRAINING_FACTORY_20260522.md` | ACTIVE | Tier0++ lokale training factory: train-only pairwise ranker, val-frozen route policy, test-only final scoring, clean/augmented/report claim boundaries en artefactcommands. |
| `CASEHOLD_TOKEN_BURN_AND_PROMPT_COMPRESSION_20260522.md` | ACTIVE | Tokenbesparing en promptcompressie voor CaseHOLD: LLMLingua status, conservative compressor, promptvariantmeting, MiniMax verifier-grens en low-burn ATH-plan. |
| `CASEHOLD_NEXT_MAX_RUN_PLAYBOOK_20260518.md` | ACTIVE | Next-run playbook voor maximale CaseHOLD score: route-inventory, neutral smokes, train/val kalibratie, frozen full-test command, freeze/verify gates en claimgrenzen. |
| `SESSION_CASEHOLD_DUAL_RECORD_20260514.md` | ACTIVE | Session index for CaseHOLD cloud/dual-lane record push and active cloud/autoloop artifacts. |
| `SESSION_CASEHOLD_LOCAL_ATH_20260514.md` | ACTIVE | Session index for this chat's local ATH push, local-only rules, MiniMax verifier role, hunter status, artifacts, and next loop. |
| `SESSION_CASEHOLD_ENGINE_OPTIMIZATION_GCA_20260518.md` | ACTIVE | CaseHOLD engine optimalisatie + GCA/Antigravity Gemini discovery: MiniMax analyse, ATH deconstructie, headless GCA OAuth fix, en Antigravity UI local bridge smoke evidence. |
| `HERMES_CLI_BRIDGE_20260518.md` | ACTIVE | Hermes CLI subscription/auth route voor DeepSeek V4 Pro/Flash: bridge, smoke evidence, CaseHOLD runner flags en benchmark-integriteitsgrens. |
| `HERMES_DIRECT_KIMI_QWEN_AUTH_20260518.md` | ACTIVE | Direct Hermes-auth plan voor Kimi/Qwen zonder OpenRouter: KIMI_API_KEY, DASHSCOPE_API_KEY en Qwen OAuth status/commands. |
| `KILO_OPENCODE_NATIVE_MODEL_ROUTES_20260518.md` | ACTIVE | Kilo/OpenCode native model-route audit: usable DeepSeek, NVIDIA Qwen/Kimi, MiniMax en OpenCode Zen Free routes zonder OpenRouter, plus benchmarkgrens. |
| `CASEHOLD_WINNING_ELITE_STACK_20260518.md` | ACTIVE | Definitieve CaseHOLD elite/fallback stack: GPT-5.5, Claude Sonnet 4.6, GLM 5.1, MiniMax, NIM, Gemini/GCA, Hermes, Kilo/OpenCode, validatie- en promotiegates. |
| `CASEHOLD_ANTIGRAVITY_VARIANT_PROBE_20260518.md` | ACTIVE | Antigravity UI Gemini variantprobe op CaseHOLD val: Pro High vs Gemini 3 Flash vs Flash Lite, met conclusie dat `MODEL_PLACEHOLDER_M133` de validatiefinalist is. |
| `CASEHOLD_FALLBACK_ROUTE_FIXES_20260518.md` | ACTIVE | Root-cause en fixes voor kunstmatig slechte Qwen/Kimi/NIM fallback-scores: strict parser, neutrale prompt, NIM retries en fixed n=30 shootout. |
| `..\duesight-website\docs\FINANCE_FORENSICS_EVIDENCE_LEDGER_20260520.md` | ACTIVE | Finance/Benford evidence-ledger contract: target-population guard, `Benford route smoke`, live smoke ids en automation-watchpoints. |
| `..\duesight-website\docs\OWNERSHIP_REGISTER_EVIDENCE_LEDGER_20260520.md` | ACTIVE | Ownership/register evidence-ledger contract: KvK/GLEIF/LEI/UBO routing, mismatch guard, live smoke ids en claimdiscipline. |
| `..\duesight-website\docs\OWNERSHIP_REGISTER_BENCHMARK_20260520.md` | ACTIVE | Deterministic ownership/register benchmark: 30 cases, no mismatch promotion, no review-candidate promotion, pytest guard. |
| `..\duesight-website\docs\KVK_OFFICIAL_READINESS_20260520.md` | ACTIVE | Official-source readiness smoke en aparte Dataservice bridge voor KvK Basisprofiel en Dataservice/Jaarrekeningen: credentials, routes, blockers en claimdiscipline. |
| `..\duesight-website\docs\KVK_NO_KEY_FALLBACK_BENCHMARK_20260520.md` | ACTIVE | No-key KvK fallback quality benchmark: 25 targets, public/GLEIF/Wikidata status, no unsafe promotion, manual review policy. |
| `..\duesight-website\docs\KVK_MANUAL_GOLDEN_CONTROL_SET_20260520.md` | ACTIVE | Manual golden controls en expliciete evidence hydration fallback zolang KVK-key ontbreekt: `MANUALLY_VERIFIED_CONTROL`, `MANUAL_CONTROL`, nooit memo-safe of official output. |
| `..\duesight-website\docs\KVK_OFFICIAL_ACCEPTANCE_GATE_20260520.md` | ACTIVE | Gate voor productiepromotie naar officiele KvK identity anchor: exacte official search + Basisprofiel, no unsafe promotions, blocked zonder key. |
| `..\duesight-website\docs\KVK_FINANCE_ACCEPTANCE_GATE_20260520.md` | ACTIVE | Gate voor productiepromotie naar officiele KvK finance filing evidence: Dataservice/Jaarrekeningen, source document hash, Benford target-population guard en blocked zonder key. |
| `..\duesight-website\docs\KVK_JAARREKENING_EXTRACTOR_20260520.md` | ACTIVE | Canonieke KVK jaarrekening-extractor: bronhash, boekjaar, deponeringsdatum, statement-scope, canonical financial fields en schone Benford-populatie. |
| `..\duesight-website\docs\DE_REGISTER_FILING_ACCEPTANCE_GATE_20260520.md` | ACTIVE | Gate, fixture-benchmark en manual attended ingest voor Duitse Unternehmensregister/Bundesanzeiger filing evidence: ToS/acquisitiepad, DiRUG routekeuze, source document hash, `OFFICIAL_DE_REGISTER_FILING_REFERENCE` normalisatie en review-only blokkade zonder accepted metadata. |
| `..\duesight-website\docs\DE_TEMPORARY_DATA_SOURCE_MATRIX_20260520.md` | ACTIVE | Tijdelijke Duitse source matrix zolang Unternehmensregister-toegang pending is: manual upload, SEC/issuer bridge, issuer IR, OpenRegister, North Data, Handelsregister.ai, Viaductus en FinancialReports.eu met review-only guardrails. |
| `..\duesight-website\docs\DE_NO_REGISTER_TEMPORARY_RESOLUTION_20260521.md` | ACTIVE | Tijdelijke oplossing zonder echt Unternehmensregister/Bundesanzeiger document: SEC/issuer hash, issuer IR, client upload, provider/open-web triangulatie en no-register ladder benchmark met harde claimgrenzen. |
| `..\duesight-website\docs\REGULATORY_ADVERSE_BENCHMARK_20260520.md` | ACTIVE | Deterministic regulatory/adverse-media benchmark: registration is not no-risk, no-hit is not clean reputation proof, warning/adverse remains review-only. |
| `..\duesight-website\docs\STACK_AUDIT_PROGRESS_20260520.md` | ACTIVE | Huidige stack-audit percentage, weging, zes-domeinen smoke, ownership benchmark, KvK official readiness, no-key KvK fallback benchmark en regulatory/adverse benchmark. |

---

## Belangrijke Ondersteunende Documenten

| Document | Status | Notitie |
|----------|--------|---------|
| `CURRENT_STATE.md` | NEEDS_RECONCILE | Oudere staat; nuttig maar niet leidend. |
| `PRELAUNCH_CHECKLIST.md` | NEEDS_RECONCILE | Checklist naast launch gates leggen. |
| `COMPLIANCE_GAP_ANALYSIS_20260510.md` | ACTIVE | Input voor legal/compliance docs. |
| `ARCHITECTURE.md` | ACTIVE / NEEDS_RECONCILE | Te controleren tegen huidige runtime. |
| `BLOCKERS.md` | NEEDS_RECONCILE | Historische blockers vergelijken met audit. |
| `DESIGN_SYSTEM.md` | ACTIVE | Design/brand basis. |
| `DESIGN_AUDIT.md` | ACTIVE | Designkeuzes en beoordeling. |
| `DES_STITCH_FULL_AUDIT.md` | ACTIVE | Design stitch audit/varianten. |
| `AUDIT_BRIEFING.md` | ACTIVE | Design/website briefing context. |
| `AUDIT_FIX_BRIEFING.md` | ACTIVE | Fix briefing context. |

---

## Archiefregels

Gebruik deze niet voor actuele besluitvorming zonder verificatie:

- `backups/**`
- `.session-logs/**`
- `designs/_full_backup_*/**`
- oude `index.html.backup-*`
- losse session transcript `.txt` bestanden
- gegenereerde JSON/data dumps zonder timestamp/evidence

---

## Reconcile Queue

Deze tegenstrijdigheden moeten worden gladgestreken:

1. `GAP_AUDIT_360_20260511.md` noemt 37 gaps / 5 critical; `GAP_CLOSURE_PLAN_20260511.md` noemt 9 critical blockers.
2. Closure-plan fase 1 begint met TOS/Mollie/delivery, terwijl Kompas security-first prioriteert.
3. Homepage claimt meerdere trust/compliance statussen die bewijsstatus nodig hebben; nu expliciet T16.
4. Design/homepage docs spreken niet altijd dezelfde homepage-kern uit; T6 bevat nu designvariant-hygiene.
5. Backend Python-bestanden worden door `*.py` genegeerd; nu expliciet T18.
6. Poort 8000/DDIntel-contract is inconsistent tussen daemon, premium API en website-DDIntel HTTP client; zie `INFRA_360_AUDIT_20260512.md`.
7. Externe bronclaims waren te optimistisch: OpenSanctions/OpenCorporates/KvK/OpenKVK vereisen key/contract of zijn onbetrouwbaar als no-key; zie `API_SOURCE_RELIABILITY_AUDIT_20260512.md`.
8. Full-stack live test toont credential/config blockers: Mistral/Anthropic 401, Google non-Gemini APIs 403, OpenRouter rate-limit/creditbeleid en Handelsregister quota; OpenSanctions trial is met 1 maand verlengd en PAYG-vragen zijn verstuurd, maar commercial closure blijft pending vendor reply; zie `FULL_STACK_LIVE_TEST_AUDIT_20260512.md` en `API_SOURCE_RELIABILITY_AUDIT_20260512.md`.
9. Expliciete keyed-provider testmodus bevestigt PASS voor 19 provider-contracten en `REPLACED_BY_CANONICAL_STACK` voor 7 vervangen providers; er zijn geen `MISSING_REQUIRED_KEY` blockers meer. OpenPageRank is toegevoegd en PASS. Serper, Tavily, Dealfront/Leadfeeder, OpenAI direct, Azure OpenAI direct, Apollo, Netrows, CriminalIP, OpenCorporates en Companies House tellen niet als harde blockers zolang de capability via de canonieke stack wordt geleverd. Voor Companies House is de keyless Data Products-route de primaire UK fallback; live API-key blijft optioneel. Resterende open punten zijn auth/quota/config of safe-test-contract issues; zie `KEYED_PROVIDER_TEST_MODE_AUDIT_20260512.md`.
10. Productpositionering moet vanaf nu aansluiten op `PRODUCT_PROPOSITION_10_20260512.md`: DueSight verkoopt pre-DD risicointelligentie voor M&A/deal-triage, niet generieke AI, engine-aantallen of onbewijsbare trustclaims.
11. Scoreplex is een relevante parallelle speler in KYB/EDD/OSINT. DueSight moet daarom niet als generiek EDD-platform worden geframed; zie `COMPETITIVE_INTELLIGENCE_SCOREPLEX_20260512.md`.
12. Scoreplex publiceert genoeg frontend/website-signalen om hun stack en productrichting te lezen: Lovable/Cloudflare marketing-site, Vercel/Supabase app, Ghost/HubSpot funnel, OpenCorporates/OpenSanctions source-story, agent-builder/workflow-configuratie en zwakkere mail/security-hygiene; zie `SCOREPLEX_WEBSITE_AUDIT_20260512.md`.
13. Positionering moet verschuiven van "AI due diligence platform" naar "Deal Risk Intelligence" / "Target Integrity Memo". AI en due diligence blijven ondersteunende termen, niet de hoofdidentiteit; zie `POSITIONING_360_STRATEGY_20260512.md`.
14. "Allemaal tienen" betekent vanaf nu: per domein meetbare acceptatiecriteria halen, niet hardere claims gebruiken. Zie `DUESIGHT_10_SCORECARD_20260512.md`.
15. Extra budget moet primair naar premium data, graph/evidence tooling en source reliability, niet naar nog meer LLM-providers. Zie `PREMIUM_DATA_STACK_20260512.md`.
16. Voor betaalde bronnen geldt de ROI-volgorde uit `DATA_STACK_ROI_MATRIX_20260512.md`: eerst CompanyLens/Dilisense/Netlas/Neo4j. Brave telt alleen als goedkope search/citation fallback binnen de bestaande deep-research stack, niet als primaire researchlaag. Orbis/Sayari/Lexis/World-Check/SecurityScorecard pas daarna.
17. Tier0 blijft de hoogste benchmark-prioriteit, maar moet worden geconsolideerd in een canonieke deterministic finance core. Geen publieke componentclaim zonder Pad B runtime ablation, 3-run protocol en false-positive evidence. Zie `TIER0_COMPETITIVE_ADVANTAGE_AUDIT_20260512.md`.
18. Eerste Tier0 false-positive sprint is uitgevoerd: AES bleek een FinanceBench-formuleconventie (ending inventory vs average inventory), Lockheed borgt tweejaars-CAGR en CAGR missing-year abstention. Zie `TIER0_FALSE_POSITIVE_SPRINT_20260512.md`. Volgende reconcile: volledige FinanceBench her-run en centrale `tier0_finance_core.py`.
19. Finance cloud subscription elite route is toegevoegd voor publieke benchmarks: `--subscription-elite` activeert MiniMax highspeed A/B, GLM direct en Codex GPT-5.5 via CLI-auth zonder normale DD-routing te wijzigen. Zie `FINANCE_CLOUD_SUBSCRIPTION_ELITE_20260512.md`. Volgende reconcile: volledige 150Q run op Python 3.13 en Python 3.11 NumPy-runtime herstellen/documenteren.

---

## Updateprocedure

Bij elke belangrijke wijziging:

1. Update `TASK_REGISTER.md`.
2. Voeg evidence toe of verwijs naar evidence.
3. Update relevante gate in `LAUNCH_GATE.md`.
4. Alleen bij koerswijziging: update `DUESIGHT_KOMPAS.md`.
