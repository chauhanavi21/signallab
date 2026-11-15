"""Regenerate replay evidence without contacting any external service."""
import json
from pathlib import Path
from core import analyze, to_csv, demo


def generate():
    runs = []
    default = None
    for seed in [7, 42, 2026]:
        report = analyze({"seed": seed})
        runs.append({"seed":seed, "run_id":report["run_id"], "summary":report["summary"], "comparison":report["comparison"]})
        if seed == 42: default = report
    root = Path(__file__).resolve().parent / "artifacts"
    root.mkdir(exist_ok=True)
    study = {"question":"How do noise, firing time, and detection delay change across policies?",
             "seeds":[7,42,2026], "slo":.999, "min_requests":100, "runs":runs,
             "limits":"Three seeded synthetic repetitions with the same two incident shapes, not independent real incidents or a general performance estimate."}
    (root / "policy-study.json").write_text(json.dumps(study, indent=2), encoding="utf-8")
    (root / "demo-report.json").write_text(json.dumps(default, indent=2), encoding="utf-8")
    (root / "sample.csv").write_text(to_csv(demo(42)[0]), encoding="utf-8")
    return {"study":"artifacts/policy-study.json", "default_run":default["run_id"], "comparison":default["comparison"]}


if __name__ == "__main__": print(json.dumps(generate(), indent=2))
