import json
from importlib.resources import files

import pytest
import yaml
from domain_fixtures import PACKS, load_test_domains

from ailearn.cli import main
from ailearn.engine import mastered, next_action, record, roadmap
from ailearn.exercises import create_exercise
from ailearn.graph import Graph
from ailearn.models import (
    Baseline,
    CoursePlanProposal,
    Dimension,
    Evidence,
    Exercise,
    LearningPathProfile,
    LearningPathVariant,
    LearningProfile,
    PlanStage,
)
from ailearn.onboarding import approve_plan, complete_intake, propose_plan, validate_course_plans
from ailearn.store import Store


def profile(**changes):
    return LearningProfile(
        **{
            "learner": "Arek",
            "goal": "Analyze time-series forecasts",
            "domain": "time-series",
            "target": "forecasting-without-leakage",
            "target_description": "Compare forecasts without leakage",
            "depth": "standard",
            "workspace_name": "forecasting",
            "agent_name": "Ada",
            "language": "Polish",
            "working_style": ["short explanations", "coding"],
            "prior_knowledge": "Some Python; unsure about statistical foundations",
            "diagnostic_competencies": ["statistics.mean", "time_series.autocorrelation"],
            **changes,
        }
    )


def result(key="statistics.mean", identifier="baseline-mean", **changes):
    return Evidence(
        **{
            "id": identifier,
            "attempt_id": identifier,
            "competency": key,
            "dimension": "conceptual",
            "score": 0,
            "independent": True,
            "hints": 0,
            "confidence": 0.9,
            "assessor": "independent-assessor",
            "artifact": "answers.md",
            "kind": "diagnostic",
            "notes": "Learner explicitly answered I do not know",
            **changes,
        }
    )


@pytest.fixture
def course(tmp_path):
    hub = Store(tmp_path)
    hub.bootstrap()
    course = hub.configure(profile(), load_test_domains())
    with course.transaction() as state:
        plan = propose_plan(state, plan_proposal(state, "overview"))
        approve_plan(state, plan.version)
    return course


def plan_proposal(state, phase, **changes):
    graph = Graph(state.domains)
    selected = state.intake.profile
    closure = graph.target_closure(selected.domain, selected.target)
    return CoursePlanProposal(
        **{
            "phase": phase,
            "goal": selected.goal,
            "domain": selected.domain,
            "target": selected.target,
            "target_description": selected.target_description,
            "depth": selected.depth,
            "learning_path_profile": LearningPathProfile(variant=LearningPathVariant.BALANCED),
            "title": f"{phase.title()} plan",
            "summary": "Learn the target skills and apply them to forecasting.",
            "stages": [
                PlanStage(
                    title="Foundations and application",
                    outcomes=["Explain and apply the listed competencies."],
                    competencies=closure,
                )
            ],
            "working_method": "Explanation, worked example, guided practice, "
            "then an independent checkpoint.",
            "projects": ["Compare a forecast with a simple baseline."],
            "role_responsibilities": [
                "Master coordinates the stages.",
                "Teacher teaches; Assessor independently evaluates formal checkpoints.",
            ],
            **changes,
        }
    )


def test_baseline_diagnostic_is_a_formal_checkpoint(course):
    brief = next_action(course.load())
    assert brief["assessment_checkpoint"] == "formal"
    assert "assessor" in brief["roles"]


