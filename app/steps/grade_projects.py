"""Step 4: LLM judge x rubric -> grades.json + review_queue.json.

For each sampled project: anonymize team names (bias mitigation), take k
independent judge_v1 samples at temperature 0.7, aggregate per-dimension
medians, flag disagreement, and route low-confidence / extreme / off-topic
grades to human review.

# TODO(new-hackathon-topics): to run this for a different hackathon: (1) new configs/<id>.json
# with topic+tracks, (2) rubric stays shared or point rubric_path at a topic-specific rubric,
# (3) supply topic context for the novelty/impact dimension (recent related work), (4) update
# the sourcing trust-list for the new domain. No code changes.
# TODO(reliability): pairwise tournament for top-k, position-bias swap tests, calibration
# against past winners/human scores, cross-model ensemble.
"""

import hashlib
import json
import os
import statistics
from pathlib import Path

from app import ROOT, llm
from app.models import DIMENSIONS, Grade, Hackathon, JudgeSample, Project, Rationale
from app.steps.accept_projects import accept_projects, sample_projects

PROMPT_VERSION = "judge_v1"


def grade_projects(
    hackathon: Hackathon, run_dir: Path, sample: int = 4, seed: int = 42, k: int = 3
) -> list[Grade]:
    projects_path = run_dir / "projects.json"
    if projects_path.exists():
        projects = [
            Project.model_validate(p) for p in json.loads(projects_path.read_text())
        ]
    else:
        projects = accept_projects(hackathon, run_dir)

    rubric = (ROOT / hackathon.rubric_path).read_text()
    chosen = sample_projects(projects, sample, seed)
    grades: list[Grade] = []
    for project in chosen:
        grades.append(_grade_one(hackathon, project, rubric, k))

    (run_dir / "grades.json").write_text(
        json.dumps([g.model_dump() for g in grades], indent=2)
    )
    queue = sorted(
        (g for g in grades if g.human_review_required), key=lambda g: g.confidence
    )
    (run_dir / "review_queue.json").write_text(
        json.dumps([g.model_dump() for g in queue], indent=2)
    )
    print(
        f"[grade_projects] graded {len(grades)} projects; "
        f"{len(queue)} routed to human review"
    )
    return grades


def _grade_one(
    hackathon: Hackathon, project: Project, rubric: str, k: int
) -> Grade:
    submission = anonymize(project)
    samples: list[JudgeSample] = []
    for i in range(k):
        if llm.is_live():
            sample = llm.call(
                "judge_v1",
                {
                    "topic": hackathon.topic,
                    "tracks": ", ".join(hackathon.tracks),
                    "rubric": rubric,
                    "submission": submission,
                },
                schema=JudgeSample,
                temperature=0.7,
            )
        else:
            sample = _stub_sample(project, i)
        samples.append(sample)

    scores, confidence, off_topic, agreement_flag = aggregate(samples)
    representative = samples[0]
    grade = Grade(
        project_id=project.id,
        scores=scores,
        rationale=representative.rationale,
        off_topic=off_topic,
        confidence=confidence,
        agreement_flag=agreement_flag,
        human_review_required=route(confidence, scores, off_topic, agreement_flag),
        model=os.environ.get("MODEL", "claude-sonnet-4-6")
        if llm.is_live()
        else "cached-stub",
        prompt_version=PROMPT_VERSION,
        samples_raw=[s.model_dump() for s in samples],
    )
    print(
        f"[grade_projects] project={project.id} scores={scores} "
        f"confidence={confidence} review={grade.human_review_required}"
    )
    return grade


def anonymize(project: Project) -> str:
    """Strip team/author names before judging (bias mitigation).
    # TODO(prod): NER-based scrubbing; string replace only covers exact matches."""
    content = project.content
    if project.team:
        content = content.replace(project.team, "[team redacted]")
    return f"# {project.title}\n\n{content}"


def aggregate(samples: list[JudgeSample]) -> tuple[dict[str, int], float, bool, bool]:
    """Per-dimension median; agreement_flag when any dimension's range > 1;
    confidence is the mean of judge-reported confidences."""
    scores: dict[str, int] = {}
    agreement_flag = False
    for dim in DIMENSIONS:
        vals = [s.scores[dim] for s in samples]
        # ASSUMPTION: median_high keeps scores integral for even k.
        scores[dim] = int(statistics.median_high(vals))
        if max(vals) - min(vals) > 1:
            agreement_flag = True
    confidence = round(sum(s.confidence for s in samples) / len(samples), 3)
    # ASSUMPTION: off_topic aggregates by majority vote across samples.
    off_topic = sum(1 for s in samples if s.off_topic) > len(samples) / 2
    return scores, confidence, off_topic, agreement_flag


def route(
    confidence: float, scores: dict[str, int], off_topic: bool, agreement_flag: bool
) -> bool:
    """5s are rare by the rubric's own calibration, so they get human-verified."""
    return (
        confidence < 0.7
        or any(s == 5 for s in scores.values())
        or off_topic
        or agreement_flag
    )


def _stub_sample(project: Project, i: int) -> JudgeSample:
    """Deterministic keyless stand-in so MODE=cached demos end-to-end.
    # ASSUMPTION: cached grades are clearly stamped model='cached-stub'."""
    digest = hashlib.sha256(f"{project.id}:{i}".encode()).digest()
    scores = {dim: 2 + digest[j] % 3 for j, dim in enumerate(DIMENSIONS)}
    return JudgeSample(
        scores=scores,
        rationale={
            dim: Rationale(
                text="Cached-mode stub rationale; run MODE=live for a real LLM grade.",
                evidence_quotes=[],
            )
            for dim in DIMENSIONS
        },
        off_topic=False,
        confidence=0.6 + (digest[5] % 26) / 100,
    )
