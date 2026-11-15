"""Exercise the actual Pages build, including Python worker, APIs, and tab isolation."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "signallab"
sys.path.insert(0, str(ROOT / PROJECT))


class Request:
    def __init__(self, page):
        self.page = page

    def get(self, url):
        return self.call(url, "GET")

    def post(self, url, data):
        return self.call(url, "POST", data)

    def call(self, url, method, data=None):
        response = self.page.evaluate("""async ({url,method,data}) => {
            const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},...(method==='POST'?{body:JSON.stringify(data)}:{})});
            return {status:r.status,body:await r.json()};
        }""", {"url": url, "method": method, "data": data})
        return SimpleNamespace(status=response["status"], json=lambda: response["body"])


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    from playwright.sync_api import sync_playwright, expect
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Test the deployed Pages site instead of a local build")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    args = parser.parse_args()
    server = None
    if args.url:
        base = args.url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/_site/"
    checks, errors = [], []
    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
        if not passed:
            raise AssertionError(name)
    try:
        with sync_playwright() as p:
            browser = getattr(p, args.browser).launch()
            context = browser.new_context(viewport={"width":1440,"height":1000}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(60000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base)
            expect(page.locator("#browser-demo")).to_contain_text("Data resets", timeout=120000)
            output = ROOT / PROJECT / "artifacts/browser/pages" / args.browser
            output.mkdir(parents=True, exist_ok=True)
            scenario = importlib.import_module("browser_check").scenario
            scenario(page, SimpleNamespace(request=Request(page)), "", output, check)
            page.set_viewport_size({"width":390,"height":844})
            page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")
            check("Pages mobile layout has no horizontal overflow", page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"))
            check("Pages mobile metric values fit", page.locator("#metrics strong").evaluate_all("nodes=>nodes.every(n=>n.scrollWidth<=n.clientWidth+1)"))
            page.screenshot(path=str(output / "mobile.png"), animations="disabled")
            page.keyboard.press("Control+k")
            expect(page.locator("#command-dialog")).to_be_visible()
            page.keyboard.press("Escape")
            check("Pages keyboard palette opens and closes", page.locator("#command-dialog").is_hidden())
            fresh = context.new_page()
            fresh.goto(base)
            expect(fresh.locator("#browser-demo")).to_contain_text("Data resets", timeout=120000)
            # API interception uses /api/, exactly like the original app.
            isolated = Request(fresh).get("/api/workspace") if PROJECT != "signallab" else None
            if PROJECT == "parcelguard":
                check("a second tab has a separate empty database", isolated.json()["summary"]["orders"] == 0)
            elif PROJECT == "tenantledger":
                check("sign-in does not leak to another tab", isolated.status == 401)
            page.reload()
            expect(page.locator("#browser-demo")).to_contain_text("Data resets", timeout=120000)
            if PROJECT == "parcelguard":
                check("reload clears the temporary order database", Request(page).get("/api/workspace").json()["summary"]["orders"]==0)
            elif PROJECT == "tenantledger":
                check("reload clears the demo session", Request(page).get("/api/workspace").status==401)
            check("no uncaught JavaScript errors", not errors)
            browser.close()
    finally:
        if server:
            server.shutdown()
            thread.join(5)
            server.server_close()
    result = {"project": PROJECT, "browser": args.browser, "target": args.url or "local subdirectory Pages build",
              "checks": checks, "passed": len(checks), "page_errors": errors,
              "scope": "Actual in-browser Python execution. No server-side HTTP/session/concurrency guarantee is inferred."}
    name = "pages-live" if args.url else "pages"
    (ROOT / PROJECT / f"artifacts/{name}-{args.browser}.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({"project": PROJECT, "browser": args.browser, "target": name, "passed":len(checks)}))


if __name__ == "__main__":
    main()
