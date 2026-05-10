const app = document.getElementById("app");

const state = {
  selectedFile: null,
  bill: null,
  demoBills: [],
  recentNegotiations: [],
  customAngles: [],
  customInput: "",
  error: "",
  uploadPending: false,
  startPending: false,
  demoPendingId: "",
  negotiation: null,
  turns: [],
  callError: "",
  resultConfettiPlayed: false,
  homeLoading: false,
  homeLoaded: false,
  readiness: null,
};

let currentEvents = null;
let resultRevealTimer = null;

function money(value) {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    minimumFractionDigits: 2,
  }).format(value ?? 0);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;
  if (!response.ok) {
    throw new Error(payload?.detail || "Request failed.");
  }
  return payload;
}

function navigate(path) {
  if (window.location.pathname === path) {
    return;
  }
  history.pushState({}, "", path);
  renderRoute();
}

function cleanupRoute() {
  if (currentEvents) {
    currentEvents.close();
    currentEvents = null;
  }
  if (resultRevealTimer) {
    window.clearTimeout(resultRevealTimer);
    resultRevealTimer = null;
  }
}

function renderCallView() {
  if (!state.negotiation) {
    app.innerHTML = pageShell(`<section class="card"><div class="empty">Loading negotiation...</div></section>`);
    return;
  }
  app.innerHTML = callMarkup(state.negotiation);
  document.title = "RateDrop · Live Negotiation";
  bindCallEvents();
}

function pageShell(inner) {
  return `<div class="shell">${inner}</div>`;
}

function brandTopbar(copy) {
  return `
    <header class="topbar">
      <a class="brand" href="/" data-nav>
        <span class="brand-mark">R</span>
        <div>
          <strong>RateDrop</strong>
          <small>${copy}</small>
        </div>
      </a>
      <div class="signal-pill">
        <span class="status-dot"></span>
        Live extraction, live transcript, deterministic savings
      </div>
    </header>
  `;
}

function readinessMarkup() {
  const readiness = state.readiness;
  if (!readiness) {
    return `
      <div class="ops-card">
        <span class="section-tag">Demo readiness</span>
        <p class="mini-note">Checking backend, Gemini, storage, and Twilio trial mode...</p>
      </div>
    `;
  }

  const twilio = readiness.twilio || {};
  return `
    <div class="ops-card">
      <div class="detail-row">
        <div>
          <span class="section-tag">Demo readiness</span>
          <strong>Operational state is visible before the call starts.</strong>
        </div>
        <small>${escapeHtml(readiness.status || "unknown")}</small>
      </div>
      <div class="ops-grid">
        ${readinessItem("Storage", readiness.database?.ready, readiness.database?.mode === "mongo" ? "MongoDB Atlas" : "Local persistent fallback")}
        ${readinessItem("Gemini", readiness.gemini?.configured, readiness.gemini?.model || "Not configured")}
        ${readinessItem("Twilio trial", twilio.trialCompatible, twilio.mode === "conversation_relay" ? "Live ConversationRelay" : twilio.mode === "sandbox_tts" ? "Narrated Twilio sandbox" : "Simulation fallback")}
      </div>
      <p class="mini-note">Free Twilio trial calls require a verified destination number and a public callback URL. If either is missing, RateDrop runs the same transcript and savings flow locally.</p>
    </div>
  `;
}

function readinessItem(label, ready, detail) {
  return `
    <div class="ops-item ${ready ? "ready" : "limited"}">
      <span>${escapeHtml(label)}</span>
      <strong>${ready ? "Ready" : "Limited"}</strong>
      <small>${escapeHtml(detail || "Unavailable")}</small>
    </div>
  `;
}

