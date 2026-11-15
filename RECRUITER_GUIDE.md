# Presenting SignalLab

SignalLab evaluates when observed service errors should become an alert. The project combines a tested backend, a small interactive UI, and reproducible analysis of a concrete operational trade-off.

## A short introduction

“I built a local SLO alert replay studio based on the public Google SRE Workbook. It evaluates three policies on identical request counts. The key result is a trade-off: on the default synthetic trace, the multiwindow policy fires for 158 minutes instead of 207, but median incident detection moves from 3 to 37 minutes. I verified the request weighting against an independent brute-force calculation and made imported traces explicitly unlabeled.”

## Draft résumé bullets

- Built a Python and JavaScript SLO replay studio with request-weighted rolling windows, validated CSV import, SVG charts, and JSON export; verified 21 core/HTTP tests and 36 browser checks.
- Compared three alert policies across three seeded synthetic traces, measuring false episodes, firing duration, and detection delay; documented the precision and latency trade-offs without extrapolating to production traffic.

## Evidence to show

| Claim | Evidence |
|---|---|
| Correct request weighting | [Independent rolling-window oracle](signallab/tests/test_core.py) |
| Reproducible policy result | [Three-seed study](signallab/artifacts/policy-study.json) and [findings](signallab/docs/FINDINGS.md) |
| Working interface | [Browser check report](signallab/artifacts/browser-checks.json), screenshot, and the running demo |
| Reasoned engineering choices | [Research and design](signallab/docs/RESEARCH_AND_DESIGN.md) |

Use the [three-minute walkthrough](signallab/docs/DEMO.md) for a recorded or live demo. Be ready to change a workload or explain why an incomplete rolling window is unknown. The technical discussion matters more than the company name on the enclosing folder.

## Repository and source package

Use this **`google` folder as the repository root** so `.github/workflows/verify.yml` is at the top of the repository. A fresh clone runs with Python 3.11+ and no runtime installation. The app README includes optional browser tooling setup.

From this folder:

```powershell
python tools/package.py
python tools/package.py --check
```

This creates `dist/signallab-source.zip` with a per-file SHA-256 manifest. It includes source, documentation, screenshot, tests, and recorded evidence. Runtime databases/logs, environments, caches, and raw browser screenshots are excluded by an explicit file list.

GitHub Actions runs Windows/Linux core and HTTP tests, Chromium/Firefox/WebKit workflows, accessibility and mobile lab checks, verified source packaging, and the interactive Pages deployment. The link below shows actual remote run status; checked-in reports record local runs.

This is an independent portfolio project inspired by public Google engineering publications. It is not an internal Google system, an employer endorsement, or evidence of a particular team's language requirements.

## Published review

[Live browser demo](https://chauhanavi21.github.io/signallab/) | [Short recording](https://chauhanavi21.github.io/signallab/watch.html) | [CI runs](https://github.com/chauhanavi21/signallab/actions). Review the [release evidence](signallab/docs/RELEASE.md) for browser, accessibility, mobile and historical-data checks. The Pages demo runs temporary Python/SQLite state in-browser; use local HTTP mode to assess server-session and concurrency behavior.
