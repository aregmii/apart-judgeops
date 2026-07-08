"""Step 2: draft outreach for the top-k sourced judges.

Live: one outreach_v1 call per judge. Cached: deterministic local draft from the
same inputs so the demo stays keyless.
# ASSUMPTION: cached drafts are rendered in Python from judge + hackathon fields
# (no LLM) and are regenerated send-ready under MODE=live.
"""

import json
import os
from pathlib import Path

from app import llm
from app.models import Hackathon, Judge


def contact_judges(hackathon: Hackathon, run_dir: Path, top_k: int = 3) -> list[Path]:
    judges_path = run_dir / "judges.json"
    if not judges_path.exists():
        raise FileNotFoundError(f"{judges_path} missing; run the source step first")
    judges = [Judge.model_validate(j) for j in json.loads(judges_path.read_text())]

    out_dir = run_dir / "outreach"
    out_dir.mkdir(exist_ok=True)
    sender = os.environ.get("SENDER_NAME", "Amish Regmi")

    written: list[Path] = []
    for judge in judges[:top_k]:
        ctx = {
            "name": judge.name,
            "affiliation": judge.affiliation,
            "relevance_signal": judge.relevance_signal,
            "topic": hackathon.topic,
            "dates": hackathon.dates,
            "tracks": ", ".join(hackathon.tracks),
            "sender_name": sender,
        }
        if llm.is_live():
            draft = llm.call("outreach_v1", ctx, temperature=0.7)
        else:
            draft = _cached_draft(ctx)
        path = out_dir / f"{_slug(judge.name)}.md"
        path.write_text(str(draft))
        written.append(path)
        print(f"[contact_judges] wrote {path}")
    return written


def _cached_draft(ctx: dict) -> str:
    return (
        f"Subject: Invitation to judge Apart Research's {ctx['topic']} hackathon\n\n"
        f"Hi {ctx['name']},\n\n"
        f"I'm reaching out because of your work on {ctx['relevance_signal']} "
        f"at {ctx['affiliation']}. Apart Research is running an AI safety hackathon "
        f"on {ctx['topic']} ({ctx['dates']}), with tracks on {ctx['tracks']}.\n\n"
        f"We'd love to have you as a judge. The ask is concrete: review roughly 10 "
        f"projects asynchronously over 4 days during the week of the event, scoring "
        f"each against a short rubric. Most judges spend 2-3 hours total.\n\n"
        f"If you're interested, reply and we'll send the judging portal details.\n\n"
        f"Best,\n{ctx['sender_name']}\nApart Research\n"
    )


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


def send(draft_path: Path) -> None:
    # TODO(prod): SES/Gmail behind an EmailProvider interface
    raise NotImplementedError(
        "Email sending is out of scope; wire an EmailProvider (SES/Gmail) in prod."
    )
