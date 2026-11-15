# Release and review evidence

[Interactive browser demo](https://chauhanavi21.github.io/signallab/) | [Captioned walkthrough](https://chauhanavi21.github.io/signallab/watch.html) | [Repository](https://github.com/chauhanavi21/signallab) | [GitHub Actions](https://github.com/chauhanavi21/signallab/actions)

## Two execution modes

The local app runs a loopback Python HTTP server and, where applicable, SQLite transactions. The public GitHub Pages demo reuses the same core.py and API domain methods in a dedicated Pyodide 0.27.7 worker. Python, SQLite and OpenSSL runtime files are self-hosted in the Pages build and checked against SHA256 pins in tools/pages-assets.json. They are fetched only during the build. No Python server runs on Pages.

Each browser tab has an independent in-memory filesystem and temporary database. Reload resets the workspace. The Pages adapter serializes requests and cannot demonstrate server concurrency, real HTTP cookie security, multi-user isolation, or durability across reloads. TenantLedger's browser sign-in is illustrative; anyone controlling the client can inspect or change its state. The local HTTP tests cover its server-side session boundary.

The browser runtime downloads about 16.5 MB before its first computation. This can take a minute or more on a slow connection; the banner reports loading and failure. Browser caching reduces repeat transfer. No user data is uploaded by the demo. Local execution avoids that runtime download.

## Browser and accessibility checks

The local acceptance suite runs in Chromium, Firefox and Playwright WebKit. WebKit on Windows/Linux is an engine test, not Safari or iPhone validation. The Pages build separately runs the domain workflows in all three engines, including tab isolation for the stateful projects. Reports are in artifacts/browser-checks*.json and artifacts/pages-*.json. Separate artifacts/pages-live-*.json records identify checks against the public URL. GitHub Actions reruns these checks on Ubuntu, and the core/HTTP tests on Ubuntu and Windows.

axe-core 4.10.3 reports **0 automated violations** across 4 combinations of state, light/dark theme and 1440/390 px viewport. The audit injects its local development script with CSP bypass; the acceptance suite exercises the actual CSP without bypass. Incomplete audit rules still require manual review. Automated results are not a WCAG conformance claim; screen-reader testing remains a human task.

Keyboard-scrollable tables now have named focusable regions. Navigation indices and ledger hashes have stronger light-theme contrast. Existing reduced-motion, motion toggle, keyboard command palette and responsive checks remain active.

## Mobile lab measurement

Local HTTP app, cold cache, headless Chromium, 390x844 viewport, 4x CPU slowdown, 150 ms latency, 1.6 Mbps down / 0.75 Mbps up, reduced motion:

- Initial UI ready: **5069 ms** (8,000 ms budget).
- Observed layout shift: **0.0064** (0.1 budget).
- Horizontal page overflow: **false**.

This is one local lab navigation, not real-device or field Core Web Vitals evidence. It does not include the Pages Python download, measure INP, or establish percentile performance. Raw observer entries and methodology are in artifacts/quality-checks.json.

## Historical-data validation

Source: **NASA-HTTP July 1995**. The small fixture and full attribution, selection, limitations and archive/fixture hashes are in data/. No source customer IDs, network addresses or request paths are included.

Run `python signallab/real_data_check.py` from the repository root. The normal verify.py command also runs it. Results are in artifacts/real-data-checks.json. These checks validate importer and transaction invariants with historical inputs; synthetic incidents, retries and failures remain labeled as synthetic.

To reproduce the fixture, run `python tools/prepare_real_data.py` (optional network download), or provide `--archive PATH`. Both source and generated fixture hashes must match the recorded provenance. UCI Online Retail is attributed to Daqing Chen, DOI 10.24432/C5BW33, under CC BY 4.0. NASA-HTTP is described by its source as freely available without an explicit SPDX license; only non-identifying count aggregates are included.

## Recording and reproduction

[Watch the recording](https://chauhanavi21.github.io/signallab/watch.html). docs/demo.webm is an uncut, silent, captioned capture of the local app against an isolated server and database. The metadata, chapters and content hash are in artifacts/demo-recording.json. The longer text walkthrough is in docs/DEMO.md.

From signallab/ with optional Playwright installed, run `python record_demo.py` to reproduce the capture. Core/runtime code still has no third-party Python dependency. axe-core is an optional development tool under its bundled MPL 2.0 license; the Pages runtime retains separate upstream notices in its vendor directory.