def test_new_course_requires_overview_then_baseline_then_adaptive_plan(tmp_path):
    hub = Store(tmp_path)
    hub.bootstrap()
    course = hub.configure(profile(), load_test_domains())
    state = course.load()
    assert next_action(state)["action"] == "propose-plan"
    assert next_action(state)["plan_phase"] == "overview"
    with pytest.raises(ValueError, match="approve the current course plan"):
        record(state, result())
    with pytest.raises(ValueError, match="approve the course overview"):
        complete_intake(
            state,
            Baseline(summary="Premature", evidence_ids=["not-collected-yet"]),
        )

    with course.transaction() as state:
        invalid = plan_proposal(state, "overview")
        invalid.stages[0].competencies.pop()
        with pytest.raises(ValueError, match="cover the selected target"):
            propose_plan(state, invalid)
        wrong_scope = plan_proposal(state, "overview", goal="A different course goal")
        with pytest.raises(ValueError, match="match the agreed learning profile"):
            propose_plan(state, wrong_scope)
        graph = Graph(state.domains)
        profile_scope = state.intake.profile
        reverse_order = list(
            reversed(graph.target_closure(profile_scope.domain, profile_scope.target))
        )
        invalid_order = plan_proposal(
            state,
            "overview",
            stages=[
                PlanStage(title=key, outcomes=["Understand this outcome."], competencies=[key])
                for key in reverse_order
            ],
        )
        with pytest.raises(ValueError, match="before its prerequisite"):
            propose_plan(state, invalid_order)
        proposal = propose_plan(state, plan_proposal(state, "overview"))
    assert next_action(course.load())["action"] == "await-plan-approval"
    with pytest.raises(ValueError, match="approve the current course plan"):
        record(course.load(), result())

    with course.transaction() as state:
        approve_plan(state, proposal.version)
        assert not state.knowledge
    assert next_action(course.load())["action"] == "diagnostic"
    with course.transaction() as state:
        with pytest.raises(ValueError, match="agreed diagnostic competency"):
            record(state, result("statistics.variance", "not-agreed"))
        record(state, result())
        record(state, result("time_series.autocorrelation", "baseline-acf"))
        complete_intake(
            state,
            Baseline(
                summary="Baseline complete",
                evidence_ids=["baseline-mean", "baseline-acf"],
            ),
        )
        assert next_action(state)["action"] == "propose-plan"
        assert next_action(state)["plan_phase"] == "adaptive"
        with pytest.raises(ValueError, match="approve the current course plan"):
            record(state, result("statistics.mean", "practice-before-roadmap", kind="assessment"))
        with pytest.raises(ValueError, match="approve the current course plan"):
            record(state, result("statistics.mean", "teaching-before-roadmap", kind="explanation"))
        ordered = [
            "statistics.mean",
            "statistics.variance",
            "statistics.probability",
            "statistics.covariance",
            "statistics.correlation",
            "time_series.autocorrelation",
            "time_series.stationarity",
            "statistics.inference",
            "machine_learning.validation",
            "time_series.temporal_validation",
        ]
        adaptive = propose_plan(
            state,
            plan_proposal(
                state,
                "adaptive",
                title="Forecasting route",
                stages=[
                    PlanStage(
                        title="Core foundations",
                        outcomes=["Build essential foundations."],
                        competencies=ordered[:2],
                    ),
                    PlanStage(
                        title="Probability before covariance",
                        outcomes=["Use probability in forecasting."],
                        competencies=ordered[2:],
                    ),
                ],
            ),
        )
        before = state.knowledge.copy()
        approve_plan(state, adaptive.version)
        assert state.knowledge == before
        assert roadmap(state) == ordered
        action = next_action(state)
        assert action["competency"] == "statistics.mean"
        assert action["course_plan"] == {
            "title": "Forecasting route",
            "stage": "Core foundations",
            "stage_outcomes": ["Build essential foundations."],
        }
    assert next_action(course.load())["phase"] != "course-planning"


def test_plan_revision_requires_reapproval_and_is_audited(course):
    with course.transaction() as state:
        original = state.plans[-1]
        revised = propose_plan(
            state, plan_proposal(state, "overview", summary="A clearer overview."), revise=True
        )
        assert revised.version == original.version + 1
        assert original.status == "approved"
        assert next_action(state)["action"] == "await-plan-approval"
        approve_plan(state, revised.version)
        assert original.status == "superseded"
        assert state.history[-2]["event"] == "plan.revised"
        assert state.history[-1]["event"] == "plan.approved"


def test_adaptive_plan_cannot_change_learner_approved_path(course):
    finish_baseline(course)
    with course.transaction() as state:
        changed = plan_proposal(
            state,
            "adaptive",
            learning_path_profile=LearningPathProfile(variant=LearningPathVariant.PROJECT_LED),
        )
        with pytest.raises(ValueError, match="keep the learner-approved path profile"):
            propose_plan(state, changed, revise=True)


