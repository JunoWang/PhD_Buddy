"""Onboarding profile domain logic (moved from the original ``phd_buddy.onboarding``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..storage.vault import read_json, write_dual_format


GROUNDING_RULES = {
    "grounded": "Stated in the paper; assert plainly and cite section, figure, table, or short phrase.",
    "inferred": "Assistant reasoning about the paper; flag as 'my read' and invite verification.",
    "external": "General knowledge outside the paper; flag as lower-confidence and ask the student to verify.",
}

DEEP_DIVE_LENSES = [
    "Where it sits",
    "The problem",
    "Baselines",
    "Why baselines fall short",
    "The method, with a concrete example",
    "Pros and cons",
    "Experiments vs. claims",
    "Generalizability",
]

PROFILE_STEM = "onboarding_profile"


@dataclass(frozen=True)
class StudentContext:
    """Personal and PhD-stage context used by the schedule and support buddies."""

    name: str = ""
    preferred_name: str = ""
    sex: str = ""
    age: str = ""
    school: str = ""
    department: str = ""
    degree_stage: str = ""
    advisor: str = ""
    milestones: list[str] = field(default_factory=list)
    current_goals: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    notification_preferences: list[str] = field(default_factory=list)
    weekly_availability: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "preferred_name": self.preferred_name,
            "sex": self.sex,
            "age": self.age,
            "school": self.school,
            "department": self.department,
            "degree_stage": self.degree_stage,
            "advisor": self.advisor,
            "milestones": self.milestones,
            "current_goals": self.current_goals,
            "pain_points": self.pain_points,
            "notification_preferences": self.notification_preferences,
            "weekly_availability": self.weekly_availability,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> StudentContext:
        raw = raw or {}
        return cls(
            name=str(raw.get("name", "")).strip(),
            preferred_name=str(raw.get("preferred_name", "")).strip(),
            sex=str(raw.get("sex", "")).strip(),
            age=str(raw.get("age", "")).strip(),
            school=str(raw.get("school", raw.get("university", ""))).strip(),
            department=str(raw.get("department", raw.get("program", ""))).strip(),
            degree_stage=str(raw.get("degree_stage", "")).strip(),
            advisor=str(raw.get("advisor", "")).strip(),
            milestones=_clean_list(raw.get("milestones", [])),
            current_goals=_clean_list(raw.get("current_goals", [])),
            pain_points=_clean_list(raw.get("pain_points", [])),
            notification_preferences=_clean_list(raw.get("notification_preferences", [])),
            weekly_availability=str(raw.get("weekly_availability", "")).strip(),
        )


@dataclass(frozen=True)
class FundamentalPaper:
    """A starter paper recommendation with a local summary note."""

    title: str
    authors: str
    year: str
    why_it_matters: str
    summary_markdown: str
    summary_path: str = ""

    def with_summary_path(self, summary_path: str) -> FundamentalPaper:
        return FundamentalPaper(
            title=self.title,
            authors=self.authors,
            year=self.year,
            why_it_matters=self.why_it_matters,
            summary_markdown=self.summary_markdown,
            summary_path=summary_path,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "why_it_matters": self.why_it_matters,
            "summary_path": self.summary_path,
            "summary_markdown": self.summary_markdown,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> FundamentalPaper:
        return cls(
            title=str(raw.get("title", "")).strip(),
            authors=str(raw.get("authors", "")).strip(),
            year=str(raw.get("year", "")).strip(),
            why_it_matters=str(raw.get("why_it_matters", "")).strip(),
            summary_path=str(raw.get("summary_path", "")).strip(),
            summary_markdown=str(raw.get("summary_markdown", "")).strip(),
        )


@dataclass(frozen=True)
class ResearchProfile:
    """The student-facing profile fields collected during onboarding."""

    major_field: str
    subdomains: list[str]
    venues: list[str]
    student: StudentContext = field(default_factory=StudentContext)
    google_scholar_url: str = ""
    known_seed_papers: list[str] = field(default_factory=list)
    recent_keywords: list[str] = field(default_factory=list)

    @property
    def research_identity(self) -> str:
        subdomains = ", ".join(self.subdomains) if self.subdomains else "unspecified subdomain"
        return f"{self.major_field} -> {subdomains}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "major_field": self.major_field,
            "subdomains": self.subdomains,
            "venues": self.venues,
            "student": self.student.to_dict(),
            "google_scholar_url": self.google_scholar_url,
            "known_seed_papers": self.known_seed_papers,
            "recent_keywords": self.recent_keywords,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ResearchProfile:
        return cls(
            major_field=str(raw.get("major_field", raw.get("field", ""))).strip(),
            subdomains=_clean_list(raw.get("subdomains", [raw.get("sub_area"), raw.get("topic")])),
            venues=_clean_list(raw.get("venues", [raw.get("venue")])),
            student=StudentContext.from_dict(raw.get("student", raw)),
            google_scholar_url=str(raw.get("google_scholar_url", "")).strip(),
            known_seed_papers=_clean_list(raw.get("known_seed_papers", [])),
            recent_keywords=_clean_list(raw.get("recent_keywords", [])),
        )


@dataclass(frozen=True)
class OnboardingPlan:
    """A generated first-pass plan from the onboarding profile."""

    profile_id: str
    created_at: str
    profile: ResearchProfile
    fundamental_papers: list[FundamentalPaper]
    workflow: dict[str, Any]
    deep_dive_harness: dict[str, Any]

    @classmethod
    def from_profile(cls, profile: ResearchProfile) -> OnboardingPlan:
        papers = recommend_fundamental_papers(profile)
        return cls(
            profile_id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            profile=profile,
            fundamental_papers=papers,
            workflow=_workflow_for(profile),
            deep_dive_harness={
                "opening_lenses": DEEP_DIVE_LENSES,
                "grounding_rules": GROUNDING_RULES,
                "student_role": "The student verifies claims against the paper instead of passively accepting a summary.",
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "profile": self.profile.to_dict(),
            "fundamental_papers": [paper.to_dict() for paper in self.fundamental_papers],
            "workflow": self.workflow,
            "deep_dive_harness": self.deep_dive_harness,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> OnboardingPlan:
        return cls(
            profile_id=str(raw["profile_id"]),
            created_at=str(raw["created_at"]),
            profile=ResearchProfile.from_dict(raw["profile"]),
            fundamental_papers=[FundamentalPaper.from_dict(item) for item in raw.get("fundamental_papers", [])],
            workflow=dict(raw["workflow"]),
            deep_dive_harness=dict(raw["deep_dive_harness"]),
        )


def save_plan(plan: OnboardingPlan, output_dir: Path) -> tuple[Path, Path]:
    """Write the plan to the vault as canonical JSON plus vault-friendly markdown."""

    plan = _write_fundamental_summaries(plan, output_dir)
    return write_dual_format(output_dir, PROFILE_STEM, plan.to_dict(), render_markdown(plan))


def load_plan(path: Path) -> OnboardingPlan:
    return OnboardingPlan.from_dict(read_json(path))


def render_markdown(plan: OnboardingPlan) -> str:
    profile = plan.profile
    student = profile.student
    subdomains = _markdown_list(profile.subdomains)
    venues = _markdown_list(profile.venues)
    scholar = profile.google_scholar_url or "Not provided"
    seeds = _markdown_list(profile.known_seed_papers)
    keywords = _markdown_list(profile.recent_keywords)
    papers = _paper_markdown_list(plan.fundamental_papers)

    return "\n".join(
        [
            "# PhD Buddy Onboarding Profile",
            "",
            f"Profile ID: `{plan.profile_id}`",
            f"Created: `{plan.created_at}`",
            "",
            "## Research Identity",
            "",
            f"- Name: {student.preferred_name or student.name or 'Not provided'}",
            f"- School: {student.school or 'Not provided'}",
            f"- Department/program: {student.department or 'Not provided'}",
            f"- Degree stage: {student.degree_stage or 'Not provided'}",
            f"- Major field: {profile.major_field}",
            f"- Google Scholar profile: {scholar}",
            "",
            "Subdomains:",
            subdomains,
            "",
            "Interested venues/conferences:",
            venues,
            "",
            "## Seed Inputs",
            "",
            "Known seed papers:",
            seeds,
            "",
            "Recent-search keywords:",
            keywords,
            "",
            "## Companion Context",
            "",
            f"- Sex: {student.sex or 'Not provided'}",
            f"- Age: {student.age or 'Not provided'}",
            f"- Advisor/committee: {student.advisor or 'Not provided'}",
            f"- Weekly availability: {student.weekly_availability or 'Not provided'}",
            "",
            "Current goals:",
            _markdown_list(student.current_goals),
            "",
            "Pain points:",
            _markdown_list(student.pain_points),
            "",
            "Notification preferences:",
            _markdown_list(student.notification_preferences),
            "",
            "Milestones:",
            _markdown_list(student.milestones),
            "",
            "## Fundamental Paper Starter Set",
            "",
            papers,
            "",
        ]
    )


def recommend_fundamental_papers(profile: ResearchProfile) -> list[FundamentalPaper]:
    """Return a conservative local starter set until live literature discovery is wired in."""

    terms = " ".join([profile.major_field, *profile.subdomains, *profile.recent_keywords]).lower()
    candidates: list[FundamentalPaper] = []
    if any(term in terms for term in ["context", "in-context", "icl", "language model", "llm", "prompt"]):
        candidates.extend(_IN_CONTEXT_LEARNING_PAPERS)
    if any(term in terms for term in ["retrieval", "rag", "information retrieval", "search"]):
        candidates.extend(_RETRIEVAL_PAPERS)
    if any(term in terms for term in ["nlp", "natural language", "language"]):
        candidates.extend(_NLP_PAPERS)

    seen: set[str] = set()
    papers: list[FundamentalPaper] = []
    for paper in candidates:
        key = paper.title.lower()
        if key in seen:
            continue
        seen.add(key)
        papers.append(paper)
        if len(papers) == 6:
            break
    return papers


def _workflow_for(profile: ResearchProfile) -> dict[str, Any]:
    return {
        "onboarding_recommendations": {
            "source": "onboarding_profile",
            "instruction": (
                "Use the major field and subdomains to seed a starter set of fundamental papers. "
                "Each paper gets a local summarize.md note that can be replaced by grounded PDF summaries later."
            ),
            "inputs": [profile.major_field, *profile.subdomains],
        },
        "foundational_lineage": {
            "source": "onboarding_profile",
            "instruction": (
                "Start from known seed papers and walk the citation graph to identify "
                f"origins and landmarks for {profile.research_identity}."
            ),
            "inputs": profile.known_seed_papers,
        },
        "recent_search": {
            "source": "onboarding_profile",
            "instruction": (
                "Expand recent-search queries from the major field, subdomains, and venues; "
                "retrieve candidates through literature APIs; re-rank by relevance."
            ),
            "inputs": [profile.major_field, *profile.subdomains, *profile.venues, *profile.recent_keywords],
        },
        "student_publication_search": {
            "source": "onboarding_profile",
            "instruction": "Use the Google Scholar profile link, when provided, to inspect the student's publication history.",
            "input": profile.google_scholar_url,
        },
        "citation_verification": {
            "source": "system",
            "instruction": "Confirm title, authors, and year against real citations; flag unverified items.",
        },
        "acquisition": {
            "source": "system",
            "instruction": "Acquire open-access PDFs when available, convert to structure-aware markdown, and store PDF, markdown, and metadata together.",
        },
        "summary_track": {
            "source": "system",
            "instruction": "Create cheap one-pass summaries for broad scanning before deeper reading.",
            "depth": "summary",
        },
        "deep_dive_track": {
            "source": "system",
            "instruction": "Use the 8-point opening, constrained conversation, and three-bucket grounding for selected papers.",
            "depth": "deep_dive",
        },
        "dual_format_cache": {
            "source": "system",
            "instruction": "Persist one canonical JSON object plus student-facing prose and panel fields for the vault.",
        },
    }


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = list(value)
    return [str(item).strip() for item in items if str(item).strip()]


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- None provided yet"
    return "\n".join(f"- {item}" for item in items)


def _paper_markdown_list(papers: list[FundamentalPaper]) -> str:
    if not papers:
        return "- No starter papers yet"
    lines: list[str] = []
    for paper in papers:
        summary = f" Summary: `{paper.summary_path}`" if paper.summary_path else ""
        lines.append(f"- {paper.title} ({paper.year}) by {paper.authors}.{summary}")
        lines.append(f"  Why it matters: {paper.why_it_matters}")
    return "\n".join(lines)


def _write_fundamental_summaries(plan: OnboardingPlan, output_dir: Path) -> OnboardingPlan:
    papers_dir = output_dir / "fundamental_papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    papers: list[FundamentalPaper] = []
    for paper in plan.fundamental_papers:
        paper_dir = papers_dir / _slugify(paper.title)
        paper_dir.mkdir(parents=True, exist_ok=True)
        summary_path = paper_dir / "summarize.md"
        summary_path.write_text(paper.summary_markdown, encoding="utf-8")
        papers.append(paper.with_summary_path(str(summary_path)))
    return OnboardingPlan(
        profile_id=plan.profile_id,
        created_at=plan.created_at,
        profile=plan.profile,
        fundamental_papers=papers,
        workflow=plan.workflow,
        deep_dive_harness=plan.deep_dive_harness,
    )


def _slugify(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "-" for char in value]
    slug = "-".join(part for part in "".join(chars).split("-") if part)
    return slug[:80] or "paper"


def _paper(title: str, authors: str, year: str, why: str, bullets: list[str]) -> FundamentalPaper:
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            f"Authors: {authors}",
            f"Year: {year}",
            "",
            "## Why This Paper Matters",
            "",
            why,
            "",
            "## Important Content",
            "",
            *[f"- {bullet}" for bullet in bullets],
            "",
            "## Reading Buddy Prompt",
            "",
            "Use this starter summary as orientation only. Replace or refine it after reading the PDF with grounded citations.",
            "",
        ]
    )
    return FundamentalPaper(title, authors, year, why, markdown)


_IN_CONTEXT_LEARNING_PAPERS = [
    _paper(
        "Language Models are Few-Shot Learners",
        "Brown et al.",
        "2020",
        "Popularized in-context learning as a capability of large language models prompted with examples.",
        [
            "The model performs tasks from natural-language instructions and examples without parameter updates.",
            "Performance improves with scale, but reliability varies strongly by task and prompt.",
            "This paper is a foundation for prompt design, evaluation, and emergent-capability debates.",
        ],
    ),
    _paper(
        "Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?",
        "Min et al.",
        "2022",
        "Showed that labels, input distribution, format, and task framing each affect in-context learning.",
        [
            "Demonstration format can matter even when label correctness is weakened.",
            "The paper pushes readers to separate task recognition from true example-based learning.",
            "It is a good entry point for studying what prompts actually teach the model.",
        ],
    ),
    _paper(
        "In-Context Learning and Induction Heads",
        "Olsson et al.",
        "2022",
        "Connected a mechanistic circuit, induction heads, to pattern copying and in-context behavior.",
        [
            "Induction heads are attention heads that continue token patterns seen earlier in context.",
            "The work links behavioral in-context learning to internal transformer mechanisms.",
            "It is helpful if the subfield includes interpretability or mechanistic explanations.",
        ],
    ),
]

_RETRIEVAL_PAPERS = [
    _paper(
        "Dense Passage Retrieval for Open-Domain Question Answering",
        "Karpukhin et al.",
        "2020",
        "Established dense dual-encoder retrieval as a strong neural baseline for open-domain QA.",
        [
            "Queries and passages are embedded separately, then compared by vector similarity.",
            "The method made retrieval more semantic than sparse lexical matching alone.",
            "It is core background for retrieval-augmented generation systems.",
        ],
    ),
]

_NLP_PAPERS = [
    _paper(
        "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "Devlin et al.",
        "2019",
        "Made masked-language-model pretraining a central baseline for language understanding tasks.",
        [
            "Bidirectional pretraining improved sentence and token-level NLP benchmarks.",
            "Fine-tuning one pretrained model became a default workflow for many NLP tasks.",
            "The paper is key context for the pretraining-to-adaptation pattern.",
        ],
    ),
]
