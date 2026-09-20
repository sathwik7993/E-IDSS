"""Cached SyntheticPlant instance so /api/line/state doesn't rebuild it per call."""

from app import config

_state = {"plant": None}


def get_plant():
    if _state["plant"] is None:
        from ai.synthetic import SyntheticPlant

        _state["plant"] = SyntheticPlant(seed=config.SYNTHETIC_SEED)
    return _state["plant"]