def test_course_plan_profile_is_versioned_and_legacy_plans_default_to_balanced(course):
    state = course.load()
    proposal_data = plan_proposal(state, "adaptive").model_dump()
    proposal_data.pop("learning_path_profile")
    with pytest.raises(ValueError, match="learning_path_profile"):
        CoursePlanProposal.model_validate(proposal_data)
    with pytest.raises(ValueError):
        LearningPathProfile(schema_version=2, variant="focused")

    snapshot_path = course.root / "state.json"
    saved = json.loads(snapshot_path.read_text("utf-8"))
    saved["plans"][0].pop("learning_path_profile")
    snapshot_path.write_text(json.dumps(saved), "utf-8")
    loaded = course.load()
    assert loaded.plans[0].learning_path_profile.variant == LearningPathVariant.BALANCED


def test_project_led_prioritizes_eligible_transfer_but_due_reviews_and_remediation_win(
    tmp_path,
):
    hub = Store(tmp_path)
    hub.bootstrap()
    course = hub.configure(profile(depth="minimal"), load_test_domains())
    with course.transaction() as state:
        overview = propose_plan(
            state,
            plan_proposal(
                state,
                "overview",
                learning_path_profile=LearningPathProfile(variant=LearningPathVariant.PROJECT_LED),
            ),
        )
        approve_plan(state, overview.version)
    with course.transaction() as state:
        for key, identifier in [
            ("statistics.mean", "baseline-mean"),
            ("time_series.autocorrelation", "baseline-acf"),
        ]:
            diagnostic = result(key, identifier, score=4)
            record(state, diagnostic)
        complete_intake(
            state,
            Baseline(
                summary="Both concepts are familiar",
                evidence_ids=["baseline-mean", "baseline-acf"],
            ),
        )
        adaptive = propose_plan(
            state,
            plan_proposal(
                state,
                "adaptive",
                learning_path_profile=LearningPathProfile(variant=LearningPathVariant.PROJECT_LED),
            ),
        )
        approve_plan(state, adaptive.version)

    with course.transaction() as state:
        key = roadmap(state)[0]
        for dimension in [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]:
            for attempt in ["one", "two"]:
                record(
                    state,
                    Evidence(
                        id=f"{key}-{dimension.value}-{attempt}",
                        attempt_id=f"{key}-{attempt}",
                        competency=key,
                        dimension=dimension,
                        score=4,
                        independent=True,
                        confidence=0.95,
                        assessor="independent-assessor",
                        artifact="answer.md",
                        kind="assessment",
                    ),
                )
    state = course.load()
    brief = next_action(state)
    assert brief["scope"] == "project"
    assert brief["competency"] == key
    assert brief["learning_path_profile"]["variant"] == "project-led"

    due = state.knowledge[key].review_due
    assert next_action(state, at=due)["scope"] == "review"

    with course.transaction() as state:
        second = roadmap(state)[1]
        record(
            state,
            Evidence(
                id="second-core-failure",
                attempt_id="second-core-failure",
                competency=second,
                dimension=Dimension.CONCEPTUAL,
                score=0,
                independent=True,
                confidence=0.95,
                assessor="independent-assessor",
                artifact="answer.md",
                kind="assessment",
            ),
        )
    assert next_action(course.load())["scope"] == "remediate"


def test_plan_cli_proposes_approves_and_displays_plan(tmp_path, capsys):
    hub = Store(tmp_path)
    hub.bootstrap()
    course = hub.configure(profile(), load_test_domains())
    proposal_file = tmp_path / "overview.json"
    proposal_file.write_text(plan_proposal(course.load(), "overview").model_dump_json(), "utf-8")
    prefix = ["--workspace", str(tmp_path)]
    assert main(prefix + ["plan", "propose", str(proposal_file)]) == 0
    proposed = json.loads(capsys.readouterr().out)
    assert proposed["plan"]["status"] == "proposed"
    assert proposed["next"]["action"] == "await-plan-approval"
    assert main(prefix + ["plan", "approve", "1"]) == 0
    approved = json.loads(capsys.readouterr().out)
    assert approved["plan"]["status"] == "approved"
    assert approved["next"]["action"] == "diagnostic"
    assert main(prefix + ["plan"]) == 0
    view = json.loads(capsys.readouterr().out)
    assert view["plans"][0]["version"] == 1
    assert view["next"]["action"] == "diagnostic"
    assert main(["schema", "CoursePlanProposal"]) == 0
    assert "role_responsibilities" in json.loads(capsys.readouterr().out)["properties"]


