const form = document.querySelector("#onboardingForm");
const saveStatus = document.querySelector("#saveStatus");
const markdownOutput = document.querySelector("#markdownOutput");
const outputPaths = document.querySelector("#outputPaths");
const copyMarkdown = document.querySelector("#copyMarkdown");
const loadLatest = document.querySelector("#loadLatest");

const listFields = new Set(["subdomains", "venues", "known_seed_papers", "recent_keywords"]);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Saving...", "");

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
    setStatus("Saved locally", "saved");
  } catch (error) {
    setStatus("Save failed", "error");
    markdownOutput.textContent = error instanceof Error ? error.message : String(error);
  }
});

form.addEventListener("reset", () => {
  window.setTimeout(() => {
    outputPaths.hidden = true;
    outputPaths.textContent = "";
    markdownOutput.textContent = "Complete the profile to generate the onboarding note.";
    setStatus("Local draft", "");
  }, 0);
});

loadLatest.addEventListener("click", async () => {
  setStatus("Loading...", "");
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
    setStatus("Loaded latest", "saved");
  } catch (error) {
    setStatus("Load failed", "error");
    markdownOutput.textContent = error instanceof Error ? error.message : String(error);
  }
});

copyMarkdown.addEventListener("click", async () => {
  const text = markdownOutput.textContent || "";
  if (!text || text.startsWith("Complete the profile")) {
    return;
  }
  await navigator.clipboard.writeText(text);
  setStatus("Markdown copied", "saved");
});

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
  for (const [name, value] of Object.entries(profile)) {
    const field = form.elements.namedItem(name);
    if (!field) {
      continue;
    }
    field.value = Array.isArray(value) ? value.join("\n") : value;
  }
}

function renderResult(data) {
  markdownOutput.textContent = data.markdown;
  outputPaths.hidden = false;
  outputPaths.innerHTML = `
    <div><strong>JSON:</strong> ${escapeHtml(data.paths.json)}</div>
    <div><strong>Markdown:</strong> ${escapeHtml(data.paths.markdown)}</div>
  `;
}

function setStatus(message, state) {
  saveStatus.textContent = message;
  saveStatus.className = state ? `status-pill ${state}` : "status-pill";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