function homeMarkup() {
  const bill = state.bill;
  return pageShell(`
    ${brandTopbar("Telecom bill negotiation engine")}
    <section class="hero">
      <div class="hero-copy">
        <span class="eyebrow">Telecom bill negotiation</span>
        <h1>Drop your rate before you waste another hour on hold.</h1>
        <p class="lede">
          RateDrop reads your mobile bill, finds the leverage, launches a controlled sandbox carrier call, and tracks the savings in one place.
        </p>
        <div class="hero-subline">
          <span>Reads the real bill.</span>
          <span>Runs a controlled call.</span>
          <span>Proves the savings in code.</span>
        </div>
      </div>
      <div>
        <section class="card upload-card">
          <div class="card-head">
            <div>
              <span class="section-tag">Start with your bill</span>
              <h2 class="panel-title">Upload a telecom bill</h2>
              <p class="lede muted">PDF, JPG, or PNG. RateDrop extracts the actual charges first, then builds the call plan around them.</p>
            </div>
          </div>

          <div class="sequence-inline">
            <div class="sequence-inline-item">
              <span>01</span>
              <strong>Extract charges</strong>
              <small>Read provider, recurring plan cost, and fee pressure.</small>
            </div>
            <div class="sequence-inline-item">
              <span>02</span>
              <strong>Shape leverage</strong>
              <small>Combine bill angles with customer-specific context.</small>
            </div>
            <div class="sequence-inline-item">
              <span>03</span>
              <strong>Run the call</strong>
              <small>Launch the negotiation path and track the result.</small>
            </div>
          </div>

          <div class="surface-note">
            <span class="section-tag">Input to outcome</span>
            <strong>Provider, plan, fees, promo pressure, live call strategy, and deterministic savings forecast.</strong>
          </div>

          ${readinessMarkup()}

          <form class="upload-form" id="upload-form">
            <label class="dropzone" for="bill-file">
              <span>${state.selectedFile ? escapeHtml(state.selectedFile.name) : "Choose a bill file"}</span>
              <small>${state.selectedFile ? "Ready to extract bill facts." : "Drag in a statement or tap to browse."}</small>
            </label>
            <input id="bill-file" type="file" accept=".pdf,image/png,image/jpeg,image/jpg" class="hidden" />
            <button class="primary" type="submit" ${state.uploadPending ? "disabled" : ""}>
              ${state.uploadPending ? "Extracting bill..." : "Extract bill summary"}
            </button>
          </form>

          ${state.demoBills.length ? `
            <div class="detail-block">
              <h4>Or start with a demo bill</h4>
              <div class="demo-grid">
                ${state.demoBills.map((item) => `
                  <button class="demo-card" type="button" data-demo-id="${item.id}" ${state.demoPendingId ? "disabled" : ""}>
                    <strong>${escapeHtml(item.label)}</strong>
                    <em>${escapeHtml(item.provider)}</em>
                    <span>${money(item.monthlyTotal)}/mo · ${escapeHtml(item.headlineAngle)}</span>
                    <small>${state.demoPendingId === item.id ? "Loading demo bill..." : "Use this scenario"}</small>
                  </button>
                `).join("")}
              </div>
            </div>
          ` : ""}

          ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ""}

          ${bill ? billMarkup(bill) : ""}
          ${renderRecentList()}
        </section>
      </div>
    </section>

    <section class="landing-preview">
      <div class="preview-copy">
        <span class="section-tag">Live transcript preview</span>
        <h2 class="band-title">The product feels better when the negotiation stays visible instead of disappearing behind a spinner.</h2>
        <p class="lede muted">The live view is designed to show momentum, context, and measurable progress while the call advances.</p>
      </div>
      <div class="preview-frame">
        <div class="preview-head">
          <div class="status-pill">
            <span class="pulse-dot"></span>
            Live flow
          </div>
          <span class="muted">Sandbox transcript</span>
        </div>
        <div class="preview-stream">
          ${sampleTurns().slice(0, 3).map((turn, index) => `
            <article class="turn ${turn.role}">
              <div class="turn-head">
                <strong>${index + 1 < 10 ? `0${index + 1}` : index + 1} · ${turn.role === "negotiator" ? "RateDrop" : "Carrier rep"}</strong>
                <span>${escapeHtml(turn.objective)}</span>
              </div>
              <p>${escapeHtml(turn.text)}</p>
            </article>
          `).join("")}
        </div>
      </div>
    </section>

    <section class="editorial-band product-band">
      <aside class="band-aside">
        <span class="section-tag">Why it feels credible</span>
        <p class="lede muted">This is not a chat interface with a savings claim taped on top. The flow is designed so the user can trace exactly how the result happened.</p>
      </aside>
      <div class="band-main">
        <h2 class="band-title">Fewer telecom surprises, less hold time, clearer financial proof.</h2>
        <div class="rail-statements">
          <div>
            <span>01</span>
            <strong>The bill becomes leverage, not just text.</strong>
            <p>Gemini extracts structure. RateDrop chooses the actual negotiation path in code.</p>
          </div>
          <div>
            <span>02</span>
            <strong>The call stays visible while it runs.</strong>
            <p>The transcript, current objective, and best-offer state all stay on screen.</p>
          </div>
          <div>
            <span>03</span>
            <strong>The result reads like financial proof, not model optimism.</strong>
            <p>Before and after numbers, one-time credits, and first-year value are deterministic.</p>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer-grid">
      <div class="footer-col">
        <strong>RateDrop</strong>
        <span>Bill extraction, live sandbox negotiation, deterministic savings math.</span>
      </div>
      <div class="footer-col">
        <span class="footer-label">Stack</span>
        <span>Gemini · Twilio · MongoDB · FastAPI · static frontend</span>
      </div>
      <div class="footer-col">
        <span class="footer-label">Hackathon focus</span>
        <span>Consumer clarity, visible automation, and a result judges can verify instantly.</span>
      </div>
    </footer>
  `);
}

