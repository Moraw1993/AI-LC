"""Mastery gates, review scheduling and next-action routing."""

from datetime import datetime, timedelta

from ailearn.graph import Graph, required
from ailearn.models import (
    Dimension,
    Evidence,
    Knowledge,
    Scope,
    Snapshot,
    Stage,
    active_evidence,
    now,
)
from ailearn.onboarding import diagnostic_brief

INTERVALS = (1, 3, 7, 14, 30, 60)
NON_EVIDENCE = {"explanation", "self-report"}


def qualifies(e: Evidence, threshold: int) -> bool:
    return (
        e.kind not in NON_EVIDENCE
        and e.independent
        and e.hints == 0
        and e.confidence >= 0.8
        and e.score >= threshold
        and all(s.passed for s in e.sensors)
    )


def passed(state: Snapshot, key: str, dimension: Dimension) -> bool:
    threshold = Graph(state.domains).nodes[key].threshold
    attempts: set[str] = set()
    for e in active_evidence(state):
        if e.competency != key or e.kind in NON_EVIDENCE:
            continue
        # A failed delayed retrieval demonstrates forgetting, not merely a missing
        # administrative retention score. Re-establish the competency's evidence.
        if e.kind == "delayed-retrieval" and e.independent and not qualifies(e, threshold):
            attempts.clear()
        if e.dimension != dimension:
            continue
        if qualifies(e, threshold):
            attempts.add(e.attempt_id)
        elif e.independent:
            attempts.clear()
    return len(attempts) >= 2


def mastered(state: Snapshot, key: str) -> bool:
    knowledge = state.knowledge.get(key, Knowledge())
    return not knowledge.misconceptions and all(
        passed(state, key, d) for d in required(state.config.depth)
    )


def _review_progress(state: Snapshot, key: str, threshold: int) -> tuple[int, datetime | None]:
    """Rebuild review streak from current evidence and mastery reset boundaries."""
    prefix = Snapshot(config=state.config, domains=state.domains)
    prefix.knowledge[key] = Knowledge()
    review_step = 0
    last_review = None
    for evidence in active_evidence(state):
        if evidence.competency != key:
            continue
        was_mastered = mastered(prefix, key)
        prefix.evidence.append(evidence.model_copy(update={"supersedes_id": None}))
        if evidence.kind not in NON_EVIDENCE:
            misconceptions: set[str] = set()
            for item in prefix.evidence:
                if item.competency != key or item.kind in NON_EVIDENCE:
                    continue
                misconceptions.update(item.misconceptions)
                if qualifies(item, threshold):
                    misconceptions.difference_update(item.resolves)
            prefix.knowledge[key].misconceptions = sorted(misconceptions)
        is_mastered = mastered(prefix, key)
        good = qualifies(evidence, threshold)
        if evidence.kind == "delayed-retrieval":
            review_step = min(review_step + 1, len(INTERVALS) - 1) if good else 0
            last_review = evidence.timestamp
        elif (
            evidence.kind not in NON_EVIDENCE
            and evidence.independent
            and not good
            and last_review is not None
        ):
            review_step = 0
        elif good and is_mastered and not was_mastered:
            review_step = 0
    return review_step, last_review


