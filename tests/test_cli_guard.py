import sys

import pytest

import mozzo.cli


class _StubClient:
    """No-op client so main() dispatch succeeds without touching the network."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _record(*a, **k):
            self.calls.append(name)

        return _record

    @property
    def report_days(self):
        return 365


@pytest.fixture
def cli_main(monkeypatch):
    stub = _StubClient()
    monkeypatch.setattr(mozzo.cli, "MozzoNagiosClient", lambda *a, **k: stub)
    return mozzo.cli.main, stub


@pytest.fixture
def argv(monkeypatch):
    def set_argv(*args):
        monkeypatch.setattr(sys, "argv", ["mozzo", *args])

    return set_argv


def test_service_without_host_errors(cli_main, argv, capsys):
    main_call, _ = cli_main
    argv("--disable-alerts", "--all-services")
    with pytest.raises(SystemExit) as exc:
        main_call()
    assert exc.value.code == 2
    assert "--service/--all-services require --host" in capsys.readouterr().err


def test_all_services_without_host_errors(cli_main, argv):
    main_call, _ = cli_main
    argv("--ack", "--all-services")
    with pytest.raises(SystemExit) as exc:
        main_call()
    assert exc.value.code == 2


def test_host_scoped_service_passes_guard(cli_main, argv):
    main_call, stub = cli_main
    argv("--ack", "--host", "h1.example.com", "--service", "HTTP")
    # Guard passed: dispatch reaches the client without raising SystemExit.
    main_call()
    assert stub.calls == ["ack_service"]


def test_global_toggle_passes_guard(cli_main, argv):
    main_call, stub = cli_main
    argv("--disable-alerts")
    # Guard passed: a bare global toggle dispatches without raising SystemExit.
    main_call()
    assert stub.calls == ["toggle_alerts"]


def test_empty_service_without_host_errors(cli_main, argv, capsys):
    main_call, _ = cli_main
    argv("--disable-alerts", "--service", "")
    with pytest.raises(SystemExit) as exc:
        main_call()
    assert exc.value.code == 2
    assert "--service/--all-services require --host" in capsys.readouterr().err


def test_global_ack_all_passes_guard(cli_main, argv):
    main_call, stub = cli_main
    argv("--ack", "--all")
    # Guard passed: --ack --all is a global action that needs no host.
    main_call()
    assert stub.calls == ["acknowledge_all_alerting_services"]


def test_ack_history_without_service_modifier_passes_guard(cli_main, argv):
    main_call, stub = cli_main
    argv("--ack-history", "--host", "h1.example.com")
    # Guard passed: host-scoped read commands are not rejected.
    main_call()
    assert stub.calls == ["show_ack_history"]


def test_read_only_status_service_without_host_passes_guard(cli_main, argv):
    main_call, stub = cli_main
    argv("--status", "--service", "HTTP")
    # Guard passed: read-only --status --service needs no host.
    main_call()
    assert stub.calls == ["show_single_service"]


def test_py36_utf8_branch_forces_utf8():
    """The 3.6 (no-reconfigure) branch must force UTF-8 on the wrapped stream."""
    import io as _io

    buf = _io.BytesIO()

    class FakePy36Stream:
        # Exposes the 3.6 surface (buffer/errors/line_buffering), no reconfigure.
        def __init__(self, buffer):
            self.buffer = buffer
            self.encoding = "ascii"
            self.errors = "strict"
            self.line_buffering = False

    fake = FakePy36Stream(buf)
    assert not hasattr(fake, "reconfigure")  # forces the buffer branch
    out = mozzo.cli._force_utf8_stdout(fake)
    assert isinstance(out, _io.TextIOWrapper)
    assert out.encoding == "utf-8"
    out.write("❌")
    out.flush()
    assert buf.getvalue() == b"\xe2\x9d\x8c"
