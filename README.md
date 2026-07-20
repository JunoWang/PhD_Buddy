# PhD Buddy

PhD Buddy is a local-first workspace for reading research papers with a Research
Buddy, organizing work with a Task Buddy, and getting bounded, safety-first
support from a Mental Buddy.

This repository is an early test build. It is intended to run locally on your
computer; your profile, imported PDFs, reading progress, and conversations stay
inside the local `vault/` directory and are not committed to Git.

## What You Can Try

- Complete the research-profile onboarding flow.
- Search arXiv and add papers to your readlist.
- Read the original PDF or the readable-text version.
- View figures, equations, and tables preserved from the source PDF.
- Ask Research Buddy questions about an imported paper.
- Try the Task Buddy and Mental Buddy dashboard surfaces.
- Ask a combined question such as “I am overwhelmed by this deadline” to test
  the LangGraph Mental → Task handoff.

## 1. Get The Repository

You need Git and Conda. Miniforge, Miniconda, or Anaconda will work.

For a public repository:

```bash
git clone https://github.com/JunoWang/PhD_Buddy.git
cd PhD_Buddy
```

If the repository is private, ask the owner to add your GitHub account as a
collaborator before cloning.

## 2. Create The Conda Environment

From the repository directory, run:

```bash
conda env create --file environment.yml
conda activate phd-buddy
```

This creates an isolated Python 3.12 environment and installs PhD Buddy together
with its web, PDF, LangGraph, SQLite-checkpoint, and test dependencies.

If the environment already exists, update it after pulling new code:

```bash
conda env update --file environment.yml --prune
conda activate phd-buddy
```

## 3. Start The Web App

```bash
phd-buddy serve
```

Open this address in your browser:

```text
http://127.0.0.1:8000
```

Leave the terminal window running while you use the app. Stop the server with
`Control-C`.

If the `phd-buddy` command is not found, use:

```bash
python -m phd_buddy serve
```

If port 8000 is already occupied, use another port:

```bash
phd-buddy serve --port 8001
```

Then open `http://127.0.0.1:8001`.

## 4. Suggested Test Walkthrough

1. Create a local account or continue as a guest.
2. Enter a research field and one or two subdomains during onboarding.
3. Open Research Buddy and search for a paper.
4. Add the paper to the readlist and wait for the PDF import to finish.
5. Open the paper and compare **Readable text** with **Original paper**.
6. Check that paragraphs are complete and tables, formulas, and figures are
   readable and located near the relevant discussion.
7. Ask Research Buddy:
   - “What is the paper's main contribution?”
   - “Explain the table currently next to my reading position.”
   - “What evidence supports that claim?”
8. Ask a follow-up such as “How does that compare with the previous result?” to
   test conversation memory.
9. Try “I am overwhelmed by my deadline and task list” to test the safety-first
   Mental Buddy and Task Buddy handoff.

## 5. Run The Automated Checks

```bash
pytest -q
```

## Local Data And Privacy

PhD Buddy currently uses local files and SQLite:

- `vault/onboarding/` — onboarding profile
- `vault/library/` — imported papers, extracted text, and rendered paper elements
- `vault/auth/` — local development accounts
- `vault/phd_buddy.sqlite3` — LangGraph conversation checkpoints and buddy events

The entire `vault/` directory is excluded from Git. Every clone therefore starts
with an independent, empty workspace.

This is not yet a public multi-user service. Do not expose the development server
to the public internet or enter sensitive mental-health information in a shared
demo installation.

## Optional: Airflow Ingestion

Airflow is not required for the first web-app test. The repository includes the
`phd_buddy_daily_ingestion` DAG for recommendation sync, PDF acquisition,
indexing, reporting, and cleanup. Airflow should run in its own environment
because its dependencies are intentionally isolated from the web application.

The local Airflow integration is still a developer feature; ask the repository
owner for the current Airflow setup before testing it. Never expose Airflow's
port 8080 publicly.

## Pull Future Updates

```bash
git pull --ff-only
conda env update --file environment.yml --prune
conda activate phd-buddy
```

Restart the web server after updating.

## Reporting Feedback

When something goes wrong, please include:

- What you clicked or asked.
- The paper title and the section/page you were viewing.
- A screenshot of the problem.
- The terminal error, if one appeared.
- Your operating system and browser.

Do not include passwords, private notes, or sensitive personal information in a
bug report.
