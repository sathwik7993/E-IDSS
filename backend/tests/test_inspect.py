import io

from PIL import Image

EXPECTED_KEYS = {
    "part_id", "predicted_class", "is_defective", "calibrated_confidence",
    "raw_confidence", "epistemic_uncertainty", "mahalanobis_distance",
    "novel_or_uncertain", "decision", "class_probabilities",
    "heatmap_png_base64", "overlay_png_base64", "bbox", "stub_mode",
    "data_provenance",
}

CLASSES = {"crack", "hole", "normal", "rust", "scratch"}


def _png_bytes(color=(120, 120, 120)):
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_inspect_stub_mode_returns_full_contract_shape(stub_client):
    resp = stub_client.post(
        "/api/inspect",
        files={"file": ("part.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == EXPECTED_KEYS
    assert body["stub_mode"] is True
    assert body["data_provenance"] == "ORGANIZER_DATASET"
    assert body["predicted_class"] in CLASSES
    assert body["is_defective"] == (body["predicted_class"] != "normal")
    assert body["decision"] in ("AUTO", "DEFER_TO_HUMAN")
    assert 0.0 <= body["calibrated_confidence"] <= 1.0
    assert set(body["class_probabilities"].keys()) == CLASSES
    assert abs(sum(body["class_probabilities"].values()) - 1.0) < 1e-6
    assert isinstance(body["heatmap_png_base64"], str) and len(body["heatmap_png_base64"]) > 100
    assert isinstance(body["overlay_png_base64"], str) and len(body["overlay_png_base64"]) > 100
    assert body["part_id"]


def test_inspect_stub_mode_is_deterministic_per_image(stub_client):
    resp1 = stub_client.post(
        "/api/inspect",
        files={"file": ("part.png", _png_bytes((10, 20, 30)), "image/png")},
    )
    resp2 = stub_client.post(
        "/api/inspect",
        files={"file": ("part.png", _png_bytes((10, 20, 30)), "image/png")},
    )
    b1, b2 = resp1.json(), resp2.json()
    assert b1["predicted_class"] == b2["predicted_class"]
    assert b1["calibrated_confidence"] == b2["calibrated_confidence"]


def test_inspect_real_mode_returns_full_contract_shape(client):
    resp = client.post(
        "/api/inspect",
        files={"file": ("part.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == EXPECTED_KEYS
    assert body["stub_mode"] is False
    assert body["data_provenance"] == "ORGANIZER_DATASET"
    assert body["predicted_class"] in CLASSES
    assert body["decision"] in ("AUTO", "DEFER_TO_HUMAN")
    assert set(body["class_probabilities"].keys()) == CLASSES
    assert abs(sum(body["class_probabilities"].values()) - 1.0) < 1e-3


def test_inspect_real_mode_is_stable_per_image(client):
    """Real inference uses MC-dropout (20 stochastic passes) for epistemic
    uncertainty, so exact equality across calls is the wrong assertion — the
    predicted class and confidence must be stable, not bit-identical."""
    resp1 = client.post(
        "/api/inspect",
        files={"file": ("part.png", _png_bytes((10, 20, 30)), "image/png")},
    )
    resp2 = client.post(
        "/api/inspect",
        files={"file": ("part.png", _png_bytes((10, 20, 30)), "image/png")},
    )
    b1, b2 = resp1.json(), resp2.json()
    assert b1["predicted_class"] == b2["predicted_class"]
    assert abs(b1["calibrated_confidence"] - b2["calibrated_confidence"]) < 0.01


def test_inspect_rejects_non_image_upload(client):
    resp = client.post(
        "/api/inspect",
        files={"file": ("notes.txt", io.BytesIO(b"this is not an image"), "text/plain")},
    )
    assert resp.status_code == 400
