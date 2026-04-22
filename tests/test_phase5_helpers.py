import pytest
import json


def test_print_uptime_report_service_json(client, capsys):
    report_data = {
        "host": "test-host",
        "service": "HTTP",
        "status": "OK",
        "duration": "5d 3h",
        "output": "All good",
        "availability_days": 30,
        "percent_ok": 95.5,
        "percent_warning": 2.5,
        "percent_unknown": 1.0,
        "percent_critical": 1.0,
    }

    client._print_uptime_report(report_data, "json", is_host=False)
    captured = capsys.readouterr()

    assert "test-host" in captured.out
    assert "HTTP" in captured.out
    json_output = json.loads(captured.out)
    assert json_output["percent_ok"] == 95.5


def test_print_uptime_report_service_text(client, capsys):
    report_data = {
        "host": "test-host",
        "service": "HTTP",
        "status": "OK",
        "duration": "5d 3h",
        "output": "All good",
        "availability_days": 30,
        "percent_ok": 95.5,
        "percent_warning": 2.5,
        "percent_unknown": 1.0,
        "percent_critical": 1.0,
    }

    client._print_uptime_report(report_data, "text", is_host=False)
    captured = capsys.readouterr()

    assert "Status & Uptime: 'HTTP' on 'test-host'" in captured.out
    assert "Status        : OK" in captured.out
    assert "30-Day Availability Report" in captured.out
    assert "95.500%" in captured.out


def test_print_uptime_report_host_json(client, capsys):
    report_data = {
        "host": "web01",
        "status": "UP",
        "duration": "30d 5h",
        "output": "Ping OK",
        "availability_days": 365,
        "percent_up": 99.9,
        "percent_down": 0.05,
        "percent_unreachable": 0.05,
    }

    client._print_uptime_report(report_data, "json", is_host=True)
    captured = capsys.readouterr()

    json_output = json.loads(captured.out)
    assert json_output["host"] == "web01"
    assert json_output["percent_up"] == 99.9


def test_print_uptime_report_host_text(client, capsys):
    report_data = {
        "host": "web01",
        "status": "UP",
        "duration": "30d 5h",
        "output": "Ping OK",
        "availability_days": 365,
        "percent_up": 99.9,
        "percent_down": 0.05,
        "percent_unreachable": 0.05,
    }

    client._print_uptime_report(report_data, "text", is_host=True)
    captured = capsys.readouterr()

    assert "Host Status & Uptime: 'web01'" in captured.out
    assert "Status        : UP" in captured.out
    assert "365-Day Availability Report" in captured.out
    assert "99.900%" in captured.out


def test_print_uptime_report_csv(client, capsys):
    report_data = {
        "host": "test-host",
        "service": "HTTP",
        "status": "OK",
        "percent_ok": 95.5,
    }

    client._print_uptime_report(report_data, "csv", is_host=False)
    captured = capsys.readouterr()

    assert "host,service,status,percent_ok" in captured.out
    assert "test-host,HTTP,OK,95.5" in captured.out


def test_print_uptime_report_no_availability(client, capsys):
    report_data = {
        "host": "test-host",
        "service": "HTTP",
        "status": "OK",
        "duration": "1d",
        "output": "OK",
        "availability_days": 30,
        "percent_ok": None,
    }

    client._print_uptime_report(report_data, "text", is_host=False)
    captured = capsys.readouterr()

    assert "Status & Uptime" in captured.out
    assert "Availability Report" in captured.out
    assert "95.500%" not in captured.out
