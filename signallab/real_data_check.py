"""Validate imported historical request counts without inventing incident labels."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from core import analyze

ROOT = Path(__file__).resolve().parent


def main():
    fixture = ROOT / "data/nasa-12h.csv"
    provenance = json.loads((ROOT / "data/provenance.json").read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == provenance["fixture_sha256"]
    text = fixture.read_text(encoding="utf-8")
    with fixture.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    report = analyze({"csv": text})
    assert report["run_id"] == analyze({"csv": text})["run_id"]
    assert sum(int(r["total"]) for r in rows) == provenance["total_requests"]
    assert sum(int(r["bad"]) for r in rows) == provenance["bad_requests"] == 0
    assert not report["alerts"]
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "dataset": provenance["dataset"],
              "fixture_sha256": provenance["fixture_sha256"], "passed": True,
              "minutes": len(rows), "requests": provenance["total_requests"], "http_5xx": 0,
              "alert_episodes": len(report["alerts"]), "run_id": report["run_id"],
              "scope": "Historical count-import and zero-5xx baseline validation only. No actionable incident labels exist. This sample cannot validate detection delay, false positives or production alert efficacy. 4xx responses are included in traffic and excluded from server-failure counts."}
    (ROOT / "artifacts/real-data-checks.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
