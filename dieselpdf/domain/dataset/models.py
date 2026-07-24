from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Dict, Iterable, List, Literal, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ActorRole(str, Enum):
    SYSTEM_IMPORTER = "system_importer"
    PROPOSER = "proposer"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    ADMIN = "admin"


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
    CUSTOM = "CUSTOM"


class RecordType(str, Enum):
    PROJECT = "project"
    DOCUMENT = "document"
    PAGE = "page"
    REVISION = "revision"
    RAW_ENTITY = "raw_entity"
    SEMANTIC_OBJECT = "semantic_object"
    OBJECT_ENTITY_LINK = "object_entity_link"
    RELATIONSHIP = "relationship"
    AUDIT_EVENT = "audit_event"
    IMPORT_BATCH = "import_batch"


class BoundingBox2D(FrozenModel):
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @model_validator(mode="after")
    def validate_order(self) -> "BoundingBox2D":
        if self.min_x > self.max_x or self.min_y > self.max_y:
            raise ValueError("bounding-box minima must not exceed maxima")
        return self

    def intersects(self, other: "BoundingBox2D") -> bool:
        return not (
            self.max_x < other.min_x
            or other.max_x < self.min_x
            or self.max_y < other.min_y
            or other.max_y < self.min_y
        )

    def contains(self, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y


class PointGeometry(FrozenModel):
    kind: Literal["point"] = "point"
    point: Tuple[float, float]

    def bounds(self) -> BoundingBox2D:
        x, y = self.point
        return BoundingBox2D(min_x=x, max_x=x, min_y=y, max_y=y)


class LineGeometry(FrozenModel):
    kind: Literal["line"] = "line"
    start: Tuple[float, float]
    end: Tuple[float, float]

    def bounds(self) -> BoundingBox2D:
        xs = (self.start[0], self.end[0])
        ys = (self.start[1], self.end[1])
        return BoundingBox2D(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))


class PolylineGeometry(FrozenModel):
    kind: Literal["polyline"] = "polyline"
    points: Tuple[Tuple[float, float], ...]
    closed: bool = False

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: Tuple[Tuple[float, float], ...]) -> Tuple[Tuple[float, float], ...]:
        if len(value) < 2:
            raise ValueError("polyline requires at least two points")
        return value

    def bounds(self) -> BoundingBox2D:
        xs = tuple(point[0] for point in self.points)
        ys = tuple(point[1] for point in self.points)
        return BoundingBox2D(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))


class PolygonGeometry(FrozenModel):
    kind: Literal["polygon"] = "polygon"
    points: Tuple[Tuple[float, float], ...]

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: Tuple[Tuple[float, float], ...]) -> Tuple[Tuple[float, float], ...]:
        if len(value) < 3:
            raise ValueError("polygon requires at least three points")
        return value

    def bounds(self) -> BoundingBox2D:
        xs = tuple(point[0] for point in self.points)
        ys = tuple(point[1] for point in self.points)
        return BoundingBox2D(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))


class RectangleGeometry(FrozenModel):
    kind: Literal["rectangle"] = "rectangle"
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def bounds(self) -> BoundingBox2D:
        return BoundingBox2D(min_x=self.min_x, max_x=self.max_x, min_y=self.min_y, max_y=self.max_y)


class EllipseGeometry(FrozenModel):
    kind: Literal["ellipse"] = "ellipse"
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def bounds(self) -> BoundingBox2D:
        return BoundingBox2D(min_x=self.min_x, max_x=self.max_x, min_y=self.min_y, max_y=self.max_y)


class TextGeometry(FrozenModel):
    kind: Literal["text"] = "text"
    insertion: Tuple[float, float]
    text: str
    rotation_degrees: float = 0.0

    def bounds(self) -> BoundingBox2D:
        x, y = self.insertion
        return BoundingBox2D(min_x=x, max_x=x, min_y=y, max_y=y)


class OpaqueGeometry(FrozenModel):
    kind: Literal["opaque"] = "opaque"
    source_type: str
    payload: Dict[str, Any]
    declared_bounds: BoundingBox2D

    def bounds(self) -> BoundingBox2D:
        return self.declared_bounds


GeometryPayload = Annotated[
    Union[
        PointGeometry,
        LineGeometry,
        PolylineGeometry,
        PolygonGeometry,
        RectangleGeometry,
        EllipseGeometry,
        TextGeometry,
        OpaqueGeometry,
    ],
    Field(discriminator="kind"),
]


