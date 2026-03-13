/**
 * DueSight Premium Enterprise 3D Flipbook
 * StPageFlip with enterprise-grade polish
 * 13 pages: Cover + 11 content + Back Cover (odd count for showCover)
 */
(function () {
    'use strict';

    var mount = document.getElementById('flipbook-mount');
    if (!mount) return;

    // ─── PAGE CONTENT ───────────────────────────────────────
    var PAGES = [
        // ═══ PAGE 0: FRONT COVER ═══
        '<div class="fp fp-cover">' +
        '<div class="fp-cover-ribbon">★ GOLD TIER</div>' +
        '<div class="fp-cover-inner">' +
        '<div class="fp-cover-logo">' +
        '<svg viewBox="0 0 40 40" width="56" height="56"><circle cx="20" cy="20" r="19" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2.5"/>' +
        '<path d="M12 20l5 5 11-11" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        '<span class="fp-cover-brand" style="background:none;-webkit-text-fill-color:rgba(255,255,255,0.6);color:rgba(255,255,255,0.6)">DueSight</span>' +
        '</div>' +
        '<div class="fp-cover-divider"></div>' +
        '<div class="fp-cover-target">' +
        '<div class="fp-cover-label">TARGET COMPANY</div>' +
        '<div class="fp-cover-company-logo"><img src="https://www.google.com/s2/favicons?domain=mollie.com&sz=128" alt="Mollie" onerror="this.onerror=null;this.src=\'https://img.logo.dev/mollie.com?token=pk_anonymous&size=80&format=png\'" style="height:56px;width:56px;border-radius:10px;border:1px solid rgba(255,255,255,0.15);padding:6px;background:rgba(255,255,255,0.06);margin-bottom:8px;object-fit:contain;filter:grayscale(100%) brightness(1.5);opacity:0.7"></div>' +
        '<h1 class="fp-cover-company">Mollie B.V.</h1>' +
        '<div class="fp-cover-type">Pre-Due Diligence Intelligence Report</div>' +
        '</div>' +
        '<div class="fp-cover-verdict">' +
        '<div class="fp-verdict-icon">✔</div>' +
        '<div class="fp-verdict-text">' +
        '<div class="fp-verdict-label">AI VERDICT</div>' +
        '<div class="fp-verdict-value">INVEST</div>' +
        '</div>' +
        '<div class="fp-verdict-score">' +
        '<svg viewBox="0 0 80 80" class="fp-verdict-ring"><circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="5"/>' +
        '<circle cx="40" cy="40" r="34" fill="none" stroke="url(#fpScoreGrad)" stroke-width="5" stroke-dasharray="167" stroke-dashoffset="37" stroke-linecap="round" transform="rotate(-90 40 40)"/>' +
        '<defs><linearGradient id="fpScoreGrad"><stop offset="0%" stop-color="#22d3ee"/><stop offset="100%" stop-color="#00ff88"/></linearGradient></defs>' +
        '<text x="40" y="38" text-anchor="middle" fill="white" font-size="16" font-weight="800">78%</text>' +
        '<text x="40" y="50" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="7" font-weight="600">CONFIDENCE</text></svg>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '</div>',

        // ═══ PAGE 1: EXECUTIVE SUMMARY ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">📋</span> Executive Summary</h2>' +
        '<div class="fp-verdict-bar"><span class="fp-vb-dot"></span> VERDICT: <strong>INVEST</strong> — 5-Engine Unanimous Consensus</div>' +
        '<p class="fp-text">Mollie B.V. presents a <strong>strong investment profile</strong> with robust financial indicators, clean compliance across all jurisdictions, and dominant market positioning in the European payment services space.</p>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">78%</div><div class="fp-kpi-lbl">Confidence Score</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">A+</div><div class="fp-kpi-lbl">Compliance Grade</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">12</div><div class="fp-kpi-lbl">Modules Analysed</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#f59e0b">★ 4.2</div><div class="fp-kpi-lbl">Trustpilot Rating</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">AI Cross-Validation</h3>' +
        '<div class="fp-engines">' +
        '<div class="fp-engine"><div class="fp-eng-name">GPT-4o</div><div class="fp-eng-score">INVEST · 81%</div></div>' +
        '<div class="fp-engine"><div class="fp-eng-name">Claude Opus</div><div class="fp-eng-score">INVEST · 84%</div></div>' +
        '<div class="fp-engine"><div class="fp-eng-name">Gemini Pro</div><div class="fp-eng-score">INVEST · 76%</div></div>' +
        '<div class="fp-engine"><div class="fp-eng-name">DeepSeek R1</div><div class="fp-eng-score">INVEST · 79%</div></div>' +
        '<div class="fp-engine"><div class="fp-eng-name">Llama 3.1</div><div class="fp-eng-score">INVEST · 73%</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">Key Strengths</h3>' +
        '<ul class="fp-list">' +
        '<li>€800M+ estimated revenue · 2,500+ FTE workforce</li>' +
        '<li>Processing €50B+ annually across the European Union</li>' +
        '<li>Zero sanctions matches across OFAC, EU, UN, UK HMT</li>' +
        '</ul>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 1 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 2: FINANCIAL PROXY ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">💰</span> Financial Proxy Analysis</h2>' +
        '<p class="fp-text-sm">Multi-source financial estimation using the DueSight Financial Waterfall methodology across 6 independent tiers.</p>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Metric</th><th>Value</th><th>Source</th><th>Confidence</th></tr></thead>' +
        '<tbody>' +
        '<tr><td>Revenue (est.)</td><td class="fp-val-cyan">€800M+</td><td>Tier-2 Proxy</td><td><span class="fp-pill ok">HIGH</span></td></tr>' +
        '<tr><td>FTE Count</td><td class="fp-val-purple">2,500+</td><td>Apollo.io</td><td><span class="fp-pill ok">HIGH</span></td></tr>' +
        '<tr><td>Revenue / FTE</td><td class="fp-val-white">€320K</td><td>CBS StatLine</td><td><span class="fp-pill ok">HIGH</span></td></tr>' +
        '<tr><td>Total Funding</td><td class="fp-val-cyan">€800M</td><td>Crunchbase</td><td><span class="fp-pill ok">VERIFIED</span></td></tr>' +
        '<tr><td>Funding Stage</td><td class="fp-val-purple">Series C+</td><td>Apollo.io</td><td><span class="fp-pill ok">HIGH</span></td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">Revenue Composition</h3>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">€50B+</div><div class="fp-kpi-lbl">Payment Volume</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">1.6%</div><div class="fp-kpi-lbl">Avg. Take Rate</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">25+</div><div class="fp-kpi-lbl">Countries Active</div></div>' +
        '</div>' +
        '<div class="fp-callout ok">✓ Revenue figures cross-validated via KvK XBRL, CBS sector proxy, and Apollo enrichment — all 3 sources converge within ±15% range.</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 2 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 3: BENFORD'S LAW FORENSIC ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">📊</span> Benford\'s Law Forensic Analysis</h2>' +
        '<p class="fp-text">First-digit distribution analysis of 847 financial data points tested against Benford\'s theoretical distribution for anomaly detection.</p>' +
        '<div class="fp-benford-row">' +
        '<div class="fp-benford-card ok"><div class="fp-bf-icon">✓</div><div class="fp-bf-label">VERDICT</div><div class="fp-bf-value">Conforming</div></div>' +
        '<div class="fp-benford-card"><div class="fp-bf-icon">χ²</div><div class="fp-bf-label">CHI-SQUARED</div><div class="fp-bf-value">4.2</div></div>' +
        '<div class="fp-benford-card"><div class="fp-bf-icon">Δ</div><div class="fp-bf-label">MAD SCORE</div><div class="fp-bf-value">0.008</div></div>' +
        '<div class="fp-benford-card"><div class="fp-bf-icon">n</div><div class="fp-bf-label">SAMPLE SIZE</div><div class="fp-bf-value">847</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">First-Digit Distribution</h3>' +
        '<div class="fp-benford-bar">' +
        '<div class="fp-bar-segment" style="width:30.1%;background:rgba(34,211,238,0.4)"><span>1</span></div>' +
        '<div class="fp-bar-segment" style="width:17.6%;background:rgba(129,140,248,0.4)"><span>2</span></div>' +
        '<div class="fp-bar-segment" style="width:12.5%;background:rgba(165,180,252,0.35)"><span>3</span></div>' +
        '<div class="fp-bar-segment" style="width:9.7%;background:rgba(99,102,241,0.3)"><span>4</span></div>' +
        '<div class="fp-bar-segment" style="width:7.9%;background:rgba(34,211,238,0.25)"><span>5</span></div>' +
        '<div class="fp-bar-segment" style="width:6.7%;background:rgba(129,140,248,0.2)"><span>6</span></div>' +
        '<div class="fp-bar-segment" style="width:5.8%;background:rgba(165,180,252,0.18)"><span>7</span></div>' +
        '<div class="fp-bar-segment" style="width:5.1%;background:rgba(99,102,241,0.15)"><span>8</span></div>' +
        '<div class="fp-bar-segment" style="width:4.6%;background:rgba(34,211,238,0.12)"><span>9</span></div>' +
        '</div>' +
        '<p class="fp-text-sm" style="margin-top:12px">No anomalies detected — financial data passes forensic first-digit tests with close conformity. MAD score 0.008 is well below the 0.015 threshold for concern.</p>' +
        '<div class="fp-callout ok">✓ All financial datasets tested conform to Benford\'s Law — no indications of data fabrication or manipulation detected.</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 3 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 4: COMPLIANCE & SANCTIONS ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">🛡️</span> Compliance & Sanctions</h2>' +
        '<div class="fp-verdict-bar ok"><span class="fp-vb-dot ok"></span> ALL CLEAR — Zero Matches Across 5 Databases</div>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Database</th><th>Jurisdiction</th><th>Status</th><th>Matches</th></tr></thead>' +
        '<tbody>' +
        '<tr><td>OFAC SDN</td><td>United States</td><td><span class="fp-pill ok">CLEAR</span></td><td>0</td></tr>' +
        '<tr><td>EU Financial Sanctions</td><td>European Union</td><td><span class="fp-pill ok">CLEAR</span></td><td>0</td></tr>' +
        '<tr><td>UN Security Council</td><td>International</td><td><span class="fp-pill ok">CLEAR</span></td><td>0</td></tr>' +
        '<tr><td>UK HMT</td><td>United Kingdom</td><td><span class="fp-pill ok">CLEAR</span></td><td>0</td></tr>' +
        '<tr><td>OpenSanctions</td><td>80+ datasets</td><td><span class="fp-pill ok">CLEAR</span></td><td>0</td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">Legal Intelligence</h3>' +
        '<ul class="fp-list">' +
        '<li>Rechtspraak.nl: No adverse court rulings found</li>' +
        '<li>CIR: No insolvency or bankruptcy records</li>' +
        '<li>WIPO: 4 active payment security patents</li>' +
        '</ul>' +
        '<div class="fp-callout warn">⚠ DNB PSD2 license — Verify current regulatory status with primary source</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 4 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 5: CYBER & SECURITY ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">🔒</span> Cyber Exposure Assessment</h2>' +
        '<div class="fp-verdict-bar ok"><span class="fp-vb-dot ok"></span> LOW RISK — Exposure Score 12/100</div>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">0</div><div class="fp-kpi-lbl">Known CVEs</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">2</div><div class="fp-kpi-lbl">Open Ports</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">12/100</div><div class="fp-kpi-lbl">Exposure Score</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">A</div><div class="fp-kpi-lbl">Security Grade</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">Security Headers</h3>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Header</th><th>Status</th><th>Grade</th></tr></thead>' +
        '<tbody>' +
        '<tr><td>Strict-Transport-Security (HSTS)</td><td><span class="fp-pill ok">PRESENT</span></td><td>A+</td></tr>' +
        '<tr><td>Content-Security-Policy (CSP)</td><td><span class="fp-pill ok">PRESENT</span></td><td>A</td></tr>' +
        '<tr><td>X-Frame-Options</td><td><span class="fp-pill ok">PRESENT</span></td><td>A</td></tr>' +
        '<tr><td>X-Content-Type-Options</td><td><span class="fp-pill ok">PRESENT</span></td><td>A</td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">MITRE ATT&CK Coverage</h3>' +
        '<p class="fp-text-sm">Infrastructure mapped against MITRE ATT&CK Enterprise framework — <strong style="color:#00ff88">0 high-risk techniques</strong> detected in current exposure profile.</p>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 5 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 6: MARKET POSITION & PEERS ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">📈</span> Market Position & Peers</h2>' +
        '<h3 class="fp-subtitle">Competitive Landscape</h3>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Company</th><th>Rev (est.)</th><th>FTE</th><th>Rev/FTE</th></tr></thead>' +
        '<tbody>' +
        '<tr class="fp-row-hl"><td>Mollie ★</td><td class="fp-val-cyan">€800M</td><td>2,500</td><td>€320K</td></tr>' +
        '<tr><td>Adyen</td><td>€1.6B</td><td>4,000</td><td>€400K</td></tr>' +
        '<tr><td>Stripe (EU)</td><td>€2.1B</td><td>8,000</td><td>€263K</td></tr>' +
        '<tr><td>Worldline</td><td>€4.4B</td><td>18,000</td><td>€244K</td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">Growth & Digital Signals</h3>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">↑ 24%</div><div class="fp-kpi-lbl">FTE Growth YoY</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#f59e0b">★ 4.2</div><div class="fp-kpi-lbl">Trustpilot Score</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">15</div><div class="fp-kpi-lbl">Open Vacancies</div></div>' +
        '</div>' +
        '<div class="fp-digital-grid">' +
        '<div class="fp-dg-item"><div class="fp-dg-val">82<span class="fp-dg-unit">/100</span></div><div class="fp-dg-lbl">Domain Authority</div></div>' +
        '<div class="fp-dg-item"><div class="fp-dg-val">94<span class="fp-dg-unit">/100</span></div><div class="fp-dg-lbl">PageSpeed Desktop</div></div>' +
        '<div class="fp-dg-item"><div class="fp-dg-val">#1<span class="fp-dg-unit"> SERP</span></div><div class="fp-dg-lbl">"online payments EU"</div></div>' +
        '<div class="fp-dg-item"><div class="fp-dg-val">89<span class="fp-dg-unit"> repos</span></div><div class="fp-dg-lbl">GitHub · 4.2K+ stars</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">LLM Citation Visibility</h3>' +
        '<p class="fp-text-sm">Mollie appears in <strong style="color:#22d3ee">7 of 8</strong> AI-generated sector rankings — strong GEO brand authority.</p>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 6 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 7: EMPLOYEE INTELLIGENCE ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">👥</span> Employee Intelligence</h2>' +
        '<p class="fp-text-sm">Workforce analysis via LinkedIn, GDELT, and Glassdoor proxies for hiring velocity and culture signals.</p>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">2,500+</div><div class="fp-kpi-lbl">Total FTE</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">↑ 24%</div><div class="fp-kpi-lbl">YoY Growth</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">15</div><div class="fp-kpi-lbl">Open Roles</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#f59e0b">★ 3.8</div><div class="fp-kpi-lbl">Glassdoor</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">Department Breakdown</h3>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Department</th><th>Headcount</th><th>% of Total</th><th>Trend</th></tr></thead>' +
        '<tbody>' +
        '<tr><td>Engineering</td><td class="fp-val-cyan">780</td><td>31%</td><td style="color:#00ff88">↑ 18%</td></tr>' +
        '<tr><td>Sales & Marketing</td><td class="fp-val-purple">425</td><td>17%</td><td style="color:#00ff88">↑ 22%</td></tr>' +
        '<tr><td>Operations</td><td class="fp-val-white">350</td><td>14%</td><td style="color:#f59e0b">→ 3%</td></tr>' +
        '<tr><td>Compliance & Legal</td><td class="fp-val-cyan">220</td><td>9%</td><td style="color:#00ff88">↑ 35%</td></tr>' +
        '<tr><td>Support</td><td class="fp-val-purple">375</td><td>15%</td><td style="color:#00ff88">↑ 12%</td></tr>' +
        '</tbody>' +
        '</table>' +
        '<div class="fp-callout ok">✓ Strong engineering ratio (31%) indicates product-led growth. Compliance hiring surge (+35%) shows regulatory maturity.</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 7 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 8: DIGITAL PRESENCE & SEO ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">🌐</span> Digital Presence & SEO</h2>' +
        '<p class="fp-text-sm">Multi-signal digital footprint analysis via PageSpeed, SERP rankings, CrUX Web Vitals, and domain authority estimation.</p>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">82</div><div class="fp-kpi-lbl">Domain Authority</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">94</div><div class="fp-kpi-lbl">PageSpeed</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">#1</div><div class="fp-kpi-lbl">SERP Rank</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#f59e0b">A+</div><div class="fp-kpi-lbl">SSL Grade</div></div>' +
        '</div>' +
        '<h3 class="fp-subtitle">Core Web Vitals (CrUX)</h3>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr></thead>' +
        '<tbody>' +
        '<tr><td>LCP (Largest Contentful Paint)</td><td class="fp-val-cyan">1.2s</td><td>≤2.5s</td><td><span class="fp-pill ok">GOOD</span></td></tr>' +
        '<tr><td>INP (Interaction to Next Paint)</td><td class="fp-val-purple">89ms</td><td>≤200ms</td><td><span class="fp-pill ok">GOOD</span></td></tr>' +
        '<tr><td>CLS (Cumulative Layout Shift)</td><td class="fp-val-white">0.04</td><td>≤0.1</td><td><span class="fp-pill ok">GOOD</span></td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">SERP Rankings</h3>' +
        '<ul class="fp-list">' +
        '<li>"online payments Europe" — <strong style="color:#22d3ee">#1</strong></li>' +
        '<li>"payment service provider" — <strong style="color:#22d3ee">#2</strong></li>' +
        '<li>"mollie payments" — <strong style="color:#22d3ee">#1</strong></li>' +
        '</ul>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 8 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 9: KVK COMPANY REGISTRY ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">🏛️</span> KvK Company Registry</h2>' +
        '<p class="fp-text-sm">Dutch Chamber of Commerce (Handelsregister) validation and corporate structure analysis.</p>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Field</th><th>Value</th><th>Verified</th></tr></thead>' +
        '<tbody>' +
        '<tr><td>KvK Number</td><td class="fp-val-cyan">30204462</td><td><span class="fp-pill ok">✓</span></td></tr>' +
        '<tr><td>Legal Form</td><td class="fp-val-white">Besloten Vennootschap (BV)</td><td><span class="fp-pill ok">✓</span></td></tr>' +
        '<tr><td>Founded</td><td class="fp-val-purple">2004</td><td><span class="fp-pill ok">✓</span></td></tr>' +
        '<tr><td>SBI Code</td><td class="fp-val-cyan">6619 · Financial Services</td><td><span class="fp-pill ok">✓</span></td></tr>' +
        '<tr><td>Registered Address</td><td class="fp-val-white">Keizersgracht 126, Amsterdam</td><td><span class="fp-pill ok">✓</span></td></tr>' +
        '<tr><td>Active Status</td><td class="fp-val-cyan">Active · Registered</td><td><span class="fp-pill ok">✓</span></td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">BAG Address Validation</h3>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">✓</div><div class="fp-kpi-lbl">Commercial Use</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">1,240m²</div><div class="fp-kpi-lbl">Floor Area</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">0</div><div class="fp-kpi-lbl">Shell Risk Flags</div></div>' +
        '</div>' +
        '<div class="fp-callout ok">✓ Registered at verified commercial premises — no shell company indicators detected. 20+ years of continuous operation.</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 9 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 10: MANAGEMENT PROFILING ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">🎯</span> Management Profiling</h2>' +
        '<p class="fp-text-sm">C-suite leadership analysis via Apollo.io enrichment and LinkedIn intelligence. Contact discovery for deal execution.</p>' +
        '<table class="fp-table">' +
        '<thead><tr><th>Name</th><th>Role</th><th>Verified</th></tr></thead>' +
        '<tbody>' +
        '<tr><td class="fp-val-cyan">Koen Köppen</td><td>CEO</td><td><span class="fp-pill ok">✓ LI</span></td></tr>' +
        '<tr><td class="fp-val-white">Christoph Burmeister</td><td>CFO</td><td><span class="fp-pill ok">✓ LI</span></td></tr>' +
        '<tr><td class="fp-val-purple">Erik van der Neut</td><td>CTO</td><td><span class="fp-pill ok">✓ LI</span></td></tr>' +
        '<tr><td class="fp-val-cyan">Shane Happach</td><td>CCO</td><td><span class="fp-pill ok">✓ LI</span></td></tr>' +
        '<tr><td class="fp-val-white">Adriaan Mol</td><td>Founder</td><td><span class="fp-pill ok">✓ LI</span></td></tr>' +
        '</tbody>' +
        '</table>' +
        '<h3 class="fp-subtitle">Leadership Signals</h3>' +
        '<div class="fp-kpi-row">' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#22d3ee">5</div><div class="fp-kpi-lbl">C-Suite Identified</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#00ff88">100%</div><div class="fp-kpi-lbl">LinkedIn Verified</div></div>' +
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#a5b4fc">0</div><div class="fp-kpi-lbl">PEP/Sanctions</div></div>' +
        '</div>' +
        '<div class="fp-callout ok">✓ Stable leadership team with strong fintech pedigree. Zero PEP matches. All contacts enriched via Apollo.io + LinkedIn cross-validation.</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 10 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 11: DISCLAIMER & METHODOLOGY ═══
        '<div class="fp fp-page">' +
        '<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">Mollie B.V. — GOLD Report</span></div>' +
        '<div class="fp-body">' +
        '<h2 class="fp-title"><span class="fp-icon">📜</span> Disclaimer & Methodology</h2>' +
        '<h3 class="fp-subtitle">Data Sources & Methodology</h3>' +
        '<p class="fp-text-sm">This report was generated using the DueSight Neuro-Symbolic AI stack. All data is sourced from publicly available databases and enrichment APIs:</p>' +
        '<ul class="fp-list">' +
        '<li>KvK Handelsregister & XBRL Jaarrekeningen (Dutch Chamber of Commerce)</li>' +
        '<li>CBS StatLine — Official Dutch Statistics (sector benchmarks)</li>' +
        '<li>OpenSanctions — Global watchlist screening (OFAC, EU, UN, UK HMT)</li>' +
        '<li>Shodan InternetDB — Cyber exposure assessment</li>' +
        '<li>Google PageSpeed, CrUX & Knowledge Graph APIs</li>' +
        '<li>Apollo.io — Company & contact enrichment</li>' +
        '<li>GDELT — Global news sentiment analysis</li>' +
        '</ul>' +
        '<h3 class="fp-subtitle">AI Cross-Validation</h3>' +
        '<p class="fp-text-sm">Verdicts are generated by 5 independent AI engines (GPT-4o, Claude Opus, Gemini Pro, DeepSeek R1, Llama 3.1) using structured chain-of-thought reasoning. Unanimous consensus required for final verdict.</p>' +
        '<h3 class="fp-subtitle">Disclaimer</h3>' +
        '<p class="fp-text-sm" style="color:rgba(255,255,255,0.5)">This report is provided for informational purposes only and does not constitute financial, legal, or investment advice. DueSight makes no warranties regarding accuracy or completeness. Always verify findings with primary sources before making investment decisions.</p>' +
        '<div class="fp-callout">ℹ All data collected via public APIs — zero manual research required. Report generation time: ~90 seconds.</div>' +
        '</div>' +
        '<div class="fp-footer"><span>Page 11 of 12</span><span>Confidential · Protocol v3.2</span></div>' +
        '</div>',

        // ═══ PAGE 12: BACK COVER ═══
        '<div class="fp fp-back">' +
        '<div class="fp-back-inner">' +
        '<div class="fp-back-logo">' +
        '<svg viewBox="0 0 40 40" width="64" height="64"><circle cx="20" cy="20" r="19" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2.5"/>' +
        '<path d="M12 20l5 5 11-11" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        '</div>' +
        '<div class="fp-back-brand">DueSight Intelligence</div>' +
        '<div class="fp-back-tagline">AI-Powered Due Diligence · Protocol v3.2</div>' +
        '<div class="fp-back-divider"></div>' +
        '<div class="fp-back-stats">' +
        '<div class="fp-back-stat"><div class="fp-back-stat-val">12</div><div class="fp-back-stat-lbl">Intelligence Modules</div></div>' +
        '<div class="fp-back-stat"><div class="fp-back-stat-val">64+</div><div class="fp-back-stat-lbl">Data Sources</div></div>' +
        '<div class="fp-back-stat"><div class="fp-back-stat-val">5</div><div class="fp-back-stat-lbl">AI Engines</div></div>' +
        '</div>' +
        '<div class="fp-back-info">This report was generated using the DueSight Neuro-Symbolic AI stack with 5-engine cross-validation across 64+ public data sources.</div>' +
        '<div class="fp-back-cta-wrap"><a class="fp-back-cta-btn" href="#start">Genereer uw eigen rapport →</a></div>' +
        '<div class="fp-back-url">duesight.nl</div>' +
        '<div class="fp-back-legal">© 2026 DueSight Intelligence · Confidential · All rights reserved</div>' +
        '</div>' +
        '</div>'
    ];

    var PAGE_LABELS = [
        'Cover — Mollie B.V. GOLD Report',
        'Executive Summary & AI Validation',
        'Financial Proxy Analysis',
        'Benford\'s Law Forensic Analysis',
        'Compliance & Sanctions Screening',
        'Cyber Exposure Assessment',
        'Market Position & Peer Benchmarks',
        'Employee Intelligence',
        'Digital Presence & SEO',
        'KvK Company Registry',
        'Management Profiling',
        'Disclaimer & Methodology',
        ''
    ];

    // ─── BUILD DOM ──────────────────────────────────────────
    var scene = document.createElement('div');
    scene.className = 'fp-scene';

    var wrapper = document.createElement('div');
    wrapper.className = 'fp-wrapper';

    var flipEl = document.createElement('div');
    flipEl.id = 'flipbook-container';
    wrapper.appendChild(flipEl);
    scene.appendChild(wrapper);
    mount.appendChild(scene);

    PAGES.forEach(function (html) {
        var tmp = document.createElement('div');
        tmp.innerHTML = html;
        flipEl.appendChild(tmp.firstChild);
    });

    // Navigation arrows
    var navPrev = document.createElement('button');
    navPrev.className = 'fp-nav fp-nav-prev';
    navPrev.innerHTML = '‹';
    navPrev.setAttribute('aria-label', 'Previous page');
    scene.appendChild(navPrev);

    var navNext = document.createElement('button');
    navNext.className = 'fp-nav fp-nav-next';
    navNext.innerHTML = '›';
    navNext.setAttribute('aria-label', 'Next page');
    scene.appendChild(navNext);

    // Page indicator bar
    var indicatorWrap = document.createElement('div');
    indicatorWrap.className = 'fp-indicator';

    var dotsContainer = document.createElement('div');
    dotsContainer.className = 'fp-dots';
    dotsContainer.id = 'fp-dots';
    for (var i = 0; i < PAGES.length; i++) {
        var dot = document.createElement('div');
        dot.className = 'fp-dot' + (i === 0 ? ' active' : '');
        dotsContainer.appendChild(dot);
    }
    indicatorWrap.appendChild(dotsContainer);

    var labelEl = document.createElement('div');
    labelEl.className = 'fp-label';
    labelEl.id = 'fp-label';
    labelEl.textContent = PAGE_LABELS[0];
    indicatorWrap.appendChild(labelEl);
    mount.appendChild(indicatorWrap);

    // Page curl hint
    var curlHint = document.createElement('div');
    curlHint.className = 'fp-curl-hint';
    curlHint.innerHTML = '<div class="fp-curl-arrow">↗</div><div class="fp-curl-text">Flip to explore</div>';
    scene.appendChild(curlHint);

    // ─── LOAD LIBRARY & INIT ────────────────────────────────
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js';
    script.onload = function () { initFlipbook(); };
    document.head.appendChild(script);

    function initFlipbook() {
        if (typeof St === 'undefined' || !St.PageFlip) return;

        var isMobile = window.innerWidth < 768;
        var pageFlip = new St.PageFlip(flipEl, {
            width: isMobile ? 360 : 700,
            height: isMobile ? 540 : 980,
            size: 'stretch',
            minWidth: 320,
            maxWidth: 920,
            minHeight: 460,
            maxHeight: 1200,
            usePortrait: isMobile,
            showCover: true,
            drawShadow: true,
            maxShadowOpacity: 0.7,
            flippingTime: 900,
            startPage: 0,
            autoSize: true,
            mobileScrollSupport: true
        });

        pageFlip.loadFromHTML(flipEl.querySelectorAll('.fp'));

        // Start with cover clipping (page 0 = front cover, only right half visible)
        wrapper.classList.add('fp-at-cover');

        navPrev.addEventListener('click', function () {
            pageFlip.flipPrev();
            killAutoplay();
        });
        navNext.addEventListener('click', function () {
            pageFlip.flipNext();
            killAutoplay();
        });

        pageFlip.on('flip', function (e) {
            updateUI(e.data);
        });

        function updateUI(idx) {
            var dots = document.querySelectorAll('#fp-dots .fp-dot');
            var label = document.getElementById('fp-label');
            dots.forEach(function (d, i) {
                d.className = 'fp-dot' + (i === idx ? ' active' : '');
            });
            if (label && PAGE_LABELS[idx] !== undefined) {
                label.textContent = PAGE_LABELS[idx];
            }
            navPrev.style.opacity = idx > 0 ? '1' : '0.2';
            navNext.style.opacity = idx < PAGES.length - 1 ? '1' : '0.2';

            // ─── Cover/Back half-width clipping ───
            var lastPage = PAGES.length - 1;
            if (idx === 0) {
                wrapper.classList.add('fp-at-cover');
                wrapper.classList.remove('fp-at-back');
            } else if (idx >= lastPage) {
                wrapper.classList.remove('fp-at-cover');
                wrapper.classList.add('fp-at-back');
            } else {
                wrapper.classList.remove('fp-at-cover');
                wrapper.classList.remove('fp-at-back');
            }
        }

        // ─── AUTOPLAY ───────────────────────────────────────
        var autoTimer = null;
        var autoDead = false;

        function startAutoplay() {
            if (autoDead || autoTimer) return;
            autoTimer = setInterval(function () {
                var cur = pageFlip.getCurrentPageIndex();
                if (cur < PAGES.length - 1) {
                    pageFlip.flipNext();
                } else {
                    pageFlip.flip(0);
                }
            }, 4000);
        }

        function killAutoplay() {
            if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
            autoDead = true;
            if (curlHint) curlHint.style.opacity = '0';
        }

        ['mouseenter', 'touchstart', 'pointerdown'].forEach(function (evt) {
            wrapper.addEventListener(evt, function () { killAutoplay(); }, { once: true, passive: true });
        });

        if ('IntersectionObserver' in window) {
            var obs = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting && !autoDead) {
                        setTimeout(startAutoplay, 2000);
                        if (curlHint) {
                            curlHint.style.opacity = '1';
                            setTimeout(function () {
                                if (curlHint) curlHint.style.opacity = '0';
                            }, 4000);
                        }
                        obs.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.4 });
            obs.observe(mount);
        } else {
            setTimeout(startAutoplay, 2500);
        }
    }
})();
