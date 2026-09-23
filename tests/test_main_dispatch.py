"""Drive mozzo.cli.main() end to end for the argparse dispatch layer.

Patches requests.Session.get/post at the class level (main() builds its own
client) and sets sys.argv, mirroring the fixture-plus-capsys approach in
tests/test_ack_all_services.py.
"""

import datetime
import sys
from unittest.mock import patch

import pytest

from mozzo.cli import main
from test_helpers import make_mock_response, make_service_entry

RECENT_TS = 1_600_000_000
# Comment timestamp inside the default 365-day reporting window so the
# ack-history formatting path is actually reached (not filtered out).
COMMENT_TS = int(datetime.datetime.now().timestamp())

SERVICELIST = {
    "host1.example.com": {
        "HTTP": make_service_entry(status=16, output="Connection refused"),
        "PING": make_service_entry(status=2, output="OK"),
    }
}

HOST_DATA = {
    "status": 4,
    "notifications_enabled": 1,
    "scheduled_downtime_depth": 0,
    "problem_has_been_acknowledged": 0,
    "plugin_output": "host down",
    "last_state_change": RECENT_TS,
}

SERVICE_DATA = {
    "status": 16,
    "plugin_output": "crit",
    "last_state_change": RECENT_TS,
}

PROGRAMSTATUS = {
    "enable_notifications": 1,
    "execute_service_checks": 1,
    "execute_host_checks": 0,
    "enable_event_handlers": 1,
}

COMMENTLIST = {
    "1": {
        "entry_type": 4,
        "entry_time": COMMENT_TS,
        "host_name": "host1.example.com",
        "service_description": "",
        "author": "admin",
        "comment_data": "acked by admin",
    },
    "2": {
        "entry_type": 4,
        "entry_time": COMMENT_TS,
        "host_name": "host1.example.com",
        "service_description": "HTTP",
        "author": "admin",
        "comment_data": "acked by admin svc",
    },
}

HOST_AVAILABILITY = {
    "host_name": "host1.example.com",
    "name": "host1.example.com",
    "time_up": 90,
    "time_down": 10,
    "time_unreachable": 0,
    "time_indeterminate_nodata": 0,
    "time_indeterminate_notrunning": 0,
}

SERVICE_AVAILABILITY = {
    "description": "HTTP",
    "time_ok": 80,
    "time_warning": 5,
    "time_unknown": 5,
    "time_critical": 10,
    "time_indeterminate_nodata": 0,
    "time_indeterminate_notrunning": 0,
}

LOG_TEXT = (
    "[09-18-2026 10:00:00] SERVICE ALERT: host1;HTTP;CRITICAL;HARD;1;down\n"
    "[09-18-2026 10:05:00] CURRENT HOST STATE: host1;UP;HARD;1;ok\n"
)


def fake_get(url, params=None, **kwargs):
    params = params or {}
    if "archivejson" in url:
        if params.get("availabilityobjecttype") == "services":
            return make_mock_response(
                json_data={"data": {"service": SERVICE_AVAILABILITY}}
            )
        return make_mock_response(json_data={"data": {"host": HOST_AVAILABILITY}})
    if "showlog" in url:
        return make_mock_response(text=LOG_TEXT)

    query = params.get("query")
    if query == "servicelist":
        return make_mock_response(json_data={"data": {"servicelist": SERVICELIST}})

    payloads = {
        "programstatus": {"data": {"programstatus": PROGRAMSTATUS}},
        "host": {"data": {"host": HOST_DATA}},
        "hostlist": {"data": {"hostlist": {HOST: HOST_DATA}}},
        "service": {"data": {"service": SERVICE_DATA}},
        "commentlist": {"data": {"commentlist": COMMENTLIST}},
    }
    return make_mock_response(json_data=payloads.get(query, {"data": {}}))


def fake_post(url, **kwargs):
    return make_mock_response(text="Command successfully submitted")


def make_post_recorder():
    """Return (calls, side_effect) where calls collects each posted payload."""
    calls = []

    def _post(url, **kwargs):
        calls.append(kwargs.get("data", {}))
        return make_mock_response(text="Command successfully submitted")

    return calls, _post


def run_main(argv, config, monkeypatch, post=fake_post):
    monkeypatch.setattr(sys, "argv", ["mozzo", "-c", config] + argv)
    with patch("requests.Session.get", side_effect=fake_get), patch(
        "requests.Session.post", side_effect=post
    ):
        main()


