"""Command-line interface for PhD Buddy."""

from __future__ import annotations

import argparse
from pathlib import Path

from .onboarding import OnboardingPlan, ResearchProfile, load_plan, render_markdown, save_plan


def main() -> None:
    parser = argparse.ArgumentParser(prog="phd-buddy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    onboard = subparsers.add_parser("onboard", help="Capture a PhD Buddy onboarding profile.")
    onboard.add_argument(
        "--output-dir",
        type=Path,
        default=Path("vault/onboarding"),
        help="Directory for onboarding_profile.json and onboarding_profile.md.",
    )

    render = subparsers.add_parser("render-onboarding", help="Render onboarding JSON to markdown.")
    render.add_argument("profile_json", type=Path)

    serve = subparsers.add_parser("serve", help="Run the local PhD Buddy web app.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    args = parser.parse_args()

    if args.command == "onboard":
        plan = OnboardingPlan.from_profile(_prompt_for_profile())
        json_path, markdown_path = save_plan(plan, args.output_dir)
        print(f"Wrote {json_path}")
        print(f"Wrote {markdown_path}")
        return

    if args.command == "render-onboarding":
        print(render_markdown(load_plan(args.profile_json)))
        return

    if args.command == "serve":
        import uvicorn

        uvicorn.run("phd_buddy.web:app", host=args.host, port=args.port, reload=args.reload)
        return


def _prompt_for_profile() -> ResearchProfile:
    print("PhD Buddy onboarding")
    print("Optional fields can be skipped.")
    return ResearchProfile(
        major_field=_required("Major field"),
        subdomains=_required_list("Subdomains, comma-separated"),
        venues=_required_list("Interested venues/conferences, comma-separated"),
        google_scholar_url=input("Google Scholar profile URL, optional: ").strip(),
        known_seed_papers=_list_prompt("Known seed papers, comma-separated"),
        recent_keywords=_list_prompt("Recent-search keywords, comma-separated"),
    )


def _required(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("This field is required.")


def _list_prompt(label: str) -> list[str]:
    raw = input(f"{label}: ").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _required_list(label: str) -> list[str]:
    while True:
        values = _list_prompt(label)
        if values:
            return values
        print("At least one value is required.")
