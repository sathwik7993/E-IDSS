"""Render the trained model's metrics as markdown for the README.

    python scripts/report_metrics.py [--checkpoint models/convnext_tiny_eidss.pt]
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="models/convnext_tiny_eidss.pt")
    parser.add_argument("--metrics", default="models/metrics.json")
    args = parser.parse_args()

    metrics_path, ckpt_path = Path(args.metrics), Path(args.checkpoint)
    if metrics_path.exists():
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        robustness, temperature = payload["robustness"], payload.get("temperature")
    elif ckpt_path.exists():
        import torch
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        robustness = ckpt["metrics"]["robustness"]
        temperature = ckpt.get("temperature")
    else:
        raise SystemExit("no metrics.json or checkpoint found - has training finished?")

    clean = robustness["clean"]

    print("\n### Held-out test performance\n")
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Accuracy | {clean['accuracy']:.4f} |")
    print(f"| Macro F1 | {clean['macro_f1']:.4f} |")
    print(f"| False-accept rate (defect shipped) | {clean['false_accept_rate']:.4f} |")
    print(f"| False-reject rate (good part scrapped) | {clean['false_reject_rate']:.4f} |")
    if temperature:
        print(f"| Calibration temperature | {temperature:.4f} |")

    print("\n### Per-class (held-out, clean)\n")
    print("| Class | Precision | Recall | F1 | Support |")
    print("|---|---|---|---|---|")
    for name, row in clean["per_class"].items():
        if isinstance(row, dict) and "precision" in row and name not in ("macro avg", "weighted avg"):
            print(
                f"| {name} | {row['precision']:.3f} | {row['recall']:.3f} | "
                f"{row['f1-score']:.3f} | {int(row['support'])} |"
            )

    print("\n### Robustness to unseen conditions\n")
    print("These shifts are applied to the held-out test split only and are never")
    print("seen during training.\n")
    print("| Condition | Accuracy | Macro F1 | False-accept | False-reject |")
    print("|---|---|---|---|---|")
    baseline = clean["accuracy"]
    for condition, m in robustness.items():
        drop = "" if condition == "clean" else f" ({m['accuracy'] - baseline:+.3f})"
        print(
            f"| {condition} | {m['accuracy']:.4f}{drop} | {m['macro_f1']:.4f} | "
            f"{m['false_accept_rate']:.4f} | {m['false_reject_rate']:.4f} |"
        )

    worst = min(robustness.items(), key=lambda kv: kv[1]["accuracy"])
    print(f"\nWorst condition: **{worst[0]}** at {worst[1]['accuracy']:.4f} accuracy "
          f"({worst[1]['accuracy'] - baseline:+.3f} vs clean).")


if __name__ == "__main__":
    main()
