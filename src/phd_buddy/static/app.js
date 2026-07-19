const form = document.querySelector("#onboardingForm");
const authForm = document.querySelector("#authForm");
const authView = document.querySelector("#authView");
const onboardingView = document.querySelector("#onboardingView");
const dashboardView = document.querySelector("#dashboardView");
const saveStatus = document.querySelector("#saveStatus");
const markdownOutput = document.querySelector("#markdownOutput");
const outputPaths = document.querySelector("#outputPaths");
const copyMarkdown = document.querySelector("#copyMarkdown");
const loadLatest = document.querySelector("#loadLatest");
const paperList = document.querySelector("#paperList");
const paperCount = document.querySelector("#paperCount");
const stepMeterFill = document.querySelector("#stepMeterFill");
const nextStep = document.querySelector("#nextStep");
const previousStep = document.querySelector("#previousStep");
const continueGuest = document.querySelector("#continueGuest");
const authSubmit = document.querySelector("#authSubmit");
const authNameField = document.querySelector("#authNameField");
const editOnboarding = document.querySelector("#editOnboarding");
const dashboardTitle = document.querySelector("#dashboardTitle");
const dashboardSubtitle = document.querySelector("#dashboardSubtitle");
const dashboardPaperList = document.querySelector("#dashboardPaperList");
const importedPaperList = document.querySelector("#importedPaperList");
const researchHome = document.querySelector("#researchHome");
const readerView = document.querySelector("#readerView");
const backToReadlist = document.querySelector("#backToReadlist");
const readingProgress = document.querySelector("#readingProgress");
const readingProgressLabel = document.querySelector("#readingProgressLabel");
const queueCount = document.querySelector("#queueCount");
const progressCount = document.querySelector("#progressCount");
const studentName = document.querySelector("#studentName");
const paperReaderTitle = document.querySelector("#paperReaderTitle");
const paperReaderMeta = document.querySelector("#paperReaderMeta");
const paperReader = document.querySelector("#paperReader");
const researchIdentityLine = document.querySelector("#researchIdentityLine");
const researchBuddyPrompt = document.querySelector("#researchBuddyPrompt");
const chatContextLine = document.querySelector("#chatContextLine");
const chatSurface = document.querySelector(".chat-surface");
const chatDraft = document.querySelector("#chatDraft");
const askResearchBuddy = document.querySelector("#askResearchBuddy");
const paperSearchDraft = document.querySelector("#paperSearchDraft");
const searchPapers = document.querySelector("#searchPapers");
const refreshRecommendations = document.querySelector("#refreshRecommendations");
const paperSearchResults = document.querySelector("#paperSearchResults");
const paperAgentAnswer = document.querySelector("#paperAgentAnswer");
const researchChatPanel = document.querySelector("#researchChatPanel");
const toggleResearchChat = document.querySelector("#toggleResearchChat");
const understandingModeButtons = document.querySelectorAll("[data-understanding-mode]");
const authSegments = document.querySelectorAll("[data-auth-mode]");
const stepButtons = document.querySelectorAll("[data-step]");
const stepPanels = document.querySelectorAll("[data-step-panel]");
const dashboardTabs = document.querySelectorAll("[data-dashboard-tab]");
const dashboardPanels = document.querySelectorAll("[data-dashboard-panel]");
const goalButtons = document.querySelectorAll("#goalPicker button");

const listFields = new Set([
  "subdomains",
  "venues",
  "known_seed_papers",
  "seed_paper_urls",
  "recent_keywords",
  "milestones",
  "current_goals",
  "pain_points",
  "notification_preferences",
]);

let authMode = "signup";
let currentStep = 0;
let currentPlan = null;
let selectedGoal = "";
let paperSearchCache = [];
let importedPapersCache = [];
let selectedPaperId = "";
let selectedPaperTitle = "";
let selectedUnderstandingMode = "Explain simply";
let readingProgressByPaper = loadReadingProgress();

const storedUser = loadSession();
if (storedUser) {
  setStatus(`Signed in as ${storedUser.name || storedUser.email}`, "saved");
  syncNameFromAccount(storedUser);
  showOnboarding();
}

