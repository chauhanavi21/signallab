/* Only included in the Pages build. Local HTTP operation stays unchanged. */
(() => {
  const realFetch = window.fetch.bind(window);
  const worker = new Worker(new URL("./worker.js", document.currentScript.src));
  let sequence = 0;
  const pending = new Map();
  let resolveReady, rejectReady;
  const ready = new Promise((resolve, reject) => {
    resolveReady = resolve;
    rejectReady = reject;
  });
  ready.catch(() => {});
  function message(text, failed = false) {
    const banner = document.querySelector("#browser-demo");
    if (banner) {
      banner.textContent = text;
      if (text.startsWith("Interactive")) {
        const link = document.createElement("a");
        link.href = "./watch.html";
        link.textContent = " Watch walkthrough";
        link.style.cssText =
          "color:inherit;text-decoration:underline;margin-left:12px";
        banner.append(link);
      }
      banner.dataset.failed = String(failed);
    }
  }
  document.addEventListener("DOMContentLoaded", () => {
    const banner = document.createElement("p");
    banner.id = "browser-demo";
    banner.setAttribute("role", "status");
    document.body.prepend(banner);
    new ResizeObserver(() =>
      document.documentElement.style.setProperty(
        "--demo-banner-height",
        `${banner.getBoundingClientRect().height}px`,
      ),
    ).observe(banner);
    document.documentElement.dataset.demo = "browser";
    message(
      "Starting browser demo - Downloading Python once. Each tab has its own temporary data.",
    );
  });
  worker.onmessage = ({ data }) => {
    if (data.ready) {
      message(
        document.documentElement.dataset.project === "tenantledger"
          ? "Interactive browser demo - Data resets on reload. Sign-in illustrates the workflow; it is not server authentication."
          : "Interactive browser demo - Data resets on reload. Python calculations run privately in this tab.",
      );
      resolveReady();
      return;
    }
    if (data.fatal) {
      message(
        "The browser runtime could not start. Reload to retry, or run the Python app from the repository.",
        true,
      );
      rejectReady(new Error(data.fatal));
      return;
    }
    const request = pending.get(data.id);
    if (!request) return;
    pending.delete(data.id);
    if (data.error) request.reject(new Error(data.error));
    else
      request.resolve(
        new Response(JSON.stringify(data.body), {
          status: data.status,
          headers: { "Content-Type": "application/json" },
        }),
      );
  };
  worker.onerror = () => {
    message("The browser runtime stopped. Reload to start a fresh demo.", true);
    rejectReady(new Error("Browser worker failed"));
    for (const request of pending.values())
      request.reject(new Error("Browser worker failed"));
    pending.clear();
  };
  window.fetch = async (input, options = {}) => {
    const target = new URL(
      typeof input === "string" ? input : input.url,
      location.href,
    );
    if (!target.pathname.startsWith("/api/")) return realFetch(input, options);
    await ready;
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      pending.set(id, { resolve, reject });
      worker.postMessage({
        id,
        path: target.pathname + target.search,
        method: options.method || "GET",
        headers: Object.fromEntries(new Headers(options.headers)),
        body: options.body || null,
      });
    });
  };
})();
