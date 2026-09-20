"""Tight repro loop for the gateway multipart bug.

Exit 0 = inspect succeeded through the gateway (bug fixed/absent).
Exit 1 = reproduced (422, file field missing) or any other failure.

    python scripts/repro_gateway_multipart.py --base http://localhost:8081
"""
import argparse
import io
import sys

import requests
from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8081")
    args = p.parse_args()

    tok = requests.post(
        f"{args.base}/auth/login",
        json={"username": "operator", "password": "operator123"},
        timeout=20,
    ).json()["token"]

    buf = io.BytesIO()
    Image.new("L", (64, 64), color=90).save(buf, format="PNG")
    buf.seek(0)

    r = requests.post(
        f"{args.base}/api/inspect",
        headers={"Authorization": f"Bearer {tok}"},
        files={"file": ("part.png", buf, "image/png")},
        timeout=60,
    )

    if r.status_code == 200:
        print(f"GREEN: 200, predicted_class={r.json().get('predicted_class')}")
        sys.exit(0)

    print(f"RED: {r.status_code} {r.text[:200]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