def record(
    state: Snapshot,
    evidence: Evidence,
    at: datetime | None = None,
    replace_id: str | None = None,
) -> None:
    # Public API callers may have mutated a model after construction.
    evidence = Evidence.model_validate(evidence.model_dump())
    if evidence.supersedes_id is not None:
        if replace_id is None or evidence.supersedes_id != replace_id:
            raise ValueError("use --replace to explicitly replace an existing assessment")
    elif replace_id is not None:
        evidence.supersedes_id = replace_id
    at = at or now()
    graph = Graph(state.domains)
    if evidence.competency not in graph.nodes:
        raise ValueError(f"unknown competency: {evidence.competency}")
    if state.session.get("scope") == "explore" and evidence.kind not in NON_EVIDENCE:
        raise ValueError("explore session cannot grant mastery; start an assessment")
    if state.intake is not None:
        if state.intake.baseline is None and evidence.kind not in NON_EVIDENCE | {"diagnostic"}:
            raise ValueError("complete the baseline diagnosis before learning assessments")
        if evidence.dimension == Dimension.IMPLEMENTATION and evidence.kind not in NON_EVIDENCE:
            task = next((task for task in state.exercises if task.path == evidence.artifact), None)
            if (
                task is None
                or task.competency != evidence.competency
                or task.id != evidence.attempt_id
                or task.kind != evidence.kind
            ):
                raise ValueError("implementation evidence must reference its numbered exercise")
    if evidence.timestamp > at + timedelta(seconds=5):
        raise ValueError("future evidence is not allowed")
    if state.evidence and evidence.timestamp < state.evidence[-1].timestamp:
        raise ValueError("evidence must be recorded in chronological order")
    if any(e.id == evidence.id for e in state.evidence):
        raise ValueError(f"duplicate evidence ID: {evidence.id}")
    previous = next((e for e in state.evidence if e.id == replace_id), None)
    if (
        replace_id is not None
        and state.intake
        and state.intake.baseline
        and replace_id in state.intake.baseline.evidence_ids
    ):
        raise ValueError("cannot replace evidence used by the completed baseline")
    duplicate = next(
        (
            e
            for e in active_evidence(state)
            if e.attempt_id == evidence.attempt_id and e.dimension == evidence.dimension
        ),
        None,
    )
    if replace_id is None and duplicate is not None:
        raise ValueError(
            f"duplicate attempt/dimension; use --replace {duplicate.id} to correct this assessment"
        )
    if replace_id is not None:
        if previous is None or duplicate is None or duplicate.id != replace_id:
            raise ValueError(
                "--replace must identify the active evidence for the same attempt and dimension"
            )
        if (previous.attempt_id, previous.dimension, previous.competency) != (
            evidence.attempt_id,
            evidence.dimension,
            evidence.competency,
        ):
            raise ValueError("replacement must keep the same attempt, dimension and competency")
        if previous.kind != evidence.kind:
            raise ValueError("replacement must keep the same evidence kind")
    key = evidence.competency
    k = state.knowledge.get(key, Knowledge())
    threshold = graph.nodes[key].threshold
    good = qualifies(evidence, threshold)
    was_mastered = mastered(state, key)
    if (
        replace_id is None
        and evidence.dimension in {Dimension.TRANSFER, Dimension.RETENTION}
        and not was_mastered
    ):
        raise ValueError("transfer and retention require demonstrated core mastery first")
    if replace_id is None and evidence.kind == "delayed-retrieval":
        if k.review_due is None or evidence.timestamp < k.review_due:
            raise ValueError("retention is only valid when a scheduled review is due")
    state.knowledge[key] = k
    state.evidence.append(evidence)
    if replace_id is not None:
        state.history.append(
            {
                "event": "evidence-revised",
                "id": evidence.id,
                "supersedes_id": replace_id,
                "attempt_id": evidence.attempt_id,
                "dimension": evidence.dimension.value,
                "timestamp": evidence.timestamp.isoformat(),
            }
        )
    if evidence.kind in NON_EVIDENCE:
        if k.stage == Stage.UNSEEN:
            k.stage = Stage.EXPOSED
    else:
        k.levels[evidence.dimension] = evidence.score
        active_misconceptions: set[str] = set()
        for item in active_evidence(state):
            if item.competency != key or item.kind in NON_EVIDENCE:
                continue
            active_misconceptions.update(item.misconceptions)
            if qualifies(item, threshold):
                active_misconceptions.difference_update(item.resolves)
        k.misconceptions = sorted(active_misconceptions)
        if mastered(state, key):
            k.stage = Stage.DEMONSTRATED
            if passed(state, key, Dimension.TRANSFER):
                k.stage = Stage.TRANSFERABLE
                if passed(state, key, Dimension.RETENTION):
                    k.stage = Stage.RETAINED
        else:
            k.stage = Stage.PRACTICED if evidence.independent else Stage.GUIDED
        if evidence.kind == "delayed-retrieval":
            review_step, last_review = _review_progress(state, key, threshold)
            k.review_step = review_step
            k.last_review = last_review
            k.review_due = last_review + timedelta(days=INTERVALS[review_step])
        elif good and mastered(state, key) and not was_mastered:
            k.review_step = 0
            k.review_due = evidence.timestamp + timedelta(days=1)
        elif evidence.independent and not good and k.review_due is not None:
            k.review_step = 0
            k.review_due = evidence.timestamp + timedelta(days=1)
    state.history.append(
        {
            "event": "evidence",
            "id": evidence.id,
            "competency": key,
            "stage": k.stage.value,
            "timestamp": evidence.timestamp.isoformat(),
        }
    )
    # Recompute the plan after every assessment, rather than maintaining a fixed sequence.
    if state.session.get("scope") != "explore":
        state.session = {}


def roadmap(state: Snapshot) -> list[str]:
    if state.intake is not None and state.intake.baseline is None:
        raise ValueError("complete the learner baseline before designing a roadmap")
    graph = Graph(state.domains)
    return graph.closure(graph.domains[state.config.domain].targets[state.config.target])


