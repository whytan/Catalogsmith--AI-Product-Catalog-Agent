(() => {
  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const gatePanel = document.getElementById("gate-panel");
  const sendBtn = document.getElementById("send-btn");
  const statusEl = document.getElementById("connection-status");
  const steps = document.querySelectorAll(".pipeline-steps .step");
  const welcome = document.getElementById("chat-welcome");
  const toast = document.getElementById("toast");
  const productPhotoInput = document.getElementById("product-photo");
  const photoPreview = document.getElementById("photo-preview");

  if (!form || !input || !sendBtn || !gatePanel) {
    console.error("Agent console UI is missing required elements.");
    return;
  }

  let threadId = null;
  let socket = null;
  let toastTimer = null;
  let inFlight = false;
  let sendBtnLabel = sendBtn.textContent || "Send to agent";

  function hideWelcome() {
    welcome?.remove();
  }

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
  }

  function setStatus(state, label) {
    if (!statusEl) return;
    statusEl.dataset.state = state;
    statusEl.querySelector(".status-label").textContent = label;
  }

  function setPipelineStep(step) {
    const order = ["parse", "draft", "gate", "publish"];
    const idx = order.indexOf(step);
    steps.forEach((el, i) => {
      el.classList.toggle("done", i < idx);
      el.classList.toggle("active", i === idx);
    });
  }

  function setSendBusy(busy) {
    inFlight = busy;
    sendBtn.disabled = busy || !socket || socket.readyState !== WebSocket.OPEN;
    sendBtn.textContent = busy ? "Processing…" : sendBtnLabel;
  }

  function finishRequest() {
    setSendBusy(false);
  }

  function appendChat(role, content) {
    hideWelcome();
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    bubble.innerHTML = `
      <span class="bubble-role">${role === "user" ? "You" : "Agent"}</span>
      <div class="bubble-body">${escapeHtml(content)}</div>`;
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
  }

  function appendSystem(content) {
    const line = document.createElement("div");
    line.className = "chat-system";
    line.textContent = content;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  async function uploadFileInput(inputEl) {
    const file = inputEl?.files?.[0];
    if (!file) return undefined;

    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/agent/upload-image", { method: "POST", body: formData });
    if (!res.ok) {
      let detail = "Image upload failed.";
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    const data = await res.json();
    return data.filename;
  }

  function hidePhotoPreview() {
    if (!photoPreview) return;
    photoPreview.hidden = true;
    photoPreview.removeAttribute("src");
  }

  function showPhotoPreview(file) {
    if (!photoPreview || !file) return;
    photoPreview.src = URL.createObjectURL(file);
    photoPreview.hidden = false;
  }

  function showGateLoading(label = "Loading gate preview…") {
    gatePanel.innerHTML = `
      <div class="gate-loading">
        <span class="spinner" aria-hidden="true"></span>
        <p>${escapeHtml(label)}</p>
      </div>`;
  }

  async function loadGatePanel(id) {
    if (!id) return;
    showGateLoading();
    try {
      const res = await fetch(`/app/gate/${id}`);
      if (!res.ok) throw new Error("Gate fetch failed");
      gatePanel.innerHTML = await res.text();
      wireGateButtons();
    } catch {
      gatePanel.innerHTML = `<p class="empty-state">Could not load gate preview. Retry by refreshing.</p>`;
    }
  }

  function renderGate(payload) {
    if (!payload || payload.type === "chat") return;

    if (payload.type === "gate") {
      threadId = payload.thread_id;
      setPipelineStep("gate");
      loadGatePanel(threadId);
      return;
    }

    if (payload.type === "needs_facts") {
      threadId = payload.thread_id;
      setPipelineStep("parse");
      loadGatePanel(threadId);
      appendSystem("Add the selling price in the panel on the right, then click Continue to draft.");
      return;
    }

    if (payload.type === "complete") {
      setPipelineStep("publish");
      if (payload.product_id) {
        showToast(`Product #${payload.product_id} is now live on the storefront`);
      }
      if (payload.thread_id) {
        loadGatePanel(payload.thread_id);
      } else {
        gatePanel.innerHTML = `
          <div class="gate-card complete">
            <div class="complete-badge">Published</div>
            <h3>${escapeHtml(payload.status || "Done")}</h3>
            ${payload.product_id ? `<p>Product <a href="/products/${payload.product_id}" target="_blank" rel="noopener">#${payload.product_id}</a> is live.</p>` : ""}
            <blockquote>${escapeHtml(payload.description || "")}</blockquote>
          </div>`;
      }
      const frame = document.querySelector(".storefront-frame");
      if (frame) frame.src = "/?t=" + Date.now();
    }
  }

  function setGateBusy(busy) {
    gatePanel.querySelectorAll("button[data-action]").forEach((btn) => {
      btn.disabled = busy;
    });
  }

  function showGateProcessing(label) {
    clearGateProcessing();
    const card = gatePanel.querySelector(".gate-card");
    if (!card) return;
    const overlay = document.createElement("div");
    overlay.className = "gate-processing";
    overlay.id = "gate-processing";
    overlay.innerHTML = `<span class="spinner" aria-hidden="true"></span><p>${escapeHtml(label)}</p>`;
    card.appendChild(overlay);
  }

  function clearGateProcessing() {
    document.getElementById("gate-processing")?.remove();
  }

  function wireGateButtons() {
    const completeFactsBtn = gatePanel.querySelector("button[data-action='complete_facts']");
    if (completeFactsBtn) {
      completeFactsBtn.onclick = async () => {
        if (!socket || socket.readyState !== WebSocket.OPEN || !threadId) {
          appendSystem("Connection lost — wait for Connected (top right), then try again.");
          return;
        }
        const price = document.getElementById("facts-price")?.value?.trim() || "";
        const category = document.getElementById("facts-category")?.value?.trim() || "";
        const name = document.getElementById("facts-name")?.value?.trim() || "";
        if (!price) {
          appendSystem("Selling price is required before continuing.");
          return;
        }
        if (!category) {
          appendSystem("Category is required before continuing.");
          return;
        }
        setGateBusy(true);
        showGateProcessing("Continuing to draft…");
        try {
          const photoFilename = await uploadFileInput(document.getElementById("facts-photo"));
          socket.send(JSON.stringify({
            type: "complete_facts",
            thread_id: threadId,
            price,
            category,
            name: name || undefined,
            photo_filename: photoFilename,
          }));
        } catch (err) {
          clearGateProcessing();
          setGateBusy(false);
          appendSystem(err.message || "Could not upload photo.");
        }
      };
      return;
    }

    const attachPhotoBtn = gatePanel.querySelector("button[data-action='attach_photo']");
    if (attachPhotoBtn) {
      attachPhotoBtn.onclick = async () => {
        if (!socket || socket.readyState !== WebSocket.OPEN || !threadId) {
          appendSystem("Connection lost — wait for Connected (top right), then try again.");
          return;
        }
        setGateBusy(true);
        showGateProcessing("Uploading photo…");
        try {
          const photoFilename = await uploadFileInput(document.getElementById("gate-photo"));
          if (!photoFilename) {
            appendSystem("Choose an image file first.");
            clearGateProcessing();
            setGateBusy(false);
            return;
          }
          socket.send(JSON.stringify({
            type: "attach_photo",
            thread_id: threadId,
            photo_filename: photoFilename,
          }));
        } catch (err) {
          clearGateProcessing();
          setGateBusy(false);
          appendSystem(err.message || "Could not upload photo.");
        }
      };
    }

    gatePanel.querySelectorAll("button[data-action]").forEach((btn) => {
      if (btn.dataset.action === "attach_photo") return;
      btn.onclick = () => {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          appendSystem("Connection lost — wait for Connected (top right), then try again.");
          return;
        }
        if (!threadId) {
          appendSystem("No active thread. Paste product facts and send first.");
          return;
        }

        const action = btn.dataset.action;
        const description = document.getElementById("gate-description")?.value || "";
        const comment = document.getElementById("gate-comment")?.value || "";
        if (action === "edit" && !description.trim()) {
          appendSystem("Description cannot be empty for save & redraft.");
          return;
        }
        if (action === "reject" && !comment.trim()) {
          appendSystem("Add a feedback comment so the agent knows how to redraft.");
          return;
        }

        const labels = {
          approve: "Publishing…",
          reject: "Redrafting…",
          edit: "Saving edit…",
        };
        setGateBusy(true);
        showGateProcessing(labels[action] || "Processing…");

        try {
          socket.send(JSON.stringify({
            type: "gate_action",
            thread_id: threadId,
            action,
            edited_description: action === "edit" ? description : undefined,
            comment,
          }));
        } catch {
          clearGateProcessing();
          setGateBusy(false);
          appendSystem("Could not send gate action. Try again.");
        }
      };
    });
  }

  function handlePayload(payload) {
    if (payload.type === "chat") {
      appendChat(payload.role, payload.content);
      if (payload.role === "assistant" && payload.content.toLowerCase().includes("draft")) {
        setPipelineStep("gate");
      }
      return;
    }

    if (payload.type === "processing") {
      const labels = { parse: "Parsing with AI…", draft: "Drafting description…", gate: "Updating gate…" };
      showGateLoading(labels[payload.stage] || "Working…");
      return;
    }

    if (payload.type === "error") {
      clearGateProcessing();
      setGateBusy(false);
      finishRequest();
      appendSystem(payload.message || "Something went wrong.");
      return;
    }

    if (payload.type === "thread") {
      threadId = payload.thread_id;
      setPipelineStep("parse");
      appendSystem("Pipeline started — parsing your facts…");
      return;
    }

    clearGateProcessing();
    setGateBusy(false);
    finishRequest();
    renderGate(payload);
  }

  function connect() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/chat`);

    socket.onopen = () => {
      setStatus("connected", "Connected");
      setSendBusy(inFlight);

      const params = new URLSearchParams(window.location.search);
      const pendingThread = params.get("thread");
      if (pendingThread) {
        threadId = pendingThread;
        hideWelcome();
        setPipelineStep("gate");
        appendSystem("Loop 2 rewrite loaded — review the proposed description in the gate.");
        loadGatePanel(pendingThread);
        params.delete("thread");
        const clean = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
        window.history.replaceState({}, "", clean);
      }
    };

    socket.onmessage = (event) => {
      try {
        handlePayload(JSON.parse(event.data));
      } catch {
        finishRequest();
        appendSystem("Received an invalid response from the server.");
      }
    };

    socket.onclose = () => {
      setStatus("disconnected", "Reconnecting…");
      sendBtn.disabled = true;
      setTimeout(connect, 1000);
    };

    socket.onerror = () => setStatus("disconnected", "Connection error");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const content = input.value.trim();
    if (!content) {
      appendSystem("Type or paste product facts before sending.");
      return;
    }
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      appendSystem("Not connected yet — wait for Connected status (top right).");
      return;
    }
    if (inFlight) {
      appendSystem("Still processing your last request…");
      return;
    }

    appendChat("user", content);
    setPipelineStep("parse");
    setSendBusy(true);
    showGateLoading("Parsing with AI…");

    try {
      const photoFilename = await uploadFileInput(productPhotoInput);
      socket.send(JSON.stringify({
        type: "start",
        content,
        photo_filename: photoFilename,
      }));
      input.value = "";
      if (productPhotoInput) productPhotoInput.value = "";
      hidePhotoPreview();
    } catch (err) {
      finishRequest();
      appendSystem(err.message || "Could not send message. Refresh and try again.");
    }
  });

  productPhotoInput?.addEventListener("change", () => {
    const file = productPhotoInput.files?.[0];
    if (file) showPhotoPreview(file);
    else hidePhotoPreview();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  document.getElementById("sample-prompts")?.addEventListener("click", (event) => {
    const chip = event.target.closest(".sample-chip");
    if (!chip) return;
    input.value = chip.dataset.prompt || "";
    input.focus();
  });

  connect();
  setPipelineStep("parse");
})();
