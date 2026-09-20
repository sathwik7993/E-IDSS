import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

for _p in (REPO_ROOT, BACKEND_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import model_service  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def stub_client(client, monkeypatch):
    """The real checkpoint is present in this repo, so force stub state for
    tests that specifically cover the no-weights fallback path, then restore
    real state afterwards so later tests see the model again."""
    monkeypatch.setattr(config, "MODEL_WEIGHTS_PATH", REPO_ROOT / "models" / "__nonexistent__.pt")
    model_service.load()
    try:
        yield client
    finally:
        monkeypatch.undo()
        model_service.load()
