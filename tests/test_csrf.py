from unittest.mock import patch

import requests

from test_helpers import make_mock_response


def test_post_success(client, capsys):
    with patch.object(
        client.session,
        "post",
        return_value=make_mock_response(text="Command successfully submitted"),
    ) as mock_post:
        client._post_cmd({"cmd_typ": 33, "host": "h1", "sticky_ack": "on"})
    assert mock_post.call_count == 1
    assert "✅ Command successfully submitted" in capsys.readouterr().out


def test_post_csrf_rejection_gives_actionable_message(client, capsys):
    with patch.object(
        client.session,
        "post",
        return_value=make_mock_response(
            text="<p>Error: Invalid or missing CSRF cookie!</p>"
        ),
    ):
        client._post_cmd({"cmd_typ": 33, "host": "h1", "sticky_ack": "on"})
    out = capsys.readouterr().out
    assert "rejected by Nagios cmd.cgi CSRF check" in out
    assert "cgi_cookie_fail_open" in out


def test_post_invalid_form_id_message(client, capsys):
    with patch.object(
        client.session,
        "post",
        return_value=make_mock_response(text="<p>Error: Invalid form id!</p>"),
    ):
        client._post_cmd({"cmd_typ": 33, "host": "h1", "sticky_ack": "on"})
    out = capsys.readouterr().out
    assert "rejected by Nagios cmd.cgi CSRF check" in out


def test_post_unknown_failure_keeps_old_warning(client, capsys):
    with patch.object(
        client.session,
        "post",
        return_value=make_mock_response(text="<p>Some other error</p>"),
    ):
        client._post_cmd({"cmd_typ": 33, "host": "h1", "sticky_ack": "on"})
    out = capsys.readouterr().out
    assert "success message not found" in out


def test_post_csrf_word_alone_is_not_nagios_rejection(client, capsys):
    with patch.object(
        client.session,
        "post",
        return_value=make_mock_response(text="<p>Access denied: CSRF protection</p>"),
    ):
        client._post_cmd({"cmd_typ": 33, "host": "h1", "sticky_ack": "on"})
    out = capsys.readouterr().out
    assert "success message not found" in out
    assert "CSRF check" not in out


def test_post_http_error(client, capsys):
    def _post(url, data=None, **kwargs):
        raise requests.ConnectionError("boom")

    with patch.object(client.session, "post", side_effect=_post) as mock_post:
        client._post_cmd({"cmd_typ": 33, "host": "h1", "sticky_ack": "on"})
    assert mock_post.call_count == 1
    assert "❌ HTTP Error submitting command" in capsys.readouterr().out
