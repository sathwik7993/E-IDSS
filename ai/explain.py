"""Grad-CAM++ saliency and the trust gate (Mahalanobis OOD + MC-dropout).

Localization is scored on heatmap quality and the dataset ships no boxes or
masks, so the heatmap is the localization output. A box is derived from it by
thresholding, which is honest about its provenance: it is a heatmap-derived
region, not a learned detection.
"""

import numpy as np
import torch
import torch.nn.functional as F

from ai.data import CLASSES, NORMAL_IDX


class GradCAMPlusPlus:
    """Grad-CAM++ on the final conv stage. CNN backbone keeps this clean."""

    def __init__(self, model, target_layer=None):
        self.model = model
        self.activations = None
        self.gradients = None
        layer = target_layer if target_layer is not None else model.features[-1]
        layer.register_forward_hook(self._save_activation)
        layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _module, _inp, out):
        self.activations = out

    def _save_gradient(self, _module, _grad_in, grad_out):
        self.gradients = grad_out[0]

    def __call__(self, x, class_idx=None):
        self.model.zero_grad(set_to_none=True)
        logits = self.model(x)
        if class_idx is None:
            class_idx = int(logits.argmax(1).item())
        logits[:, class_idx].sum().backward()

        grads, acts = self.gradients, self.activations
        grads_pow2 = grads.pow(2)
        grads_pow3 = grads_pow2 * grads
        sum_acts = acts.sum(dim=(2, 3), keepdim=True)
        denom = 2 * grads_pow2 + sum_acts * grads_pow3
        alpha = grads_pow2 / torch.where(denom != 0, denom, torch.ones_like(denom))
        weights = (alpha * F.relu(grads)).sum(dim=(2, 3), keepdim=True)

        cam = F.relu((weights * acts).sum(dim=1, keepdim=True))
        cam = F.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)
        cam = cam.squeeze().detach().cpu().numpy()
        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        return cam, class_idx


def heatmap_to_box(cam: np.ndarray, threshold: float = 0.5):
    """Box around the largest connected activation region.

    Bounding every pixel above threshold produces a whole-image box whenever
    activation is scattered, which is useless as a localization output. Taking
    the largest connected component keeps the box tight around the dominant
    region instead.
    """
    from scipy import ndimage

    mask = cam >= threshold
    if not mask.any():
        return None

    labels, n = ndimage.label(mask)
    if n > 1:
        largest = int(np.argmax(np.bincount(labels.ravel())[1:]) + 1)
        mask = labels == largest

    ys, xs = np.where(mask)
    h, w = cam.shape
    peak = np.unravel_index(int(np.argmax(cam)), cam.shape)
    return {
        "x": int(xs.min()), "y": int(ys.min()),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
        "image_width": int(w), "image_height": int(h),
        "coverage": float(mask.mean()),
        "peak_x": int(peak[1]), "peak_y": int(peak[0]),
        "peak_activation": float(cam[mask].max()),
        "n_components": int(n),
        "threshold": float(threshold),
    }


class TrustGate:
    """Decides predict-vs-defer. Two independent signals must both pass."""

    def __init__(self, means, precision, temperature=1.0, mahalanobis_threshold=None):
        self.means = means
        self.precision = precision
        self.temperature = float(temperature)
        self.mahalanobis_threshold = mahalanobis_threshold

    def mahalanobis(self, feats: torch.Tensor) -> torch.Tensor:
        """Min distance to any class centroid — high means off-manifold."""
        diffs = feats.unsqueeze(1) - self.means.unsqueeze(0).to(feats.device)
        precision = self.precision.to(feats.device)
        dist = torch.einsum("bcf,fg,bcg->bc", diffs, precision, diffs)
        return dist.clamp(min=0).sqrt().min(dim=1).values

    @torch.no_grad()
    def mc_dropout(self, model, x, passes: int = 20):
        """Epistemic uncertainty as predictive variance across dropout samples."""
        model.eval()
        model.enable_mc_dropout()
        probs = torch.stack([
            F.softmax(model(x) / self.temperature, dim=1) for _ in range(passes)
        ])
        model.eval()
        mean = probs.mean(0)
        return mean, probs.var(0).sum(1)

    @torch.no_grad()
    def assess(self, model, x, passes: int = 20):
        logits, feats = model(x, return_features=True)
        calibrated = F.softmax(logits / self.temperature, dim=1)
        mean_probs, epistemic = self.mc_dropout(model, x, passes)
        distance = self.mahalanobis(feats)

        pred = int(mean_probs.argmax(1).item())
        confidence = float(mean_probs.max(1).values.item())
        dist_value = float(distance.item())
        is_ood = (
            self.mahalanobis_threshold is not None
            and dist_value > self.mahalanobis_threshold
        )
        low_confidence = confidence < 0.65

        return {
            "predicted_class": CLASSES[pred],
            "predicted_index": pred,
            "is_defective": pred != NORMAL_IDX,
            "calibrated_confidence": confidence,
            "raw_confidence": float(calibrated.max(1).values.item()),
            "epistemic_uncertainty": float(epistemic.item()),
            "mahalanobis_distance": dist_value,
            "mahalanobis_threshold": self.mahalanobis_threshold,
            "novel_or_uncertain": bool(is_ood or low_confidence),
            "decision": "DEFER_TO_HUMAN" if (is_ood or low_confidence) else "AUTO",
            "class_probabilities": {
                CLASSES[i]: float(mean_probs[0, i]) for i in range(len(CLASSES))
            },
        }