authSegments.forEach((button) => {
  button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus(authMode === "signup" ? "Creating account..." : "Signing in...", "");
  const payload = Object.fromEntries(new FormData(authForm).entries());
  try {
    const response = await fetch(`/api/auth/${authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    localStorage.setItem("phdBuddySession", JSON.stringify(data));
    syncNameFromAccount(data.user);
    setStatus(`Signed in as ${data.user.name || data.user.email}`, "saved");
    showOnboarding();
  } catch (error) {
    setStatus("Auth failed", "error");
  }
});

continueGuest.addEventListener("click", () => {
  localStorage.removeItem("phdBuddySession");
  setStatus("Guest draft", "");
  showOnboarding();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Saving onboarding...", "");

  const payload = formToPayload(new FormData(form));
  try {
    const response = await fetch("/api/onboarding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const data = await response.json();
    renderResult(data);
    showDashboard(data);
    setStatus("Saved locally", "saved");
  } catch (error) {
    setStatus("Save failed", "error");
    markdownOutput.textContent = messageFromError(error);
  }
});

form.addEventListener("reset", () => {
  window.setTimeout(() => {
    outputPaths.hidden = true;
    outputPaths.textContent = "";
    renderPapers([]);
    markdownOutput.textContent = "Complete any fields you know, then save onboarding to generate the companion profile.";
    setStatus(loadSession() ? "Signed in" : "Local draft", "");
    showStep(0);
  }, 0);
});

loadLatest.addEventListener("click", async () => {
  setStatus("Loading latest...", "");
  try {
    const response = await fetch("/api/onboarding/latest");
    if (response.status === 404) {
      setStatus("No saved profile", "error");
      return;
    }
    if (!response.ok) {
      throw new Error(await response.text());
    }

    const data = await response.json();
    populateForm(data.plan.profile);
    renderResult(data);
    showDashboard(data);
    setStatus("Loaded latest", "saved");
  } catch (error) {
    setStatus("Load failed", "error");
    markdownOutput.textContent = messageFromError(error);
  }
});

copyMarkdown.addEventListener("click", async () => {
  const text = markdownOutput.textContent || "";
  if (!text || text.startsWith("Complete any fields")) {
    return;
  }
  await navigator.clipboard.writeText(text);
  setStatus("Markdown copied", "saved");
});

nextStep.addEventListener("click", () => showStep(Math.min(currentStep + 1, stepPanels.length - 1)));
previousStep.addEventListener("click", () => showStep(Math.max(currentStep - 1, 0)));

stepButtons.forEach((button) => {
  button.addEventListener("click", () => showStep(Number(button.dataset.step)));
});

dashboardTabs.forEach((button) => {
  button.addEventListener("click", () => showDashboardTab(button.dataset.dashboardTab));
});

goalButtons.forEach((button) => {
  button.addEventListener("click", () => {
    goalButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedGoal = button.textContent.trim().toLowerCase();
    researchBuddyPrompt.textContent = `Good. I will start by helping you ${selectedGoal} using your foundational papers.`;
  });
});

askResearchBuddy.addEventListener("click", askResearchQuestion);
searchPapers.addEventListener("click", searchPaperLibrary);
refreshRecommendations.addEventListener("click", searchPaperLibrary);
toggleResearchChat.addEventListener("click", toggleChatPanel);
backToReadlist.addEventListener("click", showResearchHome);
readingProgress.addEventListener("input", updateReadingProgress);
understandingModeButtons.forEach((button) => {
  button.addEventListener("click", () => setUnderstandingMode(button.dataset.understandingMode));
});
chatDraft.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    askResearchQuestion();
  }
});
paperSearchDraft.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchPaperLibrary();
  }
});
editOnboarding.addEventListener("click", () => {
  showOnboarding();
});

document.querySelectorAll(".support-checkin button").forEach((button) => {
  button.addEventListener("click", () => {
    const response = button.closest(".checkin-card")?.querySelector(".checkin-response");
    document.querySelectorAll(".support-checkin button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    if (response) {
      response.textContent = mentalBuddyResponse(button.textContent.trim());
    }
  });
});

document.querySelectorAll(".reader-outline nav button").forEach((button, index) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".reader-outline nav button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const heading = paperReader.querySelectorAll("h1, h2, h3")[Math.max(0, index - 1)];
    (heading || paperReader).scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

function showAuth() {
  setActiveView(authView);
}

function showOnboarding() {
  setActiveView(onboardingView);
}

function setActiveView(activeView) {
  [authView, onboardingView, dashboardView].forEach((view) => {
    view.hidden = view !== activeView;
    view.classList.toggle("active", view === activeView);
  });
}

function setAuthMode(mode) {
  authMode = mode;
  authSegments.forEach((button) => button.classList.toggle("active", button.dataset.authMode === mode));
  authNameField.hidden = mode === "signin";
  authSubmit.textContent = mode === "signup" ? "Create account" : "Sign in";
}

function showStep(step) {
  currentStep = step;
  stepButtons.forEach((button) => button.classList.toggle("active", Number(button.dataset.step) === step));
  stepPanels.forEach((panel) => panel.classList.toggle("active", Number(panel.dataset.stepPanel) === step));
  previousStep.disabled = step === 0;
  nextStep.disabled = step === stepPanels.length - 1;
  stepMeterFill.style.width = `${((step + 1) / stepPanels.length) * 100}%`;
}

function formToPayload(formData) {
  const payload = {};
  for (const [name, value] of formData.entries()) {
    if (name === "seed_paper_files") {
      continue;
    }
    const text = String(value).trim();
    payload[name] = listFields.has(name) ? parseList(text) : text;
  }
  const seedUrls = payload.seed_paper_urls || [];
  if (seedUrls.length) {
    payload.known_seed_papers = [...(payload.known_seed_papers || []), ...seedUrls];
  }
  delete payload.seed_paper_urls;
  return payload;
}

function parseList(text) {
  if (!text) {
    return [];
  }
  return text
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function populateForm(profile) {
  const flatProfile = { ...profile, ...(profile.student || {}) };
  for (const [name, value] of Object.entries(flatProfile)) {
    const field = form.elements.namedItem(name);
    if (!field) {
      continue;
    }
    field.value = Array.isArray(value) ? value.join("\n") : value;
  }
}

function syncNameFromAccount(user) {
  if (!user?.name) {
    return;
  }
  const nameField = form.elements.namedItem("name");
  const preferredField = form.elements.namedItem("preferred_name");
  if (nameField && !nameField.value) {
    nameField.value = user.name;
  }
  if (preferredField && !preferredField.value) {
    preferredField.value = user.name.split(" ")[0];
  }
}

function renderResult(data) {
  currentPlan = data.plan;
  markdownOutput.textContent = data.markdown;
  outputPaths.hidden = false;
  outputPaths.innerHTML = `
    <div><strong>JSON:</strong> ${escapeHtml(data.paths.json)}</div>
    <div><strong>Markdown:</strong> ${escapeHtml(data.paths.markdown)}</div>
  `;
  renderPapers(data.plan.fundamental_papers || []);
}

function showDashboard(data) {
  currentPlan = data.plan;
  renderDashboard(currentPlan);
  setActiveView(dashboardView);
  showDashboardTab("research");
  loadImportedPapers();
  searchPaperLibrary();
}

function showDashboardTab(tab) {
  const labels = {
    research: ["Research Buddy", "A calm place to discover, queue, and deeply read the papers that matter."],
    schedule: ["Task Buddy", "Turn milestones into a realistic week and a small, useful next step."],
    support: ["Mental Buddy", "A private, low-pressure place to pause, name what is hard, and reset."],
  };
  dashboardTabs.forEach((button) => button.classList.toggle("active", button.dataset.dashboardTab === tab));
  dashboardPanels.forEach((panel) => panel.classList.toggle("active", panel.dataset.dashboardPanel === tab));
  dashboardTitle.textContent = labels[tab][0];
  dashboardSubtitle.textContent = labels[tab][1];
  if (tab === "research") {
    showResearchHome();
  }
}

function renderDashboard(plan) {
  const profile = plan.profile || {};
  const student = profile.student || {};
  const papers = plan.fundamental_papers || [];
  const subdomains = profile.subdomains || [];
  const researchLine = [profile.major_field, subdomains.join(", ")].filter(Boolean).join(" / ");

  researchIdentityLine.textContent = researchLine || "Research identity saved from onboarding";
  studentName.textContent = student.preferred_name || student.name || profile.preferred_name || profile.name || "Researcher";
  researchBuddyPrompt.textContent = `I found ${papers.length} seed papers for ${researchLine || "your research area"}. Select an imported paper and I will answer from its chunked RAG context.`;
  resetChatSurface(researchBuddyPrompt.textContent);
  dashboardPaperList.innerHTML = renderDashboardPaperCards(papers);
}

async function askResearchQuestion() {
  const message = chatDraft.value.trim();
  if (!message) {
    chatDraft.focus();
    return;
  }
  const modePrefix = `${selectedUnderstandingMode}${selectedPaperTitle ? ` for "${selectedPaperTitle}"` : ""}`;
  appendChatMessage("student", `${message} (${selectedUnderstandingMode})`);
  chatDraft.value = "";
  askResearchBuddy.disabled = true;
  askResearchBuddy.textContent = "Thinking";
  paperAgentAnswer.innerHTML = `<div class="empty-state"><span>Running guardrail, retrieval, grading, and answer generation...</span></div>`;
  try {
    const response = await fetch("/api/reading/ask-agentic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: `${modePrefix}: ${message}`,
        paper_id: selectedPaperId,
      }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    appendResearchBuddyResponse(data);
  } catch (error) {
    appendChatMessage("assistant", messageFromError(error));
  } finally {
    askResearchBuddy.disabled = false;
    askResearchBuddy.textContent = "Ask";
  }
}

function resetChatSurface(message) {
  chatSurface.innerHTML = `
    <div class="chat-message assistant">
      <strong>Research Buddy</strong>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function appendChatMessage(role, message) {
  const label = role === "student" ? "You" : "Research Buddy";
  chatSurface.insertAdjacentHTML(
    "beforeend",
    `
      <div class="chat-message ${role}">
        <strong>${label}</strong>
        <p>${escapeHtml(message)}</p>
      </div>
    `,
  );
  chatSurface.scrollTop = chatSurface.scrollHeight;
}

function appendResearchBuddyResponse(data) {
  const steps = (data.reasoning_steps || [])
    .map((step) => `<span>${escapeHtml(step.node)}: ${escapeHtml(step.status)}</span>`)
    .join("");
  const references = (data.sources || data.referenced_papers || [])
    .map((source) => `<span>${escapeHtml(source.title)}${source.section ? ` · ${escapeHtml(source.section)}` : ""}</span>`)
    .join("");
  chatSurface.insertAdjacentHTML(
    "beforeend",
    `
      <div class="chat-message assistant">
        <strong>Research Buddy</strong>
        <p>${escapeHtml(data.answer || data.message)}</p>
        ${steps ? `<div class="agent-steps">${steps}</div>` : ""}
        ${references ? `<div class="chat-references">${references}</div>` : ""}
      </div>
    `,
  );
  paperAgentAnswer.innerHTML = references
    ? `<div class="agent-response"><p>${escapeHtml(data.answer || data.message)}</p><div class="chat-references">${references}</div></div>`
    : "";
  chatSurface.scrollTop = chatSurface.scrollHeight;
}

async function searchPaperLibrary() {
  const query = paperSearchDraft.value.trim();
  searchPapers.disabled = true;
  searchPapers.textContent = "Searching";
  paperSearchResults.innerHTML = `<div class="empty-state"><span>Searching arXiv...</span></div>`;
  try {
    const response = await fetch("/api/library/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, use_onboarding: !query }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    paperSearchCache = data.results || [];
    renderPaperSearchResults(paperSearchCache);
  } catch (error) {
    paperSearchResults.innerHTML = `<div class="empty-state"><strong>Search failed</strong><span>${escapeHtml(messageFromError(error))}</span></div>`;
  } finally {
    searchPapers.disabled = false;
    searchPapers.textContent = "Search";
  }
}

function renderPaperSearchResults(results) {
  if (!results.length) {
    paperSearchResults.innerHTML = `<div class="empty-state"><strong>No recommendations yet</strong><span>Try a broader topic, method, author, or venue.</span></div>`;
    return;
  }
  paperSearchResults.innerHTML = results
    .map(
      (paper, index) => `
        <article class="paper-result">
          <div>
            <span class="paper-year">${escapeHtml(paper.year || "n.d.")}</span>
            <h3>${escapeHtml(paper.title)}</h3>
            <p>${escapeHtml((paper.authors || []).join(", ") || "Unknown authors")}</p>
            <p>${escapeHtml(paper.abstract || "").slice(0, 260)}</p>
          </div>
          <button class="secondary-button small" type="button" data-import-paper="${index}">+ Add to readlist</button>
        </article>
      `,
    )
    .join("");
  paperSearchResults.querySelectorAll("[data-import-paper]").forEach((button) => {
    button.addEventListener("click", () => importPaper(Number(button.dataset.importPaper), button));
  });
}

async function importPaper(index, button) {
  const paper = paperSearchCache[index];
  if (!paper) {
    return;
  }
  button.disabled = true;
  button.textContent = "Adding…";
  try {
    const response = await fetch("/api/library/papers/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(paper),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    await fetch(`/api/reading/papers/${encodeURIComponent(data.paper.paper_id)}/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_text: "" }),
    });
    readingProgressByPaper[data.paper.paper_id] = 0;
    saveReadingProgress();
    button.textContent = data.acquisition_error ? "Added · PDF pending" : "Added to readlist ✓";
    setStatus(data.acquisition_error ? "Added to readlist · PDF pending" : "Added to readlist", data.acquisition_error ? "" : "saved");
    await loadImportedPapers();
  } catch (error) {
    button.disabled = false;
    button.textContent = "+ Add to readlist";
    paperAgentAnswer.innerHTML = `<div class="empty-state"><strong>Import failed</strong><span>${escapeHtml(messageFromError(error))}</span></div>`;
  }
}

async function loadImportedPapers() {
  try {
    const response = await fetch("/api/library/papers");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    renderImportedPapers(data.papers || []);
  } catch (error) {
    importedPaperList.innerHTML = `<div class="empty-state"><strong>Could not load imported papers</strong><span>${escapeHtml(messageFromError(error))}</span></div>`;
  }
}

function renderImportedPapers(papers) {
  importedPapersCache = papers;
  if (!papers.length) {
    importedPaperList.innerHTML = `
      <div class="empty-state">
        <strong>Your readlist is ready for its first paper</strong>
        <span>Choose “Add to readlist” on a recommendation below. It will land here as ready to read.</span>
      </div>
    `;
    queueCount.textContent = "0";
    progressCount.textContent = "0";
    return;
  }

  const groups = {
    progress: papers.filter((paper) => paperProgress(paper.paper_id) > 0 && paperProgress(paper.paper_id) < 100),
    ready: papers.filter((paper) => paperProgress(paper.paper_id) === 0),
    finished: papers.filter((paper) => paperProgress(paper.paper_id) === 100),
  };
  queueCount.textContent = String(groups.ready.length);
  progressCount.textContent = String(groups.progress.length);
  importedPaperList.innerHTML = [
    renderReadlistLane("In progress", "Continue where you left off", groups.progress, "progress"),
    renderReadlistLane("Ready to read", "Saved for your next session", groups.ready, "ready"),
    groups.finished.length ? renderReadlistLane("Completed", "Finished papers", groups.finished, "finished") : "",
  ].join("");

  importedPaperList.querySelectorAll("[data-read-paper]").forEach((card) => {
    card.addEventListener("click", () => loadPaperMarkdown(card.dataset.readPaper));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        loadPaperMarkdown(card.dataset.readPaper);
      }
    });
  });
}

function renderReadlistLane(title, subtitle, papers, state) {
  const emptyCopy = state === "progress"
    ? "Start a ready paper and it will move here automatically."
    : "Add one of the recommendations below to build your queue.";
  return `
    <section class="readlist-lane">
      <div class="lane-label"><strong>${title}</strong><span>${subtitle}</span></div>
      <div class="lane-papers">
        ${papers.length ? papers.map((paper) => renderReadlistCard(paper, state)).join("") : `<div class="empty-state"><span>${emptyCopy}</span></div>`}
      </div>
    </section>
  `;
}

function renderReadlistCard(paper, state) {
  const progress = paperProgress(paper.paper_id);
  const action = progress > 0 && progress < 100 ? "Continue reading" : progress === 100 ? "Read again" : "Start reading";
  const status = progress === 100 ? "Completed" : progress > 0 ? `${progress}% read` : "Ready";
  return `
    <article class="reading-card imported ${state}" data-read-paper="${escapeHtml(paper.paper_id)}" role="button" tabindex="0" aria-label="${escapeHtml(action)}: ${escapeHtml(paper.title)}">
      <div class="reading-card-top"><span class="status-chip">${status}</span><span>${escapeHtml(paper.year || "n.d.")}</span></div>
      <div><h3>${escapeHtml(paper.title)}</h3><p>${escapeHtml((paper.authors || []).join(", ") || "Unknown authors")}</p></div>
      <div class="reading-card-actions">
        <span><strong>${action} →</strong></span>
        <div class="progress-track" aria-label="${progress}% read"><i style="--progress:${progress}%"></i></div>
      </div>
    </article>
  `;
}

function setUnderstandingMode(mode) {
  selectedUnderstandingMode = mode || "Explain simply";
  understandingModeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.understandingMode === selectedUnderstandingMode);
  });
  updateChatContextLine();
}

