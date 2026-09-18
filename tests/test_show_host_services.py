from unittest.mock import patch

from test_helpers import make_mock_response, make_service_entry


def _host_services(services):
    def _get(url, params=None, **kwargs):
        return make_mock_response(
            json_data={"data": {"servicelist": {"host1.example.com": services}}}
        )

    return _get


def test_output_filter_no_match_message(client, capsys):
    services = {
        "PING": make_service_entry(status=2, output="OK"),
    }
    with patch.object(client.session, "get", side_effect=_host_services(services)):
        client.show_host_services("host1.example.com", output_filter="CRITICAL")

    err = capsys.readouterr().err
    assert "no services match the filter 'CRITICAL'" in err
    assert "None" not in err


def test_service_not_found_message(client, capsys):
    services = {
        "PING": make_service_entry(status=2, output="OK"),
    }
    with patch.object(client.session, "get", side_effect=_host_services(services)):
        client.show_host_services("host1.example.com", service="HTTP")

    err = capsys.readouterr().err
    assert "service 'HTTP' not found" in err


def test_output_filter_match_prints_service(client, capsys):
    services = {
        "HTTP": make_service_entry(status=16, output="down"),
        "PING": make_service_entry(status=2, output="OK"),
    }
    with patch.object(client.session, "get", side_effect=_host_services(services)):
        client.show_host_services("host1.example.com", output_filter="CRITICAL")

    out = capsys.readouterr().out
    assert "HTTP" in out
    assert "PING" not in out
