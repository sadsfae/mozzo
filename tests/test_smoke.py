def test_client_initialization(client):
    assert client is not None
    assert client.server == "https://nagios.example.com"
    assert client.downtime_mins == 120
    assert client.report_days == 365


def test_status_maps_exist(client):
    assert hasattr(client, 'SERVICE_STATUS_MAP')
    assert hasattr(client, 'HOST_STATUS_MAP')
    assert hasattr(client, 'FILTER_MAP')
    assert 2 in client.SERVICE_STATUS_MAP
    assert 2 in client.HOST_STATUS_MAP


def test_config_loading(mock_config_file):
    from mozzo.cli import MozzoNagiosClient
    client = MozzoNagiosClient(config_path=mock_config_file)
    assert client.auth == ('testuser', 'testpass')
    assert client.verify_ssl is False
