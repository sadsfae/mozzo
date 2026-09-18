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
        monkeypatch.setattr(sys, "argv", ["mozzo", *args])

    return set_argv


def test_service_without_host_errors(cli_main, argv, capsys):
    argv("--disable-alerts", "--all-services")
    with pytest.raises(SystemExit) as exc:
        cli_main()
    assert exc.value.code == 2
    assert "--service/--all-services require --host" in capsys.readouterr().err


def test_all_services_without_host_errors(cli_main, argv):
    argv("--ack", "--all-services")
    with pytest.raises(SystemExit) as exc:
        cli_main()
    assert exc.value.code == 2


def test_host_scoped_service_passes_guard(cli_main, argv):
    argv("--ack", "--host", "h1.example.com", "--service", "HTTP")
    # Guard passed: dispatch reaches the client without raising SystemExit.
    cli_main()


def test_global_toggle_passes_guard(cli_main, argv):
    argv("--disable-alerts")
    # Guard passed: a bare global toggle dispatches without raising SystemExit.
    cli_main()


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
