# DueSight Project Context — Auto-Generated

> **Generated:** 2026-03-27 17:55
> **Script:** `python generate_context.py`
> **DO NOT EDIT MANUALLY** — re-run the script after changes

## 📊 Project Summary

| Metric | Count |
|--------|-------|
| Python modules (root) | 93 |
| Python modules (tools/) | 44 |
| Total Python files | 145 |
| Total lines of code | 50,414 |
| Classes | 206 |
| Top-level functions | 377 |
| Cloud AI engines | 13 |
| Local Ollama models | 12 |
| Specialist models | 0 |
| Environment variables | 56 |
| External API endpoints | 114 |
| Pipeline phases | 13 |

## 🤖 AI Engines

### Cloud Engines (13)
| Variable | Model ID | Description |
|----------|----------|-------------|
| `GEMINI_FLASH` | `gemini-3-flash-preview` | If API key doesn't have access (403), falls back to FALLBACK_FLASH |
| `GEMINI_FLASH_LITE` | `gemini-3.1-flash-lite-preview` | Falls back to gemini-2.0-flash-lite-001 if unavailable |
| `GEMINI_ADVERSARIAL` | `gemini-2.5-pro` | Gemini 2.5 Pro — BEAR CASE / ADVERSARIAL ENGINE |
| `MISTRAL_SMALL_4` | `mistralai/mistral-small-2503` | Replaces Mistral Large 3 (cheaper AND better) |
| `GLM_5` | `z-ai/glm-5:nitro` | Humanity's Last Exam: 50.4% > Claude Opus (43.4%) > GPT-5.2 (45.5%) |
| `GLM_5_TURBO` | `z-ai/glm-5-turbo:nitro` | GLM 5.0 Turbo — Agent-optimized, Bear Case engine via OpenRouter |
| `CEREBRAS_MODEL` | `qwen-3-235b-a22b-instruct-2507` | Free tier credit ($29.81 balance). Fastest inference on Earth. |
| `CEREBRAS_GPT_OSS` | `gpt-oss-120b` | Reasoning + coding model, free tier, 65K context window |
| `MINIMAX_M27` | `MiniMax-M2.7` | $0.30/$1.20 per M = 1/20th Claude Opus cost at same quality tier |
| `MINIMAX_M27_HIGHSPEED` | `MiniMax-M2.7-highspeed` | Direct API model ID |
| `MINIMAX_API_BASE` | `https://api.minimax.io/v1` | Faster, same quality |
| `SAMBANOVA_MODEL` | `DeepSeek-R1-0528` | Requires: SAMBANOVA_API_KEY (free at cloud.sambanova.ai) |
| `OPENROUTER_MAVERICK` | `meta-llama/llama-4-maverick` | OpenRouter — Llama 4 Maverick 400B (MoE Flagship) |

### Local Ollama Models (12)
| Variable | Model ID | Context Budget |
|----------|----------|----------------|
| `MISTRAL_SMALL` | `ollama/mistral-small3.1:latest` | — |
| `OLLAMA_AGENT` | `HammerAI/hermes-4.3:latest` | — |
| `OLLAMA_OCR` | `glm-ocr:latest` | — |
| `ollama_hermes4_enterprise` | `ollama_hermes4_enterprise` | 4000 |
| `ollama_xortron` | `ollama_xortron` | 16384 |
| `ollama_glm_flash` | `ollama_glm_flash` | 8000 |
| `ollama_nemotron` | `ollama_nemotron` | 8000 |
| `ollama_qwen35_9b` | `ollama_qwen35_9b` | 8000 |
| `ollama_qwen35_27b` | `ollama_qwen35_27b` | 32768 |
| `ollama_gemma3_12b` | `ollama_gemma3_12b` | 8000 |
| `ollama_mistral_small` | `ollama_mistral_small` | 8000 |
| `ollama_glm_ocr` | `ollama_glm_ocr` | 3000 |

## ⚡ Pipeline Architecture (orchestrator.py)

```
  Phase 1: intake
  Phase 2: preflight
  Phase 3: research
  Phase 4: enrichment
  Phase 5: escalation
  Phase 6: analysis
  Phase 7: deep_research
  Phase 8: validation
  Phase 9: epistemic
  Phase 10: data_quality
  Phase 11: beast_mode_quality
  Phase 12: anti_hallucination
  Phase 13: synthesis
```

