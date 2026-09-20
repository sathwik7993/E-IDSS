"""Add a calibrated OOD threshold to a checkpoint that lacks one.

ai/train.py now writes `mahalanobis_threshold`, but a checkpoint produced
before that fix has no threshold, which silently reduces the trust gate to
confidence-only checking. This recomputes it locally from the validation split
so the run does not have to be repeated.

    python scripts/finalize_checkpoint.py --checkpoint models/convnext_tiny_eidss.pt
"""

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from ai.data import DefectDataset, build_transforms, stratified_split
from ai.model import DefectNet
from ai.train import calibrate_ood_threshold


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="models/convnext_tiny_eidss.pt")
    parser.add_argument("--data-root", default="train/train")
    parser.add_argument("--percentile", type=float, default=99.0)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    path = Path(args.checkpoint)
    if not path.exists():
        raise SystemExit(f"no checkpoint at {path}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(path, map_location=device, weights_only=False)
    print(f"loaded {path}  keys={sorted(ckpt)}")

    if "mahalanobis_threshold" in ckpt and ckpt["mahalanobis_threshold"] is not None:
        print(f"threshold already present: {ckpt['mahalanobis_threshold']:.4f} - nothing to do")
        return

    model = DefectNet(arch=ckpt.get("arch", "convnext_tiny"), pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()

    splits = stratified_split(Path(args.data_root), seed=ckpt.get("seed", 1337))
    img_size = ckpt.get("img_size", 224)
    loader = DataLoader(
        DefectDataset(splits["val"], build_transforms(img_size, train=False)),
        batch_size=args.batch_size, num_workers=0, pin_memory=True,
    )
    print(f"calibrating on {len(splits['val'])} validation images ({device})")

    threshold = calibrate_ood_threshold(
        model, loader, device,
        ckpt["mahalanobis_means"], ckpt["mahalanobis_precision"],
        percentile=args.percentile,
    )
    ckpt["mahalanobis_threshold"] = threshold
    torch.save(ckpt, path)
    print(f"wrote mahalanobis_threshold={threshold:.4f} (p{args.percentile}) into {path}")


if __name__ == "__main__":
    main()