def test_legacy_profile_without_plan_workflow_remains_usable(tmp_path):
    from ailearn.models import Config, Intake

    store = Store(tmp_path)
    selected = profile()
    store.init(
        Config(
            learner=selected.learner,
            domain=selected.domain,
            target=selected.target,
            depth=selected.depth,
            preferences=selected.working_style,
        ),
        load_test_domains(),
        Intake(profile=selected),
    )
    legacy_path = store.root / "state.json"
    legacy = json.loads(legacy_path.read_text("utf-8"))
    legacy.pop("plan_workflow")
    legacy.pop("plans")
    legacy_path.write_text(json.dumps(legacy), "utf-8")
    state = store.load()
    assert not state.plan_workflow
    assert next_action(state)["action"] == "diagnostic"
    record(state, result())


def test_modern_snapshot_rejects_completed_baseline_without_overview_plan(course):
    state = course.load()
    state.plans.clear()
    state.intake.baseline = Baseline(summary="Completed", evidence_ids=["baseline-mean"])
    with pytest.raises(ValueError, match="approved overview plan"):
        validate_course_plans(state)


def finish_baseline(course):
    with course.transaction() as state:
        record(state, result())
        record(state, result("time_series.autocorrelation", "baseline-acf"))
        complete_intake(
            state,
            Baseline(
                summary="Both concepts are unfamiliar",
                evidence_ids=["baseline-mean", "baseline-acf"],
            ),
        )
        selected_path = next(
            plan.learning_path_profile
            for plan in reversed(state.plans)
            if plan.phase == "overview" and plan.status == "approved"
        )
        adaptive = propose_plan(
            state,
            plan_proposal(state, "adaptive", learning_path_profile=selected_path),
        )
        approve_plan(state, adaptive.version)


def spec(**changes):
    return Exercise(
        **{
            "lesson": 1,
            "topic": 1,
            "attempt": 1,
            "competency": "statistics.mean",
            "kind": "diagnostic",
            "instructions": "Implement the mean without a library. Explain an empty input.",
            "source": "def mean(values):\n    # TODO: implement\n    pass\n",
            **changes,
        }
    )


def test_neutral_init_and_master_entrypoint(tmp_path, capsys):
    (tmp_path / "AGENTS.md").write_text("User instructions", "utf-8")
    prefix = ["--workspace", str(tmp_path)]
    assert main(prefix + ["init"]) == 0
    assert "$ai-lc-master" in capsys.readouterr().out
    store = Store(tmp_path)
    before = (store.root / "bootstrap.json").read_bytes()
    assert not (store.root / "state.json").exists()
    assert not (tmp_path / "workspaces").exists()
    assert main(prefix + ["init"]) == 0
    assert (store.root / "bootstrap.json").read_bytes() == before
    assert (tmp_path / "AGENTS.md").read_text("utf-8") == "User instructions"
    for command in ["status", "plan", "session", "doctor"]:
        capsys.readouterr()
        assert main(prefix + [command]) == 0
        brief = json.loads(capsys.readouterr().out)
        assert brief["phase"] == "intent-discovery"
        assert "domain" not in brief and "target" not in brief
    assert main(prefix + ["record", "missing.json"]) == 2


def test_explicit_profile_is_required_and_portable():
    data = profile().model_dump()
    del data["target"]
    with pytest.raises(ValueError):
        LearningProfile.model_validate(data)
    for name in ["../escape", "CON", "LPT1", "has spaces", "/absolute"]:
        with pytest.raises(ValueError):
            profile(workspace_name=name)


