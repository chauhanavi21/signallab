import argparse
import json
from pathlib import Path

from core import VERSION, analyze, demo, to_csv
from httpkit import Fault, Handler, Server, serve


class API(Handler):
    def get_api(self, path, query):
        if path == "/api/health": return {"status": "ok", "project": "SignalLab", "version": VERSION}
        if path == "/api/sample": return {"csv": to_csv(demo(42)[0])}
        raise Fault(404, "Route not found.")

    def post_api(self, path, body):
        if path == "/api/analyze": return analyze(body)
        raise Fault(404, "Route not found.")


def main():
    parser = argparse.ArgumentParser(description="SignalLab reliability replay studio")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.report:
        report = analyze()
        (root / "artifacts/demo-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
        print(json.dumps({"run_id": report["run_id"], "comparison": report["comparison"]}, indent=2))
    else: serve(Server(args.port, API, root))


if __name__ == "__main__": main()
