from pathlib import Path

from scripts.generate_delta_v30_review_console import (
    HTML_PATH,
    build_guided_review_console_model,
    render_guided_review_console_html,
    write_guided_review_console,
)


def test_v30_guided_review_console_contains_required_sections():
    html = render_guided_review_console_html(build_guided_review_console_model())
    for section in (
        "Ask DELTA",
        "Answer",
        "Provenance",
        "Pipeline Trace",
        "Safety Gates",
        "Disabled Capabilities",
        "Next Recommended Action",
    ):
        assert section in html


def test_v30_guided_review_console_report_writes_static_html():
    data = write_guided_review_console()
    assert data["phase"] == "Runtime V3.0C"
    assert Path(HTML_PATH).exists()
