def test_build_ack_payload_service(client):
    payload = client._build_ack_payload("test-host", service="HTTP")
    assert payload is not None
    assert payload["cmd_typ"] == 34
    assert payload["cmd_mod"] == 2
    assert payload["host"] == "test-host"
    assert payload["service"] == "HTTP"
    assert payload["sticky_ack"] == "on"
    assert payload["send_notification"] == "off"
    assert payload["persistent"] == "off"


def test_build_ack_payload_host(client):
    payload = client._build_ack_payload("test-host")
    assert payload is not None
    assert payload["cmd_typ"] == 33
    assert payload["cmd_mod"] == 2
    assert payload["host"] == "test-host"
    assert "service" not in payload
    assert payload["sticky_ack"] == "on"
    assert payload["send_notification"] == "off"
    assert payload["persistent"] == "off"


def test_build_downtime_payload_service(client):
    payload = client._build_downtime_payload("test-host", service="HTTP")
    assert payload is not None
    assert payload["cmd_typ"] == 56
    assert payload["cmd_mod"] == 2
    assert payload["host"] == "test-host"
    assert payload["service"] == "HTTP"
    assert payload["fixed"] == 1
    assert "start_time" in payload
    assert "end_time" in payload


def test_build_downtime_payload_host(client):
    payload = client._build_downtime_payload("test-host")
    assert payload is not None
    assert payload["cmd_typ"] == 55
    assert payload["cmd_mod"] == 2
    assert payload["host"] == "test-host"
    assert "service" not in payload
    assert payload["fixed"] == 1
    assert "start_time" in payload
    assert "end_time" in payload


def test_build_downtime_payload_all_services(client):
    payload = client._build_downtime_payload("test-host", all_services=True)
    assert payload is not None
    assert payload["cmd_typ"] == 86
    assert payload["cmd_mod"] == 2
    assert payload["host"] == "test-host"
    assert payload["service"] == "all"
    assert payload["fixed"] == 1
    assert "start_time" in payload
    assert "end_time" in payload
