# 3.13 matches the environment the requirements were pinned against; several
# pins (shap>=0.52) publish no wheels for 3.11.
FROM python:3.13-slim

# Mirror the repo layout (repo_root/{ai,backend,models}) so app/config.py's
# relative path arithmetic needs no container-specific changes.
WORKDIR /app

# System lib needed by lightgbm at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt

# CPU-only torch/torchvision wheels keep the image small; --extra-index-url
# lets every other package still resolve from PyPI as usual.
RUN pip install --no-cache-dir -r backend/requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY ai ./ai
COPY backend ./backend
# Telemetry table for the TreeSHAP attribution tier (synthetic demonstration
# data); regenerated deterministically at startup if missing.
COPY data ./data
# models/ may be empty (checkpoint not trained yet) — the app starts fine in
# stub mode either way. No .env is baked in; config.py's defaults already
# match the documented values, and real deployments pass env vars at runtime.
COPY models ./models

ENV TORCH_DEVICE=cpu \
    PYTHONUNBUFFERED=1

EXPOSE 8000

WORKDIR /app/backend
# --http h11: uvicorn[standard] installs the compiled httptools parser here
# (the host dev machine lacks it and silently falls back to h11), and
# httptools fails to parse the chunked-transfer-encoded multipart body Spring's
# RestClient sends for image uploads -- the file part arrives empty. h11 (pure
# Python, slightly slower, correctness-first) parses the identical bytes fine.
# See scripts/repro_gateway_multipart.py for the regression check.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--http", "h11"]
