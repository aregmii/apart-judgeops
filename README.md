# apart-judgeops

Judge sourcing + LLM-judge grading pipeline for Apart Research hackathons. One workflow with four steps (source judges, draft outreach, accept projects, grade against the rubric), driven entirely by a hackathon config file: a new hackathon topic is a new `configs/<id>.json`, zero new code. All state between steps is committed JSON under `runs/<id>/`, so the outputs are auditable and reviewable in the repo itself.

```
create_hackathon_workflow(configs/<id>.json)
  ├─ 1. source_judges     LLM + Anthropic web_search → runs/<id>/judges.json (+ judges.csv)
  ├─ 2. contact_judges    LLM → runs/<id>/outreach/<judge>.md   (send() = TODO stub)
  ├─ 3. accept_projects   seeds → runs/<id>/projects.json       (TODO: real importer)
  └─ 4. grade_projects    LLM judge × rubric → runs/<id>/grades.json + review_queue.json
```

## Quickstart with zero keys

```bash
make setup   # uv sync
make test    # pytest, no network, no env vars
make demo    # full workflow for both configs in MODE=cached (replays seeds/artifacts)
```

## Live mode

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=sk-ant-...
make generate          # MODE=live: real web search sourcing + real LLM grading
```

CLI directly:

```bash
uv run judgeops run configs/digital_minds.json --steps source,contact
uv run judgeops run configs/ai_control.json --steps source,accept,grade --sample 4 --seed 42
uv run judgeops review-queue ai_control
uv run judgeops export ai_control --csv
```

## Design

JSON is the canonical format because judges and grades are nested (contacts with evidence, per-dimension rationales with quotes, raw samples); CSV is a lossy projection generated on demand (`judges.csv`, `export --csv`). `app/llm.py` is the only module that touches the Anthropic API; prompts are versioned files in `prompts/` with trivial `{placeholder}` templating, so tuning the judge means editing `prompts/judge_v1.md` and re-running step 4.

## Assumptions & judgment calls

- Seed judges/projects are clearly labeled placeholders, never fabricated real people. The contact policy is enforced by a Pydantic validator: a `public_email` without source URLs and an evidence snippet fails validation.
- `MODE=cached` grade samples are deterministic stubs stamped `model=cached-stub`, so the keyless demo exercises the full aggregation/routing path honestly.
- Median aggregation uses `median_high` to keep scores integral for even sample counts; `off_topic` aggregates by majority vote.
- Email sending is a `NotImplementedError` stub behind a future `EmailProvider` interface.

## Judge reliability

Implemented: k=3 independent samples with per-dimension median, disagreement flag when any dimension's range exceeds 1, evidence quotes required per rationale, team-name anonymization before judging, calibration anchors in the prompt (3 = solid weekend work, 5 = top ~5-10%), and review routing (`confidence < 0.7`, any score of 5, off-topic, or disagreement → human review queue, sorted by confidence ascending). Noted as TODOs in `app/steps/grade_projects.py`: pairwise tournament for top-k, position-bias swap tests, calibration against past winners/human scores, cross-model ensemble.

## Infrastructure

"Not one person's laptop" here means: containerized (Dockerfile), CI on every push (ruff + pytest), env-only configuration (`.env.example`), and committed auditable run artifacts. Production path: ECS/Cloud Run for the workflow, Postgres for judges/grades, S3 for submission snapshots, a queue for grading fan-out, and a small review UI over `review_queue.json`.

## Cost note

Live sourcing uses Anthropic's server-side [web search tool](https://docs.claude.com/en/docs/agents-and-tools/tool-use/web-search-tool) at $10 per 1,000 searches plus tokens; each sourcing run caps at 8 searches.
