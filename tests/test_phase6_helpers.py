from unittest.mock import patch
import requests

import pytest

from test_helpers import make_mock_response


def test_show_logs_default_days(client, capsys):
    mock_response = make_mock_response(text="""
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Connection timeout</div>
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    <div>Informational Message[04-29-2026 17:25:00] Auto-save of retention data completed successfully.</div>
    <div>State Ok[04-29-2026 17:20:00] CURRENT HOST STATE: host.example.com;UP;HARD;1;PING OK</div>
    """)

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs()

    captured = capsys.readouterr()
    assert "Nagios Log Entries" in captured.out
    assert "Last 1.0 day(s)" in captured.out


def test_show_logs_custom_days(client, capsys):
    mock_response = make_mock_response(text="""
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    """)

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs(days=7.0)

    captured = capsys.readouterr()
    assert "Last 7.0 day(s)" in captured.out


def test_show_logs_parses_service_alerts(client, capsys):
    mock_response = make_mock_response(text="""
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Connection timeout</div>
    """)

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs()

    captured = capsys.readouterr()
    assert "SERVICE ALERT" in captured.out


def test_show_logs_filters_current_state(client, capsys):
    mock_response = make_mock_response(text="""
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    <div>State Ok[04-29-2026 17:20:00] CURRENT HOST STATE: host.example.com;UP;HARD;1;PING OK</div>
    <div>State Ok[04-29-2026 17:15:00] CURRENT SERVICE STATE: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    """)

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs()

    captured = capsys.readouterr()
    assert "CURRENT HOST STATE" not in captured.out
    assert "CURRENT SERVICE STATE" not in captured.out


def test_show_logs_shows_icons(client, capsys):
    mock_response = make_mock_response(text="""
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Timeout</div>
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    <div>Service Critical[04-29-2026 17:28:00] SERVICE ALERT: host.example.com;HTTP;CRITICAL;HARD;1;Connection refused</div>
    """)

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs()

    captured = capsys.readouterr()
    assert "⚠️" in captured.out or "WARNING" in captured.out
    assert "✅" in captured.out or "OK" in captured.out
    assert "❌" in captured.out or "CRITICAL" in captured.out


def test_show_logs_no_entries(client, capsys):
    mock_response = make_mock_response(text="<html><body></body></html>")

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs()

    captured = capsys.readouterr()
    assert "No log entries found" in captured.out or "No alert entries found" in captured.out


def test_show_logs_http_error(client, capsys):
    with patch.object(client.session, 'get', side_effect=requests.exceptions.RequestException("HTTP Error")):
        client.show_logs()

    captured = capsys.readouterr()
    assert "Error fetching logs" in captured.out


def test_show_logs_timestamp_params(client):
    mock_response = make_mock_response(text="""
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    """)

    with patch.object(client.session, 'get', return_value=mock_response) as mock_get:
        client.show_logs(days=2.0)

        assert mock_get.called
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs['params']

        assert 'ts_start' in params
        assert 'ts_end' in params

        ts_start = params['ts_start']
        ts_end = params['ts_end']

        time_diff = ts_end - ts_start
        expected_diff = 2.0 * 24 * 60 * 60

        assert abs(time_diff - expected_diff) < 5


FULL_FLAG_LOG_HTML = """
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Timeout</div>
    <div>State Ok[04-29-2026 17:20:00] CURRENT HOST STATE: host.example.com;UP;HARD;1;PING OK</div>
    <div>State Ok[04-29-2026 17:15:00] CURRENT SERVICE STATE: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    """


@pytest.mark.parametrize("full,expect_present", [(True, True), (False, False)],
                         ids=["full", "filtered"])
def test_show_logs_full_flag(client, capsys, full, expect_present):
    mock_response = make_mock_response(text=FULL_FLAG_LOG_HTML)

    with patch.object(client.session, 'get', return_value=mock_response):
        client.show_logs(full=full)

    captured = capsys.readouterr()
    if expect_present:
        assert "CURRENT HOST STATE" in captured.out
        assert "CURRENT SERVICE STATE" in captured.out
    else:
        assert "CURRENT HOST STATE" not in captured.out
        assert "CURRENT SERVICE STATE" not in captured.out
