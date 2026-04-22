import pytest


def test_build_service_result_basic(client):
    details = {
        "status": 2,
        "plugin_output": "OK - test output",
        "long_plugin_output": "Long test output",
    }
    result = client._build_service_result("test-host", "HTTP", details)

    assert result is not None
    assert result["host"] == "test-host"
    assert result["service"] == "HTTP"
    assert result["status_code"] == 2
    assert "OK" in result["status"]
    assert result["plugin_output"] == "OK - test output"
    assert result["long_plugin_output"] == "Long test output"


def test_build_service_result_critical(client):
    details = {
        "status": 16,
        "plugin_output": "CRITICAL - service down",
    }
    result = client._build_service_result("web01", "MySQL", details)

    assert result is not None
    assert result["host"] == "web01"
    assert result["service"] == "MySQL"
    assert result["status_code"] == 16
    assert "CRITICAL" in result["status"]
    assert result["plugin_output"] == "CRITICAL - service down"


def test_build_service_result_missing_output(client):
    details = {"status": 4}
    result = client._build_service_result("db-server", "PostgreSQL", details)

    assert result is not None
    assert result["plugin_output"] == ""
    assert result["long_plugin_output"] == ""


def test_build_service_result_unknown_status(client):
    details = {"status": 999}
    result = client._build_service_result("test-host", "CustomCheck", details)

    assert result is not None
    assert result["status_code"] == 999
    assert result["status"] == "[999]"
