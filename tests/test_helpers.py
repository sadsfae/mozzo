from unittest.mock import Mock


def make_mock_response(status_code=200, json_data=None, text=None):
    resp = Mock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text
    return resp


def make_service_entry(status=16, notifications_enabled=1, acknowledged=0,
                       downtime_depth=0, output="Connection refused"):
    return {
        "status": status,
        "notifications_enabled": notifications_enabled,
        "problem_has_been_acknowledged": acknowledged,
        "has_been_acknowledged": acknowledged,
        "scheduled_downtime_depth": downtime_depth,
        "plugin_output": output,
    }
