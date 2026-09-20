def test_rootcause_attribute_returns_synthetic_provenance(client):
    resp = client.post("/api/rootcause", json={"defect_class": "rust", "observation": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_provenance"] == "SYNTHETIC_DEMONSTRATION"
    assert body["defect_class"] == "rust"
    assert len(body["drivers"]) > 0
    assert "narrative" in body


def test_rootcause_attribute_rejects_unknown_defect_class(client):
    resp = client.post("/api/rootcause", json={"defect_class": "not_a_class"})
    assert resp.status_code == 400


def test_rootcause_validation_recall_recovers_causal_structure(client):
    resp = client.get("/api/rootcause/validation")
    assert resp.status_code == 200
    body = resp.json()
    # SHAP should recover the constructed causal drivers reasonably well.
    assert body["mean_recall"] >= 0.5
    assert body["confounder_check"]["correctly_ranked"] is True


def test_drift_endpoint_returns_synthetic_provenance(client):
    resp = client.get("/api/drift/B-000")
    assert resp.status_code == 200
    body = resp.json()
    assert body["batch_id"] == "B-000"
    assert body["data_provenance"] == "SYNTHETIC_DEMONSTRATION"
    assert "drift_detected" in body
