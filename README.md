# AI-LC — AI Learning Lifecycle

AI-LC is an evidence-driven framework for adaptive technical learning. It decides what
a learner should do next from prerequisites, demonstrated dimensions, misconceptions and
reviews due. It is a learning lifecycle engine, not a static course or exercise bank.

Version 0.1 supplies a Python CLI, deterministic core and instructions for an external AI
harness. The harness performs teaching and just-in-time exercise generation. No API key,
model SDK, web server or autonomous chat runtime is required.

## Installation

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required for the recommended workflow.
From this checkout:

```sh
uv sync
uv run ailearn --help
uv tool install .
```

The distribution is `ai-learning-lifecycle`; the executable is `ailearn`. The package has
not been published to PyPI. The source repository is
[Moraw1993/AI-LC](https://github.com/Moraw1993/AI-LC). For the development branch:

```sh
uv tool install git+https://github.com/Moraw1993/AI-LC.git@develop
```

This repository is exclusively for implementation and development. Initialize learner
workspaces in a separate directory outside the checkout.

## Quick start

In an empty learning directory, using the installed tool:

```sh
ailearn init --learner Arek --domain time-series --target mid --depth comprehensive
ailearn doctor
ailearn plan
ailearn session
```

Initialization is noninteractive and defaults to statistics/mid/standard. It stores a
versioned authoritative `.ai-learning/state.json` and copies six role instructions plus
shared policy. It creates `AGENTS.md` only if absent. When instructions already exist,
load `.ai-learning/AGENTS.md` explicitly in the harness. Reinitializing with identical
settings preserves state; different settings fail safely.

Use `ailearn --workspace /path/to/learning COMMAND` to address another directory.
The first task is an independent diagnostic of an uncertain prerequisite. After failure,
the next task becomes remediation. After sufficient independent evidence, the roadmap
advances. Due reviews preempt new material; transfer tasks follow the core gates.

## Agent interaction and an example session

The Learning Conductor reads the task brief and delegates to Curriculum Architect,
Teacher, Lab Coach, Assessor or Research & Data. Assessor receives limited teaching context.
The learner attempts first; hints progress from conceptual direction to a full solution.
The actual hint level is recorded, and hinted attempts cannot pass mastery gates.

For time series, the prerequisite closure includes mean, variance, covariance and
correlation. If a diagnostic reveals weak covariance interpretation, the Conductor routes
Teacher and Lab Coach to covariance. Assessor separately evaluates the learner's artifact.
Two independent passing attempts for each required dimension permit progression back
toward autocorrelation. See [the runnable example](examples/time_series.py).

Assessor produces JSON matching `ailearn.models.Evidence`. Print its complete contract with:

```sh
uv run python -c "import json; from ailearn.models import Evidence; print(json.dumps(Evidence.model_json_schema(), indent=2))"
```

An example of one independent result (not enough alone for mastery):

```json
{
  "id": "covariance-interpretation-1",
  "attempt_id": "unseen-scatterplot-1",
  "competency": "statistics.covariance",
  "dimension": "interpretation",
  "score": 3,
  "independent": true,
  "hints": 0,
  "confidence": 0.9,
  "assessor": "external-independent-assessor",
  "artifact": "answers/scatterplot-1.md",
  "kind": "assessment",
  "notes": "Correct sign, units and limitation; no causal claim."
}
```

```sh
ailearn record result.json
ailearn status
ailearn session
```

Results are trusted assessor submissions; v0.1 does not authenticate assessor identity or
verify the contents of artifact references. Preserve referenced artifacts yourself.

## CLI

| Command | Purpose |
| --- | --- |
| `init` | Initialize safely; `--packs DIR` adds custom packs |
| `domains` | List validated built-in domains |
| `status` | Show dimension levels, stages, misconceptions and next action |
| `plan` | Recompute target dependency closure and readiness |
| `session --scope SCOPE` | Save a task brief for the harness |
| `record FILE --sensors FILE` | Validate evidence; optionally run fresh deterministic checks |
| `doctor` | Validate schema, DAG and evidence replay |
| `history` | Read session and evidence audit events |
| `export --evidence-jsonl` | Print full portable state or evidence lines |
| `sensors FILE` | Run structured checks without executing code |
| `sources` | List official dataset entry points |

Scopes: learn, deep-learn, review, remediate, practice, assessment, project, explore.
Explicit scope selection does not bypass prerequisite routing. Explore permits exposure
but rejects mastery-producing submissions until a new assessment session starts.

## Architecture and policy

```mermaid
flowchart LR
  Master[Learning Conductor] --> Brief[Adaptive task brief]
  Brief --> Agents[Five specialized agent roles]
  Agents --> Learner[Learner attempt]
  Learner --> Assessor[Independent Assessor and sensors]
  Assessor --> Evidence[Validated evidence]
  Evidence --> Gates[Dimension mastery gates]
  Gates --> State[Atomic state and review queue]
  State --> Master
```

Mastery dimensions are conceptual, mathematical, implementation, interpretation, debugging,
transfer and retention. Minimal depth requires conceptual and interpretation; standard adds
mathematical and implementation; comprehensive adds debugging. Transfer and retention are
separate later gates. Core gates require two distinct attempts, score ≥ pack threshold,
confidence ≥ 0.8, independence, no hints and no failing sensors or active misconceptions.
Failed independent evidence resets accumulated success in that dimension; failed delayed
retrieval invalidates all prior dimension passes and routes back to remediation. An explanation
or self-report can mark exposure but never mastery.

Transfer and retention evidence require core mastery first. Reviews start after the core
gate and are rescheduled after renewed mastery following failure. Dimension levels display
the last observed score; passing gates additionally check independent evidence history.

Intervals (1, 3, 7, 14, 30, 60 days) and evidence thresholds are product heuristics. Retrieval
practice motivates delayed testing; the implementation does not claim psychometric
calibration. See [architecture](docs/architecture.md), [agent model](docs/agent-model.md),
[domain authoring](docs/domain-authoring.md) and [contribution rules](CONTRIBUTING.md).

## Development and verification

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
uv run python examples/time_series.py
```

Starter packs cover statistics (6 competencies), machine learning (4) and time series (4).
They are small curricula with outcomes and rubrics, not exercise catalogs.

## v0.1 boundaries

Semantic assessment and live source discovery require an external harness. No learner-code
sandbox, automatic public-data connectors, encrypted storage, collaborative multi-user
workspace or schema migration is provided. Writer locks fail promptly and do not guess
whether a stale lock is safe to remove. If a process crashes, verify no writer is running
before removing `.ai-learning/write.lock`. JSON snapshots favor simple consistency over
large-scale storage; unsupported schemas and corrupt state fail without resetting data.

MIT licensed. Keep personal learning workspaces outside version control.
