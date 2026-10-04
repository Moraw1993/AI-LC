import json
from datetime import timedelta

import pytest
from yaml import YAMLError

from ailearn.cli import main
from ailearn.data import Dataset, Registry, Requirements
from ailearn.engine import mastered, next_action, record, roadmap
from ailearn.graph import Graph, load_domains
from ailearn.models import Config, Dimension, Evidence, Snapshot, Stage, active_evidence, now
from ailearn.sensors import baseline, finite, numeric, run, split
from ailearn.store import Store


@pytest.fixture
def state():
    return Snapshot(config=Config(domain="time-series", depth="minimal"), domains=load_domains())


def evidence(key="statistics.mean", dimension=Dimension.CONCEPTUAL, attempt="one", **kw):
    return Evidence(
        id=f"{key}-{dimension}-{attempt}",
        attempt_id=f"{key}-{attempt}",
        competency=key,
        dimension=dimension,
        score=3,
        independent=True,
        confidence=0.9,
        assessor="independent-harness",
        artifact="answer.txt",
        **kw,
    )


def demonstrate(state, key, at=None):
    for dimension in [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]:
        for attempt in ["a", "b"]:
            e = evidence(key, dimension, attempt, timestamp=at or now())
            record(state, e, at)


def test_packs_and_cross_domain_closure(state):
    graph = Graph(state.domains)
    path = graph.closure(["time_series.autocorrelation"])
    assert path.index("statistics.covariance") < path.index("time_series.autocorrelation")
    assert len(load_domains()) == 3
    assert "machine_learning.validation" in roadmap(state)


def test_missing_cycle_duplicate_rejected(state):
    broken = state.model_copy(deep=True)
    broken.domains[0].competencies[0].prerequisites = ["unknown.x"]
    with pytest.raises(ValueError, match="missing prerequisite"):
        Graph(broken.domains)
    broken.domains[0].competencies[0].prerequisites = [broken.domains[0].competencies[0].id]
    with pytest.raises(ValueError, match="cycle"):
        Graph(broken.domains)
    with pytest.raises(ValueError, match="duplicate"):
        Graph(state.domains + [state.domains[0]])


def test_explanation_hints_and_one_attempt_do_not_master(state):
    record(state, evidence(kind="explanation"))
    assert state.knowledge["statistics.mean"].stage == Stage.EXPOSED
    assert not mastered(state, "statistics.mean")
    e = evidence(attempt="hinted")
    e.hints = 1
    record(state, e)
    record(state, evidence(attempt="independent"))
    assert not mastered(state, "statistics.mean")


def test_mastery_regression_misconceptions(state):
    demonstrate(state, "statistics.mean")
    assert mastered(state, "statistics.mean")
    e = evidence(attempt="failed", misconceptions=["mean equals median"])
    e.score = 1
    record(state, e)
    assert not mastered(state, "statistics.mean")
    assert next_action(state)["scope"] == "remediate"
    for attempt in ["repair-a", "repair-b"]:
        record(state, evidence(attempt=attempt, resolves=["mean equals median"]))
    assert mastered(state, "statistics.mean")


def test_next_target_changes_and_due_review_wins(state):
    assert next_action(state)["scope"] == "assessment"
    demonstrate(state, "statistics.mean")
    assert next_action(state)["competency"] == "statistics.variance"
    due = state.knowledge["statistics.mean"].review_due
    assert next_action(state, at=due)["scope"] == "review"


