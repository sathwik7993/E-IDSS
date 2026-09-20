"""Backbone wrapper exposing logits and penultimate features.

The features are needed twice downstream: for the Mahalanobis OOD gate and for
Grad-CAM++ saliency, so the model returns them rather than hiding them.
"""

import torch
import torch.nn as nn
from torchvision import models

from ai.data import CLASSES


class DefectNet(nn.Module):
    def __init__(self, arch: str = "convnext_tiny", num_classes: int = len(CLASSES), pretrained: bool = True):
        super().__init__()
        self.arch = arch

        if arch == "convnext_tiny":
            weights = models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1 if pretrained else None
            net = models.convnext_tiny(weights=weights)
            self.features = net.features
            self.norm = net.classifier[0]
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.feat_dim = net.classifier[2].in_features
        elif arch == "efficientnet_v2_s":
            weights = models.EfficientNet_V2_S_Weights.IMAGENET1K_V1 if pretrained else None
            net = models.efficientnet_v2_s(weights=weights)
            self.features = net.features
            self.norm = nn.Identity()
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.feat_dim = net.classifier[1].in_features
        else:
            raise ValueError(f"unsupported arch {arch!r}")

        self.dropout = nn.Dropout(p=0.3)
        self.head = nn.Linear(self.feat_dim, num_classes)

    def forward_features(self, x):
        """Spatial feature map — Grad-CAM++ hooks here."""
        return self.features(x)

    def forward(self, x, return_features: bool = False):
        fmap = self.features(x)
        pooled = self.pool(self.norm(fmap)).flatten(1)
        logits = self.head(self.dropout(pooled))
        if return_features:
            return logits, pooled
        return logits

    def enable_mc_dropout(self):
        """Keep dropout active at eval time for epistemic uncertainty sampling."""
        self.dropout.train()


def load_for_inference(checkpoint_path, device="cuda"):
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = DefectNet(arch=ckpt.get("arch", "convnext_tiny"), pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()
    return model, ckpt
