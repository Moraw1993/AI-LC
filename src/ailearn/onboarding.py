"""Conversation-first onboarding and diagnostic readiness, without an LLM client."""

from ailearn.graph import Graph
from ailearn.history import append_history, audit_context
from ailearn.models import (
    Baseline,
    CoursePlan,
    CoursePlanProposal,
    PlanPhase,
    Snapshot,
    active_evidence,
    now,
)


def onboarding_brief() -> dict:
    return {
        "schema_version": 1,
        "phase": "intent-discovery",
        "roles": ["master"],
        "skill": "ai-lc-master",
        "action": "conversation",
        "reason": "Collect explicit learner intent before configuring a course.",
        "instructions": "Ask what the learner wants to learn and why. Establish the target "
        "ability, prior experience, language, working style, tutor name and workspace name. "
        "Discuss whether the learner prefers focused core practice, a balanced sequence or "
        "early project application; the proposed overview plan must recommend one explicit "
        "built-in path for learner approval. "
        "Do not select a default topic or build a roadmap. Save explicit decisions in a "
        "LearningProfile and use ailearn configure profile.json. "
        "After configure, present and obtain approval for the overview plan before baseline "
        "diagnosis. After completing intake, present and obtain approval for the adaptive "
        "roadmap before teaching.",
    }


