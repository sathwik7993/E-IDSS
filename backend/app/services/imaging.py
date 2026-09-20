"""Grad-CAM heatmap -> PNG base64 encoding shared by stub and real inference."""

import base64
import io

import matplotlib.cm as cm
import numpy as np
from PIL import Image


def _cam_to_rgb(cam: np.ndarray) -> np.ndarray:
    colored = cm.jet(cam)[:, :, :3]
    return (colored * 255).astype(np.uint8)


def _encode_png(array_or_image) -> str:
    if isinstance(array_or_image, np.ndarray):
        image = Image.fromarray(array_or_image)
    else:
        image = array_or_image
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def encode_heatmap(cam: np.ndarray) -> str:
    return _encode_png(_cam_to_rgb(cam))


def encode_overlay(original: Image.Image, cam: np.ndarray, alpha: float = 0.45) -> str:
    h, w = cam.shape
    base = original.convert("RGB").resize((w, h))
    heat = Image.fromarray(_cam_to_rgb(cam))
    blended = Image.blend(base, heat, alpha=alpha)
    return _encode_png(blended)