function toggleChatPanel() {
  researchChatPanel.classList.toggle("collapsed");
  const isCollapsed = researchChatPanel.classList.contains("collapsed");
  toggleResearchChat.title = isCollapsed ? "Expand RAG chat" : "Collapse RAG chat";
  toggleResearchChat.querySelector("[aria-hidden='true']").textContent = isCollapsed ? "+" : "–";
}

async function loadPaperMarkdown(paperId) {
  if (!paperId) {
    return;
  }
  selectedPaperId = paperId;
  readingProgress.value = String(paperProgress(paperId));
  readingProgressLabel.textContent = `${paperProgress(paperId)}%`;
  showReaderView();
  paperReaderTitle.textContent = "Loading Paper";
  paperReader.innerHTML = `<p class="reader-empty">Preparing the paper…</p>`;
  try {
    const detail = await fetch(`/api/library/papers/${encodeURIComponent(paperId)}`);
    if (!detail.ok) {
      throw new Error(await detail.text());
    }
    const paper = (await detail.json()).paper;
    const response = await fetch(`/api/reading/papers/${encodeURIComponent(paperId)}/markdown`);
    if (!response.ok) {
      throw new Error("Markdown is not available yet. Download/import the PDF again or provide the PDF manually.");
    }
    selectedPaperTitle = paper.title || "";
    if (paperProgress(paperId) === 0) {
      readingProgressByPaper[paperId] = 5;
      readingProgress.value = "5";
      readingProgressLabel.textContent = "5%";
      saveReadingProgress();
    }
    paperReaderTitle.textContent = paper.title || "Paper Reader";
    paperReaderMeta.textContent = `${(paper.authors || []).join(", ") || "Unknown authors"}${paper.year ? ` · ${paper.year}` : ""}${(paper.chunks || []).length ? ` · ${paper.chunks.length} chunks` : ""}`;
    paperReader.innerHTML = renderMarkdownDocument(await response.text());
    markSelectedPaper(paperId);
    updateChatContextLine();
    researchBuddyPrompt.textContent = `I’m reading “${selectedPaperTitle}” with you. Pick a mode or ask about any claim, method, or experiment.`;
    resetChatSurface(researchBuddyPrompt.textContent);
  } catch (error) {
    paperReaderTitle.textContent = "Paper Reader";
    paperReaderMeta.textContent = "Markdown unavailable";
    paperReader.innerHTML = `<p class="reader-empty">${escapeHtml(messageFromError(error))}</p>`;
  }
}

