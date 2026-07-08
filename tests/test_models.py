"""Schema round-trips for all 4 models + the hard contact policy."""

import pytest
from pydantic import ValidationError

from app.models import Contact, Grade, Hackathon, Judge, Project, Rationale


def _roundtrip(model):
    return type(model).model_validate_json(model.model_dump_json())


def test_hackathon_roundtrip():
    h = Hackathon(id="x", topic="T", tracks=["a", "b"], dates="d", judge_count=5)
    assert _roundtrip(h) == h


def test_judge_roundtrip():
    j = Judge(
        name="A B",
        affiliation="Lab",
        relevance_signal="paper",
        contact=Contact(type="linkedin", value="https://linkedin.com/in/ab"),
        source_urls=["https://lab.example/ab"],
        evidence_snippet="quote",
        rank=1,
    )
    assert _roundtrip(j) == j


def test_project_roundtrip():
    p = Project(id="p1", event_id="x", title="T", team="team", content="# md")
    assert _roundtrip(p) == p


def test_grade_roundtrip():
    g = Grade(
        project_id="p1",
        scores={"impact_innovation": 3, "execution_quality": 4, "presentation_clarity": 3},
        rationale={"impact_innovation": Rationale(text="ok", evidence_quotes=["q"])},
        confidence=0.8,
        model="m",
        prompt_version="judge_v1",
    )
    assert _roundtrip(g) == g


def test_public_email_without_evidence_rejected():
    with pytest.raises(ValidationError):
        Judge(name="X", contact=Contact(type="public_email", value="x@y.org"))


def test_public_email_without_snippet_rejected():
    with pytest.raises(ValidationError):
        Judge(
            name="X",
            contact=Contact(type="public_email", value="x@y.org"),
            source_urls=["https://y.org/x"],
            evidence_snippet="   ",
        )


def test_public_email_with_evidence_accepted():
    j = Judge(
        name="X",
        contact=Contact(type="public_email", value="x@y.org"),
        source_urls=["https://y.org/x"],
        evidence_snippet="Contact: x@y.org",
    )
    assert j.contact.type == "public_email"