function billMarkup(bill) {
  return `
    <section class="detail-block">
      <div class="summary-head">
        <div>
          <span class="section-tag">Extracted summary</span>
          <h3 class="summary-title">${escapeHtml(bill.provider)} · ${money(bill.monthlyTotal)}/mo</h3>
          <p class="lede muted">Structured bill facts are ready. The next step turns this into a controlled negotiation run.</p>
        </div>
        <div class="meta-chip">${Math.round((bill.extractionConfidence || 0) * 100)}% confidence</div>
      </div>

      <div class="stats">
        <div class="metric-card stat"><span>Plan</span><strong>${escapeHtml(bill.planName)}</strong></div>
        <div class="metric-card stat"><span>Line items</span><strong>${bill.lineItems.length}</strong></div>
        <div class="metric-card stat"><span>Likely leverage</span><strong>${escapeHtml(bill.negotiationAngles[0] || "Retention review")}</strong></div>
      </div>

      <div class="callout">
        <span class="section-tag">Call setup</span>
        <strong>RateDrop will use the extracted bill facts to pick a deterministic negotiation path.</strong>
        <p>No freestyle math. No hidden assumptions. The phone flow is a controlled carrier sandbox, not a real telecom provider call.</p>
      </div>

      <div class="detail-block">
        <h4>Negotiation angles</h4>
        <div class="chip-row">
          ${bill.negotiationAngles.map((angle) => `<span class="chip">${escapeHtml(angle)}</span>`).join("")}
          ${state.customAngles.map((angle) => `<span class="chip custom">${escapeHtml(angle)}</span>`).join("")}
        </div>
        <form class="angle-form" id="angle-form">
          <input
            class="text-input"
            id="custom-angle-input"
            type="text"
            maxlength="80"
            value="${escapeAttribute(state.customInput)}"
            placeholder="Add your own leverage point, like 10-year customer or competitor quote"
          />
          <button class="secondary" type="submit" ${state.customInput.trim() ? "" : "disabled"}>Add</button>
        </form>
        <div class="angle-note">
          <span class="section-tag">Human in the loop</span>
          <p>Add customer-specific pressure points before the call starts. This keeps the flow grounded in facts instead of turning the negotiation into a black box.</p>
        </div>
      </div>

      <div class="detail-block">
        <h4>Bill charges</h4>
        <div class="detail-table">
          ${bill.lineItems.map((item) => `
            <div class="charge">
              <div><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.category)}</small></div>
              <span>${money(item.amount)}</span>
            </div>
          `).join("")}
        </div>
      </div>

      <div class="call-actions">
        <button class="primary" type="button" data-start-mode="conversation_relay" ${state.startPending ? "disabled" : ""}>
          ${state.startPending ? "Starting call..." : "Start live phone demo"}
        </button>
        <button class="secondary" type="button" data-start-mode="sandbox_tts" ${state.startPending ? "disabled" : ""}>
          Run narrated sandbox
        </button>
      </div>
      <div class="angle-note">
        <span class="section-tag">Live phone setup</span>
        <p>Answer the verified Twilio trial phone, speak as the carrier rep, keep replies short, and mention discounts, credits, or retention options. If public callbacks are missing, RateDrop safely falls back to the local simulated flow.</p>
      </div>
    </section>
  `;
}

