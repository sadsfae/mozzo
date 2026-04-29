import pytest


@pytest.fixture
def mock_showlog_response():
    return """
    <html>
    <body>
    <div class='logEntry'>
    <div class='logEntryType'>SERVICE ALERT</div>
    <div class='logTime'>[04-29-2026 17:32:20]</div>
    <div class='logText'>SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Connection timeout</div>
    </div>
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Connection timeout</div>
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    <div>Informational Message[04-29-2026 17:25:00] Auto-save of retention data completed successfully.</div>
    <div>State Ok[04-29-2026 17:20:00] CURRENT HOST STATE: host.example.com;UP;HARD;1;PING OK</div>
    <div>State Ok[04-29-2026 17:15:00] CURRENT SERVICE STATE: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    </body>
    </html>
    """


def test_show_logs_default_days(client, requests_mock, capsys, mock_showlog_response):
    requests_mock.get(
        f"{client.showlog_url}",
        text=mock_showlog_response,
        status_code=200
    )

    client.show_logs()

    captured = capsys.readouterr()
    assert "Nagios Log Entries" in captured.out
    assert "Last 1.0 day(s)" in captured.out


def test_show_logs_custom_days(client, requests_mock, capsys, mock_showlog_response):
    requests_mock.get(
        f"{client.showlog_url}",
        text=mock_showlog_response,
        status_code=200
    )

    client.show_logs(days=7.0)

    captured = capsys.readouterr()
    assert "Last 7.0 day(s)" in captured.out


def test_show_logs_parses_service_alerts(client, requests_mock, capsys, mock_showlog_response):
    requests_mock.get(
        f"{client.showlog_url}",
        text=mock_showlog_response,
        status_code=200
    )

    client.show_logs()

    captured = capsys.readouterr()
    assert "SERVICE ALERT" in captured.out


def test_show_logs_filters_current_state(client, requests_mock, capsys, mock_showlog_response):
    requests_mock.get(
        f"{client.showlog_url}",
        text=mock_showlog_response,
        status_code=200
    )

    client.show_logs()

    captured = capsys.readouterr()
    assert "CURRENT HOST STATE" not in captured.out
    assert "CURRENT SERVICE STATE" not in captured.out


def test_show_logs_shows_icons(client, requests_mock, capsys):
    response_with_alerts = """
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Timeout</div>
    <div>Service Ok[04-29-2026 17:30:00] SERVICE ALERT: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    <div>Service Critical[04-29-2026 17:28:00] SERVICE ALERT: host.example.com;HTTP;CRITICAL;HARD;1;Connection refused</div>
    """

    requests_mock.get(
        f"{client.showlog_url}",
        text=response_with_alerts,
        status_code=200
    )

    client.show_logs()

    captured = capsys.readouterr()
    assert "⚠️" in captured.out or "WARNING" in captured.out
    assert "✅" in captured.out or "OK" in captured.out
    assert "❌" in captured.out or "CRITICAL" in captured.out


def test_show_logs_no_entries(client, requests_mock, capsys):
    requests_mock.get(
        f"{client.showlog_url}",
        text="<html><body></body></html>",
        status_code=200
    )

    client.show_logs()

    captured = capsys.readouterr()
    assert "No log entries found" in captured.out or "No alert entries found" in captured.out


def test_show_logs_http_error(client, requests_mock, capsys):
    requests_mock.get(
        f"{client.showlog_url}",
        status_code=500
    )

    client.show_logs()

    captured = capsys.readouterr()
    assert "Error fetching logs" in captured.out


def test_show_logs_timestamp_params(client, requests_mock, mock_showlog_response):
    import datetime

    mock_request = requests_mock.get(
        f"{client.showlog_url}",
        text=mock_showlog_response,
        status_code=200
    )

    client.show_logs(days=2.0)

    assert mock_request.called
    assert 'ts_start' in mock_request.last_request.qs
    assert 'ts_end' in mock_request.last_request.qs

    ts_start = int(mock_request.last_request.qs['ts_start'][0])
    ts_end = int(mock_request.last_request.qs['ts_end'][0])

    time_diff = ts_end - ts_start
    expected_diff = 2.0 * 24 * 60 * 60

    assert abs(time_diff - expected_diff) < 5


def test_show_logs_full_flag(client, requests_mock, capsys):
    response_with_states = """
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Timeout</div>
    <div>State Ok[04-29-2026 17:20:00] CURRENT HOST STATE: host.example.com;UP;HARD;1;PING OK</div>
    <div>State Ok[04-29-2026 17:15:00] CURRENT SERVICE STATE: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    """

    requests_mock.get(
        f"{client.showlog_url}",
        text=response_with_states,
        status_code=200
    )

    client.show_logs(full=True)

    captured = capsys.readouterr()
    assert "CURRENT HOST STATE" in captured.out
    assert "CURRENT SERVICE STATE" in captured.out


def test_show_logs_without_full_flag(client, requests_mock, capsys):
    response_with_states = """
    <div>Service Warning[04-29-2026 17:32:20] SERVICE ALERT: host.example.com;HTTP;WARNING;HARD;3;Timeout</div>
    <div>State Ok[04-29-2026 17:20:00] CURRENT HOST STATE: host.example.com;UP;HARD;1;PING OK</div>
    <div>State Ok[04-29-2026 17:15:00] CURRENT SERVICE STATE: host.example.com;HTTP;OK;HARD;1;HTTP OK</div>
    """

    requests_mock.get(
        f"{client.showlog_url}",
        text=response_with_states,
        status_code=200
    )

    client.show_logs(full=False)

    captured = capsys.readouterr()
    assert "CURRENT HOST STATE" not in captured.out
    assert "CURRENT SERVICE STATE" not in captured.out