def test_retention_delay_and_intervals(state):
    demonstrate(state, "statistics.mean")
    e = evidence(dimension=Dimension.RETENTION, kind="delayed-retrieval")
    with pytest.raises(ValueError, match="scheduled review"):
        record(state, e)
    due = state.knowledge["statistics.mean"].review_due
    e.timestamp = due
    record(state, e, at=due)
    assert state.knowledge["statistics.mean"].review_due == due + timedelta(days=3)
    assert state.knowledge["statistics.mean"].stage != Stage.RETAINED
    exposure_at = due + timedelta(seconds=1)
    record(
        state,
        evidence(attempt="explanation", kind="explanation", timestamp=exposure_at),
        at=exposure_at,
    )
    assert state.knowledge["statistics.mean"].review_step == 1
    due2 = state.knowledge["statistics.mean"].review_due
    failed = evidence(
        dimension=Dimension.RETENTION, attempt="failed", kind="delayed-retrieval", timestamp=due2
    )
    failed.score = 0
    record(state, failed, at=due2)
    assert state.knowledge["statistics.mean"].review_due == due2 + timedelta(days=1)
    assert not mastered(state, "statistics.mean")
    assert state.knowledge["statistics.mean"].stage == Stage.PRACTICED
    assert next_action(state, at=due2)["scope"] == "remediate"
    corrected = evidence(
        dimension=Dimension.RETENTION,
        attempt="failed",
        kind="delayed-retrieval",
    )
    corrected.id = "corrected-review"
    corrected.timestamp = failed.timestamp + timedelta(seconds=1)
    record(state, corrected, at=corrected.timestamp, replace_id=failed.id)
    assert mastered(state, "statistics.mean")
    step = state.knowledge["statistics.mean"].review_step
    corrected_again = evidence(
        dimension=Dimension.RETENTION,
        attempt="failed",
        kind="delayed-retrieval",
    )
    corrected_again.id = "corrected-review-again"
    corrected_again.timestamp = corrected.timestamp + timedelta(seconds=1)
    record(
        state,
        corrected_again,
        at=corrected_again.timestamp,
        replace_id=corrected.id,
    )
    assert state.knowledge["statistics.mean"].review_step == step


def test_replacement_cannot_change_evidence_kind(state):
    original = evidence(attempt="a")
    record(state, original)
    changed_kind = evidence(attempt="a", kind="explanation")
    changed_kind.id = "changed-kind"
    with pytest.raises(ValueError, match="same evidence kind"):
        record(state, changed_kind, replace_id=original.id)


def test_review_streak_restarts_after_core_failure_and_repair(state):
    start = now() - timedelta(days=100)
    demonstrate(state, "statistics.mean", at=start)
    due = state.knowledge["statistics.mean"].review_due
    for attempt in ["review-a", "review-b"]:
        review = evidence(
            dimension=Dimension.RETENTION,
            attempt=attempt,
            kind="delayed-retrieval",
            timestamp=due,
        )
        record(state, review, at=due)
        due = state.knowledge["statistics.mean"].review_due
    assert state.knowledge["statistics.mean"].review_step == 2
    failed_at = due + timedelta(seconds=1)
    failure = evidence(attempt="regression", timestamp=failed_at)
    failure.score = 0
    record(state, failure, at=failed_at)
    for index in [1, 2]:
        repaired_at = failed_at + timedelta(seconds=index + 1)
        record(
            state,
            evidence(attempt=f"repair-{index}", timestamp=repaired_at),
            at=repaired_at,
        )
    assert mastered(state, "statistics.mean")
    next_review = state.knowledge["statistics.mean"].review_due
    retrieval = evidence(
        dimension=Dimension.RETENTION,
        attempt="review-after-repair",
        kind="delayed-retrieval",
        timestamp=next_review,
    )
    record(state, retrieval, at=next_review)
    assert state.knowledge["statistics.mean"].review_step == 1


def test_duplicate_future_and_sensor_failure(state):
    e = evidence()
    record(state, e)
    with pytest.raises(ValueError, match="duplicate"):
        record(state, e)
    with pytest.raises(ValueError, match="future"):
        record(state, evidence(attempt="future", timestamp=now() + timedelta(days=1)))
    failed = evidence(attempt="sensor")
    failed.sensors = [numeric(1, 2)]
    record(state, failed)
    assert next_action(state)["scope"] == "remediate"


def test_safe_init_persistence_lock_and_corruption(tmp_path, state):
    instructions = tmp_path / "AGENTS.md"
    instructions.write_text("Existing instructions", encoding="utf-8")
    store = Store(tmp_path)
    assert store.init(state.config, state.domains)
    assert not store.init(state.config, state.domains)
    assert instructions.read_text("utf-8") == "Existing instructions"
    with pytest.raises(ValueError, match="different configuration"):
        store.init(Config(domain="statistics"), state.domains)
    with store.transaction() as saved:
        record(saved, evidence())
    assert len(store.load().evidence) == 1
    before = (store.root / "state.json").read_bytes()
    with pytest.raises(RuntimeError), store.transaction() as saved:
        saved.history.append({"bad": True})
        raise RuntimeError("abort")
    assert (store.root / "state.json").read_bytes() == before
    (store.root / "write.lock").write_text("other writer")
    with pytest.raises(ValueError, match="workspace is locked"), store.transaction():
        pass
    (store.root / "write.lock").unlink()
    (store.root / "state.json").write_text("corrupt")
    with pytest.raises(ValueError):
        store.load()


