import builtins

import pytest

from mozzo.cli import (
    MozzoNagiosClient,
    ProxyError,
    build_proxy_map,
    normalize_proxy,
    redact_proxy,
)

BASE_CONFIG = """
nagios_server: https://nagios.example.com
nagios_cgi_path: /nagios/cgi-bin
nagios_username: testuser
nagios_password: testpass
proxy: {proxy}
"""


def _write_config(tmp_path, proxy=""):
    config_file = tmp_path / "config.yml"
    config_file.write_text(BASE_CONFIG.format(proxy=proxy))
    return str(config_file)


def test_normalize_proxy():
    assert normalize_proxy("") == ""
    assert normalize_proxy(None) == ""
    assert normalize_proxy("  socks5h://127.0.0.1:1080  ") == (
        "socks5h://127.0.0.1:1080"
    )
    assert normalize_proxy("none") == ""
    assert normalize_proxy("-") == ""


def test_build_proxy_map_covers_http_and_https():
    assert build_proxy_map("http://10.0.0.1:3128") == {
        "http": "http://10.0.0.1:3128",
        "https": "http://10.0.0.1:3128",
    }


def test_build_proxy_map_empty():
    assert build_proxy_map("") == {}


def test_build_proxy_map_keeps_userinfo():
    proxy = "http://user:pass@10.0.0.1:3128"
    assert build_proxy_map(proxy) == {"http": proxy, "https": proxy}


def test_build_proxy_map_unsupported_scheme():
    with pytest.raises(ProxyError, match="Unsupported proxy scheme 'ftp'"):
        build_proxy_map("ftp://127.0.0.1:1080")


def test_build_proxy_map_missing_host():
    with pytest.raises(ProxyError, match="must include a host and port"):
        build_proxy_map("socks5h://:1080")


def test_build_proxy_map_missing_port():
    with pytest.raises(ProxyError, match="must include a host and port"):
        build_proxy_map("socks5h://127.0.0.1")


def test_build_proxy_map_invalid_port():
    with pytest.raises(ProxyError, match="invalid port"):
        build_proxy_map("socks5h://127.0.0.1:notaport")


def test_build_proxy_map_malformed_ipv6():
    with pytest.raises(ProxyError, match="Invalid proxy URL"):
        build_proxy_map("socks5h://user:secret@[::1")


def test_build_proxy_map_socks_requires_pysocks(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "socks":
            raise ImportError("No module named 'socks'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ProxyError, match="PySocks"):
        build_proxy_map("socks5h://127.0.0.1:1080")


def test_redact_proxy_strips_userinfo():
    assert redact_proxy("http://user:secret@10.0.0.1:3128") == "http://10.0.0.1:3128"
    assert redact_proxy("socks5h://user:p@ss@127.0.0.1:1080") == (
        "socks5h://127.0.0.1:1080"
    )
    assert redact_proxy("127.0.0.1:1080") == "127.0.0.1:1080"


def test_client_wires_proxy_into_session(tmp_path):
    config = _write_config(tmp_path, "socks5h://127.0.0.1:1080")
    client = MozzoNagiosClient(config_path=config)
    assert client.session.proxies == {
        "http": "socks5h://127.0.0.1:1080",
        "https": "socks5h://127.0.0.1:1080",
    }
    assert client.session.trust_env is False


def test_client_without_proxy_leaves_session_alone(tmp_path):
    config = _write_config(tmp_path, "")
    client = MozzoNagiosClient(config_path=config)
    assert client.session.proxies == {}
    assert client.session.trust_env is True


def test_client_proxy_uses_env_ca_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/tmp/my-ca.pem")
    config = _write_config(tmp_path, "http://10.0.0.1:3128")
    client = MozzoNagiosClient(config_path=config)
    assert client.verify_ssl == "/tmp/my-ca.pem"


def test_client_proxy_does_not_override_explicit_verify_false(tmp_path, monkeypatch):
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/tmp/my-ca.pem")
    config_file = _write_config(tmp_path, "http://10.0.0.1:3128")
    with open(config_file, "a") as f:
        f.write("verify_ssl: false\n")
    client = MozzoNagiosClient(config_path=config_file)
    assert client.verify_ssl is False


def test_client_invalid_proxy_exits(tmp_path, capsys):
    config = _write_config(tmp_path, "ftp://127.0.0.1:1080")
    with pytest.raises(SystemExit) as exc:
        MozzoNagiosClient(config_path=config)
    assert exc.value.code == 1
    assert "Unsupported proxy scheme 'ftp'" in capsys.readouterr().out


def test_client_non_string_proxy_exits(tmp_path, capsys):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "nagios_server: https://nagios.example.com\nproxy: true\n"
    )
    with pytest.raises(SystemExit) as exc:
        MozzoNagiosClient(config_path=str(config_file))
    assert exc.value.code == 1
    assert "must be a proxy URL string" in capsys.readouterr().out


def test_client_proxy_error_redacts_credentials(tmp_path, capsys):
    config = _write_config(tmp_path, "http://user:secret@:3128")
    with pytest.raises(SystemExit):
        MozzoNagiosClient(config_path=config)
    out = capsys.readouterr().out
    assert "secret" not in out
