# apart-judgeops

A Python prototype for sourcing judges, drafting outreach, and grading projects for Apart Research hackathons. It brings candidate research and submission review into one configurable workflow, with files that an organizer can inspect before taking action.

## Overview

The repository includes example configurations for Digital Minds and AI Control, synthetic seed data, and a demonstration that runs without API credentials. An optional live mode uses Anthropic for judge research, outreach drafts, and project grading.

**Status:** prototype. Outreach is saved as drafts; email delivery is not implemented. Project intake reads local seed files in both modes. Included grades are labeled `cached-stub` and demonstrate the workflow, not the quality of an AI judge. The repository does not establish performance against human reviewers or provide a deployed service.

## Workflow

| Step | Current behavior | Output under `runs/<id>/` |
| --- | --- | --- |
| `source` | Reuse saved judges or seeds in cached mode; research candidates with Anthropic web search in live mode. Deduplicate names and assign ranks in returned order. | `judges.json`, `judges.csv` |
| `contact` | Draft outreach for the first candidates in the saved list. No messages are sent. | `outreach/*.md` |
| `accept` | Load projects from `data/seeds/<id>_projects.json`. | `projects.json` |
| `grade` | Sample projects, generate repeated grades, aggregate scores, and flag cases for human review. Cached mode generates deterministic stubs. | `grades.json`, `review_queue.json` |

JSON retains nested evidence, rationales, and individual grading samples. CSV exports provide a flatter view for inspection. Commands write to the same event directory on each run and can replace existing artifacts; they do not create Git commits or a separate run history.

## Getting started

Requirements: Python 3.12 or later, [uv](https://docs.astral.sh/uv/), and `make` for the convenience commands below. Run commands from the repository root.

```bash
git clone https://github.com/aregmii/apart-judgeops.git
cd apart-judgeops
make setup
make test
make demo
```

`make setup` installs dependencies. After setup, tests and the cached demonstration do not require model API access. `make demo` runs both included configurations and exports their grades to CSV, updating files under `runs/`.

To run one event and inspect its results:

```bash
MODE=cached uv run judgeops run configs/ai_control.json
uv run judgeops review-queue ai_control
uv run judgeops export ai_control --csv
```

To run selected steps:

```bash
MODE=cached uv run judgeops run configs/digital_minds.json --steps source,contact --top-k 3
MODE=cached uv run judgeops run configs/ai_control.json --steps accept,grade --sample 4 --seed 42 --k 3
```

`contact` requires a saved `judges.json`. `grade` uses saved projects when available and otherwise loads the project seeds. The included events each have two seed projects, so `--sample 4` grades both.

## Live mode

Copy the environment example:

```bash
cp .env.example .env
```

Set `ANTHROPIC_API_KEY`, `SENDER_NAME`, and `MODE=live` in `.env`, then run:

```bash
uv run --env-file .env judgeops run configs/digital_minds.json
```

The application reads process environment variables; it does not load `.env` itself. `--env-file .env` tells uv to load the file. `MODEL` defaults to `claude-sonnet-4-6` in the code and can be changed to a compatible model available to your Anthropic account.

Live sourcing uses web search, outreach uses generated drafts, and grading makes `k` model requests per sampled project before any retries. Project intake still reads local seeds, and no email is sent. The source URLs, contact evidence, and grades need review before operational use.

Live calls incur Anthropic API charges. Web search is configured for up to eight uses per request; retries or JSON repair can issue additional requests. This is not a total run budget.

## Configuration

Event files in [`configs/`](configs/) define `id`, `topic`, `description`, `tracks`, `dates`, and `rubric_path`. Dates in the included files are example event metadata, not a maintained schedule. The rubric path is resolved relative to the repository root.

Workflow controls are CLI options:

| Option | Default | Purpose |
| --- | --- | --- |
| `--steps` | `source,contact,accept,grade` | Steps to run, in the supplied order. |
| `--n` | `20` | Maximum number of sourced judges retained. |
| `--top-k` | `3` | Number of outreach drafts to create. |
| `--sample` | `4` | Maximum number of projects to grade. |
| `--seed` | `42` | Seed for project selection. |
| `--k` | `3` | Number of grading samples per project. |

The configuration's `judge_count` field is currently not used by the workflow; use `--n` to control the count. Use positive values for the count options. `--seed` controls project selection, not live model responses.

To add an event, create a configuration and a matching `data/seeds/<id>_projects.json` using the existing project files as the schema example. For cached judge sourcing, also supply `data/seeds/<id>_judges.json` or an existing `runs/<id>/judges.json`. Review the shared rubric and sourcing prompts for the new topic. A new configuration alone does not supply submissions or cached judges.

## Grading and review limits

The grader uses three dimensions: impact and innovation, execution quality, and presentation clarity. It takes three samples by default, aggregates each score using the upper median, averages model-reported confidence, and uses a majority vote for off-topic status.

A grade enters the review queue when confidence is below `0.7`, any aggregate score is `5`, the project is off topic, or samples differ by more than one point on a dimension. The queue is sorted by confidence, lowest first. This is a routing rule, not evidence that the confidence values are calibrated.

Current safeguards have specific limits:

- The prompt asks for scores from 1 to 5 and quotes supporting each rationale. The schema does not enforce that score range or require nonempty evidence quotes.
- Public email records must include source URLs and an evidence snippet. Validation checks their presence; it does not independently verify the address against the source.
- Anonymization replaces exact matches of the supplied team name in submission content. It does not remove all author identifiers.
- The saved rationale comes from the first sample, while the displayed scores aggregate all samples.

Email delivery, external submission imports, evaluation against human scores, broader anonymization, bias tests, and comparisons across models remain future work. A review interface and hosted infrastructure are not included.

## Development

```bash
make lint
make test
uv run judgeops --help
uv run judgeops run --help
```

CI runs Ruff and pytest on pushes and pull requests. Existing tests cover model validation, email evidence requirements, deterministic project sampling, score aggregation, review routing, and the cached workflow. They do not validate live API behavior or grading accuracy. A [`Dockerfile`](Dockerfile) is included for packaging the CLI; no hosting configuration is provided.

| Location | Purpose |
| --- | --- |
| [`app/cli.py`](app/cli.py), [`app/workflow.py`](app/workflow.py) | CLI and step orchestration. |
| [`app/steps/`](app/steps/) | Sourcing, outreach, intake, and grading. |
| [`app/llm.py`](app/llm.py) | Anthropic calls, prompt rendering, validation repair, and retries. |
| [`app/models.py`](app/models.py) | Event, judge, project, and grade schemas. |
| [`configs/`](configs/), [`prompts/`](prompts/) | Event inputs, shared rubric, and prompt versions. |
| [`data/seeds/`](data/seeds/), [`runs/`](runs/) | Synthetic inputs and saved demonstration outputs. |
| [`tests/`](tests/) | Offline unit and workflow tests. |

## License

No license file is included in this repository.
