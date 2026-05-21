from unittest.mock import Mock, patch
import requests

import pytest


def test_ack_all_services_success(client, capsys):
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 16,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Connection refused",
                    },
                    "SSH": {
                        "status": 4,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Slow response",
                    },
                },
                "host2.example.com": {
                    "Disk": {
                        "status": 8,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Unknown state",
                    },
                },
            }
        }
    }

    mock_cmd = Mock()
    mock_cmd.status_code = 200
    mock_cmd.text = "Command successfully submitted"

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post", return_value=mock_cmd
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 3
    captured = capsys.readouterr()
    assert "Acknowledged 3 service(s)" in captured.out
    assert mock_post.call_count == 3


def test_ack_all_services_no_alerting(client, capsys):
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 2,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                    }
                }
            }
        }
    }

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    captured = capsys.readouterr()
    assert "No unhandled alerting services" in captured.out
    mock_post.assert_not_called()


def test_ack_all_services_already_acknowledged(client, capsys):
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 16,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 1,
                        "has_been_acknowledged": 1,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Connection refused",
                    },
                },
            }
        }
    }

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    mock_post.assert_not_called()


def test_ack_all_services_in_downtime(client, capsys):
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 4,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 2,
                        "plugin_output": "Timeout",
                    },
                },
            }
        }
    }

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post"
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 0
    mock_post.assert_not_called()


def test_ack_all_services_notifications_disabled(client, capsys):
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 16,
                        "notifications_enabled": 0,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Connection refused",
                    },
                },
            }
        }
    }

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
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 16,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Connection refused",
                    },
                },
            }
        }
    }

    with patch.object(
        client, "_get_json", return_value=mock_status.json.return_value
    ), patch.object(
        client, "_post_cmd", side_effect=requests.HTTPError("500 Server Error")
    ):
        with pytest.raises(requests.HTTPError):
            client.acknowledge_all_alerting_services()


def test_ack_all_services_mixed_skip_and_ack(client, capsys):
    mock_status = Mock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "data": {
            "servicelist": {
                "host1.example.com": {
                    "HTTP": {
                        "status": 16,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Critical error",
                    },
                    "SSH": {
                        "status": 4,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 1,
                        "has_been_acknowledged": 1,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "Warning",
                    },
                    "DNS": {
                        "status": 4,
                        "notifications_enabled": 0,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 0,
                        "plugin_output": "DNS timeout",
                    },
                    "NTP": {
                        "status": 8,
                        "notifications_enabled": 1,
                        "problem_has_been_acknowledged": 0,
                        "has_been_acknowledged": 0,
                        "scheduled_downtime_depth": 1,
                        "plugin_output": "NTP sync failed",
                    },
                },
            }
        }
    }

    mock_cmd = Mock()
    mock_cmd.status_code = 200
    mock_cmd.text = "OK"

    with patch.object(client.session, "get", return_value=mock_status), patch.object(
        client.session, "post", return_value=mock_cmd
    ) as mock_post:
        count = client.acknowledge_all_alerting_services()

    assert count == 1
    assert mock_post.call_count == 1
    captured = capsys.readouterr()
    assert "Skipped 3 service(s)" in captured.out
