def test_get_status_text_service_ok(client):
    assert client._get_status_text(2, is_host=False) is not None
    result = client._get_status_text(2, is_host=False)
    assert "OK" in result


def test_get_status_text_service_critical(client):
    result = client._get_status_text(16, is_host=False)
    assert result is not None
    assert "CRITICAL" in result


def test_get_status_text_service_unknown_code(client):
    result = client._get_status_text(999, is_host=False)
    assert result == "[999]"


def test_get_status_text_host_up(client):
    result = client._get_status_text(2, is_host=True)
    assert result is not None
    assert "UP" in result


def test_get_status_text_host_down(client):
    result = client._get_status_text(4, is_host=True)
    assert result is not None
    assert "DOWN" in result


def test_get_status_text_host_unknown_code(client):
    result = client._get_status_text(999, is_host=True)
    assert result == "CODE_999"


def test_format_downtime_duration_minutes(client):
    client.days = None
    client.downtime_mins = 120
    result = client._format_downtime_duration()
    assert result == "120m"


def test_format_downtime_duration_days(client):
    client.days = 5
    result = client._format_downtime_duration()
    assert result == "5 days"


def test_print_toggle_action_enable(client, capsys):
    client._print_toggle_action(True, "test service")
    captured = capsys.readouterr()
    assert "Enabling notifications for test service..." in captured.out


def test_print_toggle_action_disable(client, capsys):
    client._print_toggle_action(False, "test service")
    captured = capsys.readouterr()
    assert "Disabling notifications for test service..." in captured.out


def test_matches_host_exact_fqdn(client):
    assert client._matches_host("server.example.com", "server.example.com") is True


def test_matches_host_shortname_to_fqdn(client):
    assert client._matches_host("server", "server.example.com") is True


def test_matches_host_fqdn_to_shortname(client):
    assert client._matches_host("server.example.com", "server") is True


def test_matches_host_no_match(client):
    assert client._matches_host("other.example.com", "server.example.com") is False


def test_matches_host_case_insensitive(client):
    assert client._matches_host("SERVER.EXAMPLE.COM", "server.example.com") is True
    assert client._matches_host("SERVER", "server.example.com") is True
