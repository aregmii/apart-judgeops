"""The four core models. JSON is canonical; CSV is a flat projection."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

DIMENSIONS = ("impact_innovation", "execution_quality", "presentation_clarity")

ContactType = Literal["public_email", "webform", "linkedin", "profile_page", "unknown"]


class Contact(BaseModel):
    type: ContactType = "unknown"
    value: str = ""
    verified: bool = False


class Hackathon(BaseModel):
    id: str
    topic: str
    description: str = ""
    tracks: list[str] = Field(default_factory=list)
    dates: str = ""
    judge_count: int = 20
    rubric_path: str = "prompts/rubric.md"


class Judge(BaseModel):
    name: str
    affiliation: str = ""
    relevance_signal: str = ""
    contact: Contact = Field(default_factory=Contact)
    source_urls: list[str] = Field(default_factory=list)
    evidence_snippet: str = ""
    rank: int = 0

    @model_validator(mode="after")
    def enforce_contact_policy(self) -> "Judge":
        # HARD CONTACT POLICY: an email may only appear if it was found in a fetched
        # source. Fabricated contact info is an automatic-reject failure.
        if self.contact.type == "public_email":
            if not self.source_urls or not self.evidence_snippet.strip():
                raise ValueError(
                    "public_email requires non-empty source_urls and evidence_snippet "
                    "proving the address appeared in a fetched source"
                )
        return self


class Project(BaseModel):
    id: str
    event_id: str
    title: str
    team: str = ""
    track: str = ""
    content: str = ""
    source_url: str = ""


class Rationale(BaseModel):
    text: str
    evidence_quotes: list[str] = Field(default_factory=list)


class Grade(BaseModel):
    project_id: str
    scores: dict[str, int]
    rationale: dict[str, Rationale] = Field(default_factory=dict)
    off_topic: bool = False
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    agreement_flag: bool = False
    human_review_required: bool = False
    model: str = ""
    prompt_version: str = ""
    samples_raw: list[dict] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)


class JudgeList(BaseModel):
    """Wrapper for schema-validated LLM extraction of judges."""

    judges: list[Judge]


class QueryList(BaseModel):
    queries: list[str]


class JudgeSample(BaseModel):
    """One independent LLM-judge sample; k of these aggregate into a Grade."""

    scores: dict[str, int]
    rationale: dict[str, Rationale] = Field(default_factory=dict)
    off_topic: bool = False
    confidence: float = Field(0.5, ge=0.0, le=1.0)