# (argv, expected substring) asserting DATA-DERIVED output, not just a header,
# so a gutted command method would fail the test.
READ_CASES = [
    # execute_host_checks=0 in PROGRAMSTATUS -> DISABLED row.
    (["--status"], "❌ DISABLED"),
    # A service row (from results, printed after the fetch).
    (["--status", "--host", "host1.example.com"], "HTTP"),
    (["--status", "--service", "HTTP"], "host1.example.com"),
    # Availability percentages computed from the archivejson mock.
    (["--status", "--host", "host1.example.com", "--uptime"], "90.000%"),
    (
        ["--status", "--host", "host1.example.com", "--service", "HTTP", "--uptime"],
        "80.000%",
    ),
    (["--unhandled"], "host1.example.com -> HTTP"),
    (["--service-issues"], "for service: HTTP"),
    (["--service-issues", "--host", "host1.example.com"], "for service: HTTP"),
    # Filtered output keeps only CRITICAL rows.
    (
        ["--status", "--host", "host1.example.com", "--output-filter", "CRITICAL"],
        "HTTP",
    ),
    (
        ["--status", "--host", "host1.example.com", "--format", "csv"],
        "host,service,status_code,status",
    ),
    # Comment formatting path (author/comment) is reached only with a
    # timestamp inside the reporting window.
    (["--ack-history", "--host", "host1.example.com"], "acked by admin"),
    (
        ["--ack-history", "--host", "host1.example.com", "--service", "HTTP"],
        "acked by admin svc",
    ),
    # Alert line survives the default (non-full) state-dump filter.
    (["--log"], "SERVICE ALERT"),
    # CURRENT STATE dumps appear only with --full.
    (["--log", "--full"], "CURRENT HOST STATE"),
]


@pytest.mark.parametrize("argv,expected", READ_CASES)
def test_main_read_commands(argv, expected, mock_config_file, monkeypatch, capsys):
    run_main(argv, mock_config_file, monkeypatch)
    assert expected in capsys.readouterr().out


def test_main_log_default_hides_state_dumps(mock_config_file, monkeypatch, capsys):
    run_main(["--log"], mock_config_file, monkeypatch)
    assert "CURRENT HOST STATE" not in capsys.readouterr().out


# (argv, cmd_typ, host, service) for the payload the command must post.
# cmd_typ identifies the exact Nagios command (catches dispatch swaps and
# enable/disable inversions); host/service pin that it targets the right
# object (catches a right-command-to-wrong-target bug). None means the key
# must be absent from the payload.
HOST = "host1.example.com"
POST_CASES = [
    (["--ack", "--host", HOST], 33, HOST, None),
    (["--ack", "--host", HOST, "--service", "HTTP"], 34, HOST, "HTTP"),
    (["--ack", "--host", HOST, "--all-services"], 33, HOST, None),
    # --ack --all now acks the host problem (33) as well as services (34).
    (["--ack", "--all"], 34, HOST, "HTTP"),
    (["--ack", "--all"], 33, HOST, None),
    (["--downtime", "--host", HOST], 55, HOST, None),
    (["--downtime", "--host", HOST, "--service", "HTTP"], 56, HOST, "HTTP"),
    (["--downtime", "--host", HOST, "--all-services"], 86, HOST, "all"),
    (["--enable-alerts"], 12, None, None),
    (["--disable-alerts"], 11, None, None),
    (["--disable-alerts", "--host", HOST], 25, HOST, None),
    (["--disable-alerts", "--host", HOST, "--service", "HTTP"], 23, HOST, "HTTP"),
    (["--enable-alerts", "--host", HOST, "--service", "HTTP"], 22, HOST, "HTTP"),
    (["--enable-alerts", "--host", HOST, "--all-services"], 28, HOST, None),
]


@pytest.mark.parametrize("argv,cmd_typ,exp_host,exp_service", POST_CASES)
def test_main_post_commands(
    argv, cmd_typ, exp_host, exp_service, mock_config_file, monkeypatch, capsys
):
    calls, recorder = make_post_recorder()
    run_main(argv, mock_config_file, monkeypatch, post=recorder)
    assert "successfully submitted" in capsys.readouterr().out

    matching = [p for p in calls if p.get("cmd_typ") == cmd_typ]
    assert matching, (
        f"no payload with cmd_typ={cmd_typ}; "
        f"sent {[p.get('cmd_typ') for p in calls]}"
    )
    assert any(
        p.get("host") == exp_host and p.get("service") == exp_service for p in matching
    ), f"cmd_typ={cmd_typ} posted to wrong target: {matching}"


def test_main_no_args_prints_help(mock_config_file, monkeypatch, capsys):
    run_main([], mock_config_file, monkeypatch)
    assert "usage: mozzo" in capsys.readouterr().out


def test_main_ack_all_with_service_errors(mock_config_file, monkeypatch, capsys):
    # --host is supplied so the require-host guard passes and dispatch reaches
    # the --all/--service mutual-exclusion check.
    with pytest.raises(SystemExit):
        run_main(
            ["--ack", "--all", "--service", "HTTP", "--host", "host1.example.com"],
            mock_config_file,
            monkeypatch,
        )
    assert "cannot be combined" in capsys.readouterr().err


def test_main_json_format(mock_config_file, monkeypatch, capsys):
    run_main(
        ["--status", "--host", "host1.example.com", "--format", "json"],
        mock_config_file,
        monkeypatch,
    )
    assert '"host": "host1.example.com"' in capsys.readouterr().out