## 🧰 Tools Directory (44 modules)

| Module | Classes | Methods | Lines | Description |
|--------|---------|---------|-------|-------------|
| `adverse_media_scanner.py` | AdverseArticle, AdverseMediaResult, AdverseMediaScanner | 9 | 419 | DueSight Adverse Media Scanner — v1.0 |
| `anti_hallucination.py` | UncertaintySource, UncertaintyDecomposition, CalibrationMetrics, ConformalInterval, ReasoningTransparency, DDUncertaintyEngine, GateResult, GateCheck, DDCrossCheckReport, DDNeverAgainCrossCheck, ConvictionLevel, EpistemicAssessment, DDEpistemicRigorEngine, AntiHallucinationLayer | 35 | 1278 | DueSight — Anti-Hallucination Safety Layer v1.0 |
| `beast_mode_bridge.py` | RigorTier, EvidenceType, VerificationResult, DDVerificationGate, DDAdversarialCritic, DDConfidenceCalibrator, ResearchResult, DDDeepResearcher, DDDataHealthChecker, BeastModeBridge | 11 | 660 | DueSight — Beast Mode Bridge v1.0 |
| `companyinfo_client.py` | CompanyInfoResult, DossierV3, CompanyInfoClient | 16 | 702 | Company.info Webservices API Client |
| `competitive_intel.py` | CompetitiveIntel, CompetitiveIntelScanner | 11 | 354 | DueSight v2.0 Phase 2 - Competitive Intelligence Module |
| `csddd_compliance.py` | CSDDDAssessment, CSDDDComplianceGate | 3 | 325 | DueSight CSDDD Compliance Gate — v6.9.3 |
| `dark_data_parser.py` | DarkDataParser | 2 | 81 |  |
| `data_enrichment_layer.py` | DataEnrichmentLayer | 11 | 468 | DueSight Data Enrichment Layer — v6.9.5 |
| `data_quality_engine.py` | FailureBreakdown, DimensionScore, DataQualityEngine | 17 | 680 | DueSight Data Quality Engine |
| `digital_footprint_analyzer.py` | DigitalFootprintResult, DigitalFootprintAnalyzer | 10 | 396 | DueSight Digital Footprint Analyzer — v1.0 |
| `document_chunker.py` | ChunkResult, ChunkedDocumentResult | 2 | 329 | DueSight Document Chunker — Parallel Large Document Analysis |
| `document_destructor.py` | DestructorResult | 0 | 307 | DueSight Document Destructor — Full-Document Analysis via Mi |
| `economic_indicators.py` | MacroIndicators, SectorOutlook, EconomicIndicators | 5 | 294 | DueSight Economic Indicators Module — v6.9.3 |
| `employee_intel.py` | EmployeeIntel, EmployeeIntelScanner | 14 | 523 | DueSight v2.1 Phase 2 - Employee Intelligence Module |
| `escalation_engine.py` | EscalationTarget, EscalationBudget, EscalationEngine | 9 | 432 | DueSight Escalation Engine |
| `financial_proxies.py` | ConfidenceTier, WaterfallResult, FinancialWaterfall | 16 | 1704 | DueSight Financial Waterfall Engine |
| `finbert_analyzer.py` | SentimentResult, CompanySentiment, FinBERTAnalyzer | 3 | 324 | DueSight FinBERT Financial Sentiment Analyzer — v7.0 (ONNX G |
| `fiscal_dd.py` | TaxRisk, FiscalDDAssessment, FiscalDDEngine | 2 | 406 | DueSight Fiscal Due Diligence Module — v6.9.3 |
| `forensic_verifier.py` | RiskLevel, DirectorProfile, ForensicResult | 1 | 1112 | DueSight Forensic Verifier v1.0 |
| `gdelt_monitor.py` | NewsArticle, CompanyNewsProfile, GDELTMonitor | 3 | 253 | DueSight GDELT Real-Time News Monitor — v6.9.3 |
| `github_intel.py` | GitHubIntel, GitHubScanner | 9 | 290 | DueSight v2.0 - GitHub Intelligence Module |
| `google_places_verifier.py` | PlaceVerification, GooglePlacesVerifier | 4 | 255 | DueSight Google Places Entity Verifier — v6.9.3 |
| `inference_cache.py` | InferenceCache | 8 | 286 | DueSight Inference Cache — Zero-Dependency Response Cache |
| `insolvency_monitor.py` | InsolvencyRecord, InsolvencyCheck, InsolvencyMonitor | 4 | 215 | DueSight Insolvency Monitor — v6.9.3 |
| `job_intel_extractor.py` | JobPosting, JobIntelResult, JobIntelExtractor | 9 | 386 | DueSight Job Intel Extractor — v1.0 |
| `legal_intel.py` | LegalIntel, LegalIntelScanner | 8 | 302 | DueSight v2.0 Phase 2 - Legal Intelligence Module |
| `live_data_fetchers.py` | — | 0 | 327 | DueSight Live Data Fetchers v1.1 |
| `monte_carlo_risk.py` | RevenueSimulation, DefaultProbability, MonteCarloSimulator | 5 | 502 | DueSight Monte Carlo Risk Simulator — v6.9.3 |
| `network_graph_builder.py` | GraphNode, GraphEdge, EntityGraph, NetworkGraphBuilder | 13 | 498 | DueSight Network Graph Builder — v1.0 |
| `network_mapper.py` | NetworkMapper | 4 | 129 |  |
| `news_aggregator.py` | NewsItem, CompanyNews, NewsAggregator | 3 | 212 | DueSight News Aggregator — v6.9.3 |
| `parasite_to_factchecker_bridge.py` | ParasiteBridge | 2 | 106 | DueSight — Parasite to Fact-Checker Bridge v1.0 |
| `preflight_check.py` | HealthStatus, SourceHealth, PreflightChecker | 7 | 564 | DueSight Pre-Flight Health Checker |
| `preflight_quality_gate.py` | PreflightResult | 5 | 196 | DueSight Pre-Flight Quality Gate v1.0 |
| `product_reviews.py` | ProductReviewIntel, ProductReviewScanner | 4 | 236 | DueSight v2.0 - Product Reviews Intelligence Module |
| `quantum_security.py` | PQCAssessment, QuantumSecurityScanner | 9 | 375 | DueSight v2.0 - Quantum Security Screening Module |
| `rate_limiter.py` | ProviderLimits, UsageWindow, RateLimitTracker, track_llm_call | 11 | 558 | DueSight LLM Rate Limit Monitor & Tracker |
| `semantic_fact_checker.py` | ExtractedClaim, FactConflict, FactCheckResult, SemanticFactChecker | 2 | 537 | DueSight — Semantic Fact-Checker v1.0 |
| `sentiment_engine.py` | SentimentSignal, CompositeSentiment, DDSentimentEngine | 34 | 1933 | DueSight Unified Sentiment Engine — v3.0 (Phase 10: DD Stack |
| `serp_checker.py` | SERPResult, SERPReport, GeminiSERPChecker | 8 | 513 | DueSight SERP Checker — 4-Tier Resilient Search Cascade |
| `tool_result.py` | FailureType, ToolResult | 11 | 335 | DueSight Tool Result Classification |
| `ubo_resolver.py` | EntityType, EscalationReason, OwnershipNode, EscalationFlag, UBOResult, CorporateTreeTraversal, ByocCredentialProxy | 14 | 1007 | DueSight — Algorithmic UBO Proxy v1.0 |
| `wayback_profiler.py` | WaybackSnapshot, WaybackProfile, WaybackProfiler | 8 | 341 | DueSight Wayback Profiler — v1.0 |
| `wikidata_resolver.py` | WikidataEntity, WikidataResolver | 5 | 239 | DueSight Wikidata Entity Resolver — v6.9.3 |

## 📦 Root Modules (93)

| Module | Classes | Lines | Description |
|--------|---------|-------|-------------|
| `__init__.py` | — | 23 | DueSight Premium Agent - Agents Package |
| `adversarial_intel.py` | — | 280 | DueSight Adversarial Risk Intelligence Module v1.0 |
| `analysis_agent.py` | AnalysisAgent | 215 | DueSight Premium Agent - Analysis Agent |
| `antigravity_auth.py` | AntigravityAuth | 360 | Antigravity OAuth Token Manager — Replicates OpenCode's Google OAuth flow. |
| `api.py` | ScanRequest, ScanResponse | 306 |  |
| `autonomous_scanner.py` | ScanResult, AutonomousScanner | 300 | DueSight Autonomous Scanner — v6.9.3 |
| `base_agent.py` | AgentRole, AgentMessage, AgentContext, BaseAgent | 430 | DueSight Premium Agent - Base Agent Class |
| `batch_crosscheck.py` | — | 138 | Batch cross-check: Run all 14 pipeline reports through DeepResearchAgent v3.2. |
| `bench_deep_research.py` | — | 260 | DeepResearchAgent v6.5 BENCHMARK — full pipeline test. |
| `benchmark_accuracy.py` | — | 432 | DueSight Accuracy Benchmark v1.0 |
| `blind_holdout_benchmark.py` | — | 530 | DueSight Blind Holdout Benchmark (BHB) v1.0 |
| `calibrate_confidence.py` | — | 442 | DueSight Confidence Calibration Pipeline v1.0 |
| `config.py` | VertexConfig, ModelConfig, AgentConfig, DDIntelConfig, SupabaseConfig | 304 | DueSight Premium Agent - Configuration |
| `dealroom_client.py` | DealroomCompany, DealroomClient | 354 | DueSight Dealroom Client — v1.0 |
| `debug_serper.py` | — | 3 |  |
| `debug_stress_test.py` | — | 38 |  |
| `deep_research_agent.py` | SubQuery, ConflictEscalation, SourceVerification, DeepResearchResult, DeepResearchAgent | 1296 | DeepResearchAgent — v5.5 Unified Deep Research Agent |
| `deliver_report.py` | — | 324 | DueSight Concierge MVP — 1-Click Rapport Delivery |
| `diag_sources.py` | — | 89 | Verbose per-source diagnostic with FULL error details. |
| `duesight_daemon.py` | — | 421 | DueSight Autonomous Daemon — v2.0 |
| `enrich_reports.py` | — | 348 | DueSight Report Enrichment Engine — v2.0 |
| `epistemic_agent.py` | EpistemicAgent | 315 | DueSight v2.2 - Epistemic Agent |
| `extract_revenue.py` | — | 66 | Extract actual revenue from DD reports for all 14 companies. |
| `generate_context.py` | ModuleInfo | 548 | DueSight Project Context Generator v1.0 |
| `geo_content_engine.py` | ContentOutput, GEOContentEngine | 303 | DueSight — GEO/SEO Content Engine powered by MiniMax M2.7 (Layer 7) |
| `geo_sprint_nitro.py` | — | 160 | GEO Sprint Nitro Runner (v6.5) |
| `harvest_companies.py` | CompanyHarvester | 443 | DueSight Mass Company Harvester — Company.info Edition |
| `health_monitor.py` | — | 319 | DueSight Health Monitor — v2.0 |
| `inspect_reports.py` | — | 41 |  |
| `kvk_groei_calculator.py` | JaarrekeningGroei, KvkGroeiCalculator | 314 | DueSight KVK Groei Calculator — v1.0 |
| `list_models.py` | — | 26 | List Cerebras available models + Ollama local models. |
| `list_openrouter_models.py` | — | 25 | List available free DeepSeek + other interesting models on OpenRouter. |
| `live_deep_research.py` | — | 139 | DueSight LIVE DEEP RESEARCH — LED Impact B.V. |
| `main.py` | — | 209 | DueSight Premium Agent - Main Entry Point |
| `minimax_agent.py` | MinimaxToolAgent | 372 | DueSight — MiniMax M2.7 Agentic Tool-Caller (Layer 3) |
| `mkb_enrichment.py` | EnrichmentResult | 451 | DueSight — MKB Contact Enrichment v4: Hybrid Deterministic + LLM Stack |
| `multi_model_thinker.py` | ThinkResult, ConsensusResult, MultiModelThinker | 2650 | DueSight — Multi-Model Deep Think Engine v6.0 |
| `northdata_client.py` | NorthDataCompany, NorthDataClient | 369 | DueSight NorthData Client — v1.0 |
| `ollama_brain.py` | OllamaBrain | 834 | DueSight Ollama Brain v2.1 |
| `openclaw_launcher.py` | — | 253 | DueSight OpenClaw Agent Launcher |
| `openrouter_scout.py` | FreeModel | 370 | OpenRouter Free Model Scout — Auto-Discovery Engine |
| `orchestrator.py` | OrchestratorAgent | 789 | DueSight Premium Agent - Orchestrator v2.3 |
| `ovio_enricher.py` | KvkEnrichment | 629 | DueSight — KVK Enricher v3.0  (100% gratis, geen overheid.io) |
| `parse_enrichment.py` | — | 69 | Parse all 14 enrichment results and create summary. |
| `pipeline_full.py` | — | 540 | DueSight MAXIMALE PIPELINE — ledimpact.nl |
| `project_scanner.py` | — | 618 | DueSight Project Scanner v1.0 — Complete Ecosystem Map |
| `refresh_demos.py` | — | 99 | refresh_demos.py — DueSight Premium Asset Refresh Utility |
| `render_report.py` | — | 1395 | DueSight Report Renderer — JSON → HTML Injection |
| `research_agent.py` | ResearchAgent | 805 | DueSight Premium Agent - Research Agent v2.1 |
| `run_kaspr_batch.py` | — | 78 | Run Kaspr people enrichment on all 14 benchmark companies. |
| `shadow_crawler.py` | — | 201 |  |
| `signal_monitor.py` | Signal, SignalMonitor | 288 | DueSight Signal Monitor — v6.9.3 |
| `stealthrank_injector.py` | — | 144 | DueSight StealthRank & CORE Adversarial Injector (Phase 16) |
| `supabase_client.py` | SupabaseClient | 348 | DueSight Supabase Client |
| `target_prioritizer.py` | ScoredTarget, TargetPrioritizer | 397 | DueSight Target Prioritizer — v1.0 |
| `test_adversarial_stress.py` | — | 79 | Stress test: High-risk synthetic entity through adversarial layer. |
| `test_anti_hallucination.py` | — | 82 | Quick test of the Anti-Hallucination Safety Layer. |
| `test_azure_engine.py` | — | 55 | Quick test for Azure OpenAI o4-mini engine integration. |
| `test_azure_live.py` | — | 55 | Test BOTH Azure resources to find where the models live. |
| `test_contact_discovery.py` | — | 130 | Test v2: Contact Discovery — volledige raw output per engine. |
| `test_copilot_api.py` | — | 47 | Final test: copilot-api Copilot class. |
| `test_dealfront_discovery.py` | — | 61 | Leadfeeder LIVE test — get actual lead data for GetThere. |
| `test_dealfront_live.py` | — | 258 | Live data test: GetThere.nl via httpx (bypasses aiohttp DNS issue). |
| `test_dealfront_tier6.py` | — | 91 | Quick test: Financial Waterfall with Dealfront Tier 6 for GetThere.nl |
| `test_deep_research.py` | — | 89 | Test run: DeepResearchAgent on Mollie (small, fast target). |
| `test_engines.py` | — | 57 | Simple engine test - Which models actually work? |
| `test_entity_disambiguation.py` | MockContext | 277 | Test Entity Disambiguation — v6.9.3 |
| `test_escalation.py` | TestFailureType, TestToolResult, TestEscalationBudget, TestEscalationCascades, TestEscalationEngine, TestFailureBreakdown, TestDataQualityWithClassification | 294 | Tests for Failure Classification & Escalation Engine. |
| `test_fact_checker.py` | — | 181 | Test Semantic Fact-Checker + Multi-Model Thinker v3.0. |
| `test_getthere_crosscheck.py` | — | 136 | Direct test: multi_model_thinker.think_all() with GetThere DD context. |
| `test_google_linkedin.py` | — | 33 | Test Google search for LinkedIn URLs directly. |
| `test_kaspr_direct.py` | — | 57 | Read Kaspr API response for Mollie CEO. |
| `test_kaspr_google.py` | — | 34 | Test Google search LinkedIn discovery + Kaspr enrichment. |
| `test_live_preflight.py` | — | 48 | Live test: simulate MCP health data from DDIntel check_api_health. |
| `test_max_depth.py` | MaxDepthResearchAgent | 133 | Max Depth Benchmark - DeepResearchAgent met maximale diepgang |
| `test_max_depth_crosscheck.py` | MaxDepthDeepResearchAgent | 183 | Max Depth Batch Cross-Check - DueSight Deep Research Agent |
| `test_mkb_linkedin.py` | — | 225 | Live MKB LinkedIn Discovery Test |
| `test_ollama_quick.py` | — | 22 | Quick test: Ollama engine only. |
| `test_preflight.py` | TestPreflightChecker, TestDataQualityEngine | 195 | Tests for DueSight Pre-Flight Check & Data Quality Engine. |
| `test_sambanova_quick.py` | — | 22 | Quick test: SambaNova DeepSeek R1 engine. |
| `test_sanity_checks.py` | — | 216 | Quick integration test for new sanity checks: |
| `test_search_cascade.py` | — | 33 | Quick test of the 5-tier search cascade. |
| `test_searxng_quick.py` | — | 8 |  |
| `test_setup.py` | — | 71 | Quick test of DueSight Premium Agent |
| `test_stack_health.py` | — | 328 | DueSight Stack Health Check — Full 6-Layer Diagnostic. |
| `test_v22.py` | — | 325 | DueSight v2.2 — Integration Test & Benchmark |
| `test_wow_topics.py` | — | 366 | Test: WOW-Factor DD Topics v6.5 |
| `test_xortron.py` | — | 94 | Xortron Live Test — ledimpact.nl (output to JSON file) |
| `tracing_config.py` | — | 30 |  |
| `validate_sentiment.py` | — | 270 | DueSight Sentiment Engine v3.0 — Comprehensive Validation |
| `validation_agent.py` | BullAgent, BearAgent, JudgeAgent, ValidationAgent | 470 | DueSight Premium Agent - Validation Agent |
| `vault_mcp_server.py` | — | 658 | DueSight Vault MCP Server v2.0 — Project Context Intelligence |
| `zefix_client.py` | ZefixCompany, ZefixClient | 318 | DueSight Zefix Client — v1.0 |

## 🔑 Environment Variables (56)

| Variable | Used in |
|----------|---------|
| `AGENT_ENGINE_ID` | config |
| `ALPHA_VANTAGE_API_KEY` | economic_indicators |
| `ANTHROPIC_API_KEY` | base_agent, config, mkb_enrichment, multi_model_thinker, test_stack_health |
| `APOLLO_API_KEY` | api, deliver_report, financial_proxies, test_dealfront_live, test_dealfront_tier6 |
| `APPDATA` | antigravity_auth |
| `ATTIO_API_KEY` | deliver_report |
| `AZURE_OPENAI_API_KEY` | config, test_azure_engine |
| `AZURE_OPENAI_ENDPOINT` | config, test_azure_engine |
| `BRAVE_API_KEY` | forensic_verifier, multi_model_thinker |
| `CEREBRAS_API_KEY` | config, list_models, multi_model_thinker, sentiment_engine, test_stack_health |
| `COMPANYINFO_PASS` | companyinfo_client, financial_proxies |
| `COMPANYINFO_USER` | companyinfo_client, financial_proxies |
| `DDINTEL_SERVER_PATH` | config |
| `DEALFRONT_API_KEY` | financial_proxies, research_agent, test_dealfront_discovery, test_dealfront_live, test_dealfront_tier6, test_stack_health |
| `DEEPSEEK_API_KEY` | multi_model_thinker |
| `DUESIGHT_ALERT_WEBHOOK` | health_monitor |
| `DUESIGHT_BLIND_TEST` | research_agent |
| `DUESIGHT_BLOCKED_DOMAINS` | multi_model_thinker |
| `DUESIGHT_PLAYWRIGHT_ESCALATION` | research_agent |
| `FIRECRAWL_API_KEY` | beast_mode_bridge, financial_proxies |
| `GITHUB_MODELS_TOKEN` | multi_model_thinker |
| `GITHUB_TOKEN` | config |
| `GNEWS_API_KEY` | news_aggregator |
| `GOOGLE_API_KEY` | base_agent, config, employee_intel, financial_proxies, forensic_verifier, health_monitor, mkb_enrichment, multi_model_thinker, preflight_check, sentiment_engine, serp_checker, test_stack_health |
| `GOOGLE_API_KEYS` | health_monitor, multi_model_thinker |
| `GOOGLE_CSE_ID` | config, serp_checker |
| `GOOGLE_MAPS_API_KEY` | google_places_verifier |
| `GROQ_API_KEY` | multi_model_thinker, ollama_brain, sentiment_engine, test_stack_health |
| `KASPR_API_KEY` | run_kaspr_batch, test_kaspr_direct |
| `KVK_API_KEY` | ovio_enricher |
| `MINIMAX_API_BASE` | base_agent, document_destructor, multi_model_thinker, pipeline_full, source_verifier |
| `MINIMAX_API_KEY` | base_agent, document_destructor, geo_content_engine, health_monitor, minimax_agent, multi_model_thinker, pipeline_full, source_verifier |
| `MISTRAL_API_KEY` | multi_model_thinker, sentiment_engine |
| `NVIDIA_NIM_API_KEY` | config, multi_model_thinker |
| `OLLAMA_BASE_URL` | base_agent |
| `OLLAMA_CODING_URL` | multi_model_thinker |
| `OLLAMA_HOST` | enrich_reports, multi_model_thinker, ollama_brain, sentiment_engine |
| `OLLAMA_REASONING_PORT` | multi_model_thinker |
| `OLLAMA_REASONING_URL` | multi_model_thinker |
| `OLLAMA_URL` | shadow_crawler |
| `OLLAMA_UTIL_PORT` | multi_model_thinker |
| `OPENCLAW_PROXY` | shadow_crawler |
| `OPENROUTER_API_KEY` | config, document_destructor, list_openrouter_models, multi_model_thinker, ollama_brain |
| `OPENSANCTIONS_API_KEY` | live_data_fetchers |
| `RATE_LIMIT_LOG` | rate_limiter |
| `SAMBANOVA_API_KEY` | multi_model_thinker, sentiment_engine |
| `SEARXNG_URL` | forensic_verifier, multi_model_thinker, sentiment_engine, serp_checker |
| `SERPER_API_KEY` | health_monitor, live_deep_research, test_dealfront_live, test_dealfront_tier6, test_mkb_linkedin, test_stack_health |
| `SUPABASE_ANON_KEY` | config, supabase_client |
| `SUPABASE_SERVICE_KEY` | config, supabase_client |
| `SUPABASE_URL` | config, supabase_client |
| `USE_STEALTH_PROXY` | shadow_crawler |
| `VERTEX_LOCATION` | config |
| `VERTEX_PROJECT_ID` | config |
| `YENTE_URL` | live_data_fetchers |
| `ZHIPUAI_API_KEY` | multi_model_thinker, sentiment_engine |

## 🌐 External API Endpoints (114)

- `http://web.archive.org/cdx/search/cdx`
- `http://www.w3.org/2005/Atom`
- `https://api.anthropic.com/v1/messages`
- `https://api.apollo.io/api/v1/organizations/search`
- `https://api.apollo.io/v1`
- `https://api.apollo.io/v1/contacts`
- `https://api.apollo.io/v1/organizations/enrich`
- `https://api.cerebras.ai/v1/chat/completions`
- `https://api.cerebras.ai/v1/models`
- `https://api.crunchbase.com/odm/v4/entities/organizations`
- `https://api.dealfront.com/target/3.0/company/search`
- `https://api.dealfront.com/v1`
- `https://api.dealfront.com/v1/companies/search`
- `https://api.deepseek.com/v1/chat/completions`
- `https://api.developers.kaspr.io/profile/linkedin`
- `https://api.firecrawl.dev/v1/search`
- `https://api.gdeltproject.org/api/v2/doc/doc`
- `https://api.gdeltproject.org/api/v2/geo/geo`
- `https://api.gdeltproject.org/api/v2/summary/summary`
- `https://api.github.com`
- `https://api.gleif.org/api/v1`
- `https://api.gleif.org/api/v1/lei-records`
- `https://api.groq.com/openai/v1/chat/completions`
- `https://api.kvk.nl/api/v1`
- `https://api.kvk.nl/api/v2`
- `https://api.leadfeeder.com/accounts`
- `https://api.leadfeeder.com/v1`
- `https://api.leadfeeder.com/v1/accounts`
- `https://api.minimax.io/v1`
- `https://api.mistral.ai/v1/chat/completions`
- `https://api.opencorporates.com/v0.4`
- `https://api.opencorporates.com/v0.4/officers/search`
- `https://api.openkvk.nl/v1`
- `https://api.opensanctions.org/`
- `https://api.opensanctions.org/match/sanctions`
- `https://api.opensanctions.org/search/default`
- `https://api.overheid.io/openkvk/GetThere`
- `https://api.pullpush.io/`
- `https://api.sambanova.ai/v1/chat/completions`
- `https://api.search.brave.com/res/v1/web/search`
- `https://app.dealroom.co/api/companies`
- `https://app.dealroom.co/api/public/companies/search`
- `https://app.dealroom.co/api/suggestions`
- `https://archive.org/`
- `https://arianvanlaer-duesight-resource.services.ai.azure.com`
- `https://autopush-cloudcode-pa.sandbox.googleapis.com`
- `https://cloudcode-pa.googleapis.com`
- `https://cloudflare-dns.com/dns-query`
- `https://daily-cloudcode-pa.sandbox.googleapis.com`
- `https://darmarit.org/searx/search`
- `https://data-api.ecb.europa.eu/service/data`
- `https://data.rechtspraak.nl/`
- `https://data.rechtspraak.nl/uitspraken`
- `https://data.rechtspraak.nl/uitspraken/zoeken`
- `https://de.indeed.com/jobs`
- `https://duesight-openai.openai.azure.com`
- `https://feeds.nos.nl/nosnieuwseconomie`
- `https://generativelanguage.googleapis.com/v1beta/`
- `https://gnews.io/api/v4/search`
- `https://graydon.nl/`
- `https://haveibeenpwned.com/api/v2/breaches`
- `https://haveibeenpwned.com/api/v3/breacheddomain`
- `https://html.duckduckgo.com/html/`
- `https://insolventies.rechtspraak.nl/Services/SearchService/Search`
- `https://insolventies.rechtspraak.nl/Services/SyndicationService/GetFeed`
- `https://integrate.api.nvidia.com/v1/chat/completions`
- `https://internetdb.shodan.io/8.8.8.8`
- `https://models.inference.ai.azure.com/chat/completions`
- `https://mollie.com/checkout/test-link-pre-2999`
- `https://mollie.com/checkout/test-link-qs-299`
- `https://mollie.com/checkout/test-link-std-599`
- `https://news.google.com/rss/search`
- `https://nl.indeed.com/jobs`
- `https://oauth2.googleapis.com/token`
- `https://offshoreleaks.icij.org/api/search`
- `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- `https://opendata.cbs.nl/`
- `https://opendata.cbs.nl/ODataApi/odata`
- `https://opendata.cbs.nl/ODataApi/odata/80472NED`
- `https://opendata.cbs.nl/ODataApi/odata/81156ned/TypedDataSet`
- `https://opendata.cbs.nl/ODataApi/odata/83693NED/TypedDataSet`
- `https://opendata.kvk.nl/api/v1/hvds`
- `https://opendata.kvk.nl/api/v1/hvds/basisbedrijfsgegevens`
- `https://openkvk.nl/`
- `https://openrouter.ai/api/v1/chat/completions`
- `https://openrouter.ai/api/v1/models`
- `https://paulgo.io/search`
- `https://places.googleapis.com/v1/places`
- `https://query.wikidata.org/sparql`
- `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs`
- `https://searx.tiekoetter.com`
- `https://siliconcanals.com/feed/`
- `https://test.openai.azure.com`
- `https://uitspraken.rechtspraak.nl/api/search`
- `https://urlscan.io/api/v1/search/`
- `https://web.archive.org/web`
- `https://ws1.webservices.nl/rpc/get-simplexml/utf-8`
- `https://ws2.webservices.nl/rpc/get-simplexml/utf-8`
- `https://www.altares.nl/`
- `https://www.bing.com/search`
- `https://www.bnr.nl/rss`
- `https://www.drimble.nl`
- `https://www.drimble.nl/bedrijf/`
- `https://www.google.com/search`
- `https://www.googleapis.com/customsearch/v1`
- `https://www.indeed.com/rss`
- `https://www.linkedin.com/in/koenkoppen`
- `https://www.linkedin.com/jobs/search/`
- `https://www.mojeek.com/search`
- `https://www.northdata.de/_api/company/search`
- `https://www.nu.nl/rss/Economie`
- `https://www.sprout.nl/rss.xml`
- `https://www.zefix.ch/ZefixREST/api/v1`
- `https://zoek.officielebekendmakingen.nl`

## ✅ Website Claims vs. Actual

| Claim | Website Says | Actual Count | Status |
|-------|-------------|--------------|--------|
| Data sources | 64+ | 158 (APIs + tools) | ✅ |
| AI engines | 9 | 25 (cloud + local + specialist) | ✅ |

## 📡 Signal Types Detected (6)

- `DISTRESS`
- `DISTRESS_SENTIMENT`
- `FAILLISSEMENT`
- `GROWTH`
- `INSOLVENCY`
- `MANUAL`

---
*Auto-generated by `generate_context.py` — 2026-03-27 17:55*
*To update: `python generate_context.py`*