function showReaderView() {
  researchHome.hidden = true;
  researchHome.classList.remove("active");
  readerView.hidden = false;
  dashboardTitle.textContent = "Reading room";
  dashboardSubtitle.textContent = "Read with a clear paper map, lightweight progress, and grounded help beside you.";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showResearchHome() {
  readerView.hidden = true;
  researchHome.hidden = false;
  researchHome.classList.add("active");
  dashboardTitle.textContent = "Research Buddy";
  dashboardSubtitle.textContent = "A calm place to discover, queue, and deeply read the papers that matter.";
  if (importedPapersCache.length) {
    renderImportedPapers(importedPapersCache);
  }
}

function updateReadingProgress() {
  if (!selectedPaperId) {
    return;
  }
  const progress = Number(readingProgress.value);
  readingProgressByPaper[selectedPaperId] = progress;
  readingProgressLabel.textContent = `${progress}%`;
  saveReadingProgress();
  if (progress === 100) {
    setStatus("Paper marked complete", "saved");
  }
}

function paperProgress(paperId) {
  const value = Number(readingProgressByPaper[paperId] || 0);
  return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
}

function loadReadingProgress() {
  try {
    return JSON.parse(localStorage.getItem("phdBuddyReadingProgress") || "{}") || {};
  } catch {
    return {};
  }
}

function saveReadingProgress() {
  localStorage.setItem("phdBuddyReadingProgress", JSON.stringify(readingProgressByPaper));
}

function renderMarkdownDocument(markdown) {
  const safe = escapeHtml(markdown || "").replace(/\r\n/g, "\n");
  const lines = safe.split("\n");
  const html = [];
  let listType = "";
  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = "";
    }
  };
  lines.forEach((line) => {
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    const unordered = line.match(/^[-*]\s+(.+)$/);
    const ordered = line.match(/^\d+\.\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
    } else if (unordered || ordered) {
      const nextType = unordered ? "ul" : "ol";
      if (listType !== nextType) {
        closeList();
        listType = nextType;
        html.push(`<${listType}>`);
      }
      html.push(`<li>${inlineMarkdown((unordered || ordered)[1])}</li>`);
    } else if (line.trim()) {
      closeList();
      html.push(`<p>${inlineMarkdown(line)}</p>`);
    } else {
      closeList();
    }
  });
  closeList();
  return html.join("") || `<p class="reader-empty">This paper does not have readable text yet.</p>`;
}

function inlineMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function markSelectedPaper(paperId) {
  importedPaperList.querySelectorAll("[data-read-paper]").forEach((card) => {
    card.classList.toggle("selected", card.dataset.readPaper === paperId);
  });
}

function updateChatContextLine() {
  chatContextLine.textContent = selectedPaperTitle
    ? `${selectedUnderstandingMode} · ${selectedPaperTitle}`
    : `${selectedUnderstandingMode} · all imported papers`;
}

function renderDashboardPaperCards(papers) {
  if (!papers.length) {
    return `
      <div class="empty-state">
        <strong>No papers yet</strong>
        <span>Return to onboarding and save your research field to generate a starter set.</span>
      </div>
    `;
  }
  return papers
    .map(
      (paper) => `
        <article class="reading-card">
          <div>
            <span class="paper-year">${escapeHtml(paper.year)}</span>
            <h3>${escapeHtml(paper.title)}</h3>
            <p>${escapeHtml(paper.authors)}</p>
          </div>
          <p>${escapeHtml(paper.why_it_matters || "Starter reading note generated locally.")}</p>
          <span>${escapeHtml(paper.summary_path || "summarize.md")}</span>
        </article>
      `,
    )
    .join("");
}

function renderPapers(papers) {
  paperCount.textContent = String(papers.length);
  if (!papers.length) {
    paperList.classList.add("empty");
    paperList.innerHTML = `
      <div class="empty-state">
        <strong>No starter papers yet</strong>
        <span>Save onboarding to generate paper summaries.</span>
      </div>
    `;
    return;
  }
  paperList.classList.remove("empty");
  paperList.innerHTML = papers
    .map(
      (paper) => `
        <article class="paper-item">
          <span class="paper-year">${escapeHtml(paper.year)}</span>
          <div>
            <h3>${escapeHtml(paper.title)}</h3>
            <p>${escapeHtml(paper.authors)}</p>
          </div>
          <p class="paper-reason">${escapeHtml(paper.why_it_matters || "Starter reading note generated locally.")}</p>
          <span class="paper-path">${escapeHtml(paper.summary_path || "summarize.md")}</span>
        </article>
      `,
    )
    .join("");
}

function mentalBuddyResponse(feeling) {
  const responses = {
    "I feel stuck": "Let’s lower the bar: write one sentence describing the exact point where momentum stopped.",
    "I’m overwhelmed": "Nothing needs to be solved all at once. Choose one task to protect and let the rest wait for today.",
    "I need structure": "Try a 25-minute block: 5 minutes to define done, 15 minutes to work, 5 minutes to leave a restart note.",
    "I’m doing okay": "Good. Notice what is helping today, and protect a little of that steadiness for tomorrow.",
  };
  return responses[feeling] || "Name what is here, then choose the smallest kind action that would help.";
}

function setStatus(message, state) {
  saveStatus.textContent = message;
  saveStatus.className = state ? `status-pill ${state}` : "status-pill";
}

function loadSession() {
  try {
    return JSON.parse(localStorage.getItem("phdBuddySession") || "null")?.user || null;
  } catch {
    return null;
  }
}

function messageFromError(error) {
  return error instanceof Error ? error.message : String(error);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

showStep(0);
