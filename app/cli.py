"""Typer entrypoint: judgeops run / review-queue / export."""

import csv
import json
from pathlib import Path

import typer

from app import ROOT
from app.workflow import STEP_ORDER, create_hackathon_workflow

app = typer.Typer(help="Judge sourcing + LLM grading pipeline for Apart hackathons")


@app.command()
def run(
    config: str,
    steps: str = typer.Option(",".join(STEP_ORDER), help="comma list: source,contact,accept,grade"),
    n: int = 20,
    top_k: int = 3,
    sample: int = 4,
    seed: int = 42,
    k: int = 3,
):
    step_list = [s.strip() for s in steps.split(",") if s.strip()]
    create_hackathon_workflow(
        config, steps=step_list, n=n, top_k=top_k, sample=sample, seed=seed, k=k
    )


@app.command("review-queue")
def review_queue(hackathon_id: str):
    path = ROOT / "runs" / hackathon_id / "review_queue.json"
    if not path.exists():
        typer.echo(f"no review queue at {path}; run the grade step first")
        raise typer.Exit(1)
    queue = json.loads(path.read_text())
    typer.echo(f"{len(queue)} grade(s) need human review (lowest confidence first):")
    for grade in queue:
        typer.echo(
            f"  {grade['project_id']}  confidence={grade['confidence']}  "
            f"scores={grade['scores']}  off_topic={grade['off_topic']}  "
            f"disagreement={grade['agreement_flag']}"
        )


@app.command()
def export(hackathon_id: str, csv_out: bool = typer.Option(True, "--csv/--no-csv")):
    """Flatten grades.json to grades.csv (judges.csv is written by the source step)."""
    run_dir = ROOT / "runs" / hackathon_id
    grades_path = run_dir / "grades.json"
    if not grades_path.exists():
        typer.echo(f"no grades at {grades_path}")
        raise typer.Exit(1)
    grades = json.loads(grades_path.read_text())
    out = run_dir / "grades.csv"
    _write_grades_csv(grades, out)
    typer.echo(f"wrote {out}")


def _write_grades_csv(grades: list[dict], path: Path) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "project_id",
                "impact_innovation",
                "execution_quality",
                "presentation_clarity",
                "off_topic",
                "confidence",
                "agreement_flag",
                "human_review_required",
                "model",
                "prompt_version",
            ]
        )
        for g in grades:
            writer.writerow(
                [
                    g["project_id"],
                    g["scores"]["impact_innovation"],
                    g["scores"]["execution_quality"],
                    g["scores"]["presentation_clarity"],
                    g["off_topic"],
                    g["confidence"],
                    g["agreement_flag"],
                    g["human_review_required"],
                    g["model"],
                    g["prompt_version"],
                ]
            )


if __name__ == "__main__":
    app()
