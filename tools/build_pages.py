"""Build an isolated browser demo; vendor pinned Pyodide files with hash checks."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "signallab"
SITE = ROOT / "_site"


def asset(item):
    path = SITE / "vendor" / item["file"]
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
        with urllib.request.urlopen(item["url"], timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Vendor hash mismatch: {item['file']}")
        path.write_bytes(data)


def main():
    app = ROOT / PROJECT
    SITE.mkdir(exist_ok=True)
    (SITE / "vendor").mkdir(exist_ok=True)
    for name in ["app.js", "studio.js", "style.css"]:
        shutil.copyfile(app / "web" / name, SITE / name)
    for name in ["core.py", "server.py", "httpkit.py"]:
        shutil.copyfile(app / name, SITE / name)
    for name in ["demo.js", "worker.js", "bridge.py", "demo.css"]:
        shutil.copyfile(ROOT / "tools/pages" / name, SITE / name)
    html = (app / "web/index.html").read_text(encoding="utf-8")
    html = html.replace('href="/', 'href="./').replace('src="/', 'src="./')
    html = html.replace('<script src="./studio.js"', '<link rel="stylesheet" href="./demo.css" />\n    <script src="./demo.js"></script>\n    <script src="./studio.js"')
    (SITE / "index.html").write_text(html, encoding="utf-8")
    (SITE / ".nojekyll").touch()
    for name in ["demo.webm", "overview.png"]:
        shutil.copyfile(app / "docs" / name, SITE / name)
    shutil.copyfile(ROOT / "tools/pages/watch.html", SITE / "watch.html")
    manifest = json.loads((ROOT / "tools/pages-assets.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(asset, manifest["assets"]))
    print(f"Built {PROJECT} browser demo at {SITE}")


if __name__ == "__main__":
    main()