function callMarkup(negotiation) {
  const proof = negotiation.strategyProof;
  const title = negotiation.status === "failed"
    ? `${negotiation.provider} negotiation failed`
    : negotiation.status === "completed"
      ? `${negotiation.provider} negotiation complete`
      : `${negotiation.provider} negotiation in progress`;
  const isLivePhone = negotiation.call.mode === "conversation_relay";
  const displayCallStatus =
    negotiation.status === "failed"
      ? "failed"
      : negotiation.status === "completed" && negotiation.call.status !== "failed"
        ? "completed"
        : negotiation.call.mode === "sandbox" || isLivePhone
          ? negotiation.call.status
          : "simulation running";
  const progress = Math.min(100, Math.round((state.turns.length / 8) * 100));

  return pageShell(`
    <header class="subbar">
      <a class="brand" href="/" data-nav>
        <span class="brand-mark">R</span>
        <div>
          <strong>RateDrop</strong>
          <small>Live negotiation stage</small>
        </div>
      </a>
      <div class="signal-pill">
        <span class="status-dot"></span>
        Transcript, offer ladder, and call telemetry
      </div>
    </header>

    <section class="call-layout">
      <section class="card">
        <div class="card-head">
          <div>
            <span class="section-tag">${isLivePhone ? "Live phone call" : "Live sandbox call"}</span>
            <h1 class="page-title">${escapeHtml(title)}</h1>
          </div>
          <div class="meta-chip">${escapeHtml(negotiation.status.replace("-", " "))}</div>
        </div>

        <div class="progress">
          <div class="progress-meta">
            <strong>${state.turns.length} transcript turns captured</strong>
            <small>${progress}% of the scripted negotiation path complete</small>
          </div>
          <div class="track"><span style="width:${progress}%"></span></div>
        </div>

        <div class="call-stats">
          <div class="metric-card stat"><span>Current objective</span><strong>${escapeHtml(negotiation.currentObjective)}</strong></div>
          <div class="metric-card stat"><span>${isLivePhone ? "Phone mode" : "Sandbox call"}</span><strong>${escapeHtml(displayCallStatus)}</strong></div>
          <div class="metric-card stat"><span>Best live offer</span><strong>${negotiation.bestOfferMonthly ? `${money(negotiation.bestOfferMonthly)}/mo` : "Waiting for rep offer"}</strong></div>
        </div>

        ${negotiation.status === "in-progress" && !negotiation.call.error ? `
          <div class="wave">
            <div class="wave-bars">${"<span></span>".repeat(7)}</div>
            <span>Negotiation active</span>
            <div class="wave-bars">${"<span></span>".repeat(7)}</div>
          </div>
        ` : ""}

        ${negotiation.call.error ? `<div class="error">${escapeHtml(negotiation.call.error)}</div>` : ""}
        ${state.callError ? `<div class="error">${escapeHtml(state.callError)}</div>` : ""}
        ${sandboxDisclosure(negotiation)}
        ${isLivePhone && negotiation.status === "in-progress" ? `
          <div class="live-cue">
            <span class="pulse-dot"></span>
            <strong>${state.turns.at(-1)?.role === "negotiator" ? "AI speaking" : "Waiting for the rep"}</strong>
            <p>You are speaking as the carrier rep. Keep the answer realistic so the deterministic policy can classify the next move.</p>
          </div>
        ` : ""}
        ${negotiation.status === "completed" ? `<div class="banner">Negotiation finished. Redirecting to the result page.</div>` : ""}

        <div class="transcript-list">
          ${state.turns.length === 0 ? `<div class="empty">The call is dialing. Transcript turns will appear here as the negotiation advances.</div>` : ""}
          ${state.turns.map((turn, index) => `
            <article class="turn ${escapeHtml(turn.role)}">
              <div class="turn-head">
                <strong>${String(index + 1).padStart(2, "0")} · ${turn.role === "negotiator" ? "RateDrop" : turn.role === "rep" ? "Carrier rep" : "System"}</strong>
                <span>${escapeHtml((turn.intent || "").replaceAll("_", " "))}</span>
              </div>
              <div class="turn-intent">${escapeHtml(turn.objective || "")}</div>
              <p>${escapeHtml(turn.text || "")}</p>
              ${turn.proposedMonthly ? `<small>Offer on table: ${money(turn.proposedMonthly)}/mo</small>` : ""}
              ${turn.credit ? `<small>Credit offered: ${money(turn.credit)}</small>` : ""}
            </article>
          `).join("")}
        </div>
      </section>

      <aside class="sticky-stack">
        <section class="card">
          <span class="section-tag">Negotiation frame</span>
          <h2 class="sidebar-title">${escapeHtml(negotiation.scenarioLabel)}</h2>
          <div class="call-stats">
            <div class="metric-card stat"><span>Current bill</span><strong>${money(negotiation.currentMonthly)}/mo</strong></div>
            <div class="metric-card stat"><span>Target</span><strong>${money(negotiation.targetMonthly)}/mo</strong></div>
            <div class="metric-card stat"><span>Walk-away</span><strong>${money(negotiation.walkAwayMonthly)}/mo</strong></div>
          </div>
          <div class="scenario-strip">
            <strong>Why this path was selected</strong>
            <p>${escapeHtml(proof?.policySummary || "The backend picked this scenario from extracted bill facts, not from open-ended model improvisation.")}</p>
          </div>
          ${proof ? strategyProofMarkup(proof) : ""}
        </section>

        <section class="card">
          <span class="section-tag">Why this page matters</span>
          <h2 class="sidebar-title">The user can see the negotiation logic becoming financial proof in real time.</h2>
          <div class="timeline">
            <div class="timeline-item">
              <span>01</span>
              <strong>The bill facts are grounding the conversation.</strong>
              <p>No hidden context or improvised target math.</p>
            </div>
            <div class="timeline-item">
              <span>02</span>
              <strong>The turn sequence follows a deterministic concession policy.</strong>
              <p>The outcome is constrained by code, not just model style.</p>
            </div>
            <div class="timeline-item">
              <span>03</span>
              <strong>Any savings on the result page are calculated outside the model.</strong>
              <p>The transcript stays connected to the final number.</p>
            </div>
          </div>
          ${negotiation.status === "completed" ? `<button class="primary" type="button" id="view-result-button">View result</button>` : ""}
        </section>
      </aside>
    </section>
  `);
}

