"""Build a deterministic, allowlisted source archive using the standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

PROJECT = "signallab"
EVIDENCE = (
    "browser-checks.json", "verification.json", "research-sources.json",
    "demo-report.json", "policy-study.json", "sample.csv",
)
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "dist" / f"{PROJECT}-source.zip"
MANIFEST = "PACKAGE_MANIFEST.json"


def sources():
    """An explicit list prevents databases, sessions, logs, and local envs entering."""
    root_files = (
        "README.md", "RECRUITER_GUIDE.md", ".gitignore", ".gitattributes",
        ".github/workflows/verify.yml", "tools/package.py", "tools/build_pages.py", "tools/pages_check.py",
        "tools/pages-assets.json", "tools/prepare_real_data.py",
        "tools/pages/demo.js", "tools/pages/worker.js", "tools/pages/bridge.py", "tools/pages/demo.css", "tools/pages/watch.html",
    )
    app_files = (
        "README.md", ".gitignore", "core.py", "server.py", "httpkit.py",
        "evidence.py", "verify.py", "research_check.py", "requirements-dev.txt",
        "browser_check.py", "browser_support.py", "quality_check.py", "real_data_check.py", "record_demo.py",
        "vendor/axe.min.js", "vendor/AXE-LICENSE", "data/provenance.json",
        "data/nasa-12h.csv", "web/index.html", "web/app.js",
        "web/style.css", "web/studio.js", "tests/httpcase.py", "tests/test_core.py", "tests/test_http.py",
        "docs/RESEARCH_AND_DESIGN.md", "docs/FINDINGS.md", "docs/DEMO.md", "docs/INTERFACE.md", "docs/overview.png", "docs/demo.webm", "docs/RELEASE.md",
    )
    names = [*root_files, *(f"{PROJECT}/{name}" for name in app_files),
             *(f"{PROJECT}/artifacts/{name}" for name in (*EVIDENCE, "browser-checks-firefox.json", "browser-checks-webkit.json", "quality-checks.json", "real-data-checks.json", "demo-recording.json", "pages-chromium.json", "pages-firefox.json", "pages-webkit.json"))]
    for name in ["pages-live-chromium.json", "pages-live-firefox.json", "pages-live-webkit.json"]:
        if (ROOT / PROJECT / "artifacts" / name).is_file():
            names.append(f"{PROJECT}/artifacts/{name}")
    result = {}
    for name in sorted(names):
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Expected a regular source file inside the project: {name}")
        result[name] = path.read_bytes()
    return result


def manifest(files):
    return {"format_version":1, "project":PROJECT,
            "files":[{"path":name, "bytes":len(content), "sha256":hashlib.sha256(content).hexdigest()}
                     for name,content in sorted(files.items())]}


def build(files):
    ARCHIVE.parent.mkdir(exist_ok=True)
    contents = {**files, MANIFEST:(json.dumps(manifest(files), indent=2)+"\n").encode("utf-8")}
    descriptor, temporary = tempfile.mkstemp(prefix="source-", suffix=".tmp", dir=ARCHIVE.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name,content in sorted(contents.items()):
                info = zipfile.ZipInfo(name, date_time=(2020,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content, compresslevel=9)
        os.replace(temporary, ARCHIVE)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def verify(files):
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = archive.namelist()
        expected = {*files, MANIFEST}
        if len(names) != len(expected) or set(names) != expected:
            raise ValueError("Archive entries differ from the source allowlist.")
        if json.loads(archive.read(MANIFEST)) != manifest(files):
            raise ValueError("Archive manifest differs from the current sources.")
        for name,content in files.items():
            if archive.read(name) != content: raise ValueError(f"Archive content mismatch: {name}")
        if archive.testzip() is not None: raise ValueError("Archive CRC verification failed.")
    return {"archive":ARCHIVE.name, "source_files":len(files), "bytes":ARCHIVE.stat().st_size,
            "sha256":hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
            "verified_against_current_sources":True,
            "note":"Allowlisted source and public demo evidence only. Runtime databases, sessions, logs, environments, caches, and raw browser output are excluded. Archive timestamps are normalized; evidence retains its recorded execution dates."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify an existing archive against current files")
    args = parser.parse_args()
    files = sources()
    if not args.check: build(files)
    record = verify(files)
    if not args.check:
        (ARCHIVE.parent / "source-package.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8", newline="\n")
    print(json.dumps(record,indent=2))
