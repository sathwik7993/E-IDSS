"""Loads the E-IDSS vision model once at startup, or falls back to stub mode.

Stub mode kicks in whenever the checkpoint file is absent so the API and a
frontend can be developed against a fixed contract before training finishes
on Kaggle. Stub responses are deterministic (seeded from the uploaded image
bytes) and carry "stub_mode": true so nobody mistakes them for real scores.
"""

import hashlib
import io

import numpy as np
from PIL import Image, UnidentifiedImageError

from app import config
from app.services import imaging

_state = {
    "loaded": False,
    "stub": True,
    "device": "cpu",
    "model": None,
    "ckpt": None,
    "gradcam": None,
    "trust_gate": None,
    "transform": None,
}


def load():
    """Idempotent startup hook. Real weights load if present; else stub mode."""
    device = config.resolve_device()
    _state["device"] = device

    if not config.MODEL_WEIGHTS_PATH.exists():
        _state["loaded"] = False
        _state["stub"] = True
        return

    from ai.data import build_transforms
    from ai.explain import GradCAMPlusPlus, TrustGate
    from ai.model import load_for_inference

    model, ckpt = load_for_inference(str(config.MODEL_WEIGHTS_PATH), device=device)
    img_size = ckpt.get("img_size", config.IMG_SIZE)

    import torch

    means = ckpt["mahalanobis_means"]
    precision = ckpt["mahalanobis_precision"]
    if not torch.is_tensor(means):
        means = torch.as_tensor(means, dtype=torch.float32)
    if not torch.is_tensor(precision):
        precision = torch.as_tensor(precision, dtype=torch.float32)

    trust_gate = TrustGate(
        means=means,
        precision=precision,
        temperature=ckpt.get("temperature", 1.0),
        mahalanobis_threshold=ckpt.get("mahalanobis_threshold"),
    )

    _state.update({
        "loaded": True,
        "stub": False,
        "model": model,
        "ckpt": ckpt,
        "gradcam": GradCAMPlusPlus(model),
        "trust_gate": trust_gate,
        "transform": build_transforms(img_size, train=False),
    })


def is_loaded() -> bool:
    return _state["loaded"]


def is_stub() -> bool:
    return _state["stub"]


def device_str() -> str:
    return _state["device"]


def metrics() -> dict:
    if not _state["loaded"]:
        return {"available": False}
    return _state["ckpt"].get("metrics", {})


def _open_image(content: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"uploaded file is not a readable image: {exc}") from exc
    return image


def inspect(content: bytes, activation_threshold: float = 0.5) -> dict:
    """Run inspection on raw uploaded bytes. Raises ValueError on bad input."""
    image = _open_image(content)

    if _state["stub"]:
        return _inspect_stub(image, content, activation_threshold)
    return _inspect_real(image, activation_threshold)


def _inspect_real(image: Image.Image, activation_threshold: float = 0.5) -> dict:
    from ai.explain import heatmap_to_box

    model = _state["model"]
    device = _state["device"]
    transform = _state["transform"]
    trust_gate = _state["trust_gate"]
    gradcam = _state["gradcam"]

    model.eval()
    x = transform(image).unsqueeze(0).to(device)

    assessment = trust_gate.assess(model, x, passes=20)
    cam, _ = gradcam(x, class_idx=assessment["predicted_index"])
    bbox = heatmap_to_box(cam, threshold=activation_threshold)

    heatmap_b64 = imaging.encode_heatmap(cam)
    overlay_b64 = imaging.encode_overlay(image, cam)

    result = {k: v for k, v in assessment.items() if k != "predicted_index"}
    result.pop("mahalanobis_threshold", None)
    result["heatmap_png_base64"] = heatmap_b64
    result["overlay_png_base64"] = overlay_b64
    result["bbox"] = bbox
    result["stub_mode"] = False
    return result


def _inspect_stub(image: Image.Image, content: bytes, activation_threshold: float = 0.5) -> dict:
    from ai.data import CLASSES
    from ai.explain import heatmap_to_box

    seed = int(hashlib.sha256(content).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    predicted_idx = int(rng.integers(0, len(CLASSES)))
    alpha = np.full(len(CLASSES), 1.5)
    alpha[predicted_idx] = 6.0
    probs = rng.dirichlet(alpha)
    # Make sure the sampled distribution still peaks at predicted_idx.
    if int(np.argmax(probs)) != predicted_idx:
        probs[[predicted_idx, int(np.argmax(probs))]] = probs[[int(np.argmax(probs)), predicted_idx]]

    calibrated_confidence = float(probs[predicted_idx])
    raw_confidence = float(np.clip(calibrated_confidence + rng.normal(0, 0.03), 0.0, 1.0))
    epistemic_uncertainty = float(rng.uniform(0.0, 0.12))
    mahalanobis_distance = float(rng.uniform(0.0, 6.0))
    low_confidence = calibrated_confidence < 0.65
    novel_or_uncertain = bool(low_confidence or mahalanobis_distance > 5.0)
    predicted_class = CLASSES[predicted_idx]

    img_size = config.IMG_SIZE
    yy, xx = np.mgrid[0:img_size, 0:img_size]
    cx = int(rng.uniform(img_size * 0.25, img_size * 0.75))
    cy = int(rng.uniform(img_size * 0.25, img_size * 0.75))
    sigma = rng.uniform(img_size * 0.08, img_size * 0.2)
    cam = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2)))
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-9)

    bbox = heatmap_to_box(cam, threshold=activation_threshold)
    heatmap_b64 = imaging.encode_heatmap(cam)
    overlay_b64 = imaging.encode_overlay(image, cam)

    return {
        "predicted_class": predicted_class,
        "is_defective": predicted_class != "normal",
        "calibrated_confidence": calibrated_confidence,
        "raw_confidence": raw_confidence,
        "epistemic_uncertainty": epistemic_uncertainty,
        "mahalanobis_distance": mahalanobis_distance,
        "novel_or_uncertain": novel_or_uncertain,
        "decision": "DEFER_TO_HUMAN" if novel_or_uncertain else "AUTO",
        "class_probabilities": {CLASSES[i]: float(probs[i]) for i in range(len(CLASSES))},
        "heatmap_png_base64": heatmap_b64,
        "overlay_png_base64": overlay_b64,
        "bbox": bbox,
        "stub_mode": True,
    }
