"""Optional browser verification harness; runtime has no Playwright dependency."""
import argparse
import json
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import core
from httpkit import Server
from server import API


def run(scenario):
    from playwright.sync_api import sync_playwright, expect
    parser = argparse.ArgumentParser(description="Verify the real UI against an isolated temporary server")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--browser-path", help="Optional executable for the selected browser")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = root / "artifacts/browser" / args.browser
    output.mkdir(parents=True, exist_ok=True)
    checks, errors, failures = [], [], []
    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            page.screenshot(path=str(output / "failure.png"), full_page=True, animations="disabled")
            raise AssertionError(name)
    with tempfile.TemporaryDirectory() as temporary:
        store = core.Store(Path(temporary) / "browser.sqlite") if hasattr(core, "Store") else None
        server = Server(0, API, root, store)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                launch = {"headless": True}
                if args.browser_path: launch["executable_path"] = args.browser_path
                browser = getattr(playwright, args.browser).launch(**launch)
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: failures.append(f"{response.status} {response.url}") if response.status >= 500 else None)
                base = f"http://127.0.0.1:{server.server_port}"
                page.goto(base)
                try:
                    scenario(page, context, base, output, check)
                except Exception:
                    page.screenshot(path=str(output / "failure.png"), full_page=True, animations="disabled")
                    raise
                check("workspace motion layer loads", page.evaluate("!!window.Studio"))
                page.keyboard.press("Control+k")
                expect(page.locator("#command-dialog")).to_be_visible()
                page.fill("#command-input", "Research")
                check("keyboard navigation filters sections", page.locator(".command-item").count()==1)
                page.keyboard.press("Enter")
                expect(page.locator("#command-dialog")).to_be_hidden()
                expect(page.locator("#method")).to_be_in_viewport(ratio=.3)
                expect(page.locator("aside nav a.active")).to_have_attribute("href", "#method")
                check("scroll navigation tracks the visible section", True)
                check("scroll progress follows page position", page.evaluate("Number(document.querySelector('.topbar').style.getPropertyValue('--scroll-progress'))>0"))
                page.click("#back-to-top")
                expect(page.locator(".hero h1")).to_be_in_viewport()
                check("back-to-top returns to the workspace heading", True)
                page.keyboard.press("Control+k")
                page.keyboard.press("Escape")
                expect(page.locator("#command-dialog")).to_be_hidden()
                check("Escape dismisses keyboard navigation", True)
                original_theme=page.locator("html").get_attribute("data-appearance")
                page.click("#theme-toggle")
                changed_theme=page.locator("html").get_attribute("data-appearance")
                check("color theme changes", changed_theme!=original_theme)
                page.reload()
                expect(page.locator("#metrics .metric")).to_have_count(4)
                check("theme preference survives reload", page.locator("html").get_attribute("data-appearance")==changed_theme)
                page.click("#theme-toggle")
                page.click("#motion-toggle")
                check("motion can be paused", page.locator("html").get_attribute("data-motion")=="off" and page.evaluate("document.getAnimations().every(a => a.playState !== 'running')"))
                page.reload()
                expect(page.locator("#metrics .metric")).to_have_count(4)
                check("motion preference survives reload", page.locator("html").get_attribute("data-motion")=="off")
                page.click("#motion-toggle")
                page.emulate_media(reduced_motion="reduce")
                expect(page.locator("html")).to_have_attribute("data-motion", "off")
                check("system reduced motion suppresses animations", page.evaluate("document.getAnimations().every(a => a.playState !== 'running')"))
                page.emulate_media(reduced_motion="no-preference")
                expect(page.locator("html")).to_have_attribute("data-motion", "on")
                check("normal motion returns when system preference clears", True)
                frame_sample=page.evaluate("""async () => {
                    const deltas=[];let previous;
                    await new Promise(resolve=>{
                        function frame(timestamp){if(previous!==undefined)deltas.push(timestamp-previous);previous=timestamp;if(deltas.length<35)requestAnimationFrame(frame);else resolve();}
                        requestAnimationFrame(frame);
                    });
                    const sorted=[...deltas].sort((a,b)=>a-b);
                    return {samples:deltas.length,median_ms:sorted[Math.floor(sorted.length/2)],p95_ms:sorted[Math.ceil(sorted.length*.95)-1],note:'Local headless requestAnimationFrame cadence; not a production rendering benchmark.'};
                }""")
                for name, width, height in [("desktop", 1440, 1000), ("tablet", 1024, 768), ("mobile", 390, 844)]:
                    page.set_viewport_size({"width":width, "height":height})
                    for panel in page.locator(".reveal-wait").all():
                        if panel.is_visible(): panel.scroll_into_view_if_needed()
                    page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")
                    page.wait_for_timeout(850)
                    page.wait_for_timeout(100)
                    check(f"{name}: no page overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
                    check(f"{name}: metric values fit their cards", page.locator("#metrics strong").evaluate_all("nodes => nodes.every(node=>node.scrollWidth<=node.clientWidth+1)"))
                    if name != "desktop":
                        check(f"{name}: section navigation stays available", page.locator(".mobile-nav").is_visible())
                    if root.name == "tenantledger" and name == "mobile":
                        check("mobile sign-out remains accessible", page.locator("#logout").is_visible())
                        check("mobile money stays on one line", page.locator("#metrics strong").first.evaluate("node => node.getBoundingClientRect().height < 40"))
                    page.screenshot(path=str(output / f"{name}.png"), full_page=True, animations="disabled")
                    page.screenshot(path=str(output / f"{name}-cover.png"), full_page=False, animations="disabled")
                    if name == "desktop" and args.browser == "chromium": page.screenshot(path=str(root / "docs/overview.png"), full_page=False, animations="disabled")
                check("no uncaught JavaScript errors", not errors)
                check("no HTTP 5xx responses", not failures)
                browser_version = browser.version
                context.close()
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
    result = {"checked_at":datetime.now(timezone.utc).isoformat(), "project":root.name,
              "browser":args.browser, "browser_version":browser_version, "checks":checks, "passed":len(checks), "page_errors":errors, "http_5xx":failures,
              "frame_cadence":frame_sample,
              "note":"Headless browser engine, isolated temporary server/database. WebKit on this host is not Safari. Includes domain workflows, keyboard navigation, theme/motion persistence, reduced motion, downloads, and three viewport widths."}
    (root / ("artifacts/browser-checks.json" if args.browser == "chromium" else f"artifacts/browser-checks-{args.browser}.json")).write_text(json.dumps(result, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"project":root.name, "browser":args.browser, "passed":len(checks), "page_errors":errors, "http_5xx":failures}))
