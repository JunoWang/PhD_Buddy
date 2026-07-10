# PhD Buddy

PhD Buddy is a local-first research companion for PhD students. The onboarding slice now supports local signup/signin, a skippable profile wizard, personalized research identity capture, and a starter set of fundamental papers with local `summarize.md` notes.

## Project Setup

```bash
uv sync --dev
```

## Run Onboarding

```bash
uv run phd-buddy onboard
```

By default this writes:

- `vault/onboarding/onboarding_profile.json`
- `vault/onboarding/onboarding_profile.md`

The JSON file is the canonical profile and panel-state cache. The markdown file is the student-facing vault note.

## Render An Existing Profile

```bash
uv run phd-buddy render-onboarding vault/onboarding/onboarding_profile.json
```

## Run The Web App Locally

```bash
uv run phd-buddy serve
```

Then open:

```text
http://127.0.0.1:8000
```

The web app saves the same local files under `vault/onboarding/`.

Onboarding can collect:

- research field, subfield, venues, seed papers, and Google Scholar profile
- name, preferred name, school, department, sex, age, and degree stage
- advisor/committee notes, milestones, current goals, pain points, weekly availability, and notifications

Local accounts are stored under `vault/auth/users.json`. This is intended for local development and local-first identity, not production authentication.

## Test

```bash
uv run pytest
```
