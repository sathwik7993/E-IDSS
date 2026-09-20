"""Environment bootstrap: puts the repo root (and ai/) on sys.path, loads .env.

Must be imported before anything that does `import ai...` or reads os.environ
for E-IDSS settings. Safe to import multiple times.
"""

import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

for _p in (REPO_ROOT, BACKEND_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

API_PORT = int(os.getenv("API_PORT", "8000"))

_weights_raw = os.getenv("MODEL_WEIGHTS_PATH", "./models/convnext_tiny_eidss.pt")
MODEL_WEIGHTS_PATH = (REPO_ROOT / _weights_raw).resolve()

_telemetry_raw = os.getenv("TELEMETRY_CSV_PATH", "./data/process_parameters.csv")
TELEMETRY_CSV_PATH = (REPO_ROOT / _telemetry_raw).resolve()

TORCH_DEVICE_REQUESTED = os.getenv("TORCH_DEVICE", "cpu")
IMG_SIZE = int(os.getenv("IMG_SIZE", "224"))
SYNTHETIC_SEED = int(os.getenv("SYNTHETIC_SEED", "1337"))


def resolve_device() -> str:
    """Honor TORCH_DEVICE but never crash a CPU-only host/container."""
    import torch

    if TORCH_DEVICE_REQUESTED.startswith("cuda") and torch.cuda.is_available():
        return TORCH_DEVICE_REQUESTED
    return "cpu"
