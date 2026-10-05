"""Small argument-driven CLI for harnesses and learners."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from yaml import YAMLError

from ailearn import __version__, models
from ailearn.data import SOURCES
from ailearn.engine import mastered, next_action, record, roadmap
from ailearn.exercises import create_exercise, validate_artifacts
from ailearn.graph import Graph, load_domains
from ailearn.harness_contract import required_capabilities, validate_delivery
from ailearn.models import (
    Baseline,
    CoursePlanProposal,
    Evidence,
    Exercise,
    LearningProfile,
    Scope,
    active_evidence,
    now,
)
from ailearn.onboarding import (
    approve_plan,
    complete_intake,
    diagnostic_brief,
    onboarding_brief,
    propose_plan,
)
from ailearn.sensors import run
from ailearn.store import Store, dumps


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ailearn", description="Evidence-driven AI learning lifecycle")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--workspace", type=Path, default=Path.cwd())
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Install Master and teaching skills without choosing a topic")
    config = commands.add_parser("config", help="Configure a topic-neutral harness workspace")
    config.add_argument("--harness", required=True, choices=["codex"])
    harness = commands.add_parser("harness", help="Validate a harness manifest and AI-LC brief")
    harness_actions = harness.add_subparsers(dest="harness_action", required=True)
    validate_harness = harness_actions.add_parser(
        "validate", help="Check brief requirements against declared harness capabilities"
    )
    validate_harness.add_argument("manifest", type=Path)
    validate_harness.add_argument("brief", type=Path)
    configure = commands.add_parser(
        "configure", help="Create a course from Master's agreed profile"
    )
    configure.add_argument("file", type=Path)
    configure.add_argument(
        "--packs", type=Path, required=True, help="Agent-authored course pack directory"
    )
    baseline = commands.add_parser(
        "complete-intake", help="Confirm independently diagnosed baseline"
    )
    baseline.add_argument("file", type=Path)
    exercise = commands.add_parser("exercise", help="Create a short numbered Python task")
    exercise.add_argument("file", type=Path)
    domains = commands.add_parser("domains", help="Validate and list agent-authored domain packs")
    domains.add_argument("--packs", type=Path, required=True)
    commands.add_parser("status", help="Show demonstrated knowledge and review queue")
    commands.add_parser("doctor", help="Validate workspace, graph and audit log")
    plan = commands.add_parser("plan", help="Show or manage the approved course plan")
    plan_actions = plan.add_subparsers(dest="plan_action")
    propose = plan_actions.add_parser("propose", help="Propose the next course plan")
    propose.add_argument("file", type=Path)
    revise = plan_actions.add_parser("revise", help="Revise a proposed or approved plan")
    revise.add_argument("file", type=Path)
    approve = plan_actions.add_parser("approve", help="Approve a proposed course plan")
    approve.add_argument("version", type=int)
    commands.add_parser("history", help="Show session and evidence audit history")
    session = commands.add_parser("session", help="Create a just-in-time agent task brief")
    session.add_argument("--scope", choices=list(Scope))
    evidence = commands.add_parser("record", help="Import independently assessed evidence JSON")
    evidence.add_argument("file", type=Path)
    evidence.add_argument("--sensors", type=Path, help="Run sensor inputs and attach fresh results")
    evidence.add_argument(
        "--replace",
        metavar="EVIDENCE_ID",
        help="Supersede a prior assessment for this attempt/dimension",
    )
    sensor = commands.add_parser("sensors", help="Run deterministic checks from JSON inputs")
    sensor.add_argument("file", type=Path)
    export = commands.add_parser("export", help="Print portable state or evidence JSONL")
    export.add_argument("--evidence-jsonl", action="store_true")
    commands.add_parser("sources", help="List authoritative data-source entry points")
    schema = commands.add_parser("schema", help="Print a harness contract without external imports")
    schema.add_argument(
        "model",
        choices=[
            "LearningProfile",
            "Domain",
            "Baseline",
            "Evidence",
            "Exercise",
            "CoursePlanProposal",
            "CoursePlan",
            "Snapshot",
            "HarnessManifest",
            "HarnessBrief",
        ],
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "config":
            from ailearn.harness import configure_codex

            configure_codex(args.workspace)
            print("Codex configured. Invoke $ai-lc-master to discuss your learning goal.")
            return 0
        store = Store(args.workspace)
        if args.command not in {
            "init",
            "configure",
            "domains",
            "sources",
            "sensors",
            "schema",
            "harness",
        }:
            store = store.active()
            if not (store.root / "state.json").exists():
                if args.command in {"status", "plan", "session", "doctor"}:
                    print(dumps(onboarding_brief()))
                    return 0
                raise ValueError("invoke $ai-lc-master and configure a learning profile first")
        if args.command == "domains":
            print(
                dumps(
                    [
                        {"id": d.id, "name": d.name, "competencies": len(d.competencies)}
                        for d in load_domains(args.packs)
                    ]
                )
            )
        elif args.command == "sources":
            print(dumps(SOURCES))
        elif args.command == "harness":
            manifest_data = json.loads(args.manifest.read_text("utf-8"))
            brief_data = json.loads(args.brief.read_text("utf-8"))
            manifest, brief = validate_delivery(manifest_data, brief_data)
            print(
                dumps(
                    {
                        "declared_requirements_satisfied": True,
                        "harness_id": manifest.harness_id,
                        "brief_schema_version": brief.schema_version,
                        "required_capabilities": sorted(
                            capability.value for capability in required_capabilities(brief)
                        ),
                    }
                )
            )
        elif args.command == "schema":
            print(dumps(getattr(models, args.model).model_json_schema()))
        elif args.command == "init":
            created = store.bootstrap()
            print(
                "Workspace initialized." if created else "Workspace already initialized; preserved."
            )
            print(f"Harness instructions: {store.root / 'AGENTS.md'}")
            print("Open this directory in Codex and invoke $ai-lc-master to discuss your goal.")
            if (store.workspace / "AGENTS.md").read_text("utf-8") != (
                store.root / "AGENTS.md"
            ).read_text("utf-8"):
                print("Existing AGENTS.md preserved. Load .ai-learning/AGENTS.md in your harness.")
        elif args.command == "configure":
            profile = LearningProfile.model_validate_json(args.file.read_text("utf-8"))
            course = store.configure(profile, load_domains(args.packs))
            print(dumps({"workspace": str(course.workspace), "next": next_action(course.load())}))
        elif args.command == "complete-intake":
            baseline = Baseline.model_validate_json(args.file.read_text("utf-8"))
            with store.transaction() as state:
                complete_intake(state, baseline)
            print(dumps({"message": "Baseline recorded.", "next": next_action(store.load())}))
        elif args.command == "exercise":
            exercise = Exercise.model_validate_json(args.file.read_text("utf-8"))
            print(dumps(create_exercise(store, exercise).model_dump(mode="json")))
        elif args.command == "record":
            e = Evidence.model_validate_json(args.file.read_text("utf-8"))
            if e.dimension == "implementation":
                validate_artifacts(store)
            if args.sensors:
                e.sensors = run(json.loads(args.sensors.read_text("utf-8")))
            with store.transaction() as state:
                record(state, e, replace_id=args.replace)
            print(f"Recorded {e.id}.")
        elif args.command == "sensors":
            results = run(json.loads(args.file.read_text("utf-8")))
            print(dumps([r.model_dump() for r in results]))
            return 0 if all(r.passed for r in results) else 1
        elif args.command == "session":
            with store.transaction() as state:
                brief = next_action(state, Scope(args.scope) if args.scope else None)
                state.session = brief
                state.history.append(
                    {"event": "session", "timestamp": now().isoformat(), "brief": brief}
                )
            print(dumps(brief))
        else:
            state = store.load()
            if args.command == "status":
                print(
                    dumps(
                        {
                            "learner": state.config.learner,
                            "config": state.config.model_dump(mode="json"),
                            "intake": state.intake.model_dump(mode="json")
                            if state.intake
                            else None,
                            "workspace": str(store.workspace),
                            "knowledge": {
                                k: v.model_dump(mode="json") for k, v in state.knowledge.items()
                            },
                            "evidence_count": len(active_evidence(state)),
                            "evidence_revision_count": len(state.evidence)
                            - len(active_evidence(state)),
                            "next": next_action(state),
                        }
                    )
                )
            elif args.command == "plan":
                if args.plan_action in {"propose", "revise"}:
                    proposal = CoursePlanProposal.model_validate_json(args.file.read_text("utf-8"))
                    with store.transaction() as mutable:
                        created = propose_plan(
                            mutable, proposal, revise=args.plan_action == "revise"
                        )
                    print(
                        dumps(
                            {
                                "plan": created.model_dump(mode="json"),
                                "next": next_action(store.load()),
                            }
                        )
                    )
                elif args.plan_action == "approve":
                    with store.transaction() as mutable:
                        approved = approve_plan(mutable, args.version)
                    print(
                        dumps(
                            {
                                "plan": approved.model_dump(mode="json"),
                                "next": next_action(store.load()),
                            }
                        )
                    )
                else:
                    next_brief = next_action(state)
                    roadmap_value = None
                    if (
                        next_brief.get("phase") != "course-planning"
                        and diagnostic_brief(state) is None
                    ):
                        roadmap_value = [
                            {"competency": key, "mastered": mastered(state, key)}
                            for key in roadmap(state)
                        ]
                    print(
                        dumps(
                            {
                                "phase": next_brief.get("phase"),
                                "plans": [plan.model_dump(mode="json") for plan in state.plans],
                                "roadmap": roadmap_value,
                                "next": next_brief,
                            }
                        )
                    )
            elif args.command == "history":
                print(dumps(state.history))
            elif args.command == "export":
                if args.evidence_jsonl:
                    for e in state.evidence:
                        print(e.model_dump_json())
                else:
                    print(dumps(store.export()))
            elif args.command == "doctor":
                Graph(state.domains)
                validate_artifacts(store)
                # Replay all evidence to verify the derived state was not silently altered.
                replay = state.model_copy(deep=True)
                replay.knowledge, replay.evidence, replay.history, replay.session = {}, [], [], {}
                for e in state.evidence:
                    record(replay, e, replace_id=e.supersedes_id)
                if replay.knowledge != state.knowledge:
                    raise ValueError("knowledge snapshot differs from evidence replay")
                print("OK: schema, domains, dependencies, evidence and derived knowledge.")
        return 0
    except (
        OSError,
        ValueError,
        ValidationError,
        KeyError,
        TypeError,
        SyntaxError,
        YAMLError,
    ) as exc:
        print(f"ailearn: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
