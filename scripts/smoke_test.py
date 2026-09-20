"""End-to-end contract check against a running backend.

The backend and frontend were built in parallel against a written contract, so
this verifies the server actually returns what the client expects -- including
the data-provenance labels, which are a credibility requirement rather than a
nicety.

    python scripts/smoke_test.py [--base http://localhost:8000]
"""

import argparse
import io
import sys

import requests

SYNTHETIC = "SYNTHETIC_DEMONSTRATION"

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, condition, detail=""):
    results.append((PASS if condition else FAIL, name, detail))
    print(f"  [{PASS if condition else FAIL}] {name}" + (f" - {detail}" if detail else ""))
    return condition


def require_keys(payload, keys, name):
    missing = [k for k in keys if k not in payload]
    return check(name, not missing, f"missing {missing}" if missing else "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print(f"\nE-IDSS contract smoke test -> {base}\n")

    print("health")
    try:
        health = requests.get(f"{base}/api/health", timeout=10).json()
    except Exception as exc:  # noqa: BLE001
        print(f"  backend unreachable: {exc}")
        sys.exit(1)
    require_keys(health, ["status", "model_loaded", "stub_mode", "device"], "health shape")
    stub = health.get("stub_mode")
    print(f"        model_loaded={health.get('model_loaded')} stub_mode={stub} device={health.get('device')}")

    print("\ninspect")
    from PIL import Image
    buf = io.BytesIO()
    Image.new("L", (256, 256), color=128).save(buf, format="PNG")
    buf.seek(0)
    resp = requests.post(
        f"{base}/api/inspect", files={"file": ("part.png", buf, "image/png")}, timeout=60
    )
    check("inspect returns 200", resp.status_code == 200, f"got {resp.status_code}")
    if resp.status_code == 200:
        body = resp.json()
        require_keys(
            body,
            ["part_id", "predicted_class", "is_defective", "calibrated_confidence",
             "epistemic_uncertainty", "mahalanobis_distance", "novel_or_uncertain",
             "decision", "class_probabilities", "heatmap_png_base64",
             "overlay_png_base64", "bbox", "data_provenance"],
            "inspect shape",
        )
        check("decision is valid", body.get("decision") in ("AUTO", "DEFER_TO_HUMAN"),
              str(body.get("decision")))
        check("probabilities sum ~1",
              abs(sum(body.get("class_probabilities", {}).values()) - 1.0) < 0.02)
        check("overlay is non-trivial base64", len(body.get("overlay_png_base64") or "") > 500)
        check("inspect provenance is ORGANIZER_DATASET",
              body.get("data_provenance") == "ORGANIZER_DATASET",
              str(body.get("data_provenance")))

    print("\nsynthetic endpoints must be labelled")
    for label, method, path, payload in [
        ("line state", "get", "/api/line/state", None),
        ("economics", "get", "/api/economics?defect_rate=0.08&throughput=240", None),
        ("rootcause", "post", "/api/rootcause", {"defect_class": "rust", "observation": None}),
        ("counterfactual", "post", "/api/economics/counterfactual",
         {"defect_rate": 0.08, "throughput": 240, "speed_delta_pct": -8,
          "defect_rate_delta_pct": -30}),
    ]:
        try:
            r = (requests.get(f"{base}{path}", timeout=30) if method == "get"
                 else requests.post(f"{base}{path}", json=payload, timeout=30))
            body = r.json()
            check(f"{label} 200", r.status_code == 200, f"got {r.status_code}")
            check(f"{label} labelled synthetic", body.get("data_provenance") == SYNTHETIC,
                  str(body.get("data_provenance")))
        except Exception as exc:  # noqa: BLE001
            check(f"{label} reachable", False, str(exc)[:80])

    print("\nattribution validation")
    try:
        v = requests.get(f"{base}/api/rootcause/validation", timeout=60).json()
        recall = v.get("mean_recall")
        check("mean_recall present", recall is not None)
        check("mean_recall >= 0.75", (recall or 0) >= 0.75, f"recall={recall}")
        conf = v.get("confounder_check", {})
        check("confounder correctly demoted", bool(conf.get("correctly_ranked")),
              f"humidity#{conf.get('humidity_rank')} ambient#{conf.get('ambient_rank')}")
    except Exception as exc:  # noqa: BLE001
        check("validation reachable", False, str(exc)[:80])

    print("\ntelemetry specs")
    try:
        specs = requests.get(f"{base}/api/telemetry/specs", timeout=20).json()
        require_keys(specs, ["feature_cols", "specs", "nominal", "presets", "defect_profiles"],
                     "specs shape")
        check("eight telemetry parameters", len(specs.get("feature_cols", [])) == 8,
              f"got {len(specs.get('feature_cols', []))}")
        check("five preset incident records", len(specs.get("presets", [])) == 5,
              f"got {len(specs.get('presets', []))}")
        check("specs labelled synthetic", specs.get("data_provenance") == SYNTHETIC)
    except Exception as exc:  # noqa: BLE001
        check("telemetry specs reachable", False, str(exc)[:80])
        specs = {}

    print("\ntreeshap attribution")
    try:
        # The crack preset: thermal + pressure drift should attribute to crack.
        crack_preset = next(p for p in specs["presets"] if p["id"] == "UNIT-10492")
        attr = requests.post(
            f"{base}/api/telemetry/attribution",
            json={"telemetry": crack_preset["telemetry"]},
            timeout=30,
        ).json()
        require_keys(attr, ["predicted_defect", "confidence", "contributions",
                            "out_of_spec_parameters", "top_drivers"], "attribution shape")
        check("crack preset attributed to crack", attr.get("predicted_defect") == "crack",
              f"got {attr.get('predicted_defect')}")
        check("one contribution per parameter", len(attr.get("contributions", [])) == 8,
              f"got {len(attr.get('contributions', []))}")
        check("contributions ranked by impact",
              all(a["abs_shap"] >= b["abs_shap"]
                  for a, b in zip(attr["contributions"], attr["contributions"][1:])))
        check("drift flagged out of spec", len(attr.get("out_of_spec_parameters", [])) > 0,
              f"{len(attr.get('out_of_spec_parameters', []))} flagged")
        check("attribution labelled synthetic", attr.get("data_provenance") == SYNTHETIC)

        nominal = requests.post(
            f"{base}/api/telemetry/attribution",
            json={"telemetry": specs["nominal"]},
            timeout=30,
        ).json()
        check("nominal telemetry attributed to normal",
              nominal.get("predicted_defect") == "normal", f"got {nominal.get('predicted_defect')}")
        check("nominal telemetry has no drift",
              len(nominal.get("out_of_spec_parameters", [])) == 0)
    except Exception as exc:  # noqa: BLE001
        check("attribution reachable", False, str(exc)[:80])

    print("\nline health + financial impact")
    try:
        lh = requests.get(f"{base}/api/line/health", timeout=20).json()
        require_keys(lh, ["stations", "bottleneck_notice", "executive_kpis", "remediation_plan"],
                     "line health shape")
        check("six stations reported", len(lh.get("stations", [])) == 6,
              f"got {len(lh.get('stations', []))}")
        check("exactly one bottleneck station",
              sum(1 for s in lh.get("stations", []) if s.get("bottleneck")) == 1)
        check("four executive KPIs", len(lh.get("executive_kpis", [])) == 4)
        check("line health labelled synthetic", lh.get("data_provenance") == SYNTHETIC)

        fin = requests.get(
            f"{base}/api/line/financial",
            params={"daily_units": 2400, "defect_rate_pct": 3.8, "scrap_cost_per_unit": 92.40},
            timeout=20,
        ).json()
        check("flagged units = volume x defect rate", fin.get("flagged_units_daily") == 91,
              f"got {fin.get('flagged_units_daily')}")
        check("monthly loss = daily x operating days",
              abs(fin["monthly_loss"] - fin["daily_loss"] * fin["operating_days_per_month"]) < 0.01)
    except Exception as exc:  # noqa: BLE001
        check("line health reachable", False, str(exc)[:80])

    print("\nbad input handling")
    try:
        r = requests.post(
            f"{base}/api/inspect",
            files={"file": ("junk.txt", io.BytesIO(b"not an image"), "text/plain")},
            timeout=20,
        )
        check("non-image rejected cleanly", r.status_code in (400, 415, 422),
              f"got {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        check("bad input handled", False, str(exc)[:80])

    failed = [r for r in results if r[0] == FAIL]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("failures:")
        for _, name, detail in failed:
            print(f"  - {name} {detail}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
