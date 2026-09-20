"""Bootstrap and verify Kaggle credentials from .env.

Run:  python scripts/kaggle_auth.py
"""

import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"FAIL  no .env at {path}")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> None:
    env = load_env(ROOT / ".env")
    username = env.get("KAGGLE_USERNAME", "")
    key = env.get("KAGGLE_KEY", "")

    if not username or not key:
        sys.exit(
            "FAIL  KAGGLE_USERNAME / KAGGLE_KEY are empty in .env\n"
            "      Get a token at kaggle.com -> Settings -> API -> Create New API Token,\n"
            "      then paste the username and key from the downloaded kaggle.json."
        )
    if key.startswith("{") or len(key) < 20:
        sys.exit("FAIL  KAGGLE_KEY looks wrong — paste only the 'key' value, not the whole JSON.")

    cred_dir = Path.home() / ".kaggle"
    cred_dir.mkdir(exist_ok=True)
    cred_file = cred_dir / "kaggle.json"
    cred_file.write_text(json.dumps({"username": username, "key": key}), encoding="utf-8")
    try:
        cred_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600; no-op on some Windows filesystems
    except OSError:
        pass

    os.environ["KAGGLE_USERNAME"] = username
    os.environ["KAGGLE_KEY"] = key

    print(f"OK    wrote {cred_file}")
    print(f"OK    user={username} key={key[:4]}...{key[-2:]} (masked)")

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        sys.exit("FAIL  kaggle package not importable — run: pip install kaggle")

    api = KaggleApi()
    try:
        api.authenticate()
        datasets = api.dataset_list(search="surface defect", page=1)
    except Exception as exc:  # noqa: BLE001 — surface the real auth error verbatim
        sys.exit(f"FAIL  Kaggle auth rejected: {exc}")

    print(f"OK    authenticated — API reachable ({len(datasets)} results on test query)")
    print("\nReady. Next: upload the dataset and kick off training.")


if __name__ == "__main__":
    main()
