"""Fits RootCauseEngine once at startup and exposes it to routers.

validate_attribution() recomputes SHAP over the full synthetic dataset for
every defect class -- expensive on CPU (~5s, close to the frontend's 6s
fetch timeout) and deterministic for a fixed seed, so its result is cached
at startup rather than recomputed per request.
"""

from app import config

_state = {"engine": None, "validation": None}


def load(n_parts: int = 6000):
    from ai.rootcause import RootCauseEngine

    engine = RootCauseEngine(seed=config.SYNTHETIC_SEED).fit(n_parts=n_parts)
    _state["engine"] = engine
    _state["validation"] = engine.validate_attribution()


def get_engine():
    return _state["engine"]


def get_validation():
    return _state["validation"]
