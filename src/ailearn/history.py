"""Versioned append-only audit events with backward-compatible legacy reads."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from ailearn.models import AuditEvent, PlanPhase, Snapshot, active_evidence, now


def append_history(
    state: Snapshot,
    event: str,
    *,
    timestamp: datetime | None = None,
    **fields: Any,
) -> str:
    """Append one validated v1 event and return its stable reference ID."""
    reserved = {"audit_schema_version", "event_id", "event", "timestamp"}
    if reserved & fields.keys():
        raise ValueError("audit event fields cannot override the versioned envelope")
    if "evidence_refs" in fields:
        fields["evidence_refs"] = sorted(set(fields["evidence_refs"]))
    data = {
        "audit_schema_version": 1,
        "event_id": uuid4().hex,
        "event": event,
        "timestamp": timestamp or now(),
        **fields,
    }
    parsed = AuditEvent.model_validate(data)
    state.history.append(parsed.model_dump(mode="json", exclude_none=True))
    return parsed.event_id


def current_plan(state: Snapshot):
    return state.plans[-1] if state.plans else None


def audit_context(state: Snapshot) -> dict[str, Any]:
    """Return version references without copying learner profile text into history."""
    plan = current_plan(state)
    context: dict[str, Any] = {}
    if state.intake is not None:
        context["profile_version"] = state.intake.profile.schema_version
    if plan is not None:
        context["plan_version"] = plan.version
        context["learning_path_profile"] = plan.learning_path_profile.model_dump(mode="json")
        context["plan_phase"] = plan.phase.value
    return context


def validate_history(history: list[dict]) -> None:
    """Validate new event envelopes while leaving historical unversioned records untouched."""
    seen: set[str] = set()
    for raw in history:
        if "audit_schema_version" not in raw and "event_id" not in raw:
            continue
        event = AuditEvent.model_validate(raw)
        if event.event_id in seen:
            raise ValueError(f"duplicate audit event ID: {event.event_id}")
        seen.add(event.event_id)


def route_evidence_refs(state: Snapshot, brief: dict) -> list[str]:
    """Return evidence IDs that informed this route, never copies of learner responses."""
    refs = {
        item["id"]
        for item in brief.get("recent_evidence", [])
        if isinstance(item, dict) and item.get("id")
    }
    if brief.get("action") in {"diagnostic", "complete-intake"}:
        refs.update(
            evidence.id
            for evidence in active_evidence(state)
            if evidence.kind == "diagnostic"
            and evidence.competency
            in (state.intake.profile.diagnostic_competencies if state.intake else [])
        )
    if brief.get("plan_phase") == PlanPhase.ADAPTIVE.value and state.intake:
        if state.intake.baseline:
            refs.update(state.intake.baseline.evidence_ids)
    return sorted(refs)