def next_action(state: Snapshot, scope: Scope | None = None, at: datetime | None = None) -> dict:
    diagnostic = diagnostic_brief(state)
    if diagnostic is not None:
        return diagnostic
    at = at or now()
    scope = Scope(scope) if scope is not None else None
    graph = Graph(state.domains)
    path = roadmap(state)
    due = [
        key
        for key in path
        if state.knowledge.get(key, Knowledge()).review_due
        and state.knowledge[key].review_due <= at
        and mastered(state, key)
    ]
    if scope == Scope.REVIEW and not due:
        return {
            "phase": "consolidation",
            "action": "wait-for-review",
            "scope": "review",
            "reason": "No delayed retrieval is due yet.",
        }
    if due:
        key = min(due, key=lambda key: state.knowledge[key].review_due)
        selected = Scope.REVIEW
        dimension = Dimension.RETENTION
        reason = "Scheduled delayed retrieval is due. Use a new representation."
    else:
        key = next((key for key in path if not mastered(state, key)), None)
        if key is None:
            key = next((key for key in path if not passed(state, key, Dimension.TRANSFER)), None)
            if key is None:
                return {
                    "phase": "consolidation",
                    "action": "wait-for-review",
                    "reason": "Core and transfer gates passed; retain through delayed retrieval.",
                }
            selected, dimension = Scope.PROJECT, Dimension.TRANSFER
            reason = "Demonstrate transfer on an unseen problem or dataset."
        else:
            k = state.knowledge.get(key, Knowledge())
            dimension = next(
                (d for d in required(state.config.depth) if not passed(state, key, d)),
                Dimension.CONCEPTUAL,
            )
            attempts = [
                e
                for e in active_evidence(state)
                if e.competency == key
                and e.kind not in NON_EVIDENCE
                and (
                    e.dimension == dimension
                    or (
                        e.kind == "delayed-retrieval"
                        and e.independent
                        and not qualifies(e, graph.nodes[key].threshold)
                    )
                )
            ]
            if k.misconceptions or (
                attempts
                and attempts[-1].independent
                and not qualifies(attempts[-1], graph.nodes[key].threshold)
            ):
                selected = Scope.REMEDIATE
                reason = "Repair weak evidence or active misconceptions before progression."
            elif not attempts:
                selected = Scope.ASSESSMENT
                reason = "Knowledge is uncertain: run a small independent diagnostic first."
            else:
                selected = Scope.PRACTICE
                reason = "Collect distinct independent evidence for the missing dimension."
    # Reviews stay first even when the caller requests new learning.
    selected = selected if due else scope or selected
    if selected == Scope.PROJECT and not mastered(state, key):
        selected = Scope.ASSESSMENT
        reason = "Project transfer requires core mastery; diagnose the prerequisite first."
    elif selected == Scope.PROJECT:
        dimension = Dimension.TRANSFER
    node = graph.nodes[key]
    roles = {
        Scope.ASSESSMENT: ["assessor"],
        Scope.REVIEW: ["assessor"],
        Scope.PRACTICE: ["lab-coach", "assessor"],
        Scope.PROJECT: ["research-data", "lab-coach", "assessor"],
        Scope.EXPLORE: ["teacher", "research-data"],
    }
    return {
        "phase": "consolidation"
        if selected == Scope.REVIEW
        else "application"
        if selected == Scope.PROJECT
        else "discovery"
        if selected == Scope.ASSESSMENT
        else "learning",
        "competency": key,
        "dimension": dimension.value,
        "scope": selected.value,
        "roles": roles.get(selected, ["teacher", "lab-coach", "assessor"]),
        "reason": reason,
        "outcomes": node.outcomes.get(dimension, []),
        "misconceptions": state.knowledge.get(key, Knowledge()).misconceptions,
        "assessment_strategies": node.assessment_strategies,
        "prerequisites": node.prerequisites,
        "depth": state.config.depth,
        "preferences": state.config.preferences,
        "teaching_skills": [
            "ai-lc-materials",
            "ai-lc-visualize",
            "ai-lc-motion",
            "ai-lc-diagnose",
            "ai-lc-python-lab",
        ],
        "difficulty": max(1, state.knowledge.get(key, Knowledge()).levels.get(dimension, 0)),
        "recent_evidence": [
            e.model_dump(mode="json") for e in active_evidence(state) if e.competency == key
        ][-6:],
        "instructions": "Generate a fresh task just in time. Learner attempts first. "
        "Assessor uses the response, rubric and sensors, not Teacher encouragement. "
        "Record explanation/self-report as non-mastery evidence; explore grants no mastery.",
    }
