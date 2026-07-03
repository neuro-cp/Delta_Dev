from __future__ import annotations

import subprocess
import sys

from orchestration.runtime.v16_local_review_ui import (
    APPROVAL_TEMPLATE,
    build_local_review_dashboard_data,
    render_local_review_dashboard_html,
    validate_local_review_ui_safe,
    write_local_review_dashboard,
)
from orchestration.runtime.v16_local_review_ui_report import write_local_review_ui_report


def test_ui_generation_works_offline(tmp_path):
    data = write_local_review_dashboard(tmp_path / "dashboard.html")
    html = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert "DELTA Local Review Dashboard" in html
    assert validate_local_review_ui_safe(data, html)


def test_secrets_are_not_rendered():
    data = build_local_review_dashboard_data()
    html = render_local_review_dashboard_html(data)
    assert "sk-" not in html
    assert "API key present" in html
    assert data["env_summary"]["api_key_redacted"] is True


def test_approval_text_is_structured_and_casual_not_accepted():
    data = build_local_review_dashboard_data()
    html = render_local_review_dashboard_html(data)
    assert "APPROVE_CANONICAL_MEMORY_WRITE" in html
    assert "approval_scope=single_memory_candidate_only" in html
    assert "yeah" not in APPROVAL_TEMPLATE.lower()
    assert "looks good" not in APPROVAL_TEMPLATE.lower()


def test_ui_does_not_mutate_or_call_or_train():
    data = build_local_review_dashboard_data()
    flags = data["safety_flags"]
    assert flags["static_review_ui_enabled"] is True
    assert flags["provider_calls_enabled"] is False
    assert flags["memory_write_enabled"] is False
    assert flags["runtime_recall_mutation_enabled"] is False
    assert flags["training_enabled"] is False
    assert flags["action_execution_enabled"] is False
    assert flags["scheduler_enabled"] is False
    assert flags["model_b_default_changed"] is False
    assert flags["hyb1_default_activation_enabled"] is False
    assert flags["hyb1_promoted"] is False
    assert all(item["mutating"] is False for item in data["items"])


def test_report_generation(tmp_path, monkeypatch):
    from orchestration.runtime import v16_local_review_ui as ui_module
    from orchestration.runtime import v16_local_review_ui_report as report_module

    monkeypatch.setattr(ui_module, "DASHBOARD_HTML", tmp_path / "dashboard.html")
    monkeypatch.setattr(report_module, "DASHBOARD_HTML", tmp_path / "dashboard.html")
    monkeypatch.setattr(report_module, "REPORT_MD", tmp_path / "v16d.md")
    monkeypatch.setattr(report_module, "REPORT_JSON", tmp_path / "v16d.json")
    data = write_local_review_ui_report()
    assert data["ui_safe"] is True
    assert report_module.REPORT_MD.exists()
    assert report_module.REPORT_JSON.exists()


def test_script_generates_dashboard():
    completed = subprocess.run(
        [sys.executable, "scripts/generate_delta_review_ui.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "dashboard_path" in completed.stdout
    assert "sk-" not in completed.stdout
