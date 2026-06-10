# Legacy Zone Manifest - 2026-06-08

Purpose: quarantine stale public-surface artifacts without deleting them. All successful entries below are reversible with `git mv <archive path> <original path>`.

## Policy

- No deletes were performed.
- No glob-driven moves were used for execution.
- `engines.json`, `multi_model_thinker.py`, and their backups were not touched.
- The 7 small `index_*.html` redirect stubs with UTF-8 BOM noise were left in place.
- `backtesting/reports/20260526_Mollie.html` was skipped because `git mv` reported it is not under version control.

## Successful Archive Moves

| Status | Original path | Archive path | Reason |
|---|---|---|---|
| archived | `backtesting/asml_elite_v65.html` | `archive/legacy_zone_2026-06-08/backtesting/asml_elite_v65.html` | Legacy backtesting HTML with stale public-surface findings. |
| archived | `backtesting/coolblue_elite_v65.html` | `archive/legacy_zone_2026-06-08/backtesting/coolblue_elite_v65.html` | Legacy backtesting HTML with stale public-surface findings. |
| archived | `backtesting/gazprom_elite_v65.html` | `archive/legacy_zone_2026-06-08/backtesting/gazprom_elite_v65.html` | Legacy backtesting HTML with stale public-surface findings. |
| archived | `backtesting/postnl_elite_v65.html` | `archive/legacy_zone_2026-06-08/backtesting/postnl_elite_v65.html` | Legacy backtesting HTML with stale public-surface findings. |
| archived | `backtesting/shell_elite_v65.html` | `archive/legacy_zone_2026-06-08/backtesting/shell_elite_v65.html` | Legacy backtesting HTML with stale public-surface findings. |
| archived | `backtesting/shell_elite_v65_final.html` | `archive/legacy_zone_2026-06-08/backtesting/shell_elite_v65_final.html` | Legacy backtesting HTML with stale public-surface findings. |
| archived | `backtesting/reports/20260314_Gazprom_PJSC.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260314_Gazprom_PJSC.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/reports/20260314_Shell_plc.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260314_Shell_plc.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/reports/20260316_ASML_Holding_NV.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260316_ASML_Holding_NV.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/reports/20260316_Coolblue_BV.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260316_Coolblue_BV.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/reports/20260316_PostNL_NV.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260316_PostNL_NV.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/reports/20260317_ASR_Nederland.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260317_ASR_Nederland.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/reports/20260317_Shell_plc.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260317_Shell_plc.html` | Legacy report artifact with stale legal-entity findings. |
| archived | `backtesting/templates/report.html` | `archive/legacy_zone_2026-06-08/backtesting_templates/report.html` | Legacy template with stale legal-entity findings. |
| archived | `index.html.backup-20260325-160907.html` | `archive/legacy_zone_2026-06-08/legacy_root_backups/index.html.backup-20260325-160907.html` | Legacy root backup, not active public surface. |
| archived | `index_backup_20260325_0810.html` | `archive/legacy_zone_2026-06-08/legacy_root_backups/index_backup_20260325_0810.html` | Legacy root backup, not active public surface. |
| archived | `index_backup_20260325_0905.html` | `archive/legacy_zone_2026-06-08/legacy_root_backups/index_backup_20260325_0905.html` | Legacy root backup, not active public surface. |
| archived | `index_master_backup.html` | `archive/legacy_zone_2026-06-08/legacy_root_backups/index_master_backup.html` | Legacy root backup, not active public surface. |
| archived | `sample-report-adyen/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-adyen/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-bunq/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-bunq/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-gasunie/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-gasunie/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-getthere/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-getthere/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-mollie-gold/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-mollie-gold/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-multiselect/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-multiselect/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-nlist/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-nlist/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-postnl/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-postnl/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-shell/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-shell/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-specialist-group/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-specialist-group/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-truelegends/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-truelegends/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |
| archived | `sample-report-wise/company-intel-prompt-evaluation.json` | `archive/legacy_zone_2026-06-08/sample_report_evaluations/sample-report-wise/company-intel-prompt-evaluation.json` | Internal eval JSON, not curated public sample surface. |

## Skipped

| Status | Original path | Intended archive path | Reason |
|---|---|---|---|
| skipped | `backtesting/reports/20260526_Mollie.html` | `archive/legacy_zone_2026-06-08/backtesting/reports/20260526_Mollie.html` | `git mv` reported the source is not under version control; left in place for explicit review. |

## Known Legacy Exclusions

These files remain in place and are explicitly excluded from the legacy gate because they were not approved archive targets in this sprint:

- `index_2edcc66a.html`
- `index_2faf5765.html`
- `index_4b8a92b4.html`
- `index_aed8a4a9.html`
- `index_c75afd89.html`
- `index_gisteravond.html`
- `index_github.html`

The skipped untracked `backtesting/reports/20260526_Mollie.html` is also excluded from the legacy gate until it receives explicit target approval.

## Verification

- `python tools\public_surface_gate.py`: PASS
- `python tools\public_surface_gate.py --strict`: PASS
- `python tools\public_surface_gate.py --legacy`: PASS
