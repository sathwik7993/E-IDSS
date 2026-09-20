def test_economics_returns_synthetic_provenance_and_matches_direct_call(client):
    resp = client.get("/api/economics", params={"defect_rate": 0.08, "throughput": 240})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_provenance"] == "SYNTHETIC_DEMONSTRATION"

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ai.synthetic import unit_economics

    expected = unit_economics(0.08, 240)
    assert body == expected


def test_economics_counterfactual_adopt_when_margin_improves(client):
    # Speeding up the line with no quality penalty should improve margin -> ADOPT.
    resp = client.post(
        "/api/economics/counterfactual",
        json={
            "defect_rate": 0.05,
            "throughput": 240,
            "speed_delta_pct": 10.0,
            "defect_rate_delta_pct": 0.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_provenance"] == "SYNTHETIC_DEMONSTRATION"
    assert body["recommendation"] == "ADOPT"
    assert body["margin_delta_per_shift"] > 0


def test_economics_counterfactual_reject_when_defects_spike(client):
    # A large defect-rate spike with no throughput gain should hurt margin -> REJECT.
    resp = client.post(
        "/api/economics/counterfactual",
        json={
            "defect_rate": 0.05,
            "throughput": 240,
            "speed_delta_pct": 0.0,
            "defect_rate_delta_pct": 300.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendation"] == "REJECT"
    assert body["margin_delta_per_shift"] < 0
