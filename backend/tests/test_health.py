def test_health_reports_stub_mode_when_no_weights(stub_client):
    resp = stub_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False
    assert body["stub_mode"] is True
    assert body["device"] in ("cpu", "cuda")


def test_health_reports_real_mode_when_weights_present(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_loaded"] is True
    assert body["stub_mode"] is False
