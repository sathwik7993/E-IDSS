def test_line_state_returns_synthetic_provenance(client):
    resp = client.get("/api/line/state")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_provenance"] == "SYNTHETIC_DEMONSTRATION"
    assert "bottleneck_station_id" in body
    assert len(body["stations"]) == 5
