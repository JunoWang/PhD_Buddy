"""Local Research Buddy chat responses grounded in the onboarding plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .profile import OnboardingPlan


@dataclass(frozen=True)
class ResearchChatResponse:
    message: str
    suggested_actions: list[str]
    referenced_papers: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "suggested_actions": self.suggested_actions,
            "referenced_papers": self.referenced_papers,
        }


def reply_to_research_chat(plan: OnboardingPlan, message: str, first_goal: str = "") -> ResearchChatResponse:
    profile = plan.profile
    student = profile.student
    papers = plan.fundamental_papers[:3]
    research_area = _research_area(plan)
    question = message.strip() or "Where should I start?"
    goal = first_goal.strip() or _infer_goal(question)
    name = student.preferred_name or student.name or "you"

    opening = (
        f"For {name}, I would start with a narrow path through {research_area}. "
        f"Your question is: \"{question}\"."
    )
    paper_sentence = _paper_sentence(papers)
    goal_sentence = _goal_sentence(goal)
    message_text = " ".join([opening, paper_sentence, goal_sentence])

    return ResearchChatResponse(
        message=message_text,
        suggested_actions=_suggested_actions(goal, papers),
        referenced_papers=[
            {
                "title": paper.title,
                "year": paper.year,
                "summary_path": paper.summary_path,
            }
            for paper in papers
        ],
    )


def _research_area(plan: OnboardingPlan) -> str:
    profile = plan.profile
    subdomains = ", ".join(profile.subdomains)
    if profile.major_field and subdomains:
        return f"{profile.major_field} / {subdomains}"
    return profile.major_field or subdomains or "your research area"


def _infer_goal(message: str) -> str:
    lower = message.lower()
    if any(term in lower for term in ["advisor", "meeting", "committee"]):
        return "prepare advisor meeting"
    if any(term in lower for term in ["summary", "summarize", "read", "paper"]):
        return "plan first paper summary"
    if any(term in lower for term in ["week", "schedule", "time", "rhythm"]):
        return "create weekly research rhythm"
    return "build literature foundation"


def _paper_sentence(papers) -> str:
    if not papers:
        return "I do not see starter papers yet, so first save a research field and subfield in onboarding."
    titles = "; ".join(f"{paper.title} ({paper.year})" for paper in papers)
    return f"Use these first anchors: {titles}."


def _goal_sentence(goal: str) -> str:
    if goal == "prepare advisor meeting":
        return "Turn those papers into three advisor-ready bullets: what you understand, what is unclear, and what decision you need."
    if goal == "plan first paper summary":
        return "Pick one paper, read its abstract and introduction first, then write a short problem-method-result summary before deep reading."
    if goal == "create weekly research rhythm":
        return "Block one reading session, one synthesis session, and one writing session before adding extra papers."
    return "Build the foundation by reading for lineage: what problem each paper introduced, what assumption it changed, and what later work reused."


def _suggested_actions(goal: str, papers) -> list[str]:
    first_title = papers[0].title if papers else "the first starter paper"
    if goal == "prepare advisor meeting":
        return [
            f"Write 3 questions about {first_title}.",
            "Draft a 5-minute meeting agenda.",
            "Mark one decision you want from the advisor.",
        ]
    if goal == "plan first paper summary":
        return [
            f"Open the summarize.md note for {first_title}.",
            "Add one paragraph for problem, method, and evidence.",
            "List two terms to verify in the paper.",
        ]
    if goal == "create weekly research rhythm":
        return [
            "Reserve one 90-minute reading block.",
            "Reserve one 45-minute synthesis block.",
            "Schedule one review block before the next advisor meeting.",
        ]
    return [
        f"Start with {first_title}.",
        "Create a timeline of the top three starter papers.",
        "Write one sentence on why each paper matters to your subfield.",
    ]
