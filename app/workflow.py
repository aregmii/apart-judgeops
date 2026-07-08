"""One workflow, four steps. Everything is driven by a hackathon config file:
a new hackathon = a new config, zero new code."""

import json
from pathlib import Path

from app import ROOT
from app.models import Hackathon
from app.steps.accept_projects import accept_projects
from app.steps.contact_judges import contact_judges
from app.steps.grade_projects import grade_projects
from app.steps.source_judges import source_judges

STEP_ORDER = ["source", "contact", "accept", "grade"]


def create_hackathon_workflow(
    config_path: str | Path,
    steps: list[str] | None = None,
    n: int = 20,
    top_k: int = 3,
    sample: int = 4,
    seed: int = 42,
    k: int = 3,
    runs_root: Path | None = None,
) -> dict:
    hackathon = Hackathon.model_validate(json.loads(Path(config_path).read_text()))
    run_dir = (runs_root or ROOT / "runs") / hackathon.id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: dict = {}
    for step in steps or STEP_ORDER:
        print(f"[workflow] hackathon={hackathon.id} step={step}")
        if step == "source":
            results["source"] = source_judges(hackathon, run_dir, n=n)
        elif step == "contact":
            results["contact"] = contact_judges(hackathon, run_dir, top_k=top_k)
        elif step == "accept":
            results["accept"] = accept_projects(hackathon, run_dir)
        elif step == "grade":
            results["grade"] = grade_projects(
                hackathon, run_dir, sample=sample, seed=seed, k=k
            )
        else:
            raise ValueError(f"unknown step '{step}' (expected one of {STEP_ORDER})")
    return results