class Provenance(FrozenModel):
    source_document_id: Optional[UUID] = None
    source_page_id: Optional[UUID] = None
    source_external_id: Optional[str] = None
    source_method: str
    source_sha256: Optional[str] = None
    adapter_version: Optional[str] = None
    original_payload: Optional[Dict[str, Any]] = None

    @field_validator("source_method")
    @classmethod
    def source_method_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_method must not be empty")
        return value.strip()

    @field_validator("source_sha256")
    @classmethod
    def validate_sha(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.lower().strip()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("source_sha256 must be a 64-character hexadecimal digest")
        return normalized


class ProjectDraft(FrozenModel):
    project_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    schema_version: str = SCHEMA_VERSION

    @field_validator("name")
    @classmethod
    def name_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project name must not be empty")
        return value.strip()


class ProjectRecord(ProjectDraft):
    created_at: datetime
    updated_at: datetime
    current_revision_id: Optional[UUID] = None


class DocumentDraft(FrozenModel):
    document_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    title: str
    source_path: Optional[str] = None
    source_sha256: Optional[str] = None
    media_type: Optional[str] = None
    schema_version: str = SCHEMA_VERSION


class DocumentRecord(DocumentDraft):
    revision_id: UUID
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    created_at: datetime
    updated_at: datetime


class PageDraft(FrozenModel):
    page_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    document_id: UUID
    page_index: int = Field(ge=0)
    name: str
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    coordinate_system_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


class PageRecord(PageDraft):
    revision_id: UUID
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    created_at: datetime
    updated_at: datetime


class RawEntityDraft(FrozenModel):
    entity_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    entity_type: str
    geometry: GeometryPayload
    coordinate_system_id: str
    storey_id: Optional[str] = None
    layer_id: Optional[str] = None
    style_id: Optional[str] = None
    provenance: Provenance
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    properties: Dict[str, Any] = Field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @field_validator("entity_type", "coordinate_system_id")
    @classmethod
    def required_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identifier must not be empty")
        return value.strip()

    @property
    def bounding_box(self) -> BoundingBox2D:
        return self.geometry.bounds()


class RawEntityRecord(RawEntityDraft):
    revision_id: UUID
    content_hash: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class SemanticObjectDraft(FrozenModel):
    object_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    object_type: str
    name_or_mark: Optional[str] = None
    storey_id: Optional[str] = None
    geometry_reference: Optional[UUID] = None
    bounding_box: Optional[BoundingBox2D] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_entity_ids: Tuple[UUID, ...] = ()
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.PROPOSED
    schema_version: str = SCHEMA_VERSION


class SemanticObjectRecord(SemanticObjectDraft):
    revision_id: UUID
    content_hash: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class ObjectEntityLink(FrozenModel):
    link_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    object_id: UUID
    entity_id: UUID
    role: str = "source"
    revision_id: UUID


class RelationshipDraft(FrozenModel):
    relationship_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    relationship_type: RelationshipType
    source_id: UUID
    target_id: UUID
    properties: Dict[str, Any] = Field(default_factory=dict)
    review_status: ReviewStatus = ReviewStatus.PROPOSED
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def prevent_self_relationship(self) -> "RelationshipDraft":
        if self.source_id == self.target_id:
            raise ValueError("relationship source and target must differ")
        return self


class RelationshipRecord(RelationshipDraft):
    revision_id: UUID
    content_hash: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class RevisionRecord(FrozenModel):
    revision_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    parent_revision_id: Optional[UUID] = None
    actor_id: str
    actor_role: ActorRole
    reason: str
    status: Literal["pending", "committed", "rolled_back"] = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    committed_at: Optional[datetime] = None


class AuditEventRecord(FrozenModel):
    event_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    revision_id: UUID
    actor_id: str
    actor_role: ActorRole
    action: str
    record_type: RecordType
    record_id: UUID
    changed_fields: Tuple[str, ...] = ()
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DatasetRow(FrozenModel):
    record_type: RecordType
    record_id: UUID
    type_name: str
    name_or_mark: Optional[str] = None
    storey_id: Optional[str] = None
    review_status: ReviewStatus
    revision_id: UUID
    bounding_box: Optional[BoundingBox2D] = None


class JsonlEnvelope(FrozenModel):
    record_type: RecordType
    schema_version: str = SCHEMA_VERSION
    payload: Dict[str, Any]


class ImportBatchRecord(FrozenModel):
    import_batch_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    revision_id: UUID
    source_path: str
    source_sha256: str
    importer: str
    imported_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    report: Dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)


DATASET_RECORD_MODELS = {
    RecordType.PROJECT: ProjectRecord,
    RecordType.DOCUMENT: DocumentRecord,
    RecordType.PAGE: PageRecord,
    RecordType.REVISION: RevisionRecord,
    RecordType.RAW_ENTITY: RawEntityRecord,
    RecordType.SEMANTIC_OBJECT: SemanticObjectRecord,
    RecordType.OBJECT_ENTITY_LINK: ObjectEntityLink,
    RecordType.RELATIONSHIP: RelationshipRecord,
    RecordType.AUDIT_EVENT: AuditEventRecord,
    RecordType.IMPORT_BATCH: ImportBatchRecord,
}


def validate_envelope(envelope: JsonlEnvelope) -> BaseModel:
    model = DATASET_RECORD_MODELS[envelope.record_type]
    return model.model_validate(envelope.payload)