function resultMarkup(negotiation) {
  const result = negotiation.result;
  const proof = negotiation.strategyProof;
  const callLabel =
    negotiation.call.error ||
    (negotiation.call.mode === "conversation_relay"
      ? "live phone demo"
      : negotiation.call.mode === "sandbox"
        ? negotiation.call.status.replace("-", " ")
        : "simulated flow");
  const savingsRate = Math.max(0, Math.min(100, Math.round((result.monthlySavings / result.currentMonthly) * 100)));

  return pageShell(`
    <header class="subbar">
      <a class="brand" href="/" data-nav>
        <span class="brand-mark">R</span>
        <div>
          <strong>RateDrop</strong>
          <small>Outcome and savings proof</small>
        </div>
      </a>
      <div class="signal-pill">
        <span class="status-dot"></span>
        Result locked with transcript-backed math
      </div>
    </header>

    <section class="card">
      <div class="confetti ${state.resultConfettiPlayed ? "" : "hidden"}" id="confetti"></div>
      <span class="section-tag">Negotiation result</span>
      <h1 class="result-title">${escapeHtml(result.summary)}</h1>
      <p class="lede">One call flow, one transcript, one hard savings number the user can actually understand.</p>
      <div class="result-meta">
        <div class="meta-chip">Scenario: ${escapeHtml(negotiation.scenarioLabel)}</div>
        <div class="meta-chip">Call status: ${escapeHtml(callLabel)}</div>
        <div class="meta-chip">Target: ${money(proof?.targetMonthly || negotiation.targetMonthly)}/mo</div>
      </div>
      ${sandboxDisclosure(negotiation)}

      <div class="result-math-grid">
        <div class="metric-card stat"><span>Before</span><strong>${money(result.currentMonthly)}/mo</strong></div>
        <div class="metric-card stat accent"><span>After</span><strong id="after-monthly">${money(result.newMonthly)}/mo</strong></div>
        <div class="metric-card stat"><span>Monthly savings</span><strong>${money(result.monthlySavings)}</strong></div>
        <div class="metric-card stat"><span>First-year value</span><strong>${money(result.effectiveFirstYearValue)}</strong></div>
        <div class="metric-card stat"><span>Annual savings</span><strong>${money(result.annualSavings)}</strong></div>
        <div class="metric-card stat"><span>One-time credit</span><strong>${money(result.oneTimeCredit)}</strong></div>
      </div>

      <div class="meter">
        <div class="meter-head">
          <strong>${savingsRate}% monthly reduction</strong>
          <small>Computed from deterministic backend math</small>
        </div>
        <div class="track"><span style="width:${savingsRate}%"></span></div>
      </div>
    </section>

    <section class="result-layout" style="margin-top:24px;">
      <section class="card">
        <span class="section-tag">Savings math</span>
        <h2 class="sidebar-title">The result is small enough to scan, strong enough to trust.</h2>
        <div class="proof-math">
          <div><span class="muted">Current monthly</span><strong>${money(result.currentMonthly)}</strong></div>
          <div><span class="muted">New monthly</span><strong>${money(result.newMonthly)}</strong></div>
          <div><span class="muted">Saved each month</span><strong>${money(result.monthlySavings)}</strong></div>
        </div>
        <div class="chart">
          <div class="chart-bars">
            <div class="chart-group">
              <div class="chart-bar before" style="height:100%"></div>
              <strong>Before</strong>
            </div>
            <div class="chart-group">
              <div class="chart-bar after" id="after-bar" style="height:0%"></div>
              <strong>After</strong>
            </div>
          </div>
          <p class="mini-note">${Math.round(((result.currentMonthly - result.newMonthly) / result.currentMonthly) * 100)}% less per month</p>
        </div>
      </section>

      <section class="card">
        <span class="section-tag">What worked</span>
        <h2 class="sidebar-title">The transcript created a clean narrative for the savings win.</h2>
        <div class="timeline">
          ${result.transcriptSummary.map((item, index) => `
            <div class="timeline-item">
              <span>${String(index + 1).padStart(2, "0")}</span>
              <strong>${escapeHtml(item)}</strong>
              <p>This point persisted into the final deterministic savings calculation.</p>
            </div>
          `).join("")}
        </div>
      </section>
    </section>

    ${proof ? `
      <section class="card" style="margin-top:24px;">
        <span class="section-tag">Strategy proof</span>
        <h2 class="sidebar-title">The negotiation target came from backend policy, not a frontend guess.</h2>
        ${strategyProofMarkup(proof)}
      </section>
    ` : ""}

    <section class="card" style="margin-top:24px;">
      <div class="summary-band">
        <div>
          <span class="section-tag">Bottom line</span>
          <h2 class="band-title">The product closed the loop from bill evidence to savings proof.</h2>
        </div>
        <p>This run preserved the bill context, the negotiation path, the transcript, the call state, and the final result in one connected product flow.</p>
      </div>
    </section>

    <section class="card" style="margin-top:24px;">
      <div class="footer-band">
        <button class="ghost" type="button" id="run-another-button">Run another bill</button>
        <button class="primary" type="button" id="reopen-call-button">Reopen live transcript</button>
      </div>
    </section>
  `);
}

