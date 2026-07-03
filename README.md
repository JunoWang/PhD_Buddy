# PhD Buddy

PhD Buddy is a local-first research companion for PhD students. The first implemented slice is onboarding: it captures a student's major research field, subdomains, interested venues/conferences, and optional Google Scholar profile, then writes a dual-format cache for the vault.

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

## Test

```bash
uv run pytest
```