def test_cli_workflow(tmp_path, capsys):
    prefix = ["--workspace", str(tmp_path)]
    Store(tmp_path).init(Config(domain="time-series", depth="minimal"), load_domains())
    assert main(prefix + ["init"]) == 0
    assert main(prefix + ["init"]) == 0
    for command in ["status", "plan", "session", "history", "doctor", "export", "domains"]:
        assert main(prefix + [command]) == 0
    efile = tmp_path / "result.json"
    efile.write_text(evidence().model_dump_json(), "utf-8")
    assert main(prefix + ["record", str(efile)]) == 0
    assert main(prefix + ["doctor"]) == 0
    assert main(prefix + ["record", str(efile)]) == 2
    assert "duplicate" in capsys.readouterr().err


def test_explore_no_mastery(tmp_path):
    prefix = ["--workspace", str(tmp_path)]
    Store(tmp_path).init(Config(domain="statistics"), load_domains())
    main(prefix + ["session", "--scope", "explore"])
    artifact = tmp_path / "e.json"
    artifact.write_text(evidence().model_dump_json(), "utf-8")
    assert main(prefix + ["record", str(artifact)]) == 2
    exposure = tmp_path / "exposure.json"
    exposure.write_text(evidence(attempt="exposure", kind="explanation").model_dump_json(), "utf-8")
    assert main(prefix + ["record", str(exposure)]) == 0
    assert main(prefix + ["record", str(artifact)]) == 2
    assert main(prefix + ["session", "--scope", "assessment"]) == 0
    artifact.write_text(evidence().model_dump_json(), "utf-8")
    assert main(prefix + ["record", str(artifact)]) == 0


def test_doctor_detects_tampering(tmp_path, state):
    store = Store(tmp_path)
    store.init(state.config, state.domains)
    with store.transaction() as saved:
        record(saved, evidence())
    value = json.loads((store.root / "state.json").read_text("utf-8"))
    value["knowledge"]["statistics.mean"]["stage"] = "RETAINED"
    (store.root / "state.json").write_text(json.dumps(value), "utf-8")
    assert main(["--workspace", str(tmp_path), "doctor"]) == 2


def test_sensors():
    assert numeric(0.1 + 0.2, 0.3).passed
    assert not numeric(float("nan"), 0).passed
    assert not finite([1, float("nan")]).passed
    assert not split([1, 2], [2, 3]).passed
    assert not split([3], [2], temporal=True).passed
    assert baseline(0.1, 0.2).passed
    assert run({"shape": {"actual": [2, 3], "expected": [2, 3]}})[0].passed
    with pytest.raises(ValueError):
        run({"execute": {}})


def test_dataset_provider():
    dataset = Dataset(
        id="synthetic",
        source="local simulation",
        url="https://example.org/data",
        variables={"x": "index"},
        units={"x": "dimensionless"},
        frequency="daily",
        temporal_coverage="100 days",
        geographic_coverage="none",
        caveats=["Not real observations"],
        synthetic=True,
    )

    class LocalProvider:
        def discover(self, requirements):
            return [dataset]

    registry = Registry()
    registry.register("local", LocalProvider())
    result = registry.discover(
        "local", Requirements(domain="simulation", frequency="daily", min_observations=100)
    )
    assert result[0].synthetic
    with pytest.raises(ValueError):
        registry.register("local", LocalProvider())


def test_dimension_kind_contract_and_advanced_gates(state):
    with pytest.raises(ValueError, match="retention dimension"):
        evidence(kind="delayed-retrieval")
    with pytest.raises(ValueError, match="transfer dimension"):
        evidence(kind="transfer")
    with pytest.raises(ValueError, match="core mastery"):
        record(state, evidence(dimension=Dimension.TRANSFER, kind="transfer"))
    with pytest.raises(ValueError, match="core mastery"):
        record(state, evidence(dimension=Dimension.RETENTION, kind="delayed-retrieval"))
    assert not state.knowledge  # Rejected submissions leave no partial learner state.


