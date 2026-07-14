(() => {
  const TOURS = {
    agent: {
      key: "catalogsmith_onboard_agent",
      title: "Welcome to the agent console",
      body: "This is Loop 1 — the seller workflow. Three panes, one pipeline:",
      steps: [
        "Paste product facts in the chat pane",
        "Review and approve at the gate — nothing publishes without you",
        "Watch the live storefront update after approval",
      ],
      highlight: "[data-onboarding-step='agent-chat']",
    },
    dashboard: {
      key: "catalogsmith_onboard_dashboard",
      title: "Seller operations dashboard",
      body: "This dashboard tracks Loop 1 health — whether the agent is learning and staying safe.",
      steps: [
        "Learning graph: edit rate should fall over time",
        "Guardrails: sanitization and grounding violations",
        "Customer insights (Loop 2) live at /insights — separate from seller ops",
      ],
      highlight: ".feature-map",
    },
    insights: {
      key: "catalogsmith_onboard_insights",
      title: "Customer insights (Loop 2)",
      body: "All data here is SYNTHETIC — simulated shoppers, not real customers.",
      steps: [
        "Four personas browse your published listings",
        "Signals cluster into themes (battery, price, specs…)",
        "Rewrite proposals go back through the same seller gate",
      ],
      highlight: ".synthetic-banner",
    },
  };

  function shouldShow(key) {
    try {
      return localStorage.getItem(key) !== "1";
    } catch {
      return false;
    }
  }

  function dismiss(key, permanent) {
    if (permanent) {
      try { localStorage.setItem(key, "1"); } catch { /* ignore */ }
    }
    document.querySelector(".onboarding-overlay")?.remove();
    document.querySelector(".onboarding-highlight")?.classList.remove("onboarding-highlight");
  }

  function showTour(tour) {
    if (!shouldShow(tour.key)) return;

    const overlay = document.createElement("div");
    overlay.className = "onboarding-overlay";
    overlay.innerHTML = `
      <div class="onboarding-card" role="dialog" aria-labelledby="onboard-title">
        <h3 id="onboard-title">${tour.title}</h3>
        <p>${tour.body}</p>
        <ol>${tour.steps.map((s) => `<li>${s}</li>`).join("")}</ol>
        <div class="onboarding-actions">
          <label class="onboarding-dismiss">
            <input type="checkbox" id="onboard-dismiss" /> Don't show again
          </label>
          <button type="button" class="btn-primary" id="onboard-got-it">Got it</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    const target = document.querySelector(tour.highlight);
    if (target) target.classList.add("onboarding-highlight");

    overlay.querySelector("#onboard-got-it").onclick = () => {
      const permanent = overlay.querySelector("#onboard-dismiss")?.checked;
      dismiss(tour.key, permanent);
    };

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) dismiss(tour.key, false);
    });
  }

  const surface = document.body.dataset.onboarding;
  if (surface && TOURS[surface]) {
    requestAnimationFrame(() => showTour(TOURS[surface]));
  }
})();
