"""Reproducible automated accessibility audit and local mobile lab measurements."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time

import core
from httpkit import Server
from server import API

ROOT = Path(__file__).resolve().parent


@contextmanager
def isolated():
    with tempfile.TemporaryDirectory() as temporary:
        store = core.Store(Path(temporary) / "quality.sqlite") if hasattr(core, "Store") else None
        server = Server(0, API, ROOT, store)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(5)
            server.server_close()


def ready(page):
    from playwright.sync_api import expect
    if ROOT.name == "tenantledger":
        expect(page.locator("#status")).to_contain_text("Choose")
    else:
        expect(page.locator("#metrics .metric")).to_have_count(4, timeout=60000)


def audit(browser, base):
    from playwright.sync_api import expect
    vendor = ROOT / "vendor/axe.min.js"
    # The bypass permits only the test runner's audit-script injection. The app's
    # real CSP is exercised without bypass in browser_check.py.
    context = browser.new_context(bypass_csp=True, reduced_motion="reduce")
    page = context.new_page()
    page.goto(base)
    ready(page)
    states = []
    if ROOT.name == "tenantledger":
        states.append(("sign-in", False))
    states.append(("workspace", ROOT.name == "tenantledger"))
    results = []
    for state, login in states:
        if login:
            page.click("#aster-login")
            expect(page.locator("#workspace")).to_be_visible()
        for theme in ["light", "dark"]:
            page.evaluate("theme => document.documentElement.dataset.appearance = theme", theme)
            for width in [1440, 390]:
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                for panel in page.locator(".reveal-wait").all():
                    if panel.is_visible():
                        panel.scroll_into_view_if_needed()
                page.add_script_tag(path=str(vendor))
                report = page.evaluate("""async () => {
                    const r = await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}});
                    return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,helpUrl:v.helpUrl,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),passes:r.passes.length,incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.length}))};
                }""")
                results.append({"state": state, "theme": theme, "width": width, **report})
    context.close()
    return {"tool": "axe-core 4.10.3", "script_sha256": hashlib.sha256(vendor.read_bytes()).hexdigest(),
            "standard": "Automated WCAG 2 A/AA, 2.1 A/AA and 2.2 AA rules", "runs": results,
            "violations": sum(len(r["violations"]) for r in results),
            "scope": "Automated checks only; incomplete rules need human review. This is not a WCAG conformance certification or a screen-reader/device test."}


def mobile(browser, base):
    context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1,
                                  is_mobile=True, has_touch=True, reduced_motion="reduce")
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
             "downloadThroughput": 1600000 / 8, "uploadThroughput": 750000 / 8})
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    page.add_init_script("""window.lab={longTasks:[],lcp:0,cls:0};
        new PerformanceObserver(l=>l.getEntries().forEach(e=>lab.longTasks.push(e.duration))).observe({type:'longtask',buffered:true});
        new PerformanceObserver(l=>l.getEntries().forEach(e=>lab.lcp=e.startTime)).observe({type:'largest-contentful-paint',buffered:true});
        new PerformanceObserver(l=>l.getEntries().forEach(e=>{if(!e.hadRecentInput)lab.cls+=e.value})).observe({type:'layout-shift',buffered:true});""")
    started = time.perf_counter()
    page.goto(base)
    ready(page)
    elapsed = (time.perf_counter() - started) * 1000
    page.wait_for_timeout(500)
    result = page.evaluate("""() => ({...lab,paint:performance.getEntriesByType('paint').map(e=>({name:e.name,ms:e.startTime})),
        resource_bytes:performance.getEntriesByType('resource').reduce((n,r)=>n+r.transferSize,0),
        overflow:document.documentElement.scrollWidth>innerWidth+1})""")
    result["initial_ready_ms"] = round(elapsed, 1)
    context.close()
    return {"method": "Cold-cache headless Chromium, 390x844, 4x CPU slowdown, 150ms network latency, 1.6Mbps down/0.75Mbps up, reduced motion.",
            "measurement": result, "budgets": {"initial_ready_ms": 8000, "cls": .1, "overflow": False},
            "passed": elapsed < 8000 and result["cls"] <= .1 and not result["overflow"],
            "scope": "One local lab navigation, not real-device performance, field Core Web Vitals, INP or a percentile estimate. LCP is observed only before the measurement ends. Resource bytes exclude the document."}


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    with isolated() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        result = {"checked_at": datetime.now(timezone.utc).isoformat(), "project": ROOT.name,
                  "browser_version": browser.version, "accessibility": audit(browser, base), "mobile": mobile(browser, base)}
        browser.close()
    (ROOT / "artifacts/quality-checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project": ROOT.name, "accessibility_violations": result["accessibility"]["violations"],
                      "mobile_passed": result["mobile"]["passed"], "initial_ready_ms": result["mobile"]["measurement"]["initial_ready_ms"]}))
    if result["accessibility"]["violations"] or not result["mobile"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
