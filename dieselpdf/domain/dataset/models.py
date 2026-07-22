from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from .identity import validate_stable_id


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
StableId = Annotated[str, Field(min_length=35, max_length=65)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DieselModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_boolean_for_numbers(cls, value: Any, info: Any) -> Any:
        annotation = cls.model_fields[info.field_name].annotation
        if isinstance(value, bool) and annotation in {int, float, Optional[int], Optional[float]}:
            raise TypeError(f"{info.field_name} must not be boolean")
        return value


class ActorRole(str, Enum):
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    DRAFTER = "drafter"
    AI = "ai"
    SYSTEM = "system"
    IMPORTER = "importer"


class ReviewStatus(str, Enum):
    WORKING = "working"
    AI_PROPOSED = "ai_proposed"
    ENGINEER_REVIEW_REQUIRED = "engineer_review_required"
    ENGINEER_APPROVED = "engineer_approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class RevisionStatus(str, Enum):
    OPEN = "open"
    COMMITTED = "committed"
    SUPERSEDED = "superseded"


class EntityType(str, Enum):
    POINT = "point"
    LINE = "line"
    POLYLINE = "polyline"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ARC = "arc"
    ELLIPSE = "ellipse"
    SPLINE = "spline"
    HATCH = "hatch"
    TEXT = "text"
    DIMENSION = "dimension"
    LEADER = "leader"
    IMAGE = "image"
    BLOCK_REFERENCE = "block_reference"


class RelationshipType(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    CONNECTED_TO = "CONNECTED_TO"
    SUPPORTED_BY = "SUPPORTED_BY"
    SUPPORTS = "SUPPORTS"
    LOADS_ONTO = "LOADS_ONTO"
    CONTAINS = "CONTAINS"
    BOUNDS = "BOUNDS"
    ALIGNS_WITH = "ALIGNS_WITH"
    LOCATED_ON_GRID = "LOCATED_ON_GRID"
    LOCATED_ON_STOREY = "LOCATED_ON_STOREY"
    CLASHES_WITH = "CLASHES_WITH"
    REPRESENTED_BY = "REPRESENTED_BY"
    CALCULATED_BY = "CALCULATED_BY"
    SUPERSEDES = "SUPERSEDES"


class ActorIdentity(DieselModel):
    actor_id: StableId
    display_name: NonEmptyString
    role: ActorRole
    can_approve_engineering: bool = False

    @field_validator("actor_id")
    @classmethod
    def stable_actor_id(cls, value: str) -> str:
        return validate_stable_id(value)

    @model_validator(mode="after")
    def approval_requires_engineer_role(self) -> "ActorIdentity":
        if self.can_approve_engineering and self.role is not ActorRole.ENGINEER:
            raise ValueError("engineering approval authority requires the engineer role")
        return self


class BoundingBox2D(DieselModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @model_validator(mode="after")
    def ordered_extents(self) -> "BoundingBox2D":
        if self.min_x > self.max_x or self.min_y > self.max_y:
            raise ValueError("bounding-box minimums must not exceed maximums")
        return self


class SourceTrace(DieselModel):
    source_document_id: Optional[StableId] = None
    source_page_id: Optional[StableId] = None
    source_external_id: Optional[NonEmptyString] = None
    source_method: NonEmptyString
    source_hash: Optional[Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]] = None
    evidence_summary: Optional[NonEmptyString] = None

    @field_validator("source_document_id", "source_page_id")
    @classmethod
    def stable_source_id(cls, value: Optional[str]) -> Optional[str]:
        return validate_stable_id(value) if value is not None else None


class GeometryPayload(DieselModel):
    entity_type: EntityType
    coordinate_system_id: NonEmptyString
    unit: NonEmptyString = "mm"
    coordinates: List[float]
    text: Optional[str] = None
    closed: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def geometry_shape_matches_type(self) -> "GeometryPayload":
        count = len(self.coordinates)
        if self.entity_type is EntityType.POINT and count != 2:
            raise ValueError("point geometry requires exactly two coordinates")
        if self.entity_type in {EntityType.LINE, EntityType.RECTANGLE} and count != 4:
            raise ValueError(f"{self.entity_type.value} geometry requires exactly four coordinates")
        if self.entity_type in {EntityType.POLYLINE, EntityType.POLYGON}:
            if count < 4 or count % 2:
                raise ValueError(f"{self.entity_type.value} geometry requires coordinate pairs")
        if self.entity_type is EntityType.CIRCLE and count != 3:
            raise ValueError("circle geometry requires centre x, centre y, and radius")
        if self.entity_type is EntityType.TEXT:
            if count != 2 or self.text is None:
                raise ValueError("text geometry requires an insertion point and text")
        return self


class ProjectRecord(DieselModel):
    project_id: StableId
    schema_version: int = Field(default=1, ge=1)
    name: NonEmptyString
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def stable_project_id(cls, value: str) -> str:
        return validate_stable_id(value)


class DocumentRecord(DieselModel):
    document_id: StableId
    project_id: StableId
    revision_id: StableId
    schema_version: int = Field(default=1, ge=1)
    file_name: NonEmptyString
    source_path: Optional[str] = None
    media_type: NonEmptyString = "application/octet-stream"
    source_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("document_id", "project_id", "revision_id")
    @classmethod
    def stable_document_ids(cls, value: str) -> str:
        return validate_stable_id(value)


class PageRecord(DieselModel):
    page_id: StableId
    project_id: StableId
    document_id: StableId
    revision_id: StableId
    schema_version: int = Field(default=1, ge=1)
    page_index: int = Field(ge=0)
    paper_name: Optional[NonEmptyString] = None
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    coordinate_system_id: NonEmptyString
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("page_id", "project_id", "document_id", "revision_id")
    @classmethod
    def stable_page_ids(cls, value: str) -> str:
        return validate_stable_id(value)


class RevisionRecord(DieselModel):
    revision_id: StableId
    project_id: StableId
    sequence: int = Field(ge=1)
    parent_revision_id: Optional[StableId] = None
    author: ActorIdentity
    reason: NonEmptyString
    status: RevisionStatus = RevisionStatus.COMMITTED
    created_at: datetime = Field(default_factory=utc_now)
    source_revision: Optional[NonEmptyString] = None

    @field_validator("revision_id", "project_id", "parent_revision_id")
    @classmethod
    def stable_revision_ids(cls, value: Optional[str]) -> Optional[str]:
        return validate_stable_id(value) if value is not None else None


class VersionedRecord(DieselModel):
    schema_version: int = Field(default=1, ge=1)
    revision_id: StableId
    version_sequence: int = Field(ge=1)
    review_status: ReviewStatus
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    content_hash: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("revision_id")
    @classmethod
    def stable_revision_id(cls, value: str) -> str:
        return validate_stable_id(value)

    def calculated_content_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GeometryEntity(VersionedRecord):
    entity_id: StableId
    project_id: StableId
    entity_type: EntityType
    geometry: GeometryPayload
    bounding_box: BoundingBox2D
    coordinate_system_id: NonEmptyString
    storey_id: Optional[StableId] = None
    layer_id: Optional[StableId] = None
    style_id: Optional[StableId] = None
    source: SourceTrace

    @field_validator("entity_id", "project_id", "storey_id", "layer_id", "style_id")
    @classmethod
    def stable_entity_ids(cls, value: Optional[str]) -> Optional[str]:
        return validate_stable_id(value) if value is not None else None

    @model_validator(mode="after")
    def consistent_geometry(self) -> "GeometryEntity":
        if self.geometry.entity_type is not self.entity_type:
            raise ValueError("entity_type and geometry.entity_type must match")
        if self.geometry.coordinate_system_id != self.coordinate_system_id:
            raise ValueError("geometry and entity coordinate systems must match")
        if self.content_hash is None:
            object.__setattr__(self, "content_hash", self.calculated_content_hash())
        return self


class SemanticObject(VersionedRecord):
    object_id: StableId
    project_id: StableId
    object_type: NonEmptyString
    name_or_mark: Optional[NonEmptyString] = None
    geometry_reference: Optional[StableId] = None
    storey_id: Optional[StableId] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_entity_ids: List[StableId] = Field(default_factory=list)
    calculation_ids: List[StableId] = Field(default_factory=list)

    @field_validator(
        "object_id",
        "project_id",
        "geometry_reference",
        "storey_id",
        "source_entity_ids",
        "calculation_ids",
    )
    @classmethod
    def stable_object_ids(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            return [validate_stable_id(item) for item in value]
        return validate_stable_id(value)

    @model_validator(mode="after")
    def source_or_engineer_origin(self) -> "SemanticObject":
        if not self.source_entity_ids and "engineer_created_by" not in self.properties:
            raise ValueError(
                "semantic objects require source entities or an explicit engineer_created_by property"
            )
        if self.content_hash is None:
            object.__setattr__(self, "content_hash", self.calculated_content_hash())
        return self


class RelationshipRecord(VersionedRecord):
    relationship_id: StableId
    project_id: StableId
    relationship_type: RelationshipType
    source_id: StableId
    target_id: StableId
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("relationship_id", "project_id", "source_id", "target_id")
    @classmethod
    def stable_relationship_ids(cls, value: str) -> str:
        return validate_stable_id(value)

    @model_validator(mode="after")
    def distinct_ends_and_hash(self) -> "RelationshipRecord":
        if self.source_id == self.target_id:
            raise ValueError("relationship source and target must differ")
        if self.content_hash is None:
            object.__setattr__(self, "content_hash", self.calculated_content_hash())
        return self


class ReviewDecision(DieselModel):
    decision_id: StableId
    project_id: StableId
    revision_id: StableId
    item_kind: Annotated[str, StringConstraints(pattern=r"^(entity|semantic_object|relationship)$")]
    item_id: StableId
    previous_status: ReviewStatus
    decision: ReviewStatus
    actor: ActorIdentity
    comment: NonEmptyString
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("decision_id", "project_id", "revision_id", "item_id")
    @classmethod
    def stable_decision_ids(cls, value: str) -> str:
        return validate_stable_id(value)


class AuditEvent(DieselModel):
    event_id: StableId
    project_id: StableId
    revision_id: Optional[StableId] = None
    event_type: NonEmptyString
    actor: ActorIdentity
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("event_id", "project_id", "revision_id")
    @classmethod
    def stable_audit_ids(cls, value: Optional[str]) -> Optional[str]:
        return validate_stable_id(value) if value is not None else None