def test_transfer_retained_and_regression_recovery(state):
    demonstrate(state, "statistics.mean")
    for attempt in ["transfer-a", "transfer-b"]:
        record(state, evidence(dimension=Dimension.TRANSFER, attempt=attempt, kind="transfer"))
    assert state.knowledge["statistics.mean"].stage == Stage.TRANSFERABLE
    for attempt in ["review-a", "review-b"]:
        due = state.knowledge["statistics.mean"].review_due
        record(
            state,
            evidence(
                dimension=Dimension.RETENTION,
                attempt=attempt,
                kind="delayed-retrieval",
                timestamp=due,
            ),
            at=due,
        )
    assert state.knowledge["statistics.mean"].stage == Stage.RETAINED
    due = state.knowledge["statistics.mean"].review_due
    failure = evidence(
        dimension=Dimension.RETENTION, attempt="forgotten", kind="delayed-retrieval", timestamp=due
    )
    failure.score = 1
    record(state, failure, at=due)
    assert not mastered(state, "statistics.mean")
    for dimension in [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]:
        for attempt in ["relearn-a", "relearn-b"]:
            record(state, evidence(dimension=dimension, attempt=attempt, timestamp=due), at=due)
    assert mastered(state, "statistics.mean")
    # Forgetting invalidates old transfer and retention evidence, too.
    assert state.knowledge["statistics.mean"].stage == Stage.DEMONSTRATED
    assert state.knowledge["statistics.mean"].review_due == due + timedelta(days=1)


def test_explicit_scopes_and_due_priority(state):
    assert next_action(state, scope="review")["action"] == "wait-for-review"
    assert next_action(state, scope="project")["scope"] == "assessment"
    for scope in ["learn", "deep-learn", "remediate", "practice", "assessment", "explore"]:
        brief = next_action(state, scope=scope)
        assert brief["scope"] == scope
        assert brief["competency"] == "statistics.mean"
        assert ("assessor" in brief["roles"]) == (scope in {"practice", "assessment"})
    for scope in ["learn", "deep-learn", "remediate", "explore"]:
        assert next_action(state, scope=scope)["assessment_checkpoint"] == "formative"
    for scope in ["practice", "assessment"]:
        assert next_action(state, scope=scope)["assessment_checkpoint"] == "formal"
    demonstrate(state, "statistics.mean")
    due = state.knowledge["statistics.mean"].review_due
    assert next_action(state, scope="learn", at=due)["scope"] == "review"
    review = next_action(state, scope="learn", at=due)
    assert review["assessment_checkpoint"] == "formal"
    assert "assessor" in review["roles"]
    project = next_action(state, scope="project")
    assert project["assessment_checkpoint"] == "formal"
    assert "assessor" in project["roles"]


def test_uninitialized_and_invalid_custom_packs(tmp_path):
    store = Store(tmp_path)
    with pytest.raises(ValueError, match="ailearn init"):
        store.load()
    with pytest.raises(ValueError, match="ailearn init"), store.transaction():
        pass
    with pytest.raises(ValueError, match="no .yml"):
        load_domains(tmp_path)
    (tmp_path / "broken.yml").write_text("not: [valid", "utf-8")
    with pytest.raises(YAMLError):
        load_domains(tmp_path)


def test_cli_sensor_record_and_portable_export(tmp_path, capsys):
    prefix = ["--workspace", str(tmp_path)]
    Store(tmp_path).init(Config(domain="statistics"), load_domains())
    efile = tmp_path / "result.json"
    efile.write_text(evidence().model_dump_json(), "utf-8")
    sensor = tmp_path / "sensors.json"
    sensor.write_text(json.dumps({"numeric": {"actual": 1, "expected": 2}}), "utf-8")
    assert main(prefix + ["record", str(efile), "--sensors", str(sensor)]) == 0
    assert not Store(tmp_path).load().evidence[0].sensors[0].passed
    capsys.readouterr()
    assert main(prefix + ["export"]) == 0
    portable = Snapshot.model_validate_json(capsys.readouterr().out)
    assert len(portable.domains) == 3
    assert main(prefix + ["sensors", str(sensor)]) == 1