function strategyProofMarkup(proof) {
  return `
    <div class="proof-grid">
      <div class="metric-card stat"><span>Market benchmark</span><strong>${money(proof.marketBenchmark)}/mo</strong></div>
      <div class="metric-card stat"><span>Fee pressure</span><strong>${money(proof.feePressure)}</strong></div>
      <div class="metric-card stat"><span>Target ask</span><strong>${money(proof.targetMonthly)}/mo</strong></div>
      <div class="metric-card stat"><span>Walk-away</span><strong>${money(proof.walkAwayMonthly)}/mo</strong></div>
    </div>
    <div class="evidence-list">
      ${(proof.evidence || []).map((item, index) => `
        <div class="evidence-item">
          <span>${String(index + 1).padStart(2, "0")}</span>
          <p>${escapeHtml(item)}</p>
        </div>
      `).join("")}
    </div>
  `;
}

function sandboxDisclosure(negotiation) {
  const disclosure = negotiation.strategyProof?.sandboxDisclosure ||
    "Controlled carrier sandbox. The demo proves the bill analysis, transcript flow, and savings math without calling a real telecom provider.";
  const modeLabel = negotiation.call.mode === "conversation_relay"
    ? "Live phone demo"
    : negotiation.call.mode === "sandbox"
      ? "Twilio sandbox call"
      : "Simulated call path";
  return `
    <div class="sandbox-disclosure">
      <span class="section-tag">Sandbox disclosure</span>
      <strong>${modeLabel}</strong>
      <p>${escapeHtml(disclosure)}</p>
    </div>
  `;
}

function sampleTurns() {
  return [
    {
      role: "rep",
      objective: "Initial greeting",
      text: "Thanks for calling Bell, how can I help?",
    },
    {
      role: "negotiator",
      objective: "Identifying leverage",
      text: "My loyalty discount rolled off and my bill jumped. I want the promo restored or a comparable retention offer.",
    },
    {
      role: "rep",
      objective: "Initial offer",
      text: "I can offer a smaller monthly credit, but I would need to check whether retention can do more.",
    },
    {
      role: "negotiator",
      objective: "Escalating to retention",
      text: "Please check retention. If you can match the previous discount, I can stay and close this out today.",
    },
  ];
}

function bindHomeEvents() {
  const fileInput = document.getElementById("bill-file");
  if (fileInput) {
    fileInput.addEventListener("change", (event) => {
      state.selectedFile = event.target.files?.[0] || null;
      renderRoute();
    });
  }

  document.getElementById("upload-form")?.addEventListener("submit", handleUpload);

  document.querySelectorAll("[data-demo-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const scenarioId = button.getAttribute("data-demo-id");
      if (!scenarioId) return;
      state.error = "";
      state.demoPendingId = scenarioId;
      renderRoute();
      try {
        state.bill = await api(`/api/bills/demo/${scenarioId}`, { method: "POST" });
        state.selectedFile = null;
        state.customAngles = [];
        state.customInput = "";
        await loadRecent();
      } catch (error) {
        state.error = error.message;
      } finally {
        state.demoPendingId = "";
        renderRoute();
      }
    });
  });

  document.getElementById("angle-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = state.customInput.trim();
    if (!state.bill || !value) return;
    const existing = new Set([...state.bill.negotiationAngles, ...state.customAngles]);
    if (!existing.has(value)) {
      state.customAngles = [...state.customAngles, value];
    }
    state.customInput = "";
    renderRoute();
  });

  document.getElementById("custom-angle-input")?.addEventListener("input", (event) => {
    state.customInput = event.target.value;
    const addButton = document.querySelector("#angle-form .secondary");
    if (addButton) {
      addButton.disabled = !state.customInput.trim();
    }
  });

  document.querySelectorAll("[data-start-mode]").forEach((button) => {
    button.addEventListener("click", () => handleStart(button.dataset.startMode || "conversation_relay"));
  });

  bindNavLinks();
}

