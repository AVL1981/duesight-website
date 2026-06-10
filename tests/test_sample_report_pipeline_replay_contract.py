import json
from pathlib import Path

from tools import sample_report_pipeline_replay as replay


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_getthere_public_target_name_is_trade_name_not_ambiguous_legal_name():
    target = replay.TARGET_BY_SLUG["sample-report-getthere"]

    assert target.company_name == "Get There ICT professionals"
    assert target.company_name != "GetThere"
    assert target.company_name != "GetThere B.V."


def test_results_from_manifests_keeps_full_summary_for_subset_replays(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "WEBSITE_DIR", tmp_path)
    targets = (
        replay.TargetConfig(slug="sample-report-one", company_name="One", domain="one.test"),
        replay.TargetConfig(slug="sample-report-two", company_name="Two", domain="two.test"),
    )
    for target in targets:
        report_dir = tmp_path / target.slug
        _write_json(
            report_dir / "pipeline-manifest.json",
            {
                "run_id": f"sample-pipeline-replay-test-{target.slug}",
                "status": "pipeline_certified_with_limitations",
                "evidence": {"row_count": 7, "source_envelope_complete": True},
            },
        )
        _write_json(report_dir / "pipeline-score.json", {"display_value": "70/100"})
        _write_json(report_dir / "evidence-ledger.json", {})

    results = replay._results_from_manifests(targets)

    assert [result["slug"] for result in results] == ["sample-report-one", "sample-report-two"]
    assert all(result["source_envelope_complete"] is True for result in results)
    assert all(result["score"] == "70/100" for result in results)
