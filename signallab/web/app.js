"use strict";
const el = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
const num = (value, digits = 0) =>
  value == null
    ? "—"
    : Number(value).toLocaleString("en-US", { maximumFractionDigits: digits });
const pct = (value, digits = 1) =>
  value == null ? "—" : `${num(value * 100, digits)}%`;
const usd = (cents) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
async function api(path, body, headers = {}) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined
        ? headers
        : { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(result.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return result;
}
function notice(message, error = false) {
  el("status").textContent = message;
  el("status").classList.toggle("error", error);
  window.Studio?.celebrate(el("status"));
}
async function busy(button, action) {
  if (button.disabled) return;
  button.disabled = true;
  button.classList.add("is-loading");
  button.setAttribute("aria-busy", "true");
  try {
    await action();
  } catch (error) {
    notice(error.message, true);
  } finally {
    button.disabled = false;
    button.classList.remove("is-loading");
    button.removeAttribute("aria-busy");
  }
}
function download(name, value, type = "application/json") {
  const url = URL.createObjectURL(
    new Blob(
      [typeof value === "string" ? value : JSON.stringify(value, null, 2)],
      { type },
    ),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
function table(headers, rows, highlight = -1) {
  return rows.length
    ? `<table><thead><tr>${headers.map((x) => `<th scope="col">${esc(x)}</th>`).join("")}</tr></thead><tbody>${rows.map((row, i) => `<tr class="${i === highlight ? "highlight" : ""}">${row.map((x) => `<td>${esc(x)}</td>`).join("")}</tr>`).join("")}</tbody></table>`
    : '<p class="empty">No records yet.</p>';
}
function metric(label, value, detail, accent = false) {
  return `<article class="metric"><span class="label">${esc(label)}${window.Studio?.icon(accent ? "bolt" : "chart") || ""}</span><strong class="${accent ? "metric-accent" : ""}">${esc(value)}</strong><small>${esc(detail)}</small></article>`;
}
function method(report) {
  el("method-content").innerHTML =
    `<div class="method-grid"><ul>${report.notes.map((x) => `<li>${esc(x)}</li>`).join("")}</ul><div>${report.sources.map((x) => `<a class="source-link" href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)} ↗</a>`).join("")}<p class="caption">Source research checked November 14, 2026. This project implements a small local model of these ideas.</p></div></div>`;
}
// DOMAIN
let report, importedCSV;
function config() {
  const result = {
    slo: Number((Number(el("slo").value) / 100).toFixed(5)),
    seed: Number(el("seed").value),
    min_requests: Number(el("minimum").value),
  };
  if (importedCSV !== undefined) result.csv = importedCSV;
  return result;
}
async function replay() {
  notice("Replaying traffic and evaluating all three policies…");
  const next = await api("/api/analyze", config());
  report = next;
  render();
  notice(
    `${report.synthetic ? "Synthetic" : "Imported"} replay complete · ${num(report.summary.total)} requests · run ${report.run_id.slice(0, 12)}`,
  );
}
function render() {
  const summary = report.summary,
    multi = report.comparison[2],
    short = report.comparison[1];
  el("export").disabled = false;
  el("dataset").textContent = report.synthetic
    ? "Synthetic incident trace · 12 hours · 3 services"
    : `Imported CSV · ${summary.service_count} service(s) · no incident labels`;
  el("metrics").innerHTML =
    metric(
      "Observed requests",
      num(summary.total),
      `${summary.service_count} services in this replay`,
    ) +
    metric(
      "Availability",
      pct(summary.availability, 3),
      "Request-weighted across services",
    ) +
    metric(
      "Replay budget use",
      `${num(summary.replay_budget_use, 2)}×`,
      "Against observed requests, not a month",
    ) +
    metric(
      "Multiwindow episodes",
      num(multi.episodes),
      `${num(multi.firing_minutes)} firing minutes`,
      true,
    );
  const selected = el("service").value;
  el("service").innerHTML = report.services
    .map((s) => `<option value="${esc(s.service)}">${esc(s.service)}</option>`)
    .join("");
  if (report.services.some((s) => s.service === selected))
    el("service").value = selected;
  else
    el("service").value =
      report.services.find((s) => s.service === "checkout-api")?.service ||
      report.services[0].service;
  el("comparison").innerHTML = table(
    [
      "Policy",
      "Episodes",
      "Firing min",
      "Precision",
      "Recall",
      "Median delay",
      "False episodes",
    ],
    report.comparison.map((p) => [
      p.name,
      num(p.episodes),
      num(p.firing_minutes),
      pct(p.precision, 0),
      pct(p.recall, 0),
      p.median_detection_minutes == null
        ? "—"
        : `${num(p.median_detection_minutes, 1)} min`,
      num(p.false_episodes),
    ]),
    2,
  );
  el("label-state").textContent = report.synthetic
    ? "2 synthetic incident labels"
    : "Unlabeled imported data";
  el("finding").innerHTML =
    `<span class="big-number">${num(multi.firing_minutes)} min</span><p>Multiwindow firing time, compared with <strong>${num(short.firing_minutes)} minutes</strong> for the five-minute policy.</p><p>${report.synthetic ? `Median detection delay: <strong>${num(multi.median_detection_minutes, 1)} min</strong> versus <strong>${num(short.median_detection_minutes, 1)} min</strong>. Less firing time can come with later detection.` : "Detection precision, recall, and delay are unavailable without labeled incidents. Compare firing behavior, then validate against your own incident history."}</p>`;
  el("alerts").innerHTML = table(
    ["Service", "Start", "Duration"],
    report.alerts.map((a) => [
      a.service,
      `minute ${a.start}`,
      `${a.duration_minutes} min`,
    ]),
  );
  method(report);
  chart();
  renderHero();
  window.Studio?.refresh();
}
function renderHero() {
  const services = report.services.slice(0, 3);
  el("hero-visual").innerHTML =
    `<div class="frame-header"><span>SERVICE SIGNALS</span><div class="frame-dots" aria-hidden="true"><i></i><i></i><i></i></div></div><div class="signal-list">${services
      .map((service, index) => {
        const rows = report.series.filter(
            (row) => row.service === service.service,
          ),
          stride = Math.max(1, Math.floor(rows.length / 70));
        const samples = rows.filter((_, i) => i % stride === 0),
          ceiling = Math.max(1, ...samples.map((row) => row.burn_5m || 0));
        let open = false;
        const path = samples
          .map((row, i) => {
            if (row.burn_5m == null) {
              open = false;
              return "";
            }
            const point = `${open ? "L" : "M"}${((i / Math.max(1, samples.length - 1)) * 90).toFixed(1)},${(25 - (row.burn_5m / ceiling) * 21).toFixed(1)}`;
            open = true;
            return point;
          })
          .join(" ");
        return `<div class="service-signal"><span class="service-name">${esc(service.service)}</span><svg viewBox="0 0 90 28" aria-hidden="true" style="color:var(${["--accent", "--teal", "--amber"][index]})"><path data-draw d="${path}" stroke="currentColor" stroke-width="1.25" fill="none"/></svg><strong>${pct(service.availability, 2)}</strong></div>`;
      })
      .join(
        "",
      )}</div><div class="frame-footer"><span><i class="status-dot"></i>${report.synthetic ? "SEEDED REPLAY" : "IMPORTED TRACE"}</span><span>${report.summary.service_count} SERVICES / AVAILABILITY</span></div>`;
  window.Studio?.draw(el("hero-visual"));
}
function chart() {
  if (!report) return;
  const rows = report.series.filter((r) => r.service === el("service").value),
    w = 720,
    h = 270,
    l = 43,
    r = 14,
    t = 16,
    b = 34;
  const values = rows
      .flatMap((row) => [row.burn_5m, row.burn_1h])
      .filter((v) => v != null),
    ymax = Math.ceil((Math.max(20, ...values) * 1.1) / 5) * 5;
  const x = (i) => l + (i / Math.max(1, rows.length - 1)) * (w - l - r),
    y = (v) => h - b - (v / ymax) * (h - t - b);
  const path = (key) => {
    let open = false;
    return rows
      .map((row, i) => {
        if (row[key] == null) {
          open = false;
          return "";
        }
        const value = `${open ? "L" : "M"}${x(i).toFixed(2)},${y(row[key]).toFixed(2)}`;
        open = true;
        return value;
      })
      .join(" ");
  };
  const ticks = Array.from({ length: 5 }, (_, i) => (ymax * i) / 4);
  const labels = Array.from({ length: 5 }, (_, i) =>
    Math.round(((rows.length - 1) * i) / 4),
  );
  const incidents = (report.incidents || []).filter(
    (inc) => inc.service === el("service").value,
  );
  el("chart").removeAttribute("aria-live");
  el("chart").innerHTML =
    `<svg viewBox="0 0 ${w} ${h}" role="img" tabindex="0" aria-label="Five-minute and one-hour burn for ${esc(el("service").value)}. Use arrow keys to inspect each minute; Home and End jump to the boundaries."><title>Burn-rate replay. Shaded bands mark synthetic incidents. Unknown windows are blank.</title>${incidents.map((inc) => `<rect class="incident-band" x="${x(inc.start)}" y="${t}" width="${x(Math.min(inc.end, rows.length - 1)) - x(inc.start)}" height="${h - b - t}"/>`).join("")}${ticks.map((v) => `<line class="chart-grid" x1="${l}" x2="${w - r}" y1="${y(v)}" y2="${y(v)}"/><text class="chart-axis" x="${l - 8}" y="${y(v) + 4}" text-anchor="end">${num(v, 0)}×</text>`).join("")}<line class="threshold-line" x1="${l}" x2="${w - r}" y1="${y(14.4)}" y2="${y(14.4)}" stroke-dasharray="4 4"/><path data-draw class="burn-short" d="${path("burn_5m")}" fill="none" stroke-width="1.8"/><path data-draw class="burn-long" d="${path("burn_1h")}" fill="none" stroke-width="2.2"/>${labels.map((i) => `<text class="chart-axis" x="${x(i)}" y="${h - 9}" text-anchor="middle">${num(i / 60, 1)}h</text>`).join("")}<line class="chart-crosshair" x1="${l}" x2="${l}" y1="${t}" y2="${h - b}" visibility="hidden"/></svg><div class="chart-tooltip" hidden></div><div class="chart-helper">Hover to inspect · Focus chart + ← → to explore · Shaded bands = demo incidents</div><span id="chart-readout" class="sr-only" aria-live="polite"></span>`;
  const svg = el("chart").querySelector("svg"),
    tooltip = el("chart").querySelector(".chart-tooltip"),
    crosshair = svg.querySelector(".chart-crosshair");
  let selected = 0;
  function inspect(index, announce = false) {
    selected = Math.max(0, Math.min(rows.length - 1, index));
    const row = rows[selected],
      burn = (value) => (value == null ? "Unavailable" : `${num(value, 2)}×`);
    crosshair.setAttribute("x1", x(selected));
    crosshair.setAttribute("x2", x(selected));
    crosshair.setAttribute("visibility", "visible");
    tooltip.hidden = false;
    tooltip.innerHTML = `<strong>Minute ${row.minute}</strong><br><span>5m burn</span> ${burn(row.burn_5m)}<br><span>1h burn</span> ${burn(row.burn_1h)}<br><span>Requests</span> ${num(row.total)}`;
    const bounds = el("chart").getBoundingClientRect(),
      position = (x(selected) / w) * svg.getBoundingClientRect().width;
    // CSS recalculates the upper bound when the viewport changes while the
    // chart retains keyboard focus. A fixed pixel left could overflow mobile.
    tooltip.style.left = `clamp(0px, ${position + 12}px, calc(100% - ${tooltip.offsetWidth}px))`;
    if (announce)
      el("chart-readout").textContent =
        `Minute ${row.minute}, five-minute burn ${burn(row.burn_5m)}, one-hour burn ${burn(row.burn_1h)}, ${row.total} requests.`;
  }
  svg.addEventListener("pointermove", (event) => {
    if (event.pointerType === "touch") return;
    const bounds = svg.getBoundingClientRect();
    inspect(
      Math.round(
        ((((event.clientX - bounds.left) / bounds.width) * w - l) /
          (w - l - r)) *
          (rows.length - 1),
      ),
    );
  });
  svg.addEventListener("pointerleave", () => {
    if (document.activeElement !== svg) {
      tooltip.hidden = true;
      crosshair.setAttribute("visibility", "hidden");
    }
  });
  svg.addEventListener("focus", () => inspect(selected, true));
  svg.addEventListener("blur", () => {
    tooltip.hidden = true;
    crosshair.setAttribute("visibility", "hidden");
  });
  svg.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    inspect(
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? rows.length - 1
          : selected +
            (event.key === "ArrowLeft" ? -1 : 1) * (event.shiftKey ? 30 : 1),
      true,
    );
  });
  window.Studio?.draw(el("chart"));
}
el("config").addEventListener("submit", (event) => {
  event.preventDefault();
  busy(el("run"), replay);
});
el("service").addEventListener("change", chart);
el("export").addEventListener("click", () =>
  download(`signallab-${report.run_id.slice(0, 12)}.json`, report),
);
el("sample").addEventListener("click", () =>
  busy(el("sample"), async () => {
    const data = await api("/api/sample");
    download("signallab-sample.csv", data.csv, "text/csv");
    notice("Sample CSV downloaded.");
  }),
);
el("csv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  await busy(el("run"), async () => {
    if (file.size > 800000) throw Error("CSV must be smaller than 800 KB.");
    const prior = importedCSV;
    importedCSV = await file.text();
    try {
      await replay();
    } catch (error) {
      importedCSV = prior;
      throw error;
    }
  });
  event.target.value = "";
});
el("reset").addEventListener("click", () =>
  busy(el("run"), async () => {
    importedCSV = undefined;
    await replay();
  }),
);
busy(el("run"), replay);
