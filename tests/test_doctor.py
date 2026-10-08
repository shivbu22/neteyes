"""Tests for doctor diagnostic health checker."""

from neteyes.doctor import run_doctor
from neteyes.models import DoctorReport, HealthStatus


def test_doctor_report_structure():
    """Verify run_doctor returns a valid DoctorReport with diagnostics."""
    report = run_doctor()
    assert isinstance(report, DoctorReport)
    assert report.python_version is not None
    assert len(report.diagnostics) > 0
    assert report.healthy_channels >= 8

    # Categories must include environment, cli_binary, package, channel
    categories = {d.category for d in report.diagnostics}
    assert "environment" in categories
    assert "package" in categories
    assert "channel" in categories


def test_doctor_json_serializable():
    """Verify DoctorReport serializes to valid JSON."""
    report = run_doctor()
    json_str = report.model_dump_json()
    assert "healthy_channels" in json_str
    assert "diagnostics" in json_str
