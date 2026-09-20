"""Dataset, deterministic split, and transforms for E-IDSS.

The split is derived from sorted filenames + a fixed seed so that the local
machine and the Kaggle trainer produce byte-identical train/val/test sets
without shipping manifests between them.
"""

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

CLASSES = ["crack", "hole", "normal", "rust", "scratch"]
DEFECT_CLASSES = [c for c in CLASSES if c != "normal"]
NORMAL_IDX = CLASSES.index("normal")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def stratified_split(root: Path, seed: int = 1337, val_frac: float = 0.15, test_frac: float = 0.15):
    """Return {split: [(path, label_idx)]}, stratified per class and reproducible."""
    rng = np.random.default_rng(seed)
    out = {"train": [], "val": [], "test": []}

    for label_idx, cls in enumerate(CLASSES):
        files = sorted((root / cls).glob("*.png"))
        if not files:
            raise FileNotFoundError(f"no images found in {root / cls}")
        idx = rng.permutation(len(files))
        n_val = int(len(files) * val_frac)
        n_test = int(len(files) * test_frac)

        for split, chunk in (
            ("val", idx[:n_val]),
            ("test", idx[n_val : n_val + n_test]),
            ("train", idx[n_val + n_test :]),
        ):
            out[split].extend((files[i], label_idx) for i in chunk)

    for split in out:
        out[split].sort(key=lambda pair: str(pair[0]))
    return out


def build_transforms(img_size: int = 224, train: bool = False):
    # Source images are 256x256 grayscale; replicate to 3ch so ImageNet-pretrained
    # weights stay usable, then normalise with the standard statistics.
    to_rgb = transforms.Grayscale(num_output_channels=3)

    if train:
        return transforms.Compose([
            to_rgb,
            transforms.RandomResizedCrop(img_size, scale=(0.75, 1.0), ratio=(0.9, 1.11)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomApply([transforms.RandomRotation(20)], p=0.5),
            transforms.ColorJitter(brightness=0.3, contrast=0.3),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(p=0.25, scale=(0.02, 0.12)),
        ])

    return transforms.Compose([
        to_rgb,
        transforms.Resize(img_size + 32),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


class DefectDataset(Dataset):
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        image = Image.open(path)
        return self.transform(image), label


def binary_targets(labels: torch.Tensor) -> torch.Tensor:
    """1 = defective, 0 = acceptable. Drives false-accept / false-reject metrics."""
    return (labels != NORMAL_IDX).long()
