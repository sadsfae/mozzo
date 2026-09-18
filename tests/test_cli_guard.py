import sys

import pytest

import mozzo.cli


class _StubClient:
    """No-op client so main() dispatch succeeds without touching the network."""

    def __getattr__(self, name):
        return lambda *a, **k: None

    @property
    def report_days(self):
        return 365


@pytest.fixture
def cli_main(monkeypatch):
    monkeypatch.setattr(mozzo.cli, "MozzoNagiosClient", lambda *a, **k: _StubClient())
    return mozzo.cli.main


@pytest.fixture
def argv(monkeypatch):
    def set_argv(*args):
        _old = sys.argv
        sys.argv = ["mozzo", *args]

        def restore():
            sys.argv = _old

        return restore

    return set_argv


def test_service_without_host_errors(cli_main, argv, capsys):
    restore = argv("--disable-alerts", "--all-services")
    try:
        with pytest.raises(SystemExit) as exc:
            cli_main()
    finally:
        restore()
    assert exc.value.code == 2
    assert "--service/--all-services require --host" in capsys.readouterr().err


def test_all_services_without_host_errors(cli_main, argv, capsys):
    restore = argv("--ack", "--all-services")
    try:
        with pytest.raises(SystemExit) as exc:
            cli_main()
    finally:
        restore()
    assert exc.value.code == 2


def test_host_scoped_service_passes_guard(cli_main, argv):
    restore = argv("--ack", "--host", "h1.example.com", "--service", "HTTP")
    try:
        cli_main()
    finally:
        restore()


def test_global_toggle_passes_guard(cli_main, argv):
    restore = argv("--disable-alerts")
    try:
        cli_main()
    finally:
        restore()
