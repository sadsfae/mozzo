from unittest.mock import patch

from mozzo.cli import MozzoNagiosClient

BASE_CONFIG = """
nagios_server: https://nagios.example.com
nagios_cgi_path: /nagios/cgi-bin
nagios_username: testuser
nagios_password: testpass
verify_ssl: {verify}
"""


def _write_config(tmp_path, verify):
    config_file = tmp_path / "config.yml"
    config_file.write_text(BASE_CONFIG.format(verify=verify))
    return str(config_file)


def test_disable_warnings_called_when_ssl_verification_off(tmp_path):
    config = _write_config(tmp_path, "false")
    with patch("mozzo.cli.urllib3.disable_warnings") as mock_disable:
        client = MozzoNagiosClient(config_path=config)
    assert client.verify_ssl is False
    mock_disable.assert_called_once()


def test_disable_warnings_not_called_when_ssl_verification_on(tmp_path):
    config = _write_config(tmp_path, "true")
    with patch("mozzo.cli.urllib3.disable_warnings") as mock_disable:
        client = MozzoNagiosClient(config_path=config)
    assert client.verify_ssl is True
    mock_disable.assert_not_called()
