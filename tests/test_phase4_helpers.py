import pytest
from unittest.mock import Mock, patch
import datetime
import requests


def test_fetch_availability_data_service_success(client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "service": {
                "description": "HTTP",
                "time_ok": 8000,
                "time_warning": 1000,
                "time_unknown": 500,
                "time_critical": 500,
                "time_indeterminate_nodata": 0,
                "time_indeterminate_notrunning": 0,
            }
        }
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client._fetch_availability_data("test-host", service="HTTP", days=30)

    assert result is not None
    assert "percent_ok" in result
    assert "percent_warning" in result
    assert "percent_unknown" in result
    assert "percent_critical" in result
    assert result["percent_ok"] == 80.0
    assert result["percent_warning"] == 10.0
    assert result["percent_unknown"] == 5.0
    assert result["percent_critical"] == 5.0


def test_fetch_availability_data_host_success(client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "host": {
                "name": "test-host",
                "time_up": 9000,
                "time_down": 500,
                "time_unreachable": 500,
                "time_indeterminate_nodata": 0,
                "time_indeterminate_notrunning": 0,
            }
        }
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client._fetch_availability_data("test-host", service=None, days=30)

    assert result is not None
    assert "percent_up" in result
    assert "percent_down" in result
    assert "percent_unreachable" in result
    assert result["percent_up"] == 90.0
    assert result["percent_down"] == 5.0
    assert result["percent_unreachable"] == 5.0


def test_fetch_availability_data_http_error(client):
    mock_response = Mock()
    mock_response.status_code = 404

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client._fetch_availability_data("test-host", service="HTTP")

    assert result is None


def test_fetch_availability_data_request_exception(client):
    with patch.object(client.session, 'get', side_effect=requests.exceptions.RequestException("Connection error")):
        result = client._fetch_availability_data("test-host", service="HTTP")

    assert result is None


def test_fetch_availability_data_wrong_service(client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "service": {
                "description": "HTTPS",
                "time_ok": 8000,
            }
        }
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client._fetch_availability_data("test-host", service="HTTP")

    assert result is not None
    assert "_debug_raw_dump" in result


def test_fetch_availability_data_empty_response(client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {}}

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client._fetch_availability_data("test-host", service="HTTP")

    assert result is None
