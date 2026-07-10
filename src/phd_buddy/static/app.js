const form = document.querySelector("#onboardingForm");
const authForm = document.querySelector("#authForm");
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
const readingPaperList = document.querySelector("#readingPaperList");
const researchIdentityLine = document.querySelector("#researchIdentityLine");
const researchBuddyPrompt = document.querySelector("#researchBuddyPrompt");
const profileSummary = document.querySelector("#profileSummary");
const profileChips = document.querySelector("#profileChips");
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
  "recent_keywords",
  "milestones",
  "current_goals",
  "pain_points",
  "notification_preferences",
]);

let authMode = "signup";
let currentStep = 0;
let currentPlan = null;

const storedUser = loadSession();
if (storedUser) {
  setStatus(`Signed in as ${storedUser.name || storedUser.email}`, "saved");
  authForm.classList.add("collapsed");
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
    authForm.classList.add("collapsed");
    syncNameFromAccount(data.user);
    setStatus(`Signed in as ${data.user.name || data.user.email}`, "saved");
  } catch (error) {
    setStatus("Auth failed", "error");
    markdownOutput.textContent = messageFromError(error);
  }
});

continueGuest.addEventListener("click", () => {
  localStorage.removeItem("phdBuddySession");
  authForm.classList.add("collapsed");
  setStatus("Guest draft", "");
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
    researchBuddyPrompt.textContent = `Good. I will start by helping you ${button.textContent.trim().toLowerCase()} using your foundational papers.`;
  });
});

editOnboarding.addEventListener("click", () => {
  dashboardView.hidden = true;
  dashboardView.classList.remove("active");
  onboardingView.hidden = false;
  onboardingView.classList.add("active");
});

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
    const text = String(value).trim();
    payload[name] = listFields.has(name) ? parseList(text) : text;
  }
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
  onboardingView.hidden = true;
  onboardingView.classList.remove("active");
  dashboardView.hidden = false;
  dashboardView.classList.add("active");
  showDashboardTab("research");
}

function showDashboardTab(tab) {
  const labels = {
    research: ["Research Buddy", "Start from your fundamental papers, then pick the first research goal."],
    reading: ["Reading Buddy", "Read, summarize, and deep-dive into papers without losing the thread."],
    schedule: ["Schedule Buddy", "Turn milestones and weekly availability into a calm research rhythm."],
    support: ["Mental Support Buddy", "Use low-pressure check-ins and structure when the PhD feels heavy."],
    profile: ["Profile", "Review the saved context that personalizes every buddy."],
  };
  dashboardTabs.forEach((button) => button.classList.toggle("active", button.dataset.dashboardTab === tab));
  dashboardPanels.forEach((panel) => panel.classList.toggle("active", panel.dataset.dashboardPanel === tab));
  dashboardTitle.textContent = labels[tab][0];
  dashboardSubtitle.textContent = labels[tab][1];
}

function renderDashboard(plan) {
  const profile = plan.profile || {};
  const student = profile.student || {};
  const papers = plan.fundamental_papers || [];
  const subdomains = profile.subdomains || [];
  const researchLine = [profile.major_field, subdomains.join(", ")].filter(Boolean).join(" / ");

  researchIdentityLine.textContent = researchLine || "Research identity saved from onboarding";
  researchBuddyPrompt.textContent = `I found ${papers.length} starter papers for ${researchLine || "your research area"}. Pick a first goal and I will help you make the first step concrete.`;
  dashboardPaperList.innerHTML = renderDashboardPaperCards(papers);
  readingPaperList.innerHTML = renderDashboardPaperCards(papers);
  profileSummary.textContent = `${student.preferred_name || student.name || "Student"}${student.school ? ` at ${student.school}` : ""}${profile.major_field ? `, focused on ${profile.major_field}` : ""}.`;
  profileChips.innerHTML = [
    profile.major_field,
    ...subdomains,
    student.degree_stage,
    student.department,
    ...(student.current_goals || []),
  ]
    .filter(Boolean)
    .map((item) => `<span>${escapeHtml(item)}</span>`)
    .join("");
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
