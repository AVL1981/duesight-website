/**
 * DueSight Live Scanner Client
 * =============================
 * Connects the website's static scan dashboard to the FastAPI backend
 * via Server-Sent Events (SSE) for real-time scan progress updates.
 *
 * Usage: <script src="scan_client.js"></script> (before </body>)
 */

(() => {
    'use strict';

    // ── Configuration ────────────────────────────────────────────────

    const API_BASE = window.DUESIGHT_API_URL || 'http://localhost:8000';

    // Scanner name → metric card selector mapping
    const SCANNER_MAP = {
        domain_authority: '[data-metric="domain-authority"]',
        pagespeed: '[data-metric="pagespeed"]',
        security_headers: '[data-metric="security-headers"]',
        serp_visibility: '[data-metric="serp-visibility"]',
        sentiment: '[data-metric="sentiment"]',
        safe_browsing: '[data-metric="safe-browsing"]',
    };

    const PHASE_LABELS = {
        intake: '🔍 Intake & Scoping',
        collection: '📡 Data Collection',
        analysis: '🧠 Deep Analysis',
        validation: '⚔️ Adversarial Validation',
        synthesis: '📊 Synthesizing Report',
        execution: '🚀 Workflow Executing',
    };

    // ── State ─────────────────────────────────────────────────────────

    let currentScanId = null;
    let eventSource = null;

    // ── DOM Setup ─────────────────────────────────────────────────────

    function injectScanForm() {
        const header = document.querySelector('.scan-dashboard-header');
        if (!header) return;

        // Replace the static "Scanning..." badge with a live form hook
        const existingBadge = header.querySelector('.scan-live-badge');

        const form = document.createElement('div');
        form.className = 'scan-input-form';
        form.id = 'scanForm';
        form.innerHTML = `
            <div class="scan-form-row" style="position: relative;">
                <div style="flex: 2; position: relative;">
                    <input
                        type="text"
                        id="scanDomainInput"
                        class="scan-domain-input"
                        placeholder="Voer uw domein in (bijv. mollie.com)"
                        autocomplete="off"
                        spellcheck="false"
                        style="width: 100%;"
                    />
                    <div id="domainSuggestions" class="suggestions-dropdown" style="display:none; position:absolute; top:100%; left:0; right:0; background:var(--bg-card); border:1px solid var(--border-glass); border-radius:8px; z-index:100; max-height:200px; overflow-y:auto; box-shadow:0 10px 30px rgba(0,0,0,0.5);"></div>
                </div>
                <button id="scanStartBtn" class="scan-start-btn" type="button" style="flex: 1;">
                    <span class="scan-btn-text">Start Analyse →</span>
                    <span class="scan-btn-spinner" style="display:none;">⟳</span>
                </button>
            </div>
            <div class="scan-progress-wrap" id="scanProgressWrap" style="display:none;">
                <div class="scan-progress-bar">
                    <div class="scan-progress-fill" id="scanProgressFill"></div>
                </div>
                <span class="scan-progress-label" id="scanProgressLabel">Verbinding maken...</span>
            </div>
            <div class="scan-mode-badge" id="scanModeBadge" style="margin-top: 15px;">
                <span class="scan-mode-dot demo"></span>
                <span id="scanModeText">GRATIS PREVIEW</span>
            </div>
        `;

        // Insert form before the badge
        if (existingBadge) {
            existingBadge.style.display = 'none';
        }
        header.appendChild(form);

        // Event listeners
        document.getElementById('scanStartBtn').addEventListener('click', handleStartScan);
        document.getElementById('scanDomainInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleStartScan();
        });

        // Setup Auto-lookup
        setupAutoLookup();
    }

    // ── Auto-lookup Logic ─────────────────────────────────────────────

    function setupAutoLookup() {
        const input = document.getElementById('scanDomainInput');
        const suggestionsBox = document.getElementById('domainSuggestions');
        let debounceTimer = null;

        if (!input) return;

        input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query.length < 2) {
                suggestionsBox.style.display = 'none';
                return;
            }

            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`${API_BASE}/api/lookup?q=${encodeURIComponent(query)}`);
                    if (!res.ok) throw new Error('Lookup failed');
                    const data = await res.json();

                    if (data.results && data.results.length > 0) {
                        suggestionsBox.innerHTML = '';
                        data.results.forEach(company => {
                            const item = document.createElement('div');
                            item.className = 'suggestion-item';
                            item.style.padding = '10px 15px';
                            item.style.cursor = 'pointer';
                            item.style.borderBottom = '1px solid var(--border-glass)';
                            item.innerHTML = `
                                <div style="font-weight: 600; color: var(--text-primary);">${company.name}</div>
                                <div style="font-size: 12px; color: var(--text-secondary);">${company.domain || ''} ${company.industry ? '— ' + company.industry : ''}</div>
                            `;

                            // Hover effect
                            item.addEventListener('mouseover', () => item.style.background = 'rgba(99, 102, 241, 0.1)');
                            item.addEventListener('mouseout', () => item.style.background = 'transparent');

                            // Select action
                            item.addEventListener('click', () => {
                                input.value = company.domain || company.name.toLowerCase().replace(/[^a-z0-9]/g, '') + '.com';
                                suggestionsBox.style.display = 'none';
                            });

                            suggestionsBox.appendChild(item);
                        });
                        suggestionsBox.style.display = 'block';
                    } else {
                        suggestionsBox.style.display = 'none';
                    }
                } catch (err) {
                    console.error('Auto-lookup error:', err);
                    suggestionsBox.style.display = 'none';
                }
            }, 300); // 300ms debounce
        });

        // Hide when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.style.display = 'none';
            }
        });
    }

    // ── Scan Lifecycle ────────────────────────────────────────────────

    async function handleStartScan() {
        const domainInput = document.getElementById('scanDomainInput');
        const domain = domainInput ? domainInput.value.trim() : '';

        if (!domain) {
            domainInput.classList.add('shake');
            setTimeout(() => {
                domainInput.classList.remove('shake');
            }, 500);
            return;
        }

        // Open Modal automatically when they hit start scan
        const checkoutModal = document.getElementById('checkoutModal');
        if (checkoutModal) {
            document.getElementById('modalDomain').value = domain;

            // Default to highest converting tier
            document.getElementById('modalTier').value = 'standard';
            const tierBadge = document.getElementById('modalTierBadge');
            if (tierBadge) tierBadge.textContent = 'MEEST GEKOZEN';
            document.getElementById('modalTierTitle').textContent = 'Digital + Verified';
            document.getElementById('modalTierPrice').textContent = '€599';

            checkoutModal.style.display = 'flex';
        }
    }

    function connectToEvents(scanId) {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(`${API_BASE}/api/scan/${scanId}/events`);

        eventSource.addEventListener('phase', (e) => {
            const data = JSON.parse(e.data);
            handlePhaseEvent(data);
        });

        eventSource.addEventListener('scanner', (e) => {
            const data = JSON.parse(e.data);
            handleScannerEvent(data);
        });

        eventSource.addEventListener('completed', (e) => {
            const data = JSON.parse(e.data);
            handleCompleted(data);
        });

        eventSource.addEventListener('error', (e) => {
            if (e.data) {
                const data = JSON.parse(e.data);
                showError(data.message || 'Scan error');
            }
            resetUI();
        });

        eventSource.addEventListener('complete', () => {
            eventSource.close();
        });

        eventSource.onerror = () => {
            // SSE connection error — may be normal at end of stream
            if (eventSource.readyState === EventSource.CLOSED) {
                eventSource.close();
            }
        };
    }

    // ── Event Handlers ────────────────────────────────────────────────

    function handlePhaseEvent(data) {
        const phase = data.phase;
        const status = data.status;
        const label = PHASE_LABELS[phase] || phase;

        if (status === 'started') {
            showProgress(`${label}...`, getPhaseProgress(phase));
        } else if (status === 'completed') {
            showProgress(`${label} ✓`, getPhaseProgress(phase) + 15);
        }

        // Update scan dashboard header status
        const statusEl = document.getElementById('meterStatus');
        if (statusEl) {
            statusEl.textContent = data.message || label;
        }
    }

    function handleScannerEvent(data) {
        const scannerName = data.scanner;
        const result = data.result;

        if (!result) return;

        // Update DMI section separately
        if (scannerName === 'dmi') {
            updateDMI(result);
            return;
        }

        // Find the matching metric card
        const selector = SCANNER_MAP[scannerName];
        if (!selector) return;

        const card = document.querySelector(selector);
        if (!card) return;

        // Update the card with live data
        updateMetricCard(card, result);
    }

    function handleCompleted(data) {
        showProgress('DD Rapport voltooid! ✓', 100);

        // Update mode badge
        setModeBadge('completed');

        // Update meter value
        const meterValue = document.getElementById('meterValue');
        if (meterValue && data.confidence) {
            const pct = typeof data.confidence === 'number'
                ? Math.round(data.confidence * 100)
                : data.confidence;
            meterValue.textContent = `${pct}%`;
        }

        // Add report download button
        if (data.report_url) {
            addDownloadButton(data.report_url);
        }

        // Reset button state
        setTimeout(resetUI, 2000);

        // Close SSE
        if (eventSource) {
            eventSource.close();
        }
    }

    // ── Card Updates ──────────────────────────────────────────────────

    function updateMetricCard(card, result) {
        // Remove loading state
        card.classList.remove('loading');
        card.classList.add('live');

        // Update gauge value
        const gaugeValue = card.querySelector('.gauge-value');
        if (gaugeValue && result.score != null) {
            animateCounter(gaugeValue, parseInt(result.score));
        }

        // Update gauge fill (SVG circle)
        const gaugeFill = card.querySelector('.gauge-fill');
        if (gaugeFill && result.score != null) {
            const score = parseInt(result.score);
            const circumference = 2 * Math.PI * 34; // r=34
            const dasharray = (score / 100) * circumference;
            gaugeFill.setAttribute('stroke-dasharray', `${dasharray} ${circumference}`);
        }

        // Update bar fill
        const barFill = card.querySelector('.metric-bar-fill');
        if (barFill && result.score != null) {
            barFill.style.width = `${result.score}%`;
        }

        // Flash effect
        card.style.animation = 'cardFlash 0.6s ease-out';
        setTimeout(() => { card.style.animation = ''; }, 600);
    }

    function updateDMI(result) {
        const dmiSection = document.querySelector('.dmi-section');
        if (!dmiSection) return;

        // Update composite score
        const composite = dmiSection.querySelector('.dmi-composite-score');
        if (composite && result.composite != null) {
            animateCounter(composite, result.composite, '/100');
        }

        // Update bars
        const bars = dmiSection.querySelectorAll('.dmi-bar-row');
        const keys = ['visibility', 'trust', 'operational_resilience', 'technical_debt'];

        bars.forEach((row, i) => {
            const key = keys[i];
            if (!key || result[key] == null) return;

            const fill = row.querySelector('.dmi-bar-fill');
            const value = row.querySelector('.dmi-bar-value');

            if (fill) fill.style.width = `${result[key]}%`;
            if (value) value.textContent = result[key];
        });
    }

    // ── UI Helpers ────────────────────────────────────────────────────

    function animateCounter(el, target, suffix) {
        suffix = suffix || '';
        let current = parseInt(el.textContent) || 0;
        const step = Math.max(1, Math.abs(target - current) / 20);
        const direction = target > current ? 1 : -1;

        function tick() {
            current += step * direction;
            if ((direction > 0 && current >= target) || (direction < 0 && current <= target)) {
                el.textContent = target + suffix;
                return;
            }
            el.textContent = Math.round(current) + suffix;
            requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    function setAllCardsLoading(loading) {
        document.querySelectorAll('.metric-card').forEach(card => {
            if (loading) {
                card.classList.add('loading');
                card.classList.remove('live');
            } else {
                card.classList.remove('loading');
            }
        });
    }

    function showProgress(label, percent) {
        const wrap = document.getElementById('scanProgressWrap');
        const fill = document.getElementById('scanProgressFill');
        const labelEl = document.getElementById('scanProgressLabel');

        if (wrap) wrap.style.display = 'flex';
        if (fill) fill.style.width = `${Math.min(100, percent)}%`;
        if (labelEl) labelEl.textContent = label;
    }

    function setModeBadge(mode) {
        const dot = document.querySelector('.scan-mode-dot');
        const text = document.getElementById('scanModeText');

        if (!dot || !text) return;

        dot.className = 'scan-mode-dot ' + mode;
        switch (mode) {
            case 'live':
                text.textContent = 'LIVE SCANNING';
                break;
            case 'completed':
                text.textContent = 'SCAN COMPLETE';
                break;
            default:
                text.textContent = 'GRATIS PREVIEW';
        }
    }

    function addDownloadButton(reportUrl) {
        const progressWrap = document.getElementById('scanProgressWrap');
        if (!progressWrap) return;

        const existingBtn = progressWrap.querySelector('.scan-download-btn');
        if (existingBtn) existingBtn.remove();

        const btn = document.createElement('a');
        btn.href = `${API_BASE}${reportUrl}`;
        btn.className = 'scan-download-btn';
        btn.target = '_blank';
        btn.innerHTML = '📄 Download DD Rapport';
        progressWrap.appendChild(btn);
    }

    function showError(message) {
        const label = document.getElementById('scanProgressLabel');
        if (label) {
            label.textContent = `❌ ${message}`;
            label.style.color = '#ef4444';
        }
        showProgress(`❌ ${message}`, 100);
        const fill = document.getElementById('scanProgressFill');
        if (fill) fill.style.background = '#ef4444';
    }

    function resetUI() {
        const startBtn = document.getElementById('scanStartBtn');
        const btnText = startBtn?.querySelector('.scan-btn-text');
        const btnSpinner = startBtn?.querySelector('.scan-btn-spinner');
        const domainInput = document.getElementById('scanDomainInput');
        const nameInput = document.getElementById('scanNameInput');
        const emailInput = document.getElementById('scanEmailInput');
        const tierSelect = document.getElementById('scanTierSelect');

        if (startBtn) startBtn.disabled = false;
        if (btnText) btnText.style.display = 'inline';
        if (btnSpinner) btnSpinner.style.display = 'none';
        if (domainInput) domainInput.disabled = false;
        if (nameInput) nameInput.disabled = false;
        if (emailInput) emailInput.disabled = false;
        if (tierSelect) tierSelect.disabled = false;
    }

    function getPhaseProgress(phase) {
        const map = { intake: 5, collection: 15, analysis: 45, validation: 65, synthesis: 85, execution: 10 };
        return map[phase] || 50;
    }

    // ── Initialize ────────────────────────────────────────────────────

    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', injectScanForm);
        } else {
            injectScanForm();
        }
    }

    init();

    // ── Checkout Modal Logic ──────────────────────────────────────────

    const checkoutModal = document.getElementById('checkoutModal');
    const checkoutForm = document.getElementById('checkoutForm');

    if (checkoutModal) {
        checkoutModal.querySelector('.modal-close').addEventListener('click', () => {
            checkoutModal.style.display = 'none';
        });

        checkoutModal.querySelector('.modal-backdrop').addEventListener('click', () => {
            checkoutModal.style.display = 'none';
        });

        checkoutForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('modalSubmitBtn');
            const originalText = btn.innerHTML;

            try {
                btn.innerHTML = 'Bezig met verwerken <span class="scan-btn-spinner" style="display:inline-block">⟳</span>';
                btn.style.opacity = '0.8';
                btn.disabled = true;

                const domain = document.getElementById('modalDomain').value;
                const name = document.getElementById('modalName').value;
                const email = document.getElementById('modalEmail').value;
                const tier = document.getElementById('modalTier').value;

                // 1. Submit lead to Apollo / Custom Backend
                const response = await fetch(`${API_BASE}/api/scan`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        domain: domain,
                        tier: tier,
                        lead_name: name,
                        lead_email: email
                    }),
                });

                if (!response.ok) {
                    throw new Error('Kon aanvraag niet verwerken.');
                }

                // 2. Redirect to Mollie iDEAL Checkout
                const checkoutUrl = `${API_BASE}/api/checkout?tier=${encodeURIComponent(tier)}&domain=${encodeURIComponent(domain)}&email=${encodeURIComponent(email)}`;
                const outResponse = await fetch(checkoutUrl);
                if (outResponse.ok) {
                    const outData = await outResponse.json();
                    if (outData.checkout_url) {
                        // Store domain for post-payment questionnaire
                        sessionStorage.setItem('ds_scan_domain', domain);
                        sessionStorage.setItem('ds_scan_tier', tier);
                        window.location.href = outData.checkout_url;
                        return;
                    }
                }

                // Fallback: payment system not yet configured
                checkoutModal.style.display = 'none';
                alert('Aanvraag succesvol ontvangen! U krijgt z.s.m. een e-mail.');

            } catch (err) {
                console.error(err);
                alert('Fout bij verwerken: ' + err.message);
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
                btn.style.opacity = '1';
            }
        });
    }

    // ── Subsidie Pre-Kwalificatie Modal ─────────────────────────────────
    // Shows during the 90-second report generation loading screen.
    // Masks wait time while collecting "soft criteria" for subsidies.

    /** @type {Record<string, boolean>} */
    const subsidyAnswers = {};

    function detectPostPaymentReturn() {
        const params = new URLSearchParams(window.location.search);
        if (params.get('status') === 'pending' || params.get('payment') === 'success') {
            const domain = params.get('domain') || sessionStorage.getItem('ds_scan_domain') || '';
            const tier = params.get('tier') || sessionStorage.getItem('ds_scan_tier') || '';
            showPostPaymentOverlay(domain, tier);
        }
    }

    function showPostPaymentOverlay(domain, tier) {
        // Create full-screen loading overlay
        const overlay = document.createElement('div');
        overlay.id = 'subsidyOverlay';
        overlay.style.cssText = `
            position: fixed; inset: 0; z-index: 10000;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1f3a 100%);
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-family: 'Inter', system-ui, sans-serif; color: #e2e8f0;
        `;

        overlay.innerHTML = `
            <div style="text-align: center; max-width: 520px; padding: 40px;">
                <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
                <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 8px; background: linear-gradient(135deg, #818cf8, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    Uw DueSight rapport wordt gegenereerd
                </h2>
                <p style="color: #94a3b8; font-size: 14px; margin-bottom: 32px;">
                    Onze AI analyseert ${domain || 'uw bedrijf'} via 64+ datapunten...
                </p>

                <!-- Progress bar -->
                <div style="background: rgba(255,255,255,0.1); border-radius: 12px; height: 8px; overflow: hidden; margin-bottom: 12px;">
                    <div id="subsidyProgressFill" style="height: 100%; width: 0%; background: linear-gradient(90deg, #6366f1, #818cf8, #a5b4fc); border-radius: 12px; transition: width 0.5s ease;"></div>
                </div>
                <p id="subsidyProgressLabel" style="font-size: 12px; color: #64748b; margin-bottom: 40px;">Bezig met KvK-verificatie...</p>

                <!-- Questionnaire Container (slides up after 3s) -->
                <div id="subsidyQuestionnaire" style="opacity: 0; transform: translateY(30px); transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1); pointer-events: none;">
                    <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 16px; padding: 28px; text-align: left;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
                            <span style="font-size: 20px;">💡</span>
                            <span style="font-size: 14px; font-weight: 600; color: #a5b4fc;">SUBSIDIE PRE-KWALIFICATIE</span>
                        </div>
                        <p style="font-size: 13px; color: #94a3b8; margin-bottom: 20px; line-height: 1.5;">
                            Terwijl uw rapport wordt geschreven: uw profiel kwalificeert zich voor meerdere regelingen (totaal >€1,8 mld budget).
                            Beantwoord deze snelle vragen om uw kansen in het rapport op te nemen:
                        </p>

                        <div id="subsidyQuestions" style="display: flex; flex-direction: column; gap: 12px;">
                            <!-- Questions injected dynamically -->
                        </div>

                        <button id="subsidySubmitBtn" onclick="submitSubsidyAnswers()" style="
                            margin-top: 20px; width: 100%; padding: 12px 24px;
                            background: linear-gradient(135deg, #6366f1, #818cf8);
                            border: none; border-radius: 10px; color: white;
                            font-weight: 600; font-size: 14px; cursor: pointer;
                            transition: transform 0.2s, box-shadow 0.2s;
                        ">
                            Verwerk mijn subsidieprofiel →
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Animate progress bar
        const progressLabels = [
            { pct: 10, text: '🔍 KvK Handelsregister verificatie...' },
            { pct: 25, text: '📡 Tech stack analyse...' },
            { pct: 40, text: '🛡️ Cyber exposure assessment...' },
            { pct: 55, text: '📊 Financiële proxy berekening...' },
            { pct: 70, text: '⚔️ Adversarial validatie...' },
            { pct: 85, text: '📝 Rapport synthese...' },
            { pct: 95, text: '✨ Laatste kwaliteitscontrole...' },
        ];

        let step = 0;
        const progressFill = document.getElementById('subsidyProgressFill');
        const progressLabel = document.getElementById('subsidyProgressLabel');

        const progressInterval = setInterval(() => {
            if (step < progressLabels.length) {
                const p = progressLabels[step];
                if (progressFill) progressFill.style.width = p.pct + '%';
                if (progressLabel) progressLabel.textContent = p.text;
                step++;
            } else {
                clearInterval(progressInterval);
            }
        }, 12000); // ~12 seconds per step → 84 seconds total

        // Show questionnaire after 3 seconds (slide up animation)
        setTimeout(() => {
            const q = document.getElementById('subsidyQuestionnaire');
            if (q) {
                q.style.opacity = '1';
                q.style.transform = 'translateY(0)';
                q.style.pointerEvents = 'auto';
            }
            loadSubsidyQuestions(domain);
        }, 3000);
    }

    async function loadSubsidyQuestions(domain) {
        const container = document.getElementById('subsidyQuestions');
        if (!container) return;

        // Default questions (used if backend is unavailable)
        const defaultQuestions = [
            { id: 'wbso_q1', text: 'Ontwikkelt uw bedrijf nieuwe software, producten of productieprocessen?' },
            { id: 'wbso_q3', text: 'Zijn deze werkzaamheden technisch nieuw voor uw organisatie?' },
            { id: 'mitrd_q1', text: 'Werkt u samen met andere MKB-bedrijven aan innovatieprojecten?' },
            { id: 'eia_q1', text: 'Investeert u in energiebesparende apparatuur of duurzame energie?' },
        ];

        // Try to get personalized questions from backend
        let questions = defaultQuestions;
        try {
            const res = await fetch(`${API_BASE}/api/subsidy-questionnaire?company_name=${encodeURIComponent(domain)}&fte_count=0`, {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                if (data.subsidies) {
                    // Extract unique questions from matched subsidies
                    const allQ = [];
                    const seenIds = new Set();
                    for (const s of data.subsidies) {
                        for (const q of (s.questionnaire_needed || [])) {
                            if (!seenIds.has(q.id)) {
                                seenIds.add(q.id);
                                allQ.push({ id: q.id, text: q.text_nl });
                            }
                        }
                    }
                    if (allQ.length > 0) questions = allQ.slice(0, 5);
                }
            }
        } catch (e) {
            // Fallback to defaults — graceful degradation
        }

        container.innerHTML = questions.map(q => `
            <label style="
                display: flex; align-items: center; gap: 12px; padding: 12px 16px;
                background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px; cursor: pointer; transition: border-color 0.2s;
            " onmouseover="this.style.borderColor='rgba(99,102,241,0.4)'"
              onmouseout="this.style.borderColor='rgba(255,255,255,0.06)'">
                <input type="checkbox" data-question-id="${q.id}"
                    style="width: 18px; height: 18px; accent-color: #6366f1; flex-shrink: 0;"
                    onchange="window._dsSubsidyAnswers = window._dsSubsidyAnswers || {}; window._dsSubsidyAnswers['${q.id}'] = this.checked;"
                />
                <span style="font-size: 13px; color: #cbd5e1; line-height: 1.4;">${q.text}</span>
            </label>
        `).join('');
    }

    // Make submit function globally accessible (called from onclick)
    window.submitSubsidyAnswers = async function () {
        const btn = document.getElementById('subsidySubmitBtn');
        if (btn) {
            btn.innerHTML = '✅ Verwerkt! Wordt opgenomen in uw rapport...';
            btn.disabled = true;
            btn.style.opacity = '0.7';
        }

        const answers = window._dsSubsidyAnswers || {};
        const domain = sessionStorage.getItem('ds_scan_domain') || '';

        try {
            await fetch(`${API_BASE}/api/subsidy-questionnaire?company_name=${encodeURIComponent(domain)}&answers=${encodeURIComponent(JSON.stringify(answers))}`, {
                method: 'POST'
            });
        } catch (e) {
            // Non-critical — report continues regardless
        }

        // Fade out questionnaire after submission
        const q = document.getElementById('subsidyQuestionnaire');
        if (q) {
            setTimeout(() => {
                q.style.opacity = '0.5';
                q.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <span style="font-size: 32px;">✅</span>
                        <p style="font-size: 14px; color: #a5b4fc; margin-top: 12px;">
                            Subsidieprofiel opgenomen in uw rapport!
                        </p>
                    </div>
                `;
            }, 1500);
        }
    };

    // Auto-detect post-payment return
    detectPostPaymentReturn();

    // Attach to pricing buttons
    document.querySelectorAll('.pricing-card .btn').forEach((btn, index) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();

            const tiers = ['quick_scan', 'standard', 'premium'];
            const titles = ['Digitale Analyse', 'Digital + Verified', 'Full Service Expert'];
            const prices = ['€299', '€599', '€2.999'];

            document.getElementById('modalTier').value = tiers[index];
            document.getElementById('modalTierTitle').textContent = titles[index];
            document.getElementById('modalTierPrice').textContent = prices[index];

            if (index === 0) {
                document.getElementById('modalTierBadge').textContent = 'SNEL INZICHT';
                document.getElementById('modalTierFeatures').innerHTML = `
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Volledige AI Analyse</li>
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Automatische gap detectie</li>
                `;
            } else if (index === 1) {
                document.getElementById('modalTierBadge').textContent = 'MEEST GEKOZEN';
                document.getElementById('modalTierFeatures').innerHTML = `
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Alles uit de Digitale Analyse</li>
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Expert review bij gaps >20%</li>
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> RC/RA Validatie-verklaring</li>
                `;
            } else {
                document.getElementById('modalTierBadge').textContent = 'ENTERPRISE';
                document.getElementById('modalTierFeatures').innerHTML = `
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Dedicated Financial Controller</li>
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Primair marktonderzoek</li>
                    <li style="display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);"><span style="color: #22c55e;">✔</span> Executive Boardroom Presentatie</li>
                `;
            }

            // Pre-fill domain if entered in dashboard
            const dashboardDomain = document.getElementById('scanDomainInput');
            if (dashboardDomain && dashboardDomain.value) {
                document.getElementById('modalDomain').value = dashboardDomain.value;
            }

            checkoutModal.style.display = 'flex';
        });
    });

})();
