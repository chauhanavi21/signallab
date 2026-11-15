"""Request-weighted SLO alert replay; Python standard library only."""
import csv
import hashlib
import io
import json
import math
import random
import re
import statistics

VERSION = "1.0.0"
SOURCES = [
    {"title": "Google SRE Workbook: Alerting on SLOs", "url": "https://sre.google/workbook/alerting-on-slos/"},
    {"title": "Google SRE: Handling Overload", "url": "https://sre.google/sre-book/handling-overload/"},
]


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}.")
    return value


def validate(options):
    if not isinstance(options, dict) or set(options) - {"slo", "seed", "min_requests", "csv"}:
        raise ValueError("Expected slo, seed, min_requests, and optional csv only.")
    slo = options.get("slo", .999)
    if type(slo) not in (int, float) or not math.isfinite(slo) or not .9 <= slo <= .99999:
        raise ValueError("slo must be finite and between 0.9 and 0.99999.")
    return {"slo": float(slo), "seed": integer(options.get("seed", 42), "seed", 0, 2**32 - 1),
            "min_requests": integer(options.get("min_requests", 100), "min_requests", 0, 100000)}


def demo(seed=42):
    rng = random.Random(seed)
    incidents = [
        {"service": "checkout-api", "start": 180, "end": 230, "ratio": .035, "name": "Checkout dependency failure"},
        {"service": "search-api", "start": 540, "end": 700, "ratio": .018, "name": "Search rollout regression"},
    ]
    traces = []
    for service, base in [("edge-gateway", 1800), ("checkout-api", 900), ("search-api", 2500)]:
        for minute in range(720):
            total = int(base * (.9 + .2 * math.sin(minute / 90)) * rng.uniform(.9, 1.1))
            probability = .00015
            for incident in incidents:
                if incident["service"] == service and incident["start"] <= minute < incident["end"]:
                    probability = incident["ratio"]
            # A deliberately brief disturbance, excluded from actionable labels.
            if service == "edge-gateway" and 330 <= minute < 333:
                probability = .025
            bad = sum(rng.random() < probability for _ in range(total))
            traces.append({"minute": minute, "service": service, "total": total, "bad": bad})
    return traces, incidents


