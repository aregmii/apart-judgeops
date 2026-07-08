"""Step 3: accept project submissions.

Loads data/seeds/<id>_projects.json into runs/<id>/projects.json.
# TODO(prod): importer from Apart site / Notion / Airtable behind a
# SubmissionSource interface.
"""

import json
import random
from pathlib import Path

from app import ROOT
from app.models import Hackathon, Project


def accept_projects(hackathon: Hackathon, run_dir: Path) -> list[Project]:
    seed_path = ROOT / "data" / "seeds" / f"{hackathon.id}_projects.json"
    if not seed_path.exists():
        raise FileNotFoundError(f"no project seed at {seed_path}")
    projects = [Project.model_validate(p) for p in json.loads(seed_path.read_text())]
    out = run_dir / "projects.json"
    out.write_text(json.dumps([p.model_dump() for p in projects], indent=2))
    print(f"[accept_projects] wrote {len(projects)} projects to {out}")
    return projects


def sample_projects(projects: list[Project], n: int, seed: int) -> list[Project]:
    """Seeded RNG so the 'randomly chosen' grading set is reproducible."""
    rng = random.Random(seed)
    return rng.sample(projects, min(n, len(projects)))
