from pathlib import Path
import os
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "payment_live_readiness.ps1"


def test_payment_readiness_script_can_start_local_service_smoke():
    text = SCRIPT.read_text(encoding="utf-8", errors="ignore")

    assert "[switch]$StartLocalService" in text
    assert "[switch]$SkipLocalService" in text
    assert "[switch]$SkipSupervisor" in text
    assert "[switch]$SkipPm2" in text
    assert "-StartLocalService cannot be combined with -SkipLocalService" in text
    assert '"payment_server.py",' in text
    assert '"serve",' in text
    assert '"--host",' in text
    assert '"--port",' in text
    assert "Invoke-RestMethod -Uri $healthUrl" in text
    assert "local_payment_service_ready" in text
    assert "Stop-Process -Id $localProcess.Id -Force" in text


def test_payment_readiness_script_includes_legal_surface_gate():
    text = SCRIPT.read_text(encoding="utf-8", errors="ignore")

    assert "[switch]$SkipLegalSurface" in text
    assert "tools\\legal_launch_surface_check.py" in text
    assert "ready_for_live_payments" in text
    assert "ConvertFrom-Json" in text
    assert "MOLLIE_API_KEY" not in text
    assert "SMTP_PASS" not in text
    assert ".env" not in text
    assert "--skip-supervisor" in text
    assert "DueSight-Payment" in text
    assert "DueSight-DeliveryWorker" in text


def test_payment_readiness_require_ready_fails_when_legal_surface_is_open(tmp_path):
    db_path = tmp_path / "orders.db"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "MOLLIE_API_KEY": "test_unit_should_not_print",
            "DUESIGHT_PAYMENT_ADMIN_SECRET": "admin_unit_should_not_print",
            "DUESIGHT_EMAIL_SEND_ENABLED": "true",
            "SMTP_HOST": "smtp.test.local",
            "SMTP_USER": "docs@duesight.test",
            "SMTP_PASS": "smtp_unit_should_not_print",
        }
    )

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-SkipNetwork",
            "-SkipPm2",
            "-SkipLocalService",
            "-RequireReady",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 4
    assert "test_unit_should_not_print" not in combined
    assert "admin_unit_should_not_print" not in combined
    assert "smtp_unit_should_not_print" not in combined
    assert "terms_counsel_review_missing" in result.stdout
    assert "ready_for_live_payments" in result.stdout
