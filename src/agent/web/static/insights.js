(() => {
  const runBtn = document.getElementById("loop2-run-btn");
  const statusEl = document.getElementById("loop2-run-status");

  function setStatus(message, isError = false) {
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.hidden = !message;
    statusEl.classList.toggle("loop2-status-error", isError);
  }

  function setBusy(busy) {
    document.querySelectorAll("[data-loop2-action]").forEach((el) => {
      el.disabled = busy;
    });
  }

  async function postJson(url) {
    const response = await fetch(url, { method: "POST" });
    let data = {};
    try {
      data = await response.json();
    } catch {
      /* ignore */
    }
    if (!response.ok) {
      const detail = data.detail;
      const message = typeof detail === "string" ? detail : "Loop 2 request failed.";
      throw new Error(message);
    }
    return data;
  }

  function openGate(data) {
    const threadId = data.thread_id;
    if (!threadId) {
      throw new Error("No gate thread returned.");
    }
    window.location.href = data.gate_url || `/app?thread=${threadId}`;
  }

  async function runFullLoop(limit) {
    setBusy(true);
    setStatus("Running persona panel…");
    try {
      const data = await postJson(`/api/personas/loop2/run?limit=${encodeURIComponent(limit)}`);
      setStatus("Opening approval gate…");
      openGate(data);
    } catch (err) {
      setBusy(false);
      setStatus(err.message || "Loop 2 failed.", true);
    }
  }

  async function startRewrite(productId, theme) {
    setBusy(true);
    setStatus(`Starting rewrite for product #${productId}…`);
    try {
      const data = await postJson(
        `/api/personas/rewrite/${encodeURIComponent(productId)}/start?theme=${encodeURIComponent(theme)}`
      );
      setStatus("Opening approval gate…");
      openGate(data);
    } catch (err) {
      setBusy(false);
      setStatus(err.message || "Could not start rewrite.", true);
    }
  }

  runBtn?.addEventListener("click", () => {
    const limit = Number(runBtn.dataset.limit || "5");
    runFullLoop(Number.isFinite(limit) && limit > 0 ? limit : 5);
  });

  document.addEventListener("click", (event) => {
    const rewriteBtn = event.target.closest("[data-loop2-rewrite]");
    if (!rewriteBtn) return;
    event.preventDefault();
    const productId = rewriteBtn.dataset.productId;
    const theme = rewriteBtn.dataset.theme;
    if (!productId || !theme) return;
    startRewrite(productId, theme);
  });
})();
