import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from mozzo.cli import MozzoNagiosClient  # noqa: E402


@pytest.fixture
def mock_config_file(tmp_path):
    config_content = """
nagios_server: https://nagios.example.com
nagios_cgi_path: /nagios/cgi-bin
nagios_username: testuser
nagios_password: testpass
default_downtime: 120
default_reporting_days: 365
verify_ssl: false
date_format: "%m-%d-%Y %H:%M:%S"
"""
    config_file = tmp_path / "config.yml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def client(mock_config_file):
    return MozzoNagiosClient(config_path=mock_config_file)
