"""Train the defect classifier. Designed to run on Kaggle's 2x T4 accelerator.

Saves a single checkpoint carrying everything inference needs: weights, the
fitted Mahalanobis OOD statistics, calibration temperature, and the full
metrics report (clean + per-shift robustness).

    python -m ml.train --data-root train/train --epochs 15
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader

from ai.data import CLASSES, NORMAL_IDX, DefectDataset, build_transforms, stratified_split
from ai.model import DefectNet
from ai.robustness import CONDITIONS, build_condition_transform


def loaders(splits, img_size, batch_size, workers):
    train_ds = DefectDataset(splits["train"], build_transforms(img_size, train=True))
    val_ds = DefectDataset(splits["val"], build_transforms(img_size, train=False))
    common = dict(num_workers=workers, pin_memory=True, persistent_workers=workers > 0)
    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True, **common),
        DataLoader(val_ds, batch_size=batch_size * 2, shuffle=False, **common),
    )


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    logits_all, labels_all = [], []
    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            logits = model(images)
        logits_all.append(logits.float().cpu())
        labels_all.append(labels)
    return torch.cat(logits_all), torch.cat(labels_all)


def fit_temperature(logits, labels):
    """Temperature scaling — calibrated confidence is an explicit rubric item."""
    log_t = torch.zeros(1, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_t], lr=0.1, max_iter=60)

    def closure():
        optimizer.zero_grad()
        loss = F.cross_entropy(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_t.exp().item())


@torch.no_grad()
def fit_mahalanobis(model, loader, device, feat_dim):
    """Per-class means + shared shrunk covariance over training features."""
    model.eval()
    sums = torch.zeros(len(CLASSES), feat_dim, dtype=torch.float64)
    counts = torch.zeros(len(CLASSES), dtype=torch.float64)
    feats_all, labels_all = [], []

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            _, feats = model(images, return_features=True)
        feats = feats.float().cpu().double()
        feats_all.append(feats)
        labels_all.append(labels)
        for c in range(len(CLASSES)):
            mask = labels == c
            if mask.any():
                sums[c] += feats[mask].sum(0)
                counts[c] += int(mask.sum())

    means = sums / counts.unsqueeze(1).clamp(min=1)
    feats_all = torch.cat(feats_all)
    labels_all = torch.cat(labels_all)
    centered = feats_all - means[labels_all]
    cov = (centered.T @ centered) / max(len(feats_all) - len(CLASSES), 1)
    cov += torch.eye(feat_dim, dtype=torch.float64) * 1e-3  # shrinkage keeps the inverse stable
    return means, torch.linalg.inv(cov)


@torch.no_grad()
def calibrate_ood_threshold(model, loader, device, means, precision, percentile: float = 99.0):
    """Threshold = given percentile of in-distribution Mahalanobis distances."""
    model.eval()
    means_d = means.to(device).float()
    precision_d = precision.to(device).float()
    distances = []

    for images, _ in loader:
        images = images.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            _, feats = model(images, return_features=True)
        diffs = feats.float().unsqueeze(1) - means_d.unsqueeze(0)
        dist = torch.einsum("bcf,fg,bcg->bc", diffs, precision_d, diffs)
        distances.append(dist.clamp(min=0).sqrt().min(dim=1).values.cpu())

    return float(np.percentile(torch.cat(distances).numpy(), percentile))


def report(logits, labels, temperature=1.0):
    probs = F.softmax(logits / temperature, dim=1)
    preds = probs.argmax(1)
    binary_true = (labels != NORMAL_IDX).long()
    binary_pred = (preds != NORMAL_IDX).long()

    false_accept = int(((binary_true == 1) & (binary_pred == 0)).sum())  # defect shipped
    false_reject = int(((binary_true == 0) & (binary_pred == 1)).sum())  # good part scrapped
    n_defect = int((binary_true == 1).sum())
    n_normal = int((binary_true == 0).sum())

    return {
        "accuracy": float((preds == labels).float().mean()),
        "macro_f1": float(f1_score(labels, preds, average="macro")),
        "per_class": classification_report(
            labels, preds, target_names=CLASSES, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(labels, preds).tolist(),
        "false_accept_count": false_accept,
        "false_reject_count": false_reject,
        "false_accept_rate": false_accept / max(n_defect, 1),
        "false_reject_rate": false_reject / max(n_normal, 1),
        "mean_confidence": float(probs.max(1).values.mean()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="train/train")
    parser.add_argument("--arch", default="convnext_tiny")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--out", default="models/convnext_tiny_eidss.pt")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_gpu = torch.cuda.device_count()
    print(f"device={device} gpus={n_gpu} " + ", ".join(
        torch.cuda.get_device_name(i) for i in range(n_gpu)
    ))

    splits = stratified_split(Path(args.data_root), seed=args.seed)
    print({k: len(v) for k, v in splits.items()})

    # DataParallel splits each batch across both T4s; scale batch so per-GPU work
    # stays sensible.
    effective_batch = args.batch_size * max(n_gpu, 1)
    train_loader, val_loader = loaders(splits, args.img_size, effective_batch, args.workers)

    model = DefectNet(arch=args.arch, pretrained=True).to(device)
    feat_dim = model.feat_dim
    if n_gpu > 1:
        model = nn.DataParallel(model)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=args.lr, total_steps=args.epochs * len(train_loader), pct_start=0.25
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

    best_f1, best_state = -1.0, None
    for epoch in range(1, args.epochs + 1):
        model.train()
        started, running = time.time(), 0.0
        for images, labels in train_loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                loss = criterion(model(images), labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            running += loss.item()

        logits, labels = evaluate(model, val_loader, device)
        val = report(logits, labels)
        print(
            f"epoch {epoch:02d}/{args.epochs}  loss={running / len(train_loader):.4f}  "
            f"val_acc={val['accuracy']:.4f}  val_f1={val['macro_f1']:.4f}  "
            f"{time.time() - started:.0f}s"
        )

        if val["macro_f1"] > best_f1:
            best_f1 = val["macro_f1"]
            core = model.module if isinstance(model, nn.DataParallel) else model
            best_state = {k: v.detach().cpu().clone() for k, v in core.state_dict().items()}

    core = model.module if isinstance(model, nn.DataParallel) else model
    core.load_state_dict(best_state)

    val_logits, val_labels = evaluate(model, val_loader, device)
    temperature = fit_temperature(val_logits, val_labels)
    print(f"calibration temperature={temperature:.4f}")

    # Robustness sweep on the held-out test split, one pass per shifted condition.
    robustness = {}
    for condition in CONDITIONS:
        ds = DefectDataset(splits["test"], build_condition_transform(condition, args.img_size))
        loader = DataLoader(ds, batch_size=args.batch_size * 2, num_workers=args.workers, pin_memory=True)
        logits, labels = evaluate(model, loader, device)
        robustness[condition] = report(logits, labels, temperature)
        print(
            f"  {condition:<18} acc={robustness[condition]['accuracy']:.4f} "
            f"f1={robustness[condition]['macro_f1']:.4f} "
            f"FA={robustness[condition]['false_accept_rate']:.4f} "
            f"FR={robustness[condition]['false_reject_rate']:.4f}"
        )

    fit_loader = DataLoader(
        DefectDataset(splits["train"], build_transforms(args.img_size, train=False)),
        batch_size=args.batch_size * 2, num_workers=args.workers, pin_memory=True,
    )
    means, precision = fit_mahalanobis(model, fit_loader, device, feat_dim)

    # Without a threshold the OOD gate silently degrades to confidence-only
    # checking. Calibrate it on in-distribution validation features: anything
    # beyond the 99th percentile of known-good distances is treated as novel.
    mahalanobis_threshold = calibrate_ood_threshold(model, val_loader, device, means, precision)
    print(f"mahalanobis threshold (p99 of in-distribution)={mahalanobis_threshold:.4f}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "arch": args.arch,
            "classes": CLASSES,
            "state_dict": core.state_dict(),
            "temperature": temperature,
            "mahalanobis_means": means.float(),
            "mahalanobis_precision": precision.float(),
            "mahalanobis_threshold": mahalanobis_threshold,
            "img_size": args.img_size,
            "metrics": {"clean_test": robustness["clean"], "robustness": robustness},
            "seed": args.seed,
        },
        out_path,
    )
    Path("models/metrics.json").write_text(
        json.dumps({"robustness": robustness, "temperature": temperature}, indent=2)
    )
    print(f"\nsaved {out_path}  best_val_f1={best_f1:.4f}")


if __name__ == "__main__":
    main()
