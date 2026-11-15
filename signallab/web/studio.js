/* Shared progressive enhancement for the three standalone workspaces. */
(() => {
  "use strict";
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const fine = matchMedia("(hover: hover) and (pointer: fine)");
  const icons = {
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    moon: '<path d="M20.5 14A9 9 0 0 1 10 3.5 9 9 0 1 0 20.5 14Z"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    play: '<path d="m8 5 11 7-11 7Z"/>',
    arrow: '<path d="m7 14 5-5 5 5M12 9v12M4 4h16"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    chart: '<path d="M3 4v16h18M6 14l4-5 4 3 6-7"/>',
    layers: '<path d="m12 3 10 5-10 5L2 8l10-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
    book: '<path d="M12 5v16M3 3c4 0 6 0 9 2 3-2 5-2 9-2v15c-4 0-6 0-9 2-3-2-5-2-9-2Z"/>',
    check: '<path d="m5 12 4 4L20 5"/>',
    bolt: '<path d="m13 2-9 12h7l-1 8L21 9h-8l1-7Z"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
  };
  const svg = (name, cls = "") =>
    `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.grid}</svg>`;
  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };
  const write = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* Storage can be unavailable. */
    }
  };
  let allowed = true;
  const observed = new WeakSet();
  const animatedBars = new WeakSet();
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.remove("reveal-wait");
        entry.target.classList.add("revealed");
        if (allowed)
          entry.target.animate(
            [
              { opacity: 0, transform: "translateY(20px)" },
              { opacity: 1, transform: "translateY(0)" },
            ],
            {
              duration: 620,
              delay: Number(entry.target.dataset.stagger || 0),
              easing: "cubic-bezier(.16,1,.3,1)",
              fill: "backwards",
            },
          );
        observer.unobserve(entry.target);
      }
    },
    { threshold: 0.06, rootMargin: "0px 0px 35px 0px" },
  );

  function setMotion() {
    allowed = !reduce.matches && read("studio-motion") !== "off";
    root.dataset.motion = allowed ? "on" : "off";
    const button = document.getElementById("motion-toggle");
    button.innerHTML = svg(allowed ? "pause" : "play");
    button.setAttribute("aria-pressed", String(!allowed));
    button.setAttribute(
      "aria-label",
      reduce.matches
        ? "Animations paused by system preference"
        : allowed
          ? "Pause animations"
          : "Enable animations",
    );
    button.setAttribute("aria-disabled", String(reduce.matches));
    button.title = reduce.matches
      ? "Reduced motion follows your system preference"
      : allowed
        ? "Pause animations"
        : "Enable animations";
    if (!allowed) {
      document.getAnimations().forEach((animation) => animation.cancel());
      document
        .querySelectorAll(".reveal-wait")
        .forEach((node) => node.classList.remove("reveal-wait"));
    }
  }

  function setTheme(theme) {
    root.dataset.appearance = theme;
    const button = document.getElementById("theme-toggle");
    button.innerHTML = svg(theme === "dark" ? "sun" : "moon");
    button.setAttribute(
      "aria-label",
      `Switch to ${theme === "dark" ? "light" : "dark"} theme`,
    );
    button.title = button.getAttribute("aria-label");
    document.querySelector('meta[name="theme-color"]').content =
      theme === "dark" ? "#0b1018" : "#f5f7f4";
  }

  const header = document.querySelector(".topbar");
  const tools = document.createElement("div");
  tools.className = "topbar-tools";
  tools.innerHTML = `<span class="workspace-indicator"><i></i> LOCAL WORKSPACE</span><button class="search-trigger" id="command-open" type="button" aria-label="Search workspace sections" aria-keyshortcuts="Control+K Meta+K">${svg("search")}<span>Jump to</span><kbd>Ctrl K</kbd></button><div class="toolbar-divider"></div><button class="icon-button" id="theme-toggle" type="button"></button><button class="icon-button" id="motion-toggle" type="button"></button>`;
  header.append(tools);
  const progress = document.createElement("div");
  progress.className = "reading-progress";
  progress.setAttribute("aria-hidden", "true");
  header.append(progress);
  const skip = document.createElement("a");
  skip.className = "skip-link";
  skip.href = "#overview";
  skip.textContent = "Skip to workspace";
  document.body.prepend(skip);

  const navigation = document.querySelector("aside nav");
  const destinations = [...navigation.querySelectorAll("a")].map(
    (link, index) => {
      const name = link.childNodes[0].textContent.trim();
      const number =
        link.querySelector("span")?.textContent ||
        String(index + 1).padStart(2, "0");
      link.replaceChildren();
      link.insertAdjacentHTML(
        "beforeend",
        svg(["grid", "chart", "layers", "book", "book"][index], "nav-symbol"),
      );
      const label = document.createElement("span");
      label.className = "nav-text";
      label.textContent = name;
      link.append(label);
      const count = document.createElement("span");
      count.className = "nav-index";
      count.textContent = number;
      link.append(count);
      return {
        name,
        hash: link.hash,
        section: document.querySelector(link.hash),
      };
    },
  );
  navigation.setAttribute("aria-label", "Workspace sections");
  const mobile = document.createElement("nav");
  mobile.className = "mobile-nav";
  mobile.setAttribute("aria-label", "Mobile workspace sections");
  for (const link of navigation.querySelectorAll("a"))
    mobile.append(link.cloneNode(true));
  header.after(mobile);
  const allLinks = [...document.querySelectorAll("aside nav a, .mobile-nav a")];
  const top = document.createElement("button");
  top.id = "back-to-top";
  top.className = "back-to-top icon-button";
  top.type = "button";
  top.hidden = true;
  top.innerHTML = svg("arrow");
  top.setAttribute("aria-label", "Back to top");
  top.addEventListener("click", () =>
    window.scrollTo({ top: 0, behavior: allowed ? "smooth" : "instant" }),
  );
  document.body.append(top);

  const dialog = document.createElement("dialog");
  dialog.className = "command-dialog";
  dialog.id = "command-dialog";
  dialog.setAttribute("aria-labelledby", "command-title");
  dialog.innerHTML = `<div class="command-heading"><div><span class="eyebrow">QUICK NAVIGATION</span><h2 id="command-title">Where would you like to go?</h2></div><button class="icon-button" id="command-close" aria-label="Close navigation" type="button">${svg("close")}</button></div><label class="command-input-label">${svg("search")}<span class="sr-only">Search workspace sections</span><input id="command-input" type="search" autocomplete="off" placeholder="Search this workspace…"></label><div id="command-list" class="command-list"></div><div class="command-footer"><span>↑ ↓ to navigate · Enter to select</span><kbd>Esc to close</kbd></div>`;
  document.body.append(dialog);
  const search = dialog.querySelector("input");
  function filter() {
    const list = document.getElementById("command-list");
    list.replaceChildren();
    for (const destination of destinations.filter((item) =>
      item.name.toLowerCase().includes(search.value.toLowerCase()),
    )) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "command-item";
      const label = document.createElement("span");
      label.textContent = destination.name;
      button.append(label);
      button.insertAdjacentHTML("beforeend", svg("arrow"));
      button.addEventListener("click", () => {
        dialog.close();
        navigation.querySelector(`a[href="${destination.hash}"]`).click();
      });
      list.append(button);
    }
    if (!list.children.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No matching section. Try another name.";
      list.append(empty);
    }
  }
  function open() {
    if (document.body.classList.contains("is-guest")) return;
    search.value = "";
    filter();
    dialog.showModal();
    search.focus();
  }
  document.getElementById("command-open").addEventListener("click", open);
  document
    .getElementById("command-close")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    const bounds = dialog.getBoundingClientRect();
    if (
      event.target === dialog &&
      (event.clientX < bounds.left ||
        event.clientX > bounds.right ||
        event.clientY < bounds.top ||
        event.clientY > bounds.bottom)
    )
      dialog.close();
  });
  search.addEventListener("input", filter);
  dialog.addEventListener("keydown", (event) => {
    const items = [...dialog.querySelectorAll(".command-item")];
    if (event.key === "Enter" && event.target === search) {
      event.preventDefault();
      items[0]?.click();
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const index = items.indexOf(document.activeElement),
        step = event.key === "ArrowDown" ? 1 : -1;
      items[(index + step + items.length) % items.length]?.focus();
    }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      dialog.open ? dialog.close() : open();
    }
  });

  let scheduled = false;
  function scrollFrame() {
    scheduled = false;
    const height = document.documentElement.scrollHeight - innerHeight;
    header.style.setProperty(
      "--scroll-progress",
      height > 0 ? Math.min(1, Math.max(0, scrollY / height)) : 0,
    );
    header.classList.toggle("is-scrolled", scrollY > 16);
    top.hidden = scrollY < 550;
    const visible = destinations.filter(
      (item) => item.section && item.section.getClientRects().length,
    );
    let active = visible[0]?.hash;
    for (const item of visible)
      if (item.section.getBoundingClientRect().top <= 190) active = item.hash;
    if (
      visible.length &&
      scrollY + innerHeight >= document.documentElement.scrollHeight - 5
    )
      active = visible.at(-1).hash;
    for (const link of allLinks) {
      const selected = link.hash === active;
      link.classList.toggle("active", selected);
      if (selected) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }
  function scheduleScroll() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(scrollFrame);
    }
  }
  addEventListener("scroll", scheduleScroll, { passive: true });
  addEventListener("resize", scheduleScroll, { passive: true });

  let pendingPointer = false,
    pointerTarget,
    pointerX,
    pointerY;
  document.addEventListener(
    "pointermove",
    (event) => {
      if (!allowed || !fine.matches) return;
      const target = event.target.closest(
        ".hero-frame, .metric, .account-card",
      );
      if (!target) return;
      pointerTarget = target;
      pointerX = event.clientX;
      pointerY = event.clientY;
      if (pendingPointer) return;
      pendingPointer = true;
      requestAnimationFrame(() => {
        pendingPointer = false;
        const bounds = pointerTarget.getBoundingClientRect();
        pointerTarget.style.setProperty(
          "--pointer-x",
          `${pointerX - bounds.left}px`,
        );
        pointerTarget.style.setProperty(
          "--pointer-y",
          `${pointerY - bounds.top}px`,
        );
      });
    },
    { passive: true },
  );

  function refresh() {
    const guest = !!document.getElementById("workspace")?.hidden;
    document.body.classList.toggle("is-guest", guest);
    skip.href = guest ? "#login-view" : "#overview";
    document.getElementById("command-open").hidden = guest;
    for (const [index, node] of [
      ...document.querySelectorAll(
        ".panel,.metric,.account-card,.bar-item,.hero-frame",
      ),
    ].entries()) {
      if (observed.has(node) || !node.getClientRects().length) continue;
      observed.add(node);
      node.dataset.stagger = String((index % 3) * 45);
      if (allowed && node.getBoundingClientRect().top > innerHeight)
        node.classList.add("reveal-wait");
      observer.observe(node);
    }
    for (const bar of document.querySelectorAll(
      ".allocation i, .bar-track i",
    )) {
      if (animatedBars.has(bar)) continue;
      animatedBars.add(bar);
      if (allowed)
        bar.animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], {
          duration: 800,
          easing: "cubic-bezier(.16,1,.3,1)",
        });
    }
    scheduleScroll();
  }
  function draw(container) {
    if (!allowed) return;
    for (const path of container.querySelectorAll("path[data-draw]")) {
      const length = path.getTotalLength();
      if (!Number.isFinite(length) || !length) continue;
      path.animate(
        [
          { strokeDasharray: length, strokeDashoffset: length },
          { strokeDasharray: length, strokeDashoffset: 0 },
        ],
        { duration: 1100, easing: "cubic-bezier(.22,1,.36,1)" },
      );
    }
  }
  function celebrate(node) {
    if (allowed && node)
      node.animate(
        [
          { opacity: 0.25, transform: "translateY(5px)" },
          { opacity: 1, transform: "translateY(0)" },
        ],
        { duration: 360, easing: "ease-out" },
      );
  }
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const theme = root.dataset.appearance === "dark" ? "light" : "dark";
    write("studio-theme", theme);
    setTheme(theme);
  });
  document.getElementById("motion-toggle").addEventListener("click", () => {
    if (reduce.matches) return;
    write("studio-motion", allowed ? "off" : "on");
    setMotion();
    refresh();
  });
  reduce.addEventListener("change", () => {
    setMotion();
    refresh();
  });
  setTheme(read("studio-theme") || root.dataset.appearance);
  setMotion();
  const favicon = document.createElement("link");
  favicon.rel = "icon";
  favicon.href =
    "data:image/svg+xml," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="12" fill="${root.dataset.project === "parcelguard" ? "#dcb270" : root.dataset.project === "tenantledger" ? "#13796b" : "#789df1"}"/><text x="20" y="28" text-anchor="middle" font-family="sans-serif" font-size="26" fill="#0b1018">${document.querySelector(".mark").textContent.trim()}</text></svg>`,
    );
  document.head.append(favicon);
  window.Studio = {
    refresh,
    draw,
    celebrate,
    icon: svg,
    get motion() {
      return allowed;
    },
  };
  refresh();
})();
