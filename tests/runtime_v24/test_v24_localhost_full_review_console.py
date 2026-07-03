from orchestration.runtime.v24_localhost_full_review_console import ROUTES, build_full_console_snapshot, validate_full_console_safe, write_static_full_console_snapshot
from orchestration.runtime.v24_localhost_full_review_console_report import write_full_console_report


def test_pages_render_offline_and_routes_present(tmp_path):
    payload = write_static_full_console_snapshot(tmp_path / "console.html")
    assert set(ROUTES).issubset(set(payload["snapshot"]["routes"]))
    assert "<html>" in payload["snapshot"]["html"]
    assert validate_full_console_safe(payload)


def test_localhost_bind_config_only():
    payload = build_full_console_snapshot()
    assert payload["bind_policy"]["host"] == "127.0.0.1"
    assert payload["decision"]["server_started"] is False


def test_external_bind_rejected_and_no_key_rendered():
    payload = build_full_console_snapshot(host="0.0.0.0")
    assert payload["bind_policy"]["external_bind_rejected"] is True
    assert payload["decision"]["api_key_rendered"] is False


def test_no_mutation_or_activation_on_render():
    flags = build_full_console_snapshot()["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["provider_call_performed"] is False
    assert flags["scheduler_started"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_full_console_report()
    assert data["all_safe"] is True

