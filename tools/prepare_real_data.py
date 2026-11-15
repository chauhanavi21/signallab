"""Rebuild the public, non-identifying fixture from its pinned source archive.

Optional network operation; normal validation uses the small committed fixture.
Use --archive PATH to supply an already downloaded .zip/.gz instead.
"""
import argparse
import collections
import csv
from decimal import Decimal, ROUND_HALF_EVEN
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "signallab"


def retail(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        workbook = outer.read("Online Retail.xlsx")
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows = []
    with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
        strings = ["".join(e.itertext()) for e in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        for _, row in ET.iterparse(archive.open("xl/worksheets/sheet1.xml"), events=["end"]):
            if not row.tag.endswith("}row"):
                continue
            source_row = int(row.attrib["r"])
            values = {}
            for cell in row:
                value = cell.find("s:v", ns)
                if value is None:
                    continue
                text = strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text
                values[re.sub("[0-9]", "", cell.attrib["r"])] = text
            if source_row == 1:
                continue
            try:
                quantity = int(values["D"])
                price = int((Decimal(values["F"]) * 100).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
                if values["A"].startswith("C") or not 1 <= quantity <= 1000 or price <= 0:
                    continue
                rows.append({"source_row":source_row, "invoice":values["A"], "stock_code":values["B"],
                             "quantity":quantity, "unit_price_pence":price})
            except (KeyError, ValueError):
                continue
            if len(rows) == 200:
                break
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return "retail-lines.csv", stream.getvalue()


def nasa(raw):
    counts = collections.defaultdict(lambda: [0, 0])
    pattern = re.compile(r'\[01/Jul/1995:(\d\d):(\d\d):\d\d -0400\].*"\s+(\d{3})\s')
    for line in gzip.decompress(raw).decode("latin1").splitlines():
        match = pattern.search(line)
        if match:
            minute = int(match[1]) * 60 + int(match[2])
            if minute < 720:
                counts[minute][0] += 1
                counts[minute][1] += int(int(match[3]) >= 500)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["minute", "service", "total", "bad"])
    for minute in range(720):
        writer.writerow([minute, "nasa-web", *counts[minute]])
    return "nasa-12h.csv", stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    provenance = json.loads((ROOT / PROJECT / "data/provenance.json").read_text())
    if args.archive:
        raw = args.archive.read_bytes()
    else:
        with urllib.request.urlopen(provenance["download_url"], timeout=120) as response:
            raw = response.read()
    if hashlib.sha256(raw).hexdigest() != provenance["download_sha256"]:
        raise ValueError("Source archive differs from the recorded SHA256; review provenance before changing it.")
    name, content = nasa(raw) if PROJECT == "signallab" else retail(raw)
    data = content.encode("utf-8")
    if hashlib.sha256(data).hexdigest() != provenance["fixture_sha256"]:
        raise ValueError("Regenerated fixture differs from the recorded SHA256.")
    (ROOT / PROJECT / "data" / name).write_bytes(data)
    print(f"Reproduced {name} with matching source and fixture hashes.")


if __name__ == "__main__":
    main()
