"""Step 1: source candidate judges.

Live: LLM generates search queries, then a web_search-grounded extraction call
returns judges with source evidence. Cached: replay runs/<id>/judges.json, else
data/seeds/<id>_judges.json.
"""

import csv
import json
from pathlib import Path

from app import ROOT, llm
from app.models import Hackathon, Judge, JudgeList, QueryList


def source_judges(hackathon: Hackathon, run_dir: Path, n: int = 20) -> list[Judge]:
    out_json = run_dir / "judges.json"

    if not llm.is_live():
        if out_json.exists():
            raw = json.loads(out_json.read_text())
            print(f"[source_judges] cached replay from {out_json}")
        else:
            seed_path = ROOT / "data" / "seeds" / f"{hackathon.id}_judges.json"
            if not seed_path.exists():
                raise llm.CachedModeError(
                    f"MODE=cached and no artifact at {out_json} or seed at {seed_path}. "
                    "Run with MODE=live to source judges."
                )
            raw = json.loads(seed_path.read_text())
            print(f"[source_judges] cached seed from {seed_path}")
        judges = [Judge.model_validate(j) for j in raw]
    else:
        queries = llm.call(
            "sourcing_queries_v1",
            {
                "topic": hackathon.topic,
                "tracks": ", ".join(hackathon.tracks),
                "description": hackathon.description,
            },
            schema=QueryList,
        )
        print(f"[source_judges] generated {len(queries.queries)} search queries")
        extracted = llm.call(
            "sourcing_extract_v1",
            {
                "topic": hackathon.topic,
                "tracks": ", ".join(hackathon.tracks),
                "description": hackathon.description,
                "n": n,
                "queries": "\n".join(f"- {q}" for q in queries.queries),
            },
            schema=JudgeList,
            use_web_search=True,
        )
        judges = extracted.judges

    judges = _dedupe(judges)[:n]
    for i, judge in enumerate(judges, start=1):
        judge.rank = i

    out_json.write_text(json.dumps([j.model_dump() for j in judges], indent=2))
    _write_csv(judges, run_dir / "judges.csv")
    print(f"[source_judges] wrote {len(judges)} judges to {out_json}")
    return judges


def _dedupe(judges: list[Judge]) -> list[Judge]:
    seen: set[str] = set()
    unique: list[Judge] = []
    for judge in judges:
        key = " ".join(judge.name.lower().split())
        if key not in seen:
            seen.add(key)
            unique.append(judge)
    return unique


def _write_csv(judges: list[Judge], path: Path) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "rank",
                "name",
                "affiliation",
                "relevance_signal",
                "contact_type",
                "contact_value",
                "contact_verified",
                "source_urls",
                "evidence_snippet",
            ]
        )
        for j in judges:
            writer.writerow(
                [
                    j.rank,
                    j.name,
                    j.affiliation,
                    j.relevance_signal,
                    j.contact.type,
                    j.contact.value,
                    j.contact.verified,
                    "|".join(j.source_urls),
                    j.evidence_snippet,
                ]
            )