async function handleUpload(event) {
  event.preventDefault();
  if (!state.selectedFile) {
    state.error = "Choose a PDF or image bill first.";
    renderRoute();
    return;
  }

  state.error = "";
  state.uploadPending = true;
  renderRoute();

  try {
    const formData = new FormData();
    formData.append("file", state.selectedFile);
    state.bill = await api("/api/bills/upload", { method: "POST", body: formData });
    state.customAngles = [];
    state.customInput = "";
    await loadRecent();
  } catch (error) {
    state.error = error.message;
  } finally {
    state.uploadPending = false;
    renderRoute();
  }
}

async function handleStart(callMode = "conversation_relay") {
  if (!state.bill) return;

  state.error = "";
  state.startPending = true;
  renderRoute();

  try {
    const negotiation = await api("/api/negotiations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ billId: state.bill.id, customAngles: state.customAngles }),
    });
    const started = await api(`/api/negotiations/${negotiation.id}/start`, {
      method: "POST",
      headers: { "X-RateDrop-Call-Mode": callMode },
    });
    navigate(`/call/${started.id}`);
  } catch (error) {
    state.error = error.message;
    state.startPending = false;
    renderRoute();
  }
}

function bindCallEvents() {
  bindNavLinks();
  document.getElementById("view-result-button")?.addEventListener("click", () => {
    if (state.negotiation) {
      navigate(`/result/${state.negotiation.id}`);
    }
  });
}

function bindResultEvents() {
  bindNavLinks();
  document.getElementById("run-another-button")?.addEventListener("click", () => navigate("/"));
  document.getElementById("reopen-call-button")?.addEventListener("click", () => {
    if (state.negotiation) {
      navigate(`/call/${state.negotiation.id}`);
    }
  });

  if (state.negotiation?.result) {
    const current = state.negotiation.result.currentMonthly;
    const next = state.negotiation.result.newMonthly;
    const afterBar = document.getElementById("after-bar");
    const afterValue = document.getElementById("after-monthly");
    const ratio = Math.min(next / current, 1);

    requestAnimationFrame(() => {
      if (afterBar) {
        afterBar.style.height = `${ratio * 100}%`;
      }
      animateCurrency(afterValue, current, next);
      playConfetti();
    });
  }
}

function animateCurrency(element, from, to) {
  if (!element || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    if (element) element.textContent = `${money(to)}/mo`;
    return;
  }

  const duration = 1100;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = from + (to - from) * eased;
    element.textContent = `${money(value)}/mo`;
    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      element.textContent = `${money(to)}/mo`;
    }
  }

  requestAnimationFrame(tick);
}

