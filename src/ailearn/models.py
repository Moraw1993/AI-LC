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
    targets: dict[Literal["beginner", "mid", "advanced"], list[str]]
    competencies: list[Competency] = Field(min_length=1)
    references: list[str] = Field(default_factory=list)


class Config(Model):
    schema_version: Literal[1] = 1
    learner: str = Field(default="Learner", min_length=1)
    domain: str
    target: Literal["beginner", "mid", "advanced"] = "mid"
    depth: Literal["minimal", "standard", "comprehensive"] = "standard"
    preferences: list[str] = Field(default_factory=list)


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
