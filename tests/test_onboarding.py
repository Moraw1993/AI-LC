import json
from importlib.resources import files

import pytest
import yaml

from ailearn.cli import main
from ailearn.engine import mastered, next_action, record, roadmap
from ailearn.exercises import create_exercise
from ailearn.graph import load_domains
from ailearn.models import Baseline, Dimension, Evidence, Exercise, LearningProfile
from ailearn.onboarding import complete_intake
from ailearn.store import Store


def profile(**changes):
    return LearningProfile(
        **{
            "learner": "Arek",
            "goal": "Analyze time-series forecasts",
            "domain": "time-series",
            "target": "mid",
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
    return hub.configure(profile(), load_domains())


def test_baseline_diagnostic_is_a_formal_checkpoint(course):
    brief = next_action(course.load())
    assert brief["assessment_checkpoint"] == "formal"
    assert "assessor" in brief["roles"]


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
    before = (course.root / "state.json").read_bytes()
    assert hub.configure(profile(), load_domains()).workspace == course.workspace
    assert (course.root / "state.json").read_bytes() == before
    assert not hub.bootstrap()
    assert hub.active().workspace == course.workspace
    with pytest.raises(ValueError, match="different learning profile"):
        hub.configure(profile(agent_name="Other"), load_domains())
    with pytest.raises(ValueError, match="goal closure"):
        hub.configure(
            profile(diagnostic_competencies=["machine_learning.gradient_descent"]), load_domains()
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
    assert "statistics.mean" in next_action(state)["missing_diagnostics"]
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
    with pytest.raises(ValueError, match="another competency"):
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
    assert len(list(resources.iterdir())) == 6
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


def test_full_cli_onboarding_and_course_recreation(tmp_path, capsys):
    prefix = ["--workspace", str(tmp_path)]
    assert main(prefix + ["init"]) == 0
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(profile().model_dump_json(), "utf-8")
    assert main(prefix + ["configure", str(profile_file)]) == 0
    capsys.readouterr()
    assert main(prefix + ["plan"]) == 0
    assert json.loads(capsys.readouterr().out)["roadmap"] is None
    course = Store(tmp_path).active()
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
    assert main(prefix + ["plan"]) == 0
    assert json.loads(capsys.readouterr().out)["roadmap"]
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(spec(kind="practice").model_dump_json(), "utf-8")
    assert main(prefix + ["exercise", str(spec_file)]) == 0
    assert main(prefix + ["doctor"]) == 0
    before = (course.root / "state.json").read_bytes()
    assert main(prefix + ["configure", str(profile_file)]) == 0
    assert (course.root / "state.json").read_bytes() == before


def test_master_can_configure_a_fresh_subject(tmp_path):
    hub = Store(tmp_path)
    hub.bootstrap()
    custom = load_domains()[0].model_copy(deep=True)
    custom.id, custom.name = "optimization", "Optimization"
    custom.competencies = [custom.competencies[0]]
    custom.competencies[0].id = "optimization.objective"
    custom.competencies[0].name = "Objective functions"
    custom.targets = {
        level: ["optimization.objective"] for level in ["beginner", "mid", "advanced"]
    }
    packs = tmp_path / "packs"
    packs.mkdir()
    (packs / "optimization.yml").write_text(custom.model_dump_json(), "utf-8")
    selected = profile(
        domain="optimization",
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
    value["intake"]["profile"]["target"] = "advanced"
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
