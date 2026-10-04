"""Conversation-first onboarding and diagnostic readiness, without an LLM client."""

from ailearn.graph import Graph
from ailearn.models import Baseline, Snapshot, active_evidence, now


def onboarding_brief() -> dict:
    return {
        "phase": "intent-discovery",
        "roles": ["master"],
        "skill": "ai-lc-master",
        "action": "conversation",
        "instructions": "Ask what the learner wants to learn and why. Establish the target "
        "ability, prior experience, language, working style, tutor name and workspace name. "
        "Do not select a default topic or build a roadmap. Save explicit decisions in a "
        "LearningProfile and use ailearn configure profile.json. "
        "Then diagnose knowledge "
        "needed for the first lesson before completing intake.",
    }


def diagnostic_brief(state: Snapshot) -> dict | None:
    if state.intake is None or state.intake.baseline is not None:
        return None
    profile = state.intake.profile
    covered = {e.competency for e in active_evidence(state) if diagnostic_result(e)}
    missing = [key for key in profile.diagnostic_competencies if key not in covered]
    key = missing[0] if missing else profile.diagnostic_competencies[-1]
    node = Graph(state.domains).nodes[key]
    return {
        "phase": "discovery",
        "scope": "assessment",
        "competency": key,
        "dimension": "conceptual",
        "roles": ["teacher", "assessor"],
        "assessment_checkpoint": "formal",
        "agent_name": profile.agent_name,
        "language": profile.language,
        "action": "diagnostic" if missing else "complete-intake",
        "missing_diagnostics": missing,
        "outcomes": node.outcomes,
        "prior_knowledge": profile.prior_knowledge,
        "instructions": "Teacher gathers prior experience and asks short baseline questions. "
        "These are a formal diagnostic checkpoint: gather each response without coaching, "
        "then use the independent Assessor to evaluate it as diagnostic evidence. 'I do "
        "not know' can be a genuine failed diagnostic. Do not teach during the independent "
        "attempt or invent results. Record the baseline with "
        "ailearn complete-intake "
        "report.json before planning lessons. If coaching is requested, label the switch "
        "and collect a fresh independent diagnostic afterwards.",
    }


def diagnostic_result(e) -> bool:
    return e.kind == "diagnostic" and e.independent and e.hints == 0 and e.confidence >= 0.8


def complete_intake(state: Snapshot, baseline: Baseline) -> None:
    if state.intake is None:
        raise ValueError("this legacy workspace has no Master intake profile")
    if state.intake.baseline is not None:
        if state.intake.baseline == baseline:
            return
        raise ValueError("baseline already completed; preserve it and recompose through evidence")
    selected = [e for e in active_evidence(state) if e.id in baseline.evidence_ids]
    if {e.id for e in selected} != set(baseline.evidence_ids):
        raise ValueError("baseline references unknown evidence IDs")
    if not all(diagnostic_result(e) for e in selected):
        raise ValueError("baseline requires independent, unhinted diagnostic evidence")
    if not set(state.intake.profile.diagnostic_competencies) <= {e.competency for e in selected}:
        raise ValueError("baseline does not cover the agreed diagnostic competencies")
    state.intake.baseline = baseline
    state.session = {}
    state.history.append(
        {
            "event": "baseline-completed",
            "timestamp": now().isoformat(),
            "evidence_ids": baseline.evidence_ids,
            "summary": baseline.summary,
        }
    )
