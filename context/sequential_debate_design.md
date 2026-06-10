# Sequential Debate Topology — Design Document
## DueSight Multi-Model Thinker Migration

**Status:** DESIGN READY — Implementation pending  
**Impact:** Error amplification 17x → 4.4x  
**Risk:** LOW (feature-flagged, backward compatible)

---

## Huidige Architectuur (Parallel → Consensus)

```
           ┌─── Engine 1 (Bull) ───┐
Input ─────┼─── Engine 2 (Bear) ───┼──→ Consensus Vote → Output
           ├─── Engine 3 (Synth) ──┤
           └─── Engine 4 (Reg.) ───┘
```

**Probleem:** Alle engines zien dezelfde input onafhankelijk.  
Als de input misleidend is, maken ALLE engines dezelfde fout.  
**Error amplificatie: 17x** (documentatie: CLAUDE.md regel 144).

---

## Nieuwe Architectuur (Sequential Debate)

```
Input → Engine 1 (Analyst) → Rapport A
                              ↓
        Engine 2 (Critic)  → Tegenargumenten B  
                              ↓
        Engine 3 (Judge)   → Synthese + Verdict
```

### Werking:
1. **Engine 1 (Gemini Flash):** Eerste analyse — financieel, juridisch, compliance
2. **Engine 2 (Claude Sonnet):** Leest Rapport A, zoekt zwakheden, tegenbewijs
3. **Engine 3 (Cerebras GLM):** Leest A + B, beoordeelt bewijskracht, schrijft verdict

### Waarom dit beter is:
- Engine 2 ziet de **output** van Engine 1, niet de ruwe input
- Fouten in Engine 1 worden **expliciet betwist** door Engine 2
- Engine 3 heeft **beide perspectieven** voor de finale beoordeling
- **Verwachte error amplificatie: 4.4x** (gebaseerd op academic debate topology research)

---

## Implementatieplan

### Feature Flag
```python
# multi_model_thinker.py
DEBATE_MODE = os.environ.get("DEBATE_MODE", "parallel")  # "parallel" | "sequential"
```

### Migration Path
1. **Fase 1:** Feature flag toevoegen, default = "parallel" (backward compatible)
2. **Fase 2:** `sequential_debate()` method implementeren naast bestaande `parallel_consensus()`
3. **Fase 3:** A/B testen op 5 batch-rapporten (parallel vs sequential, vergelijk scores)
4. **Fase 4:** Default switchen naar "sequential" als scores beter zijn

### Engine Assignment (Sequential)
| Rol | Engine | Reasoning |
|-----|--------|-----------|
| Analyst | Gemini 2.5 Flash | Snel, breed, goed in eerste analyse |
| Critic | Claude Sonnet 4.6 | Sterkste in nuance en tegenargumentatie |
| Judge | Cerebras GLM 5.0 | Snel, goed in synthese, laag bias |

### Geschatte Impact op Latentie
- **Parallel:** ~12s (alle engines tegelijk)
- **Sequential:** ~25s (3 engines achtereenvolgens)
- **Trade-off:** 13s extra voor 4x betere nauwkeurigheid → **ACCEPTABEL** voor DD-rapporten

---

## Verificatie
- [ ] Run 5 identieke scans in beide modes
- [ ] Vergelijk DueSight Confidence Scores
- [ ] Vergelijk met handmatige review (ground truth)
- [ ] Meet latentie verschil