def test_configuration_preserves_course_and_hub_routing(course):
    hub = Store(course.workspace.parent.parent)
    assert hub.active().workspace == course.workspace
    assert course.load().intake.profile.agent_name == "Ada"
    assert sorted(path.name for path in course.root.iterdir()) == ["state.json"]
    assert not (course.workspace / ".agents").exists()
    assert not (course.workspace / "AGENTS.md").exists()
    assert (hub.workspace / ".agents/skills/ai-lc-master/SKILL.md").is_file()
    assert (hub.root / "agents/master.md").is_file()
    before = (course.root / "state.json").read_bytes()
    assert hub.configure(profile(), load_test_domains()).workspace == course.workspace
    assert (course.root / "state.json").read_bytes() == before
    assert not hub.bootstrap()
    assert hub.active().workspace == course.workspace
    with pytest.raises(ValueError, match="different learning profile"):
        hub.configure(profile(agent_name="Other"), load_test_domains())
    with pytest.raises(ValueError, match="goal closure"):
        hub.configure(
            profile(diagnostic_competencies=["machine_learning.gradient_descent"]),
            load_test_domains(),
        )


def test_baseline_gate_genuine_failure_and_no_self_report(course):
    state = course.load()
    with pytest.raises(ValueError, match="baseline"):
        roadmap(state)
    assert next_action(state, "learn")["action"] == "diagnostic"
    with pytest.raises(ValueError, match="baseline"):
        record(state, result(kind="assessment"))
    record(state, result(kind="self-report"))
    assert next_action(state)["missing_diagnostics"] == profile().diagnostic_competencies
    with pytest.raises(ValueError, match="diagnostic evidence"):
        complete_intake(state, Baseline(summary="Self report", evidence_ids=["baseline-mean"]))
    hinted = result(identifier="hinted", hints=1)
    record(state, hinted)
    assert next_action(state)["missing_diagnostics"] == profile().diagnostic_competencies
    with pytest.raises(ValueError, match="diagnostic evidence"):
        complete_intake(state, Baseline(summary="Hinted", evidence_ids=["hinted"]))
    finish_baseline(course)
    saved = course.load()
    assert not mastered(saved, "statistics.mean")
    assert next_action(saved)["scope"] == "remediate"
    assert "time_series.autocorrelation" in roadmap(saved)
    assert main(["--workspace", str(course.workspace), "doctor"]) == 0


def test_baseline_requires_coverage_and_known_ids(course):
    state = course.load()
    record(state, result())
    for ids, message in [(["unknown"], "unknown"), (["baseline-mean"], "cover")]:
        with pytest.raises(ValueError, match=message):
            complete_intake(state, Baseline(summary="Incomplete", evidence_ids=ids))
    record(state, result("time_series.autocorrelation", "acf", confidence=0.4))
    assert next_action(state)["missing_diagnostics"] == ["time_series.autocorrelation"]


def test_diagnostic_revision_reopens_coverage_and_completed_baseline_is_protected(course):
    state = course.load()
    original = result()
    original.score = 3
    record(state, original)
    corrected = result(identifier="baseline-mean-corrected")
    corrected.attempt_id = original.attempt_id
    corrected.score = 0
    record(state, corrected, replace_id=original.id)
    assert next_action(state)["missing_diagnostics"] == ["time_series.autocorrelation"]
    finish_baseline(course)
    saved = course.load()
    revision = result(identifier="after-baseline")
    with pytest.raises(ValueError, match="completed baseline"):
        record(saved, revision, replace_id="baseline-mean")