def diagnostic_brief(state: Snapshot) -> dict | None:
    if state.intake is None or state.intake.baseline is not None:
        return None
    plan_gate = planning_brief(state)
    if plan_gate is not None:
        return plan_gate
    profile = state.intake.profile
    covered = {e.competency for e in active_evidence(state) if diagnostic_result(e)}
    missing = [key for key in profile.diagnostic_competencies if key not in covered]
    key = missing[0] if missing else profile.diagnostic_competencies[-1]
    node = Graph(state.domains).nodes[key]
    return {
        "schema_version": 1,
        "phase": "discovery",
        "scope": "assessment",
        "competency": key,
        "dimension": "conceptual",
        "roles": ["teacher", "assessor"],
        "assessment_checkpoint": "formal",
        "agent_name": profile.agent_name,
        "language": profile.language,
        "action": "diagnostic" if missing else "complete-intake",
        "reason": "Collect independent baseline evidence for the agreed diagnostic competencies.",
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


def _expected_plan_phase(state: Snapshot) -> PlanPhase:
    if state.intake is None:
        raise ValueError("course plans require a configured learning profile")
    return PlanPhase.OVERVIEW if state.intake.baseline is None else PlanPhase.ADAPTIVE


def _plan_gate(state: Snapshot, phase: PlanPhase) -> dict:
    plans = [plan for plan in state.plans if plan.phase == phase]
    current = plans[-1] if plans else None
    if current is not None and current.status == "approved":
        return {}
    action = "await-plan-approval" if current is not None else "propose-plan"
    stage = "course-outline" if phase == PlanPhase.OVERVIEW else "adaptive-roadmap"
    return {
        "schema_version": 1,
        "phase": "course-planning",
        "scope": "plan-review",
        "action": action,
        "plan_phase": phase.value,
        "plan_version": current.version if current else None,
        "roles": ["master"] if current else ["curriculum-architect", "master"],
        "reason": (
            "Wait for explicit learner approval of the current plan version."
            if current
            else "Propose the current course phase for explicit learner approval."
        ),
        "instructions": (
            f"Prepare and present the {stage} in the learner's language. Explain its "
            "goal, stages, working method, projects and role boundaries. Include one built-in "
            "learning path profile (focused, balanced or project-led) and explain its activity "
            "priorities. The adaptive plan must keep the learner-approved profile. Profiles "
            "may reorder eligible activities only; they cannot remove required gates or "
            "evidence. Wait for explicit "
            "learner approval before continuing. Save proposals with `ailearn plan propose "
            "plan.json`, or revise one with `ailearn plan revise plan.json`; record approval "
            "with `ailearn plan approve VERSION`. Do not diagnose or teach while plan review "
            "is pending."
        ),
    }


def planning_brief(state: Snapshot) -> dict | None:
    """Gate modern courses on an approved overview and post-diagnosis route."""
    if not state.plan_workflow or state.intake is None:
        return None
    phase = _expected_plan_phase(state)
    gate = _plan_gate(state, phase)
    return gate or None


def validate_course_plans(state: Snapshot) -> None:
    if state.plan_workflow and state.intake is None:
        raise ValueError("course plan workflow requires a learning profile")
    if state.plan_workflow and state.intake is not None and state.intake.baseline is not None:
        if not any(
            plan.phase == PlanPhase.OVERVIEW and plan.approved_at is not None
            for plan in state.plans
        ):
            raise ValueError("baseline and adaptive planning require an approved overview plan")
    if not state.plans:
        return
    if not state.plan_workflow:
        raise ValueError("course plans require the versioned plan workflow")
    if state.intake is None:
        raise ValueError("course plans require a learning profile")
    if any(plan.phase == PlanPhase.ADAPTIVE for plan in state.plans) and not any(
        plan.phase == PlanPhase.OVERVIEW and plan.approved_at is not None for plan in state.plans
    ):
        raise ValueError("baseline and adaptive planning require an approved overview plan")
    from ailearn.graph import Graph

    graph = Graph(state.domains)
    profile = state.intake.profile
    approved_overview = next(
        (
            plan
            for plan in reversed(state.plans)
            if plan.phase == PlanPhase.OVERVIEW and plan.status == "approved"
        ),
        None,
    )
    closure = set(graph.target_closure(profile.domain, profile.target))
    versions: set[int] = set()
    for index, plan in enumerate(state.plans):
        if plan.version in versions:
            raise ValueError("duplicate course plan version")
        versions.add(plan.version)
        competencies = [key for stage in plan.stages for key in stage.competencies]
        if len(competencies) != len(set(competencies)) or set(competencies) != closure:
            raise ValueError("course plan must cover every target competency exactly once")
        if (
            plan.goal,
            plan.domain,
            plan.target,
            plan.target_description,
            plan.depth,
        ) != (
            profile.goal,
            profile.domain,
            profile.target,
            profile.target_description,
            profile.depth,
        ):
            raise ValueError("course plan scope differs from the agreed learning profile")
        stage_for = {
            key: index for index, stage in enumerate(plan.stages) for key in stage.competencies
        }
        position_for = {
            key: position
            for position, key in enumerate(
                key for stage in plan.stages for key in stage.competencies
            )
        }
        for key, index in stage_for.items():
            if any(
                stage_for[prerequisite] > index or position_for[prerequisite] > position_for[key]
                for prerequisite in graph.nodes[key].prerequisites
            ):
                raise ValueError("course plan places a competency before its prerequisite")
        if (plan.status == "approved" and plan.approved_at is None) or (
            plan.status == "proposed" and plan.approved_at is not None
        ):
            raise ValueError("course plan approval timestamp does not match its status")
        if plan.phase == PlanPhase.ADAPTIVE and state.intake.baseline is None:
            raise ValueError("adaptive course plan requires a completed baseline")
        if plan.phase == PlanPhase.ADAPTIVE and approved_overview is not None:
            if plan.learning_path_profile != approved_overview.learning_path_profile:
                raise ValueError("adaptive course plan must keep the learner-approved path profile")
        prior_phase_plan = any(old.phase == plan.phase for old in state.plans[:index])
        expected_event = "plan.revised" if prior_phase_plan else "plan.proposed"
        if not any(
            event.get("event") == expected_event and event.get("version") == plan.version
            for event in state.history
        ):
            raise ValueError("course plan is missing its proposal history event")
        if plan.approved_at is not None and not any(
            event.get("event") == "plan.approved" and event.get("version") == plan.version
            for event in state.history
        ):
            raise ValueError("approved course plan is missing its approval history event")
    if versions and versions != set(range(1, max(versions) + 1)):
        raise ValueError("course plan versions must be sequential")


def propose_plan(
    state: Snapshot, proposal: CoursePlanProposal, *, revise: bool = False
) -> CoursePlan:
    if not state.plan_workflow:
        raise ValueError("this course does not use the versioned plan workflow")
    proposal = CoursePlanProposal.model_validate(proposal.model_dump())
    phase = _expected_plan_phase(state)
    if proposal.phase != phase:
        raise ValueError(f"the current plan phase must be {phase.value}")
    validate_course_plans(state)
    previous = [plan for plan in state.plans if plan.phase == phase]
    if previous and not revise:
        raise ValueError("a plan already exists for this phase; use `plan revise FILE`")
    if revise and not previous:
        raise ValueError("cannot revise a plan that has not been proposed")
    if not revise and previous:
        raise ValueError("use `plan revise FILE` to replace an existing plan")
    graph = Graph(state.domains)
    profile = state.intake.profile
    if (
        proposal.goal,
        proposal.domain,
        proposal.target,
        proposal.target_description,
        proposal.depth,
    ) != (
        profile.goal,
        profile.domain,
        profile.target,
        profile.target_description,
        profile.depth,
    ):
        raise ValueError("course plan scope must match the agreed learning profile")
    if phase == PlanPhase.ADAPTIVE:
        overview = next(
            (
                plan
                for plan in reversed(state.plans)
                if plan.phase == PlanPhase.OVERVIEW and plan.status == "approved"
            ),
            None,
        )
        if overview is None:
            raise ValueError("approve the course overview before selecting a learning path")
        if proposal.learning_path_profile != overview.learning_path_profile:
            raise ValueError("adaptive course plan must keep the learner-approved path profile")
    closure = set(graph.target_closure(profile.domain, profile.target))
    competencies = [key for stage in proposal.stages for key in stage.competencies]
    if len(competencies) != len(set(competencies)):
        raise ValueError("each target competency must appear in exactly one plan stage")
    if set(competencies) != closure:
        raise ValueError("plan stages must cover the selected target and prerequisite closure")
    stage_for = {
        key: index for index, stage in enumerate(proposal.stages) for key in stage.competencies
    }
    for key, index in stage_for.items():
        if any(stage_for[prerequisite] > index for prerequisite in graph.nodes[key].prerequisites):
            raise ValueError("course plan places a competency before its prerequisite")
    version = max((plan.version for plan in state.plans), default=0) + 1
    for prior in previous:
        if prior.status == "proposed":
            prior.status = "superseded"
    plan = CoursePlan(**proposal.model_dump(), version=version, status="proposed")
    state.plans.append(plan)
    evidence_refs = (
        state.intake.baseline.evidence_ids
        if phase == PlanPhase.ADAPTIVE and state.intake.baseline is not None
        else []
    )
    append_history(
        state,
        "plan.revised" if revise else "plan.proposed",
        timestamp=plan.created_at,
        profile_version=state.intake.profile.schema_version,
        plan_version=version,
        learning_path_profile=plan.learning_path_profile.model_dump(mode="json"),
        evidence_refs=evidence_refs,
        version=version,
        phase=phase.value,
        supersedes_version=previous[-1].version if previous else None,
    )
    return plan


def approve_plan(state: Snapshot, version: int) -> CoursePlan:
    if not state.plan_workflow:
        raise ValueError("this course does not use the versioned plan workflow")
    phase = _expected_plan_phase(state)
    plans = [plan for plan in state.plans if plan.phase == phase]
    if not plans or plans[-1].version != version or plans[-1].status != "proposed":
        raise ValueError("approval must identify the current proposed plan version")
    for prior in plans[:-1]:
        if prior.status == "approved":
            prior.status = "superseded"
    approved = plans[-1]
    approved.status = "approved"
    approved.approved_at = now()
    evidence_refs = (
        state.intake.baseline.evidence_ids
        if phase == PlanPhase.ADAPTIVE and state.intake.baseline is not None
        else []
    )
    append_history(
        state,
        "plan.approved",
        timestamp=approved.approved_at,
        profile_version=state.intake.profile.schema_version,
        plan_version=approved.version,
        learning_path_profile=approved.learning_path_profile.model_dump(mode="json"),
        evidence_refs=evidence_refs,
        version=approved.version,
        phase=phase.value,
        approval="approved",
    )
    state.session = {}
    return approved


def diagnostic_result(e) -> bool:
    return e.kind == "diagnostic" and e.independent and e.hints == 0 and e.confidence >= 0.8


def complete_intake(state: Snapshot, baseline: Baseline) -> None:
    if state.intake is None:
        raise ValueError("this legacy workspace has no Master intake profile")
    if state.plan_workflow and _plan_gate(state, PlanPhase.OVERVIEW):
        raise ValueError("approve the course overview before completing baseline diagnosis")
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
    append_history(
        state,
        "baseline-completed",
        **audit_context(state),
        evidence_refs=baseline.evidence_ids,
        evidence_ids=baseline.evidence_ids,
    )
