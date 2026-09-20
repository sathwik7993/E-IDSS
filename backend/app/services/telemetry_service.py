"""Fits the telemetry attribution bundle once at startup.

LightGBM over 3500 rows x 8 features trains in well under a second, so the
bundle is refit on boot rather than shipped as a pickle -- no stale-artifact
risk and no pickle-compatibility coupling to a specific LightGBM build.
"""

from app import config

_state = {"bundle": None}


def load():
    from ai.telemetry import train_attribution_bundle

    _state["bundle"] = train_attribution_bundle(csv_path=str(config.TELEMETRY_CSV_PATH))


def get_bundle():
    return _state["bundle"]
