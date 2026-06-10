# DueSight Design System v3.0
## Concept: "Chrome Authority" — The Bloomberg of Dutch M&A Intelligence
> Oorsprong: Claude gesprek 22 maart 2026
> Opgeslagen: 31 maart 2026
> Status: NIET geïmplementeerd in index.html — tokens staan klaar

---

## Brand Positioning

DueSight is NOT a startup. It presents as an established institutional
intelligence provider. Think: Bloomberg Terminal meets Swiss private bank.
Target feel: McKinsey report quality + Goldman Sachs discretion + KPMG trust

---

## Color Tokens — DARK MODE (primary)

```css
:root {
  /* Backgrounds — near-black, never pure black */
  --ds-bg-primary: #06080f;
  --ds-bg-secondary: #0a0f1a;
  --ds-bg-card: rgba(14,20,35,0.85);
  --ds-bg-elevated: rgba(20,28,48,0.9);

  /* Chrome Metal Accents — the signature */
  --ds-chrome-100: #f8fafc;    /* Brightest chrome */
  --ds-chrome-200: #e2e8f0;    /* Light chrome */
  --ds-chrome-300: #cbd5e1;    /* Mid chrome */
  --ds-chrome-400: #94a3b8;    /* Dark chrome / silver */
  --ds-chrome-500: #64748b;    /* Deep chrome */
  --ds-chrome-600: #475569;    /* Very dark chrome */

  /* Primary Brand */
  --ds-accent-primary: #4f6d8f;    /* Steel blue — institutional, not flashy */
  --ds-accent-secondary: #3b82f6;  /* Vivid blue — CTAs only */
  --ds-accent-gradient: linear-gradient(135deg, #4f6d8f 0%, #3b82f6 100%);

  /* Semantic */
  --ds-success: #22c55e;    /* Verified / Clear */
  --ds-warning: #f59e0b;    /* Monitor / Amber */
  --ds-danger: #ef4444;     /* Risk / Red flag */

  /* Glass borders */
  --ds-border-glass: rgba(148,163,184,0.1);
  --ds-border-hover: rgba(148,163,184,0.2);
  --ds-border-active: rgba(59,130,246,0.3);

  /* Text */
  --ds-text-primary: #f1f5f9;
  --ds-text-secondary: rgba(241,245,249,0.7);
  --ds-text-muted: rgba(241,245,249,0.4);
  --ds-text-ghost: rgba(241,245,249,0.2);
}
```

## Color Tokens — LIGHT MODE

```css
[data-theme="light"] {
  --ds-bg-primary: #f8fafc;
  --ds-bg-secondary: #eef0f5;
  --ds-bg-card: rgba(255,255,255,0.9);
  --ds-bg-elevated: rgba(255,255,255,0.95);

  /* Chrome stays chrome */
  --ds-chrome-100: #0f172a;
  --ds-chrome-200: #1e293b;
  --ds-chrome-300: #334155;
  --ds-chrome-400: #475569;
  --ds-chrome-500: #64748b;
  --ds-chrome-600: #94a3b8;

  /* CTA: navy, not bright blue */
  --ds-accent-primary: #1e40af;
  --ds-accent-secondary: #1a3a9c;
  --ds-accent-gradient: linear-gradient(180deg, #1e40af 0%, #1a3a9c 100%);

  --ds-text-primary: #0f172a;
  --ds-text-secondary: rgba(15,23,42,0.7);
  --ds-text-muted: rgba(15,23,42,0.5);
}
```

---

## Typography

```css
/* Primary: Space Grotesk — geometric, professional, modern */
--ds-font-primary: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;

/* Display: Playfair Display — serene authority for H1 only */
--ds-font-display: 'Playfair Display', Georgia, serif;

/* Mono: JetBrains Mono — technical data, KvK numbers, hashes */
--ds-font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### Type Scale
```
Hero H1:     clamp(2.4rem, 4vw, 3.6rem)  font-weight: 800  letter-spacing: -1.5px
Section H2:  clamp(1.6rem, 3vw, 2.2rem)  font-weight: 700  letter-spacing: -0.5px
Card H3:     1.1rem                        font-weight: 600
Body:        0.875rem (14px)               font-weight: 400  line-height: 1.7
Caption:     0.75rem (12px)                font-weight: 500  letter-spacing: 0.5px
Micro:       0.625rem (10px)               font-weight: 600  letter-spacing: 1.5px  uppercase
```

---

## Spacing

```
Section padding:  80px 0 (desktop), 48px 0 (mobile)
Card padding:     24px (desktop), 16px (mobile)
Max-width:        1200px
Card border-radius: 16px
Button border-radius: 12px
Badge border-radius: 6px
```

---

## Component Patterns

### CTA Buttons
```css
/* Primary — steel gradient with gloss */
.ds-cta-btn {
  background: var(--ds-accent-gradient);
  color: #fff;
  font-weight: 700;
  font-size: 0.875rem;
  padding: 14px 32px;
  border-radius: 12px;
  border: 1px solid rgba(59,130,246,0.3);
  box-shadow: 0 2px 12px rgba(30,64,175,0.3),
              inset 0 1px 0 rgba(255,255,255,0.1);
}

