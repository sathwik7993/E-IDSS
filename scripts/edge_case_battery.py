"""Adversarial/edge-case battery for POST /api/inspect against a live backend.

Distinct from ai/robustness.py (which measures accuracy under physically
motivated shifts on held-out *training-distribution* images for the README's
reported metrics). This script probes structurally unusual inputs -- extreme
scale, composition, exposure, and malformed files -- and reports what the
trust gate did, so failures surface as a table instead of one-off manual
testing.

    python scripts/edge_case_battery.py [--base http://localhost:8000]
"""

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TRAIN = ROOT / "train" / "train"


def _load(cls: str, idx: int = 50) -> Image.Image:
    files = sorted((TRAIN / cls).glob("*.png"))
    return Image.open(files[idx]).convert("L")


def _bytes(img: Image.Image, fmt: str = "PNG") -> io.BytesIO:
    buf = io.BytesIO()
    img.convert("RGB" if fmt in ("JPEG", "BMP", "WEBP") else img.mode).save(buf, format=fmt)
    buf.seek(0)
    return buf


def case_extreme_closeup_crop():
    """Zoom into a tiny patch of a crack image and upscale -- far less
    context than the training crop size."""
    img = _load("crack")
    w, h = img.size
    patch = img.crop((w // 2 - 12, h // 2 - 12, w // 2 + 12, h // 2 + 12))
    return patch.resize((256, 256), Image.NEAREST)


def case_composite_two_defects():
    """Left half crack, right half rust -- a part straddling two defect
    types, which cannot exist in a single-label training set."""
    crack = _load("crack").resize((256, 256))
    rust = _load("rust").resize((256, 256))
    out = Image.new("L", (256, 256))
    out.paste(crack.crop((0, 0, 128, 256)), (0, 0))
    out.paste(rust.crop((128, 0, 256, 256)), (128, 0))
    return out


def case_defect_at_edge():
    """Defect signal pushed entirely into a corner, mostly background --
    tests whether localization still finds it and whether it's still
    confidently classified."""
    normal = _load("normal").resize((256, 256))
    crack = _load("crack").resize((256, 256))
    out = normal.copy()
    patch = crack.crop((0, 0, 60, 60))
    out.paste(patch, (196, 196))
    return out


def case_wrong_aspect_ratio():
    """Panoramic strip -- nothing in training data looks like this shape."""
    img = _load("scratch").resize((800, 150))
    return img


def case_tiny_upscaled():
    """8x8 source, heavily upscaled -- effectively no real signal."""
    img = _load("hole").resize((8, 8)).resize((256, 256), Image.NEAREST)
    return img


def case_huge_resolution():
    """4000x3000 -- far larger than any real camera capture the pipeline
    has seen, tests resize-path robustness rather than model behavior."""
    return _load("rust").resize((4000, 3000))


def case_solid_blank():
    return Image.new("L", (256, 256), color=128)


def case_pure_noise():
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, (256, 256), dtype=np.uint8)
    return Image.fromarray(arr, mode="L")


def case_near_black():
    return Image.new("L", (256, 256), color=4)


def case_near_white_overexposed():
    return Image.new("L", (256, 256), color=252)


def case_inverted_defect():
    """A real defect image with pixel values inverted -- same structure,
    wrong polarity; a lighting/sensor artifact a real line could produce."""
    img = _load("crack")
    arr = 255 - np.array(img)
    return Image.fromarray(arr, mode="L")


def case_text_overlay():
    """Real defect image with an operator annotation burned in -- checks
    the model isn't thrown by non-part content sharing the frame."""
    img = _load("scratch").resize((256, 256)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 256, 28], fill=(0, 0, 0))
    d.text((6, 6), "STATION-04 BATCH-B119", fill=(255, 255, 0))
    return img


CASES = {
    "extreme_closeup_crop": (case_extreme_closeup_crop, "PNG"),
    "composite_two_defects": (case_composite_two_defects, "PNG"),
    "defect_pushed_to_corner": (case_defect_at_edge, "PNG"),
    "wrong_aspect_ratio_panorama": (case_wrong_aspect_ratio, "PNG"),
    "tiny_8x8_upscaled": (case_tiny_upscaled, "PNG"),
    "huge_4000x3000": (case_huge_resolution, "PNG"),
    "solid_blank_gray": (case_solid_blank, "PNG"),
    "pure_random_noise": (case_pure_noise, "PNG"),
    "near_black": (case_near_black, "PNG"),
    "near_white_overexposed": (case_near_white_overexposed, "PNG"),
    "inverted_polarity_crack": (case_inverted_defect, "PNG"),
    "text_overlay_on_scratch": (case_text_overlay, "JPEG"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print(f"{'case':<30} {'status':<7} {'class':<9} {'conf':<8} {'maha_d':<9} {'decision':<16} note")
    print("-" * 110)

    concerns = []
    for name, (builder, fmt) in CASES.items():
        try:
            img = builder()
            buf = _bytes(img, fmt)
            r = requests.post(
                f"{base}/api/inspect",
                files={"file": (f"{name}.{fmt.lower()}", buf, f"image/{fmt.lower()}")},
                timeout=60,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"{name:<30} EXC     -         -        -         -                {exc}")
            concerns.append((name, f"raised exception: {exc}"))
            continue

        if r.status_code != 200:
            print(f"{name:<30} {r.status_code:<7} -         -        -         -                {r.text[:60]}")
            concerns.append((name, f"non-200: {r.status_code} {r.text[:100]}"))
            continue

        b = r.json()
        note = ""
        # Flag: a structurally-invalid input (composite, corner-pushed edge
        # case, extreme close-up, noise, blank, wrong shape) that the gate
        # let through as AUTO with high confidence deserves a second look.
        if b["decision"] == "AUTO" and b["calibrated_confidence"] > 0.9 and name in (
            "composite_two_defects", "pure_random_noise", "solid_blank_gray",
            "wrong_aspect_ratio_panorama", "tiny_8x8_upscaled",
        ):
            note = "AUTO + high-confidence on a structurally invalid input"
            concerns.append((name, note))

        print(
            f"{name:<30} {r.status_code:<7} {b['predicted_class']:<9} "
            f"{b['calibrated_confidence']:.3f}   {b['mahalanobis_distance']:<9.2f} "
            f"{b['decision']:<16} {note}"
        )

    print()
    if concerns:
        print(f"{len(concerns)} concern(s):")
        for name, note in concerns:
            print(f"  - {name}: {note}")
        sys.exit(1)
    print("No concerns flagged.")


if __name__ == "__main__":
    main()
