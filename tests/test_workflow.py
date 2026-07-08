"""Seeded-sampling determinism + end-to-end workflow in MODE=cached."""

import json

from app import ROOT
from app.models import DIMENSIONS, Project
from app.steps.accept_projects import sample_projects
from app.workflow import create_hackathon_workflow


def test_seeded_sampling_is_deterministic():
    projects = [Project(id=f"p{i}", event_id="x", title=f"t{i}") for i in range(10)]
    first = [p.id for p in sample_projects(projects, 4, seed=42)]
    second = [p.id for p in sample_projects(projects, 4, seed=42)]
    assert first == second
    assert len(first) == 4


def test_sampling_caps_at_population():
    projects = [Project(id="p0", event_id="x", title="t")]
    assert len(sample_projects(projects, 5, seed=1)) == 1


def test_end_to_end_cached_workflow(tmp_path, monkeypatch):
    monkeypatch.delenv("MODE", raising=False)  # default is cached: no network
    create_hackathon_workflow(
        ROOT / "configs" / "digital_minds.json",
        steps=["source", "contact", "accept", "grade"],
        n=20,
        top_k=2,
        sample=2,
        seed=42,
        k=3,
        runs_root=tmp_path,
    )
    run_dir = tmp_path / "digital_minds"
    assert (run_dir / "judges.json").exists()
    assert (run_dir / "judges.csv").exists()
    assert list((run_dir / "outreach").glob("*.md"))
    assert (run_dir / "projects.json").exists()

    grades = json.loads((run_dir / "grades.json").read_text())
    assert len(grades) == 2
    for grade in grades:
        assert set(grade["scores"]) == set(DIMENSIONS)
        assert grade["model"] == "cached-stub"
        assert grade["prompt_version"] == "judge_v1"
        assert len(grade["samples_raw"]) == 3

    queue = json.loads((run_dir / "review_queue.json").read_text())
    confidences = [g["confidence"] for g in queue]
    assert confidences == sorted(confidences)


def test_outreach_drafts_have_no_bracket_placeholders(tmp_path, monkeypatch):
    monkeypatch.delenv("MODE", raising=False)
    create_hackathon_workflow(
        ROOT / "configs" / "ai_control.json",
        steps=["source", "contact"],
        top_k=3,
        runs_root=tmp_path,
    )
    drafts = list((tmp_path / "ai_control" / "outreach").glob("*.md"))
    assert drafts
    for draft in drafts:
        text = draft.read_text()
        assert text.startswith("Subject:")
        assert "[" not in text.replace("[team redacted]", "")
