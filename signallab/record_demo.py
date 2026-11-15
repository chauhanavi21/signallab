"""Record a short captioned, silent walkthrough against a clean local server."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from quality_check import isolated, ready

ROOT = Path(__file__).resolve().parent


def main():
    from playwright.sync_api import sync_playwright, expect
    destination = ROOT / "docs/demo.webm"
    temporary = ROOT / "runtime/video"
    temporary.mkdir(parents=True, exist_ok=True)
    chapters = []
    with isolated() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width":1280,"height":800},
            record_video_dir=str(temporary), record_video_size={"width":1280,"height":800})
        page = context.new_page()
        page.goto(base)
        ready(page)
        page.evaluate("""() => {
            const caption=document.createElement('div');caption.id='walkthrough-caption';
            caption.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:200;max-width:1000px;width:calc(100% - 100px);padding:18px 24px;border:1px solid var(--accent);border-radius:12px;background:var(--surface);color:var(--ink);box-shadow:0 12px 40px #0005;font:600 18px/1.5 system-ui';
            document.body.append(caption);
        }""")
        def caption(text, selector=None, wait=4500):
            chapters.append(text)
            page.locator("#walkthrough-caption").evaluate("(node,text) => node.textContent=text", text)
            if selector:
                page.locator(selector).scroll_into_view_if_needed()
            page.wait_for_timeout(wait)
        if ROOT.name == "parcelguard":
            caption("ParcelGuard · Reserve once. Recover safely from a lost acknowledgement.")
            page.fill("#key", "walkthrough-01")
            page.fill("#quantity", "2")
            page.click("#order")
            expect(page.locator("#order-result")).to_contain_text("CREATED")
            caption("1 / A new request commits inventory, order, cached response and outbox together.", "#order-result")
            page.click("#order")
            expect(page.locator("#order-result")).to_contain_text("REPLAY")
            caption("2 / Repeating the same intent replays its response. Stock is reserved once.")
            page.select_option("#fault", "after_delivery")
            page.click("#dispatch")
            expect(page.locator("#worker-result")).to_contain_text("ack lost")
            caption("3 / The consumer commits, then the acknowledgement is lost. One effect; work remains pending.", "#worker-result")
            page.click("#advance")
            page.select_option("#fault", "none")
            page.click("#dispatch")
            expect(page.locator("#worker-result")).to_contain_text("duplicate delivery suppressed")
            caption("4 / Redelivery is acknowledged. The unique consumer event key suppresses a second local effect.")
            caption("5 / Compare completion and attempts together. Latency includes successful clients only.", "#experiment-table", 5500)
            caption("Independent local prototype · Synthetic retry model · Full source, tests and limitations in the repository.", "#method")
        elif ROOT.name == "tenantledger":
            caption("TenantLedger · Two workspaces. Precise postings. A verifiable audit trail.")
            page.click("#aster-login")
            expect(page.locator("#workspace")).to_be_visible()
            caption("1 / The signed-in identity selects Aster Labs. Clients cannot choose an arbitrary tenant.", "#tenant-name")
            page.fill("#amount", "12.34")
            page.fill("#memo", "Walkthrough allocation")
            page.click("#transfer")
            expect(page.locator("#status")).to_contain_text("transferred")
            caption("2 / Move exactly 1,234 integer cents. Matching postings and an audit entry commit atomically.", "#history")
            page.click("#probe")
            expect(page.locator("#probe-result")).to_contain_text("PASS")
            caption("3 / An account from the other tenant is hidden by the application query boundary.", "#probe-result")
            page.click("#logout")
            page.click("#harbor-login")
            expect(page.locator("#tenant-name")).to_have_text("Harbor Studio")
            caption("4 / Harbor Studio has separate balances and history. Aster's transfer stays in Aster.", "#metrics", 5500)
            caption("Independent local prototype · Public demo identities · SQLite application isolation, not database RLS.", "#method", 5500)
        else:
            caption("SignalLab · Replay one traffic trace through three SLO alert policies.")
            caption("1 / Request-weighted burn uses actual request counts and complete rolling windows.", "#chart", 5500)
            page.select_option("#service", "search-api")
            caption("2 / Switch services to inspect their five-minute and one-hour burn.")
            caption("3 / Compare episodes, false episodes, firing time and detection delay together.", "#comparison", 5500)
            page.fill("#slo", "99.95")
            page.click("#run")
            expect(page.locator("#run")).to_be_enabled()
            caption("4 / Change the SLO and replay the same seed. Every chart and table is recomputed.", "#comparison", 5500)
            caption("5 / Multiwindow rules trade shorter firing time for later detection in this synthetic trace.", "#comparison", 5500)
            caption("Independent local evaluator · Import your own counts · No production paging or universal-winner claims.", "#method")
        video = page.video
        context.close()
        recorded = video.path()
        shutil.copyfile(recorded, destination)
        recorded.unlink()
        browser.close()
    metadata = {"recorded_at": datetime.now(timezone.utc).isoformat(), "file": "docs/demo.webm",
                "bytes": destination.stat().st_size, "sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
                "viewport": "1280x800", "format": "WebM", "audio": "Silent, with on-screen captions",
                "chapters": chapters, "scope": "Uncut automated capture of the local Python app with an isolated temporary database."}
    (ROOT / "artifacts/demo-recording.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps({"project":ROOT.name,"video_bytes":metadata["bytes"]}))


if __name__ == "__main__":
    main()
