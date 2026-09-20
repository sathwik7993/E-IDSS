def test_metrics_reports_unavailable_without_weights(stub_client):
    resp = stub_client.get("/api/metrics")
    assert resp.status_code == 200
    assert resp.json() == {"available": False}


def test_metrics_reports_clean_and_robustness_when_weights_present(client):
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert "clean_test" in body
    assert "robustness" in body
    assert 0.0 <= body["clean_test"]["accuracy"] <= 1.0
    assert "defocus_blur" in body["robustness"]