def parse_csv(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > 800000:
        raise ValueError("CSV must be text smaller than 800 KB.")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if reader.fieldnames != ["minute", "service", "total", "bad"]:
        raise ValueError("CSV header must be minute,service,total,bad.")
    traces = []
    seen = set()
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Each CSV row must contain exactly four columns.")
        if len(traces) >= 10000:
            raise ValueError("At most 10,000 rows are supported.")
        try:
            minute, total, bad = (int(row[k]) for k in ["minute", "total", "bad"])
            service = row["service"]
        except (ValueError, TypeError, KeyError):
            raise ValueError("Rows need integer minute/total/bad and a service name.") from None
        if not isinstance(service, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,49}", service):
            raise ValueError("Service names must be short letters, digits, dashes, or underscores.")
        if not 0 <= minute < 2880 or not 0 <= bad <= total <= 100000000:
            raise ValueError("Invalid row: require minute 0..2879 and 0 <= bad <= total <= 100,000,000.")
        key = (service, minute)
        if key in seen:
            raise ValueError("Duplicate service/minute rows are not allowed.")
        seen.add(key)
        traces.append({"minute": minute, "service": service, "total": total, "bad": bad})
    if not traces:
        raise ValueError("CSV contains no observations.")
    services = {r["service"] for r in traces}
    if len(services) > 12:
        raise ValueError("At most 12 services are supported.")
    for service in services:
        minutes = sorted(r["minute"] for r in traces if r["service"] == service)
        if minutes != list(range(len(minutes))):
            raise ValueError("Each service must have contiguous minute buckets beginning at zero. Missing data is not assumed healthy.")
    return sorted(traces, key=lambda r: (r["service"], r["minute"]))


def to_csv(traces):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, ["minute", "service", "total", "bad"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(traces)
    return stream.getvalue()


def rolling(rows, window, slo, minimum=0):
    """Full-window, request-weighted burn, not mean of per-minute percentages."""
    total, bad = [0], [0]
    output = []
    for i, row in enumerate(rows):
        total.append(total[-1] + row["total"])
        bad.append(bad[-1] + row["bad"])
        if i + 1 < window:
            output.append(None)
            continue
        count = total[i + 1] - total[i + 1 - window]
        failures = bad[i + 1] - bad[i + 1 - window]
        output.append(failures / count / (1 - slo) if count > 0 and count >= minimum else None)
    return output


def episodes(points, service, policy):
    out, start = [], None
    for i, active in enumerate([*points, False]):
        if active and start is None:
            start = i
        elif not active and start is not None:
            out.append({"service": service, "policy": policy, "start": start, "end": i,
                        "duration_minutes": i - start})
            start = None
    return out


def score(alerts, incidents):
    if incidents is None:
        return {"precision": None, "recall": None, "median_detection_minutes": None, "false_episodes": None}
    overlaps = lambda a, b: a["service"] == b["service"] and a["start"] < b["end"] and b["start"] < a["end"]
    true_alerts = sum(any(overlaps(a, inc) for inc in incidents) for a in alerts)
    delays = []
    for inc in incidents:
        detected = [max(a["start"], inc["start"]) - inc["start"] for a in alerts if overlaps(a, inc)]
        if detected:
            delays.append(min(detected))
    return {"precision": true_alerts / len(alerts) if alerts else None,
            "recall": len(delays) / len(incidents) if incidents else None,
            "median_detection_minutes": statistics.median(delays) if delays else None,
            "false_episodes": len(alerts) - true_alerts}


def analyze(options=None):
    options = {} if options is None else options
    cfg = validate(options)
    imported = "csv" in options
    traces, incidents = (parse_csv(options["csv"]), None) if imported else demo(cfg["seed"])
    all_episodes = {"threshold": [], "short_burn": [], "multiwindow": []}
    output, service_stats = [], []
    above = lambda v, limit: v is not None and v > limit + 1e-12
    for service in sorted({r["service"] for r in traces}):
        rows = sorted((r for r in traces if r["service"] == service), key=lambda r: r["minute"])
        burns = {w: rolling(rows, w, cfg["slo"], cfg["min_requests"]) for w in [1, 5, 30, 60, 360]}
        naive = [above(v, 1) for v in burns[1]]
        short = [above(v, 14.4) for v in burns[5]]
        paired = [(above(burns[60][i], 14.4) and above(burns[5][i], 14.4))
                  or (above(burns[360][i], 6) and above(burns[30][i], 6)) for i in range(len(rows))]
        for key, active in [("threshold", naive), ("short_burn", short), ("multiwindow", paired)]:
            all_episodes[key] += episodes(active, service, key)
        for i, row in enumerate(rows):
            output.append({**row, "burn_5m": burns[5][i], "burn_1h": burns[60][i],
                           "burn_30m": burns[30][i], "burn_6h": burns[360][i], "firing": paired[i],
                           "eligible_fast": burns[60][i] is not None and burns[5][i] is not None})
        total, bad = sum(r["total"] for r in rows), sum(r["bad"] for r in rows)
        service_stats.append({"service": service, "total": total, "bad": bad,
                              "availability": 1 - bad / total if total else None,
                              "episodes": sum(a["service"] == service for a in all_episodes["multiwindow"]),
                              "last_burn": burns[60][-1], "minutes": len(rows)})
    total, bad = sum(r["total"] for r in traces), sum(r["bad"] for r in traces)
    canonical = {"config": cfg, "traces": traces, "model": VERSION}
    run_id = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    comparison = [{"key": key, "name": name, "episodes": len(all_episodes[key]),
                   "firing_minutes": sum(a["duration_minutes"] for a in all_episodes[key]),
                   **score(all_episodes[key], incidents)} for key, name in [
                       ("threshold", "One-minute SLO threshold"), ("short_burn", "Five-minute burn only"),
                       ("multiwindow", "Multiwindow burn-rate")]]
    return {"model_version": VERSION, "run_id": run_id, "config": cfg, "synthetic": not imported,
            "summary": {"total": total, "bad": bad, "availability": 1 - bad / total if total else None,
                        "replay_budget_use": bad / (total * (1 - cfg["slo"])) if total else None,
                        "service_count": len(service_stats)}, "services": service_stats,
            "comparison": comparison, "alerts": all_episodes["multiwindow"], "incidents": incidents,
            "series": output, "sources": SOURCES,
            "notes": ["One-minute buckets, request-weighted error ratios, and complete rolling windows.",
                      "Fast page: both 1h and 5m burn >14.4; slow page: both 6h and 30m burn >6. Rules are ORed and contiguous firings merged per service.",
                      "Thresholds are Google's illustrative 30-day-policy starting points, not universally optimal settings.",
                      "Replay-window budget use is bad / ((1−SLO) × observed requests); it is not an observed 30-day budget balance.",
                      "Demo precision and recall use two hand-labeled actionable synthetic incidents. Imported data has no ground-truth labels, so those metrics are unavailable.",
                      "No notifications are sent. This is a local replay evaluator, not production monitoring."]}
