"""Optional public-source retrieval record; not needed to run or verify the app."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from core import SOURCES


class Title(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active, self.done, self.parts = False, False, []
    def handle_starttag(self, tag, attrs):
        if tag == "title" and not self.done: self.active = True
    def handle_endtag(self, tag):
        if tag == "title" and self.active: self.active, self.done = False, True
    def handle_data(self, data):
        if self.active: self.parts.append(data)


def fetch(source):
    request = Request(source["url"], headers={"User-Agent":"PortfolioResearch/1.0 (public engineering source verification)"})
    with urlopen(request, timeout=30) as response:
        data = response.read(5_000_000)
        parser = Title()
        parser.feed(data.decode("utf-8", errors="replace"))
        return {**source, "page_title":" ".join("".join(parser.parts).split()),
                "resolved_url":response.url, "http_status":response.status, "bytes":len(data),
                "content_sha256":hashlib.sha256(data).hexdigest(), "retrieved_at":datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as pool: records = list(pool.map(fetch, SOURCES))
    path = Path(__file__).resolve().parent / "artifacts/research-sources.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(records, indent=2))
