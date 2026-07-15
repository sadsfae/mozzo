from unittest.mock import patch
import requests

import pytest

from test_helpers import make_mock_response, make_service_entry


def test_ack_all_services_success(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(status=16, output="Connection refused"),
                    "SSH": make_service_entry(status=4, output="Slow response"),
                },
                "host2.example.com": {
                    "Disk": make_service_entry(status=8, output="Unknown state"),
                },
            }
        }
    })

    mock_cmd = make_mock_response(text="Command successfully submitted")

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post", return_value=mock_cmd
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 3
    captured = capsys.readouterr()
    assert "Acknowledged 3 service(s)" in captured.out
    assert mock_post.call_count == 3


def test_ack_all_services_no_alerting(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(status=2),
                }
            }
        }
    })

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    captured = capsys.readouterr()
    assert "No unhandled alerting services" in captured.out
    mock_post.assert_not_called()


def test_ack_all_services_already_acknowledged(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(acknowledged=1),
                },
            }
        }
    })

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    mock_post.assert_not_called()


def test_ack_all_services_in_downtime(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(status=4, downtime_depth=2, output="Timeout"),
                },
            }
        }
    })

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    mock_post.assert_not_called()


def test_ack_all_services_notifications_disabled(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(notifications_enabled=0),
                },
            }
        }
    })

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    mock_post.assert_not_called()


def test_ack_all_services_http_error_on_status(client, capsys):
    with patch.object(
        client, "_get_json", side_effect=requests.HTTPError("500 Server Error")
    ):
        with pytest.raises(requests.HTTPError):
            client.acknowledge_all_alerting_services()


def test_ack_all_services_http_error_on_cmd(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(),
                },
            }
        }
    })

    with patch.object(
        client, "_get_json", return_value=mock_status.json.return_value
    ), patch.object(
        client, "_post_cmd", side_effect=requests.HTTPError("500 Server Error")
    ):
        with pytest.raises(requests.HTTPError):
            client.acknowledge_all_alerting_services()


def test_ack_all_services_mixed_skip_and_ack(client, capsys):
    mock_status = make_mock_response(json_data={
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": make_service_entry(output="Critical error"),
                    "SSH": make_service_entry(status=4, acknowledged=1, output="Warning"),
                    "DNS": make_service_entry(status=4, notifications_enabled=0, output="DNS timeout"),
                    "NTP": make_service_entry(status=8, downtime_depth=1, output="NTP sync failed"),
                },
            }
        }
    })

    mock_cmd = make_mock_response(text="OK")

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post", return_value=mock_cmd
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 1
    assert mock_post.call_count == 1
    captured = capsys.readouterr()
    assert "Skipped 3 service(s)" in captured.out