function playConfetti() {
  if (state.resultConfettiPlayed) return;
  state.resultConfettiPlayed = true;
  const container = document.getElementById("confetti");
  if (!container || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  container.classList.remove("hidden");

  for (let index = 0; index < 22; index += 1) {
    const piece = document.createElement("span");
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = ["#d56e39", "#152038", "#20735e", "#f0b25f", "#ffffff"][index % 5];
    piece.style.setProperty("--drift", `${(Math.random() - 0.5) * 180}px`);
    piece.style.setProperty("--spin", `${(Math.random() - 0.5) * 720}deg`);
    piece.style.animationDelay = `${index * 25}ms`;
    container.appendChild(piece);
  }
}

async function loadHome() {
  const [demos, recent, readiness] = await Promise.allSettled([
    api("/api/demo-bills"),
    api("/api/negotiations?limit=8"),
    api("/api/readiness"),
  ]);

  if (demos.status === "fulfilled") {
    state.demoBills = demos.value.items || [];
  } else {
    state.error = state.error || demos.reason.message;
  }

  if (recent.status === "fulfilled") {
    state.recentNegotiations = recent.value.items || [];
  }

  if (readiness.status === "fulfilled") {
    state.readiness = readiness.value;
  }

  state.homeLoaded = true;
}

async function loadRecent() {
  const recent = await api("/api/negotiations?limit=8");
  state.recentNegotiations = recent.items || [];
}

async function loadCall(negotiationId) {
  state.callError = "";
  const [negotiation, transcript] = await Promise.all([
    api(`/api/negotiations/${negotiationId}`),
    api(`/api/negotiations/${negotiationId}/transcript`),
  ]);
  state.negotiation = negotiation;
  state.turns = transcript.turns || [];
}

async function loadResult(negotiationId) {
  state.negotiation = await api(`/api/negotiations/${negotiationId}`);
}

function connectEvents(negotiationId) {
  currentEvents = new EventSource(`/api/negotiations/${negotiationId}/events`);
  currentEvents.addEventListener("snapshot", (event) => {
    const payload = JSON.parse(event.data);
    state.negotiation = payload.negotiation;
    state.turns = payload.turns || [];
    renderCallView();
  });
  currentEvents.addEventListener("turn", (event) => {
    const payload = JSON.parse(event.data);
    state.negotiation = payload.negotiation;
    state.turns = [...state.turns, payload.turn];
    renderCallView();
  });
  currentEvents.addEventListener("status", (event) => {
    const payload = JSON.parse(event.data);
    state.negotiation = payload.negotiation;
    renderCallView();
    if (state.negotiation?.status === "completed") {
      resultRevealTimer = window.setTimeout(() => navigate(`/result/${state.negotiation.id}`), 1600);
    }
  });
  currentEvents.onerror = () => {
    state.callError = "Live updates dropped. Refresh to reconnect.";
    renderCallView();
  };
}

function bindNavLinks() {
  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const href = link.getAttribute("href");
      if (href) navigate(href);
    });
  });

  document.querySelectorAll(".recent-card[data-href]").forEach((card) => {
    card.addEventListener("click", () => navigate(card.getAttribute("data-href")));
  });
}

function renderRecentList() {
  if (!state.recentNegotiations.length) return "";
  return `
    <div class="detail-block">
      <div class="detail-row">
        <h4>Recent negotiations</h4>
        <small>Loaded from persistent backend storage</small>
      </div>
      <div class="recent-grid">
        ${state.recentNegotiations.map((item) => `
          <button class="recent-card" data-href="/result/${item.id}" type="button">
            <div>
              <strong>${escapeHtml(item.provider)}</strong>
              <small>${escapeHtml(item.scenarioLabel)}</small>
            </div>
            <div class="recent-metrics">
              <span>${money(item.currentMonthly)}/mo</span>
              <small>${escapeHtml(historyOutcome(item))}</small>
            </div>
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function historyOutcome(item) {
  if (item.call?.error) return item.call.error;
  if (item.call?.status === "failed") return "Sandbox call failed";
  if (item.result) return `${money(item.result.newMonthly)}/mo after`;
  return (item.status || "").replace("-", " ");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("\n", " ");
}

async function renderRoute(reset = true) {
  const path = window.location.pathname;
  if (reset) {
    cleanupRoute();
  }

  if (path === "/") {
    app.innerHTML = homeMarkup();
    document.title = "RateDrop";
    bindHomeEvents();
    if (!state.homeLoaded && !state.homeLoading) {
      state.homeLoading = true;
      loadHome().finally(() => {
        state.homeLoading = false;
        if (window.location.pathname === "/") {
          renderRoute(false);
        }
      });
    }
    return;
  }

  const callMatch = path.match(/^\/call\/([^/]+)$/);
  if (callMatch) {
    app.innerHTML = pageShell(`<section class="card"><div class="empty">Loading negotiation...</div></section>`);
    try {
      await loadCall(callMatch[1]);
      renderCallView();
      connectEvents(callMatch[1]);
    } catch (error) {
      app.innerHTML = pageShell(`<section class="card"><div class="error">${escapeHtml(error.message)}</div></section>`);
    }
    return;
  }

  const resultMatch = path.match(/^\/result\/([^/]+)$/);
  if (resultMatch) {
    state.resultConfettiPlayed = false;
    app.innerHTML = pageShell(`<section class="card"><div class="empty">Preparing result...</div></section>`);
    try {
      await loadResult(resultMatch[1]);
      if (!state.negotiation?.result) {
        app.innerHTML = pageShell(`<section class="card"><div class="banner">This negotiation is not finished yet.</div></section>`);
        return;
      }
      app.innerHTML = resultMarkup(state.negotiation);
      document.title = "RateDrop · Result";
      bindResultEvents();
    } catch (error) {
      app.innerHTML = pageShell(`<section class="card"><div class="error">${escapeHtml(error.message)}</div></section>`);
    }
    return;
  }

  app.innerHTML = pageShell(`<section class="card"><div class="error">Page not found.</div></section>`);
}

window.addEventListener("popstate", () => {
  renderRoute();
});

renderRoute();
