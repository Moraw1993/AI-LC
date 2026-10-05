"""Validated, versioned contracts shared by the CLI and external agents."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


def now() -> datetime:
    return datetime.now(UTC)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Dimension(StrEnum):
    CONCEPTUAL = "conceptual"
    MATHEMATICAL = "mathematical"
    IMPLEMENTATION = "implementation"
    INTERPRETATION = "interpretation"
    DEBUGGING = "debugging"
    TRANSFER = "transfer"
    RETENTION = "retention"


class Scope(StrEnum):
    LEARN = "learn"
    DEEP = "deep-learn"
    REVIEW = "review"
    REMEDIATE = "remediate"
    PRACTICE = "practice"
    ASSESSMENT = "assessment"
    PROJECT = "project"
    EXPLORE = "explore"


class HarnessRole(StrEnum):
    MASTER = "master"
    CURRICULUM_ARCHITECT = "curriculum-architect"
    TEACHER = "teacher"
    LAB_COACH = "lab-coach"
    ASSESSOR = "assessor"
    RESEARCH_DATA = "research-data"


class HarnessCapabilityState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class HarnessCapability(StrEnum):
    INSTRUCTION_ACCESS = "instruction_access"
    LOCAL_CLI = "local_cli"
    FILE_ARTIFACTS = "file_artifacts"
    FORMAL_ASSESSMENT = "formal_assessment"
    MEDIA_TOOLS = "media_tools"
    SANDBOX_EXECUTION = "sandbox_execution"


class HarnessCapabilities(Model):
    instruction_access: HarnessCapabilityState = HarnessCapabilityState.UNKNOWN
    local_cli: HarnessCapabilityState = HarnessCapabilityState.UNKNOWN
    file_artifacts: HarnessCapabilityState = HarnessCapabilityState.UNKNOWN
    formal_assessment: HarnessCapabilityState = HarnessCapabilityState.UNKNOWN
    media_tools: HarnessCapabilityState = HarnessCapabilityState.UNKNOWN
    sandbox_execution: HarnessCapabilityState = HarnessCapabilityState.UNKNOWN


class HarnessManifest(Model):
    """Harness-declared availability; declarations are not execution evidence."""

    schema_version: Literal[1]
    harness_id: str = Field(pattern=r"^[a-z][a-z0-9._-]*$")
    capabilities: HarnessCapabilities = Field(default_factory=HarnessCapabilities)


class HarnessBrief(Model):
    """Stable brief envelope; additional AI-LC brief fields are preserved as extensions."""

    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1]
    phase: str = Field(min_length=1)
    action: str = Field(min_length=1)
    roles: list[HarnessRole] = Field(min_length=1)
    instructions: str = Field(min_length=1)
    assessment_checkpoint: Literal["formal", "formative"] | None = None
    required_capabilities: list[HarnessCapability] = Field(default_factory=list)


class Stage(StrEnum):
    UNSEEN = "UNSEEN"
    EXPOSED = "EXPOSED"
    GUIDED = "GUIDED"
    PRACTICED = "PRACTICED"
    DEMONSTRATED = "DEMONSTRATED"
    TRANSFERABLE = "TRANSFERABLE"
    RETAINED = "RETAINED"


class Competency(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    prerequisites: list[str] = Field(default_factory=list)
    outcomes: dict[Dimension, Annotated[list[str], Field(min_length=1)]]
    misconceptions: list[str] = Field(default_factory=list)
    threshold: int = Field(default=3, ge=1, le=4)
    assessment_strategies: list[str] = Field(min_length=1)


class Domain(Model):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z][a-z-]*$")
    name: str
    targets: dict[str, list[str]] = Field(min_length=1)
    competencies: list[Competency] = Field(min_length=1)
    references: list[str] = Field(default_factory=list)


class Config(Model):
    schema_version: Literal[1] = 1
    learner: str = Field(default="Learner", min_length=1)
    domain: str
    target: str = Field(default="mid", min_length=1)
    depth: Literal["minimal", "standard", "comprehensive"] = "standard"
    preferences: list[str] = Field(default_factory=list)


class LearningProfile(Model):
    """Explicit decisions collected by Master, never inferred by initialization."""

    schema_version: Literal[1] = 1
    learner: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    target: str = Field(min_length=1)
    target_description: str = Field(min_length=1)
    depth: Literal["minimal", "standard", "comprehensive"]
    workspace_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    agent_name: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=1)
    working_style: list[str] = Field(min_length=1)
    prior_knowledge: str = Field(min_length=1)
    diagnostic_competencies: list[str] = Field(min_length=1)

    @field_validator("workspace_name")
    @classmethod
    def portable_name(cls, value: str) -> str:
        if value.upper() in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *[f"COM{i}" for i in range(1, 10)],
            *[f"LPT{i}" for i in range(1, 10)],
        }:
            raise ValueError("workspace name is reserved on Windows")
        return value


class Baseline(Model):
    summary: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class PlanPhase(StrEnum):
    OVERVIEW = "overview"
    ADAPTIVE = "adaptive"


class LearningPathVariant(StrEnum):
    FOCUSED = "focused"
    BALANCED = "balanced"
    PROJECT_LED = "project-led"


class LearningPathProfile(Model):
    """Versioned built-in priorities for eligible learning activities."""

    schema_version: Literal[1] = 1
    variant: LearningPathVariant


def balanced_learning_path_profile() -> LearningPathProfile:
    """Provide the compatibility default for courses created before profiles."""
    return LearningPathProfile(variant=LearningPathVariant.BALANCED)


class AuditEvent(Model):
    """Versioned, privacy-conscious event envelope; unknown legacy events stay readable."""

    model_config = ConfigDict(extra="allow")
    audit_schema_version: Literal[1]
    event_id: str = Field(min_length=1)
    event: str = Field(min_length=1)
    timestamp: AwareDatetime
    profile_version: int | None = Field(default=None, ge=1)
    plan_version: int | None = Field(default=None, ge=1)
    learning_path_profile: LearningPathProfile | None = None
    routing_reason: str | None = Field(default=None, min_length=1)
    evidence_refs: list[Annotated[str, Field(min_length=1)]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def exclude_conversations(cls, value):
        def contains_conversation(data):
            if isinstance(data, dict):
                blocked = {
                    "brief",
                    "conversation",
                    "learner_profile",
                    "messages",
                    "plan",
                    "profile",
                    "transcript",
                }
                return any(str(key).lower() in blocked for key in data) or any(
                    contains_conversation(item) for item in data.values()
                )
            if isinstance(data, (list, tuple)):
                return any(contains_conversation(item) for item in data)
            return False

        if contains_conversation(value):
            raise ValueError("audit events must not store conversation content")
        return value


class PlanStage(Model):
    title: str = Field(min_length=1)
    outcomes: list[str] = Field(min_length=1)
    competencies: list[str] = Field(min_length=1)


class CoursePlanProposal(Model):
    phase: PlanPhase
    goal: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    target: str = Field(min_length=1)
    target_description: str = Field(min_length=1)
    depth: Literal["minimal", "standard", "comprehensive"]
    learning_path_profile: LearningPathProfile
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    stages: list[PlanStage] = Field(min_length=1)
    working_method: str = Field(min_length=1)
    projects: list[str] = Field(default_factory=list)
    role_responsibilities: list[str] = Field(min_length=1)


class CoursePlan(CoursePlanProposal):
    # Older snapshots without a selected variant retain the pre-profile route.
    learning_path_profile: LearningPathProfile = Field(
        default_factory=balanced_learning_path_profile
    )
    version: int = Field(ge=1)
    status: Literal["proposed", "approved", "superseded"]
    created_at: AwareDatetime = Field(default_factory=now)
    approved_at: AwareDatetime | None = None


class Intake(Model):
    profile: LearningProfile
    baseline: Baseline | None = None


class Bootstrap(Model):
    schema_version: Literal[1] = 1
    phase: Literal["intent-discovery"] = "intent-discovery"
    active_workspace: str | None = None


class Exercise(Model):
    lesson: int = Field(ge=1, le=999)
    topic: int = Field(ge=1, le=999)
    attempt: int = Field(ge=1, le=999)
    competency: str
    kind: Literal["diagnostic", "practice", "assessment"] = "practice"
    instructions: str = Field(min_length=1, max_length=3000)
    source: str = Field(min_length=1, max_length=12000)


class ExerciseArtifact(Model):
    id: str
    lesson: int
    topic: int
    attempt: int
    competency: str
    kind: Literal["diagnostic", "practice", "assessment"]
    path: str
    timestamp: AwareDatetime = Field(default_factory=now)


class SensorResult(Model):
    name: str
    passed: bool
    details: str


class Evidence(Model):
    id: str = Field(min_length=1, max_length=100)
    attempt_id: str = Field(min_length=1, max_length=100)
    competency: str
    dimension: Dimension
    score: int = Field(ge=0, le=4)
    independent: bool
    hints: int = Field(default=0, ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    assessor: str = Field(min_length=1)
    artifact: str = Field(min_length=1)
    kind: Literal[
        "diagnostic",
        "practice",
        "assessment",
        "transfer",
        "delayed-retrieval",
        "project",
        "explanation",
        "self-report",
    ] = "assessment"
    timestamp: datetime = Field(default_factory=now)
    supersedes_id: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str = ""
    misconceptions: list[str] = Field(default_factory=list)
    resolves: list[str] = Field(default_factory=list)
    sensors: list[SensorResult] = Field(default_factory=list)

    @field_validator("timestamp")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def kind_dimension(self):
        if self.dimension == Dimension.RETENTION and self.kind != "delayed-retrieval":
            raise ValueError("retention requires delayed-retrieval evidence")
        if self.kind == "delayed-retrieval" and self.dimension != Dimension.RETENTION:
            raise ValueError("delayed-retrieval must assess the retention dimension")
        if self.kind == "transfer" and self.dimension != Dimension.TRANSFER:
            raise ValueError("transfer tasks must assess the transfer dimension")
        if self.dimension == Dimension.TRANSFER and self.kind not in {"transfer", "project"}:
            raise ValueError("transfer requires transfer or project evidence")
        if set(self.misconceptions) & set(self.resolves):
            raise ValueError("cannot introduce and resolve the same misconception")
        return self


class Knowledge(Model):
    stage: Stage = Stage.UNSEEN
    levels: dict[Dimension, Annotated[int, Field(ge=0, le=4)]] = Field(default_factory=dict)
    misconceptions: list[str] = Field(default_factory=list)
    review_due: AwareDatetime | None = None
    review_step: int = Field(default=0, ge=0, le=5)
    last_review: AwareDatetime | None = None


class Snapshot(Model):
    schema_version: Literal[1] = 1
    config: Config
    domains: list[Domain]
    knowledge: dict[str, Knowledge] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)
    session: dict = Field(default_factory=dict)
    intake: Intake | None = None
    exercises: list[ExerciseArtifact] = Field(default_factory=list)
    plans: list[CoursePlan] = Field(default_factory=list)
    plan_workflow: bool = False


def active_evidence(snapshot: Snapshot) -> list[Evidence]:
    """Return current judgments and validate append-only revision links."""
    by_id: dict[str, Evidence] = {}
    replaced: set[str] = set()
    pair_heads: dict[tuple[str, Dimension], Evidence] = {}
    ordered: list[Evidence] = []
    for evidence in snapshot.evidence:
        if evidence.id in by_id:
            raise ValueError(f"duplicate evidence ID: {evidence.id}")
        key = (evidence.attempt_id, evidence.dimension)
        prior = pair_heads.get(key)
        if prior is None:
            if evidence.supersedes_id is not None:
                raise ValueError(
                    "replacement references evidence from another attempt or dimension"
                )
        elif evidence.supersedes_id != prior.id:
            raise ValueError(
                "duplicate attempt/dimension; replacement must supersede its active evidence"
            )
        else:
            replaced.add(prior.id)
        by_id[evidence.id] = evidence
        pair_heads[key] = evidence
        ordered.append(evidence)
    return [evidence for evidence in ordered if evidence.id not in replaced]