/* Ghost — for secondary actions */
.ds-cta-ghost {
  background: transparent;
  border: 1px solid var(--ds-border-glass);
  color: var(--ds-chrome-300);
}
```

### Cards
```css
.ds-card {
  background: var(--ds-bg-card);
  border: 1px solid var(--ds-border-glass);
  border-radius: 16px;
  backdrop-filter: blur(12px);
  transition: border-color 0.3s, box-shadow 0.3s;
}
.ds-card:hover {
  border-color: var(--ds-border-hover);
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}
```

### Trust Badges
```css
.ds-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid rgba(59,130,246,0.12);
  background: rgba(59,130,246,0.08);
  color: var(--ds-chrome-400);
}
```

---

## Animation Rules

Institutioneel publiek tolereert geen drukke animaties.

✓ Gentle fade-ins (0.4s ease)
✓ Metric counter animations (getal oplopen, 1.8s cubic)
✓ Benford chart bars groeien op scroll
✓ Orbit animation: langzaam (45s rotatie), subtiel
✗ Geen bounce effects
✗ Geen rapid flashing
✗ Geen emoji animations in trust-context

---

## Pagina-Architectuur — Definitieve Volgorde

```
POS │ SECTIE                          │ DOEL
────┼─────────────────────────────────┼──────────────────────
 01 │ HERO + Zoekbalk                 │ Propositie + CTA
 02 │ SOCIAL PROOF (quotes/logos)     │ Direct trust na hero
 03 │ "DE UITDAGING" VIDEO            │ Probleem visualiseren
 04 │ 6-AGENT ARCHITECTUUR            │ Oplossing tonen
 05 │ AI ORBIT (multi-engine)         │ Tech-differentiator
 06 │ FORENSISCH (Benford+dashboard)  │ Methodologie bewijs
 07 │ DELTA ANALYSE                   │ Unique value prop
 08 │ SAMPLE REPORTS (2×2 grid)       │ Sociaal bewijs
 09 │ PRICING (2 cards + monitor bar) │ Conversie
 10 │ TRUST SHIELD                    │ Bezwaar wegnemen
 11 │ FAQ (max 5 vragen)              │ Laatste bezwaren
 12 │ EARLY ACCESS FORM               │ Lead capture
 13 │ FOOTER                          │ Legal + contact
```

VERWIJDER uit frontpage (→ subpagina's):
- Sector solutions / Notaris / Whitelabel → /oplossingen
- Volume packs / add-ons → checkout only
- Competitor comparison table → /vergelijken
- Before/After section (te consument-gericht)
- ROI calculator → /tarieven

---

## Wat NIET Meer Mag

1. Neon-cyaan accenten op diepzwart → vervang met --ds-chrome-400 (#94a3b8)
2. Drie verschillende CTA-kleuren (rood/geel/groen) → één kleur: --ds-accent-secondary
3. Gekleurde emoji-iconen in kaarten → monochroom SVG of Material Icons
4. Add-ons op frontpage → checkout only
5. "Instituional" typo → "Institutional"
6. Gradient knoppen met paars → steel blue gradient only

---

## Trust Badge Legal Matrix

### WEL claimen (eigen verklaringen):
- ✅ "Zero Data Retention" — eigen technische claim
- ✅ "AVG Art. 25 Privacy by Design" — eigen verklaring
- ✅ "TLS 1.3 + AES-256" — verifieerbare technische claim
- ✅ "6/11-Engine Cross-Check" — eigen productclaim
- ✅ "DPIA Uitgevoerd" — intern document vereist
- ✅ "EU AI Act Aligned" — eigen beleidskeuze

### VOORZICHTIG (herformuleren):
- ⚠️ "EU AI Act Ready" → herformuleren naar "EU AI Act Aligned"
- ⚠️ "NIS2-aligned" → OK zolang geen certificeringsclaim
- ⚠️ "SOC 2 Roadmap" → OK als roadmap, niet als claim
- ⚠️ "ISO 42001 Aligned" → "ISO 42001-conform ontworpen" (geen certificering)

### NOOIT claimen:
- ❌ ISO 27001 zonder daadwerkelijke certificering
- ❌ SOC 2 Type II zonder audit
- ❌ "Gecertificeerd" zonder erkende instantie
- ❌ Logo's van certificeringsinstanties zonder certificaat
