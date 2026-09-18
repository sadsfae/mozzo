from unittest.mock import patch

from test_helpers import make_mock_response, make_service_entry


def _dispatch_get(servicelist, host_data=None):
    """Return a session.get side_effect that dispatches on the query param."""

    def _get(url, params=None, **kwargs):
        params = params or {}
        if params.get("query") == "host":
            return make_mock_response(json_data={"data": {"host": host_data or {}}})
        return make_mock_response(json_data={"data": {"servicelist": servicelist}})

    return _get


def test_show_service_issues_includes_handled(client, capsys):
    servicelist = {
        "host1.example.com": {
            "HTTP": make_service_entry(status=16, output="down"),
            "SSH": make_service_entry(status=4, acknowledged=1, output="ack'd"),
            "OK-svc": make_service_entry(status=2),
        }
    }
    with patch.object(client.session, "get", side_effect=_dispatch_get(servicelist)):
        client.show_service_issues()

    out = capsys.readouterr().out
    assert "host1.example.com:" in out
    # Both the critical and the already-acknowledged warning are listed.
    assert "for service: HTTP" in out
    assert "for service: SSH" in out
    # OK service is never an issue.
    assert "OK-svc" not in out


def test_show_service_issues_none(client, capsys):
    servicelist = {"host1.example.com": {"OK-svc": make_service_entry(status=2)}}
    with patch.object(client.session, "get", side_effect=_dispatch_get(servicelist)):
        client.show_service_issues()
    assert "No service issues found" in capsys.readouterr().out


def test_show_unhandled_skips_handled(client, capsys):
    servicelist = {
        "host1.example.com": {
            "HTTP": make_service_entry(status=16, output="real problem"),
            "SSH": make_service_entry(status=4, acknowledged=1, output="handled"),
        }
    }
    host_data = {"notifications_enabled": 1, "scheduled_downtime_depth": 0}
    with patch.object(
        client.session, "get", side_effect=_dispatch_get(servicelist, host_data)
    ):
        client.show_unhandled()

    out = capsys.readouterr().out
    assert "host1.example.com -> HTTP" in out
    assert "SSH" not in out


def test_show_unhandled_none(client, capsys):
    servicelist = {
        "host1.example.com": {
            "SSH": make_service_entry(status=4, acknowledged=1),
        }
    }
    with patch.object(client.session, "get", side_effect=_dispatch_get(servicelist)):
        client.show_unhandled()
    assert "No unhandled service alerts found" in capsys.readouterr().out
