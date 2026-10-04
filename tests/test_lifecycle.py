import json
from datetime import timedelta

import pytest
from yaml import YAMLError

from ailearn.cli import main
from ailearn.data import Dataset, Registry, Requirements
from ailearn.engine import mastered, next_action, record, roadmap
from ailearn.graph import Graph, load_domains
from ailearn.models import Config, Dimension, Evidence, Snapshot, Stage, now
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
    demonstrate(state, "statistics.mean")
    due = state.knowledge["statistics.mean"].review_due
    assert next_action(state, scope="learn", at=due)["scope"] == "review"


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
    with pytest.raises(ValueError, match="duplicate"):
        record(state, repeated)
    record(state, evidence(attempt="fresh-one"))
    assert not mastered(state, "statistics.mean")
    record(state, evidence(attempt="fresh-two"))
    assert mastered(state, "statistics.mean")


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


def test_every_domain_outcome_required(state):
    broken = state.model_copy(deep=True)
    del broken.domains[0].competencies[0].outcomes[Dimension.RETENTION]
    with pytest.raises(ValueError, match="missing dimension outcomes"):
        Graph(broken.domains)
