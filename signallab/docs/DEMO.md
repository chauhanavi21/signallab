# SignalLab: three-minute walkthrough

Run `python server.py` from `signallab` and open http://127.0.0.1:8770. If that port is in use, run `python server.py --port 8780` and open port 8780. No cloud account or setup data is needed.

## 0:00–0:30 — State the operational question

“The question is when a service's error rate should become a page. This is a synthetic 12-hour replay, not a production uptime claim.” Keep SLO 99.9%, seed 42, and minimum requests 100. Run the replay.

Point out the three policies in the comparison table and the difference between alert episodes and total firing minutes.

## 0:30–1:20 — Show the measurable trade-off

Select `checkout-api` in the chart. Explain that burn is the window's error ratio divided by the allowed error ratio, with requests used as weights. Complete windows are required.

On the default trace, the five-minute policy produces 2 episodes, 207 firing minutes, and 3 minutes median detection delay. Multiwindow produces 2 episodes, 158 firing minutes, and 37 minutes median delay. Both detect the two hand-labeled actionable incidents. The one-minute threshold creates 88 episodes, 86 of them outside those labels.

“The longer windows reduce firing time and noise in these examples, but can detect later. This experiment helps expose that choice.”

## 1:20–2:00 — Change an assumption

Change SLO to 99.95% and run again. Explain that the same failures consume more of a smaller allowed error budget; the chart and policies recompute from the counts.

Download the sample CSV. Import it to demonstrate that CSV imports have no incident labels, so precision, recall, and detection delay become unavailable. This prevents a plausible-looking but invented score.

## 2:00–2:40 — Show the evidence

Export the report and point out the normalized configuration and run hash. Open `artifacts/policy-study.json` for the three seeded repetitions, then `tests/test_core.py` for the independent rolling-window calculation.

“The repetitions change background noise but keep the same incident shapes. They do not establish a general ranking or confidence interval.”

## 2:40–3:00 — Explain one boundary

Replay budget use is relative to observed requests; 12 hours of observations cannot measure a real 30-day remaining budget. The next useful validation would use independently labeled real request traces and a held-out evaluation period.

Finish with the measured trade-off and the reasoning behind the model. All on-screen outputs are computed by the local API; this app sends no alerts.
