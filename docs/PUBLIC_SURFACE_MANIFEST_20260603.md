# DueSight Public Surface Manifest

Date: 2026-06-03

## Public Artifact

GitHub Pages must publish only the generated `_pages/` artifact, not the repository root.

Included by default:

- Curated static website files required for the live website.
- Public assets such as CSS, JavaScript, images, videos, `robots.txt`, `sitemap.xml`, `llms.txt` and `security.txt`.
- Claim-reviewed live customer-copy pages.
- Curated sample-report entrypoints only: `flipbook.html`, `hub.html`, `index.html`, `index-premium.html` and `styles.css`.

Excluded by default:

- Repository control/config paths: `.git/`, `.github/`, local agent/cache/session folders.
- Internal docs and evidence paths: `docs/`, `reports/`, `output/`, `data/`, `context/`.
- Raw or generated workspaces: `backtesting/`, raw files inside `sample-report-*/`, `company/`, `designs/`, `website_src/`, `tmp/`, `test-results/`, `frontend/`.
- Local tooling and tests: `tools/`, `tests/`, `app/`, `functions/`, `claude_playground/`, scripts, logs, JSON audit files, databases, spreadsheets, PDFs and Markdown files.
- Legacy root backups: `index_*.html`, `index_backup*.html`, `*.bak*`, `*.backup*.html`.

## Claim Gate

`tools/public_surface_gate.py` is the deploy gate for `_pages/`.

It blocks:

- Legacy score claims such as `100/100`, `105/110`, `105/100`, `DueSight Score` and `Hit Rate`.
- Unsubstantiated comparison or trust tokens such as `PwC`, `KPMG`, `Big 4`, `ISO 27001` and `SOC 2`.
- Absolute marketing language such as `perfect`, `unbeatable`, `100% zekerheid` and `100% Wwft`.
- Browser-save artifacts, raw tracker scripts and high-confidence secret patterns.
- Any denied directory or backup file that leaks into `_pages/`.
- Any non-curated file inside public `sample-report-*` directories.

## Operating Rule

Generated reports, company pages and design variants must remain outside the public artifact until they receive a separate claim review and are explicitly promoted. No public deploy or IndexNow submission should happen unless the public surface gate passes.