def test_duplicate_attempt_cannot_recover_after_failure(state):
    demonstrate(state, "statistics.mean")
    failed = evidence(attempt="failed")
    failed.score = 0
    record(state, failed)
    repeated = evidence(attempt="a")
    repeated.id = "new-id-same-attempt"
    with pytest.raises(ValueError, match="--replace"):
        record(state, repeated)
    for attempt in ["fresh-one", "fresh-two"]:
        record(state, evidence(attempt=attempt))
    assert mastered(state, "statistics.mean")
    corrected_failure = evidence(attempt="failed")
    corrected_failure.id = "corrected-failed-assessment"
    corrected_failure.score = 0
    record(state, corrected_failure, replace_id=failed.id)
    assert not mastered(state, "statistics.mean")


def test_assessment_can_be_audited_and_revised_for_same_attempt(state):
    original = evidence(attempt="a")
    original.score = 1
    record(state, original)
    corrected = evidence(attempt="a")
    corrected.id = "corrected-assessment"
    record(state, corrected, replace_id=original.id)
    assert [item.id for item in state.evidence] == [original.id, corrected.id]
    assert [item.id for item in active_evidence(state)] == [corrected.id]
    assert state.evidence[1].supersedes_id == original.id
    assert state.history[-2]["event"] == "evidence-revised"
    assert not mastered(state, "statistics.mean")
    record(state, evidence(attempt="b", dimension=Dimension.INTERPRETATION))
    assert not mastered(state, "statistics.mean")


def test_replacement_removes_superseded_misconception(state):
    demonstrate(state, "statistics.mean")
    failed = evidence(attempt="misconception", misconceptions=["mean-is-median"])
    failed.score = 1
    record(state, failed)
    corrected = evidence(attempt="misconception")
    corrected.id = "corrected-misconception"
    record(state, corrected, replace_id=failed.id)
    assert "mean-is-median" not in state.knowledge["statistics.mean"].misconceptions
    assert mastered(state, "statistics.mean")


def test_replacement_requires_current_matching_assessment(state):
    original = evidence(attempt="a")
    record(state, original)
    with pytest.raises(ValueError, match="same attempt and dimension"):
        record(state, evidence(attempt="b"), replace_id=original.id)
    revised = evidence(attempt="a")
    revised.id = "revision-one"
    record(state, revised, replace_id=original.id)
    again = evidence(attempt="a")
    again.id = "revision-two"
    with pytest.raises(ValueError, match="active evidence"):
        record(state, again, replace_id=original.id)


def test_mutated_contract_revalidated(state):
    e = evidence()
    e.score = 99
    with pytest.raises(ValueError):
        record(state, e)
    assert not state.evidence


def test_doctor_replays_historical_reviews(tmp_path, state):
    store = Store(tmp_path)
    store.init(state.config, state.domains)
    start = now() - timedelta(days=100)
    with store.transaction() as saved:
        demonstrate(saved, "statistics.mean", at=start)
        due = saved.knowledge["statistics.mean"].review_due
        record(
            saved,
            evidence(dimension=Dimension.RETENTION, kind="delayed-retrieval", timestamp=due),
            at=due,
        )
    assert main(["--workspace", str(tmp_path), "doctor"]) == 0


def test_doctor_replays_assessment_revisions(tmp_path, state):
    store = Store(tmp_path)
    store.init(state.config, state.domains)
    original = evidence(attempt="a")
    corrected = evidence(attempt="a")
    corrected.id = "corrected"
    corrected.score = 4
    corrected.timestamp = original.timestamp + timedelta(seconds=1)
    with store.transaction() as saved:
        record(saved, original)
        record(saved, corrected, replace_id=original.id)
    assert main(["--workspace", str(tmp_path), "doctor"]) == 0


def test_every_domain_outcome_required(state):
    broken = state.model_copy(deep=True)
    del broken.domains[0].competencies[0].outcomes[Dimension.RETENTION]
    with pytest.raises(ValueError, match="missing dimension outcomes"):
        Graph(broken.domains)