def test_numbered_files_preserve_attempts_and_never_execute(course):
    sentinel = course.workspace / "executed.txt"
    task = create_exercise(course, spec(source=f"open({str(sentinel)!r}, 'w').write('BAD')"))
    assert not sentinel.exists()
    assert task.id == "L001-T001-A001"
    path = course.workspace / task.path
    assert path.name == "lesson_001_topic_001_attempt_001_statistics_mean.py"
    path.write_text("# Learner's work\n", "utf-8")
    with pytest.raises(ValueError, match="already exists"):
        create_exercise(course, spec())
    assert path.read_text("utf-8") == "# Learner's work\n"
    retry = create_exercise(course, spec(attempt=2))
    assert retry.path != task.path
    with pytest.raises(ValueError, match="agreed diagnostic competencies"):
        create_exercise(course, spec(attempt=3, competency="statistics.variance"))
    with pytest.raises(ValueError, match="80 lines"):
        create_exercise(course, spec(attempt=3, source="pass\n" * 81))
    with pytest.raises(SyntaxError):
        create_exercise(course, spec(attempt=3, source="def broken("))
    with pytest.raises(ValueError, match="baseline"):
        create_exercise(course, spec(attempt=3, kind="practice"))


def test_implementation_evidence_requires_registered_task(course):
    with course.transaction() as state:
        with pytest.raises(ValueError, match="numbered exercise"):
            record(state, result(dimension=Dimension.IMPLEMENTATION))
    task = create_exercise(course, spec())
    evidence = result(dimension=Dimension.IMPLEMENTATION, attempt_id=task.id, artifact=task.path)
    with course.transaction() as state:
        record(state, evidence)
    (course.workspace / task.path).unlink()
    assert main(["--workspace", str(course.workspace), "doctor"]) == 2


def test_exercise_rolls_back_on_snapshot_publication_failure(course, monkeypatch):
    before = (course.root / "state.json").read_bytes()

    def fail(_):
        raise OSError("simulated publication failure")

    monkeypatch.setattr(course, "save", fail)
    with pytest.raises(OSError):
        create_exercise(course, spec())
    assert not list((course.workspace / "lessons").glob("*.py"))
    assert (course.root / "state.json").read_bytes() == before


def test_skills_install_conflicts_and_packaging(tmp_path):
    resources = files("ailearn").joinpath("resources/skills")
    assert len(list(resources.iterdir())) == 8
    for resource in resources.iterdir():
        header = resource.joinpath("SKILL.md").read_text("utf-8").split("---")[1]
        metadata = yaml.safe_load(header)
        assert metadata["name"] == resource.name
        assert metadata["description"]
    conflict = tmp_path / ".agents/skills/ai-lc-master/SKILL.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("Existing user skill", "utf-8")
    with pytest.raises(ValueError, match="preserved"):
        Store(tmp_path).bootstrap()
    assert conflict.read_text("utf-8") == "Existing user skill"
    assert not (tmp_path / ".ai-learning").exists()

    installed = tmp_path / "installed"
    Store(installed).bootstrap()
    assert (installed / ".ai-learning/agents/teaching-modes.md").is_file()
    assert (installed / ".ai-learning/agents/styles/lecturer.md").is_file()
    assert (installed / ".ai-learning/agents/styles/exercise_coach.md").is_file()
    assert (installed / ".agents/skills/ai-lc-lecture/SKILL.md").is_file()
    assert (installed / ".agents/skills/ai-lc-laboratory/SKILL.md").is_file()


def test_full_cli_onboarding_and_course_recreation(tmp_path, capsys):
    prefix = ["--workspace", str(tmp_path)]
    assert main(prefix + ["init"]) == 0
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(profile().model_dump_json(), "utf-8")
    assert main(prefix + ["configure", str(profile_file), "--packs", str(PACKS)]) == 0
    capsys.readouterr()
    assert main(prefix + ["plan"]) == 0
    assert json.loads(capsys.readouterr().out)["roadmap"] is None
    course = Store(tmp_path).active()
    overview_file = tmp_path / "overview.json"
    overview_file.write_text(plan_proposal(course.load(), "overview").model_dump_json(), "utf-8")
    assert main(prefix + ["plan", "propose", str(overview_file)]) == 0
    capsys.readouterr()
    assert main(prefix + ["plan", "approve", "1"]) == 0
    capsys.readouterr()
    for response in [result(), result("time_series.autocorrelation", "baseline-acf")]:
        file = tmp_path / "result.json"
        file.write_text(response.model_dump_json(), "utf-8")
        assert main(prefix + ["record", str(file)]) == 0
    report = tmp_path / "baseline.json"
    report.write_text(
        Baseline(
            summary="Unfamiliar concepts", evidence_ids=["baseline-mean", "baseline-acf"]
        ).model_dump_json(),
        "utf-8",
    )
    assert main(prefix + ["complete-intake", str(report)]) == 0
    capsys.readouterr()
    adaptive_file = tmp_path / "adaptive.json"
    adaptive_file.write_text(plan_proposal(course.load(), "adaptive").model_dump_json(), "utf-8")
    assert main(prefix + ["plan", "propose", str(adaptive_file)]) == 0
    capsys.readouterr()
    assert main(prefix + ["plan", "approve", "2"]) == 0
    capsys.readouterr()
    assert main(prefix + ["plan"]) == 0
    assert json.loads(capsys.readouterr().out)["roadmap"]
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(spec(kind="practice").model_dump_json(), "utf-8")
    assert main(prefix + ["exercise", str(spec_file)]) == 0
    assert main(prefix + ["doctor"]) == 0
    before = (course.root / "state.json").read_bytes()
    assert main(prefix + ["configure", str(profile_file), "--packs", str(PACKS)]) == 0
    assert (course.root / "state.json").read_bytes() == before


def test_master_can_configure_a_fresh_subject_and_custom_target(tmp_path):
    hub = Store(tmp_path)
    hub.bootstrap()
    custom = next(d for d in load_test_domains() if d.id == "statistics").model_copy(deep=True)
    custom.id, custom.name = "optimization", "Optimization"
    custom.competencies = [custom.competencies[0]]
    custom.competencies[0].id = "optimization.objective"
    custom.competencies[0].name = "Objective functions"
    custom.targets = {"optimization-objective": ["optimization.objective"]}
    packs = tmp_path / "packs"
    packs.mkdir()
    (packs / "optimization.yml").write_text(custom.model_dump_json(), "utf-8")
    selected = profile(
        domain="optimization",
        target="optimization-objective",
        workspace_name="optimization",
        goal="Understand objective functions",
        diagnostic_competencies=["optimization.objective"],
    )
    file = tmp_path / "profile.json"
    file.write_text(selected.model_dump_json(), "utf-8")
    assert main(["--workspace", str(tmp_path), "configure", str(file), "--packs", str(packs)]) == 0
    assert hub.active().load().config.domain == "optimization"
    (packs / "optimization.yml").write_text("not: [valid", "utf-8")
    assert main(["--workspace", str(tmp_path), "configure", str(file), "--packs", str(packs)]) == 2


def test_paths_cannot_redirect_outside_hub(tmp_path):
    hub = Store(tmp_path)
    hub.bootstrap()
    bootstrap = hub.bootstrap_state()
    bootstrap.active_workspace = "../outside"
    (hub.root / "bootstrap.json").write_text(bootstrap.model_dump_json(), "utf-8")
    with pytest.raises(ValueError, match="inside"):
        hub.active()


def test_profile_or_baseline_corruption_fails_clearly(course):
    finish_baseline(course)
    before = (course.root / "state.json").read_text("utf-8")
    value = json.loads(before)
    value["intake"]["baseline"]["evidence_ids"] = ["fabricated"]
    (course.root / "state.json").write_text(json.dumps(value), "utf-8")
    with pytest.raises(ValueError, match="unknown evidence"):
        course.load()
    value = json.loads(before)
    value["intake"]["profile"]["target"] = "different-goal"
    (course.root / "state.json").write_text(json.dumps(value), "utf-8")
    with pytest.raises(ValueError, match="configuration"):
        course.load()


def test_missing_active_snapshot_is_corruption_not_neutral_onboarding(course, capsys):
    hub = Store(course.workspace.parent.parent)
    (course.root / "state.json").unlink()
    with pytest.raises(ValueError, match="snapshot is missing"):
        hub.active()
    for command in ["status", "plan", "session", "doctor"]:
        assert main(["--workspace", str(hub.workspace), command]) == 2
        output = capsys.readouterr()
        assert "snapshot is missing" in output.err
        assert "intent-discovery" not in output.out
