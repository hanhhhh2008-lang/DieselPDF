from __future__ import annotations

import json
import sqlite3
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
from uuid import UUID, uuid4

from dieselpdf.domain.dataset import (
    ActorRole,
    AuditEventRecord,
    BoundingBox2D,
    DatasetRow,
    DocumentDraft,
    DocumentRecord,
    ImportBatchRecord,
    JsonlEnvelope,
    ObjectEntityLink,
    PageDraft,
    PageRecord,
    ProjectDraft,
    ProjectRecord,
    RawEntityDraft,
    RawEntityRecord,
    RecordType,
    RelationshipDraft,
    RelationshipRecord,
    ReviewStatus,
    RevisionRecord,
    SemanticObjectDraft,
    SemanticObjectRecord,
    content_hash,
    utc_now,
    validate_envelope,
    validate_initial_status,
    validate_review_transition,
)


def _dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: Optional[str], default):
    return default if value is None else json.loads(value)


def _uuid(value) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _dt(value: Optional[str]) -> Optional[datetime]:
    return None if value is None else datetime.fromisoformat(value)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return None if value is None else value.isoformat()


class DatasetRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be a sqlite3.Connection")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self.connection = connection

    def create_project(
        self,
        draft: ProjectDraft,
        *,
        actor_id: str,
        actor_role: ActorRole = ActorRole.ADMIN,
        reason: str = "Create project",
    ) -> ProjectRecord:
        now = utc_now()
        revision = RevisionRecord(
            project_id=draft.project_id,
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason,
            status="committed",
            created_at=now,
            committed_at=now,
        )
        record = ProjectRecord(
            **draft.model_dump(),
            created_at=now,
            updated_at=now,
            current_revision_id=revision.revision_id,
        )
        event = AuditEventRecord(
            project_id=draft.project_id,
            revision_id=revision.revision_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="create",
            record_type=RecordType.PROJECT,
            record_id=draft.project_id,
            changed_fields=tuple(draft.model_fields_set or {"name"}),
        )
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self._insert_project(record)
            self._insert_revision(revision)
            self._insert_audit_event(event)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return record

    def get_project(self, project_id: UUID) -> ProjectRecord:
        row = self.connection.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (str(project_id),),
        ).fetchone()
        if row is None:
            raise KeyError(f"project {project_id} not found")
        return ProjectRecord(
            project_id=_uuid(row["project_id"]),
            schema_version=row["schema_version"],
            name=row["name"],
            description=row["description"],
            current_revision_id=(
                _uuid(row["current_revision_id"])
                if row["current_revision_id"]
                else None
            ),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
        )

    def begin_revision(
        self,
        project_id: UUID,
        *,
        actor_id: str,
        actor_role: ActorRole,
        reason: str,
        parent_revision_id: Optional[UUID] = None,
    ) -> "RevisionSession":
        return RevisionSession(
            self,
            project_id=project_id,
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason,
            parent_revision_id=parent_revision_id,
        )

    def get_raw_entity(self, entity_id: UUID) -> RawEntityRecord:
        row = self.connection.execute(
            "SELECT * FROM raw_entities WHERE entity_id = ? AND deleted_at IS NULL",
            (str(entity_id),),
        ).fetchone()
        if row is None:
            raise KeyError(f"raw entity {entity_id} not found")
        return self._raw_from_row(row)

    def list_raw_entities(
        self,
        project_id: UUID,
        *,
        review_status: Optional[ReviewStatus] = None,
    ) -> Tuple[RawEntityRecord, ...]:
        sql = "SELECT * FROM raw_entities WHERE project_id = ? AND deleted_at IS NULL"
        parameters: List[object] = [str(project_id)]
        if review_status is not None:
            sql += " AND review_status = ?"
            parameters.append(review_status.value)
        sql += " ORDER BY entity_type, entity_id"
        return tuple(
            self._raw_from_row(row)
            for row in self.connection.execute(sql, tuple(parameters))
        )

    def query_raw_entities(
        self,
        project_id: UUID,
        bounds: BoundingBox2D,
    ) -> Tuple[RawEntityRecord, ...]:
        rows = self.connection.execute(
            """
            SELECT entity.*
            FROM raw_entity_rtree spatial
            JOIN raw_entities entity ON entity.spatial_id = spatial.spatial_id
            WHERE entity.project_id = ?
              AND entity.deleted_at IS NULL
              AND spatial.min_x <= ? AND spatial.max_x >= ?
              AND spatial.min_y <= ? AND spatial.max_y >= ?
            ORDER BY entity.entity_type, entity.entity_id
            """,
            (
                str(project_id),
                bounds.max_x,
                bounds.min_x,
                bounds.max_y,
                bounds.min_y,
            ),
        )
        return tuple(self._raw_from_row(row) for row in rows)

    def get_semantic_object(self, object_id: UUID) -> SemanticObjectRecord:
        row = self.connection.execute(
            "SELECT * FROM semantic_objects WHERE object_id = ? AND deleted_at IS NULL",
            (str(object_id),),
        ).fetchone()
        if row is None:
            raise KeyError(f"semantic object {object_id} not found")
        return self._semantic_from_row(row)

    def list_semantic_objects(self, project_id: UUID) -> Tuple[SemanticObjectRecord, ...]:
        return tuple(
            self._semantic_from_row(row)
            for row in self.connection.execute(
                """
                SELECT * FROM semantic_objects
                WHERE project_id = ? AND deleted_at IS NULL
                ORDER BY object_type, object_id
                """,
                (str(project_id),),
            )
        )

    def query_semantic_objects(
        self,
        project_id: UUID,
        bounds: BoundingBox2D,
    ) -> Tuple[SemanticObjectRecord, ...]:
        return tuple(
            self._semantic_from_row(row)
            for row in self.connection.execute(
                """
                SELECT object.*
                FROM semantic_object_rtree spatial
                JOIN semantic_objects object ON object.spatial_id = spatial.spatial_id
                WHERE object.project_id = ?
                  AND object.deleted_at IS NULL
                  AND spatial.min_x <= ? AND spatial.max_x >= ?
                  AND spatial.min_y <= ? AND spatial.max_y >= ?
                ORDER BY object.object_type, object.object_id
                """,
                (
                    str(project_id),
                    bounds.max_x,
                    bounds.min_x,
                    bounds.max_y,
                    bounds.min_y,
                ),
            )
        )

    def list_relationships(self, project_id: UUID) -> Tuple[RelationshipRecord, ...]:
        return tuple(
            self._relationship_from_row(row)
            for row in self.connection.execute(
                """
                SELECT * FROM relationships
                WHERE project_id = ? AND deleted_at IS NULL
                ORDER BY relationship_type, relationship_id
                """,
                (str(project_id),),
            )
        )

    def dataset_rows(self, project_id: UUID) -> Tuple[DatasetRow, ...]:
        rows: List[DatasetRow] = []
        for entity in self.list_raw_entities(project_id):
            rows.append(
                DatasetRow(
                    record_type=RecordType.RAW_ENTITY,
                    record_id=entity.entity_id,
                    type_name=entity.entity_type,
                    name_or_mark=entity.properties.get("name_or_mark"),
                    storey_id=entity.storey_id,
                    review_status=entity.review_status,
                    revision_id=entity.revision_id,
                    bounding_box=entity.bounding_box,
                )
            )
        for value in self.list_semantic_objects(project_id):
            rows.append(
                DatasetRow(
                    record_type=RecordType.SEMANTIC_OBJECT,
                    record_id=value.object_id,
                    type_name=value.object_type,
                    name_or_mark=value.name_or_mark,
                    storey_id=value.storey_id,
                    review_status=value.review_status,
                    revision_id=value.revision_id,
                    bounding_box=value.bounding_box,
                )
            )
        return tuple(sorted(rows, key=lambda row: (row.record_type.value, row.type_name, str(row.record_id))))

    def list_revisions(self, project_id: UUID) -> Tuple[RevisionRecord, ...]:
        return tuple(
            RevisionRecord(
                revision_id=_uuid(row["revision_id"]),
                project_id=_uuid(row["project_id"]),
                parent_revision_id=(
                    _uuid(row["parent_revision_id"])
                    if row["parent_revision_id"]
                    else None
                ),
                actor_id=row["actor_id"],
                actor_role=ActorRole(row["actor_role"]),
                reason=row["reason"],
                status=row["status"],
                created_at=_dt(row["created_at"]),
                committed_at=_dt(row["committed_at"]),
            )
            for row in self.connection.execute(
                "SELECT * FROM revisions WHERE project_id = ? ORDER BY created_at, revision_id",
                (str(project_id),),
            )
        )

    def list_audit_events(self, project_id: UUID) -> Tuple[AuditEventRecord, ...]:
        return tuple(
            AuditEventRecord(
                event_id=_uuid(row["event_id"]),
                project_id=_uuid(row["project_id"]),
                revision_id=_uuid(row["revision_id"]),
                actor_id=row["actor_id"],
                actor_role=ActorRole(row["actor_role"]),
                action=row["action"],
                record_type=RecordType(row["record_type"]),
                record_id=_uuid(row["record_id"]),
                changed_fields=tuple(_load(row["changed_fields_json"], [])),
                details=_load(row["details_json"], {}),
                created_at=_dt(row["created_at"]),
            )
            for row in self.connection.execute(
                "SELECT * FROM audit_events WHERE project_id = ? ORDER BY created_at, event_id",
                (str(project_id),),
            )
        )

    def list_documents(self, project_id: UUID) -> Tuple[DocumentRecord, ...]:
        return tuple(self._document_from_row(row) for row in self.connection.execute(
            "SELECT * FROM documents WHERE project_id = ? ORDER BY document_id", (str(project_id),)
        ))

    def list_pages(self, project_id: UUID) -> Tuple[PageRecord, ...]:
        return tuple(self._page_from_row(row) for row in self.connection.execute(
            "SELECT * FROM pages WHERE project_id = ? ORDER BY document_id, page_index", (str(project_id),)
        ))

    def semantic_object_ids_for_entity(self, entity_id: UUID) -> Tuple[UUID, ...]:
        return tuple(
            _uuid(row["object_id"])
            for row in self.connection.execute(
                "SELECT object_id FROM object_entity_links WHERE entity_id = ? ORDER BY object_id",
                (str(entity_id),),
            )
        )

    def list_links(self, project_id: UUID) -> Tuple[ObjectEntityLink, ...]:
        return tuple(ObjectEntityLink(
            link_id=_uuid(row["link_id"]), project_id=_uuid(row["project_id"]),
            object_id=_uuid(row["object_id"]), entity_id=_uuid(row["entity_id"]),
            role=row["role"], revision_id=_uuid(row["revision_id"]),
        ) for row in self.connection.execute(
            "SELECT * FROM object_entity_links WHERE project_id = ? ORDER BY link_id", (str(project_id),)
        ))

    def list_import_batches(self, project_id: UUID) -> Tuple[ImportBatchRecord, ...]:
        return tuple(ImportBatchRecord(
            import_batch_id=_uuid(row["import_batch_id"]), project_id=_uuid(row["project_id"]),
            revision_id=_uuid(row["revision_id"]), source_path=row["source_path"],
            source_sha256=row["source_sha256"], importer=row["importer"],
            imported_count=row["imported_count"], warning_count=row["warning_count"],
            report=_load(row["report_json"], {}), created_at=_dt(row["created_at"]),
        ) for row in self.connection.execute(
            "SELECT * FROM import_batches WHERE project_id = ? ORDER BY created_at", (str(project_id),)
        ))

    def snapshot_records(self, project_id: UUID) -> Tuple[Tuple[RecordType, object], ...]:
        project = self.get_project(project_id)
        result: List[Tuple[RecordType, object]] = [(RecordType.PROJECT, project)]
        result.extend((RecordType.REVISION, value) for value in self.list_revisions(project_id))
        result.extend((RecordType.DOCUMENT, value) for value in self.list_documents(project_id))
        result.extend((RecordType.PAGE, value) for value in self.list_pages(project_id))
        result.extend((RecordType.RAW_ENTITY, value) for value in self.list_raw_entities(project_id))
        result.extend((RecordType.SEMANTIC_OBJECT, value) for value in self.list_semantic_objects(project_id))
        result.extend((RecordType.OBJECT_ENTITY_LINK, value) for value in self.list_links(project_id))
        result.extend((RecordType.RELATIONSHIP, value) for value in self.list_relationships(project_id))
        result.extend((RecordType.AUDIT_EVENT, value) for value in self.list_audit_events(project_id))
        result.extend((RecordType.IMPORT_BATCH, value) for value in self.list_import_batches(project_id))
        return tuple(result)

    def restore_snapshot(
        self,
        envelopes: Iterable[JsonlEnvelope],
        *,
        duplicate_policy: str = "error",
    ) -> Dict[str, int]:
        if duplicate_policy not in {"error", "skip"}:
            raise ValueError("duplicate_policy must be 'error' or 'skip'")
        validated = [(envelope.record_type, validate_envelope(envelope)) for envelope in envelopes]
        order = {
            RecordType.PROJECT: 0,
            RecordType.REVISION: 1,
            RecordType.DOCUMENT: 2,
            RecordType.PAGE: 3,
            RecordType.RAW_ENTITY: 4,
            RecordType.SEMANTIC_OBJECT: 5,
            RecordType.OBJECT_ENTITY_LINK: 6,
            RecordType.RELATIONSHIP: 7,
            RecordType.AUDIT_EVENT: 8,
            RecordType.IMPORT_BATCH: 9,
        }
        validated.sort(key=lambda item: order[item[0]])
        counts = {record_type.value: 0 for record_type in RecordType}
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for record_type, model in validated:
                inserted = self._restore_model(record_type, model, duplicate_policy)
                counts[record_type.value] += int(inserted)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return counts

    def _restore_model(self, record_type: RecordType, model, duplicate_policy: str) -> bool:
        before = self.connection.total_changes
        prefix = "INSERT OR IGNORE" if duplicate_policy == "skip" else "INSERT"
        if record_type is RecordType.PROJECT:
            self._insert_project(model, prefix=prefix)
        elif record_type is RecordType.REVISION:
            self._insert_revision(model, prefix=prefix)
        elif record_type is RecordType.DOCUMENT:
            self._insert_document(model, prefix=prefix)
        elif record_type is RecordType.PAGE:
            self._insert_page(model, prefix=prefix)
        elif record_type is RecordType.RAW_ENTITY:
            self._insert_raw(model, prefix=prefix)
        elif record_type is RecordType.SEMANTIC_OBJECT:
            self._insert_semantic(model, prefix=prefix)
        elif record_type is RecordType.OBJECT_ENTITY_LINK:
            self._insert_link(model, prefix=prefix)
        elif record_type is RecordType.RELATIONSHIP:
            self._insert_relationship(model, prefix=prefix)
        elif record_type is RecordType.AUDIT_EVENT:
            self._insert_audit_event(model, prefix=prefix)
        elif record_type is RecordType.IMPORT_BATCH:
            self._insert_import_batch(model, prefix=prefix)
        else:
            raise ValueError(f"unsupported snapshot record type: {record_type.value}")
        return self.connection.total_changes > before

    def _insert_project(self, record: ProjectRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO projects(
                project_id, schema_version, name, description, current_revision_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(record.project_id), record.schema_version, record.name, record.description,
                str(record.current_revision_id) if record.current_revision_id else None,
                _iso(record.created_at), _iso(record.updated_at),
            ),
        )

    def _insert_revision(self, record: RevisionRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO revisions(
                revision_id, project_id, parent_revision_id, actor_id, actor_role,
                reason, status, created_at, committed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(record.revision_id), str(record.project_id),
                str(record.parent_revision_id) if record.parent_revision_id else None,
                record.actor_id, record.actor_role.value, record.reason, record.status,
                _iso(record.created_at), _iso(record.committed_at),
            ),
        )

    def _insert_document(self, record: DocumentRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO documents(
                document_id, project_id, schema_version, title, source_path,
                source_sha256, media_type, revision_id, review_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.document_id), str(record.project_id), record.schema_version, record.title,
             record.source_path, record.source_sha256, record.media_type, str(record.revision_id),
             record.review_status.value, _iso(record.created_at), _iso(record.updated_at)),
        )

    def _insert_page(self, record: PageRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO pages(
                page_id, project_id, document_id, schema_version, page_index, name,
                width, height, coordinate_system_id, properties_json, revision_id,
                review_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.page_id), str(record.project_id), str(record.document_id), record.schema_version,
             record.page_index, record.name, record.width, record.height, record.coordinate_system_id,
             _dump(record.properties), str(record.revision_id), record.review_status.value,
             _iso(record.created_at), _iso(record.updated_at)),
        )

    def _insert_raw(self, record: RawEntityRecord, *, prefix: str = "INSERT") -> None:
        box = record.bounding_box
        self.connection.execute(
            f"""{prefix} INTO raw_entities(
                entity_id, project_id, schema_version, entity_type, geometry_json,
                coordinate_system_id, storey_id, layer_id, style_id,
                min_x, max_x, min_y, max_y, provenance_json, confidence,
                review_status, properties_json, revision_id, content_hash,
                created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.entity_id), str(record.project_id), record.schema_version, record.entity_type,
             _dump(record.geometry.model_dump(mode="json")), record.coordinate_system_id,
             record.storey_id, record.layer_id, record.style_id, box.min_x, box.max_x,
             box.min_y, box.max_y, _dump(record.provenance.model_dump(mode="json", exclude_none=True)),
             record.confidence, record.review_status.value, _dump(record.properties),
             str(record.revision_id), record.content_hash, _iso(record.created_at),
             _iso(record.updated_at), _iso(record.deleted_at)),
        )

    def _insert_semantic(self, record: SemanticObjectRecord, *, prefix: str = "INSERT") -> None:
        box = record.bounding_box
        self.connection.execute(
            f"""{prefix} INTO semantic_objects(
                object_id, project_id, schema_version, object_type, name_or_mark,
                storey_id, geometry_reference, min_x, max_x, min_y, max_y,
                properties_json, source_entity_ids_json, confidence, review_status,
                revision_id, content_hash, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.object_id), str(record.project_id), record.schema_version, record.object_type,
             record.name_or_mark, record.storey_id,
             str(record.geometry_reference) if record.geometry_reference else None,
             box.min_x if box else None, box.max_x if box else None,
             box.min_y if box else None, box.max_y if box else None,
             _dump(record.properties), _dump([str(value) for value in record.source_entity_ids]),
             record.confidence, record.review_status.value, str(record.revision_id),
             record.content_hash, _iso(record.created_at), _iso(record.updated_at),
             _iso(record.deleted_at)),
        )

    def _insert_link(self, record: ObjectEntityLink, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO object_entity_links(
                link_id, project_id, object_id, entity_id, role, revision_id
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (str(record.link_id), str(record.project_id), str(record.object_id),
             str(record.entity_id), record.role, str(record.revision_id)),
        )

    def _insert_relationship(self, record: RelationshipRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO relationships(
                relationship_id, project_id, schema_version, relationship_type,
                source_id, target_id, properties_json, review_status, revision_id,
                content_hash, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.relationship_id), str(record.project_id), record.schema_version,
             record.relationship_type.value, str(record.source_id), str(record.target_id),
             _dump(record.properties), record.review_status.value, str(record.revision_id),
             record.content_hash, _iso(record.created_at), _iso(record.updated_at),
             _iso(record.deleted_at)),
        )

    def _insert_audit_event(self, record: AuditEventRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO audit_events(
                event_id, project_id, revision_id, actor_id, actor_role, action,
                record_type, record_id, changed_fields_json, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.event_id), str(record.project_id), str(record.revision_id),
             record.actor_id, record.actor_role.value, record.action, record.record_type.value,
             str(record.record_id), _dump(record.changed_fields), _dump(record.details),
             _iso(record.created_at)),
        )

    def _insert_import_batch(self, record: ImportBatchRecord, *, prefix: str = "INSERT") -> None:
        self.connection.execute(
            f"""{prefix} INTO import_batches(
                import_batch_id, project_id, revision_id, source_path, source_sha256,
                importer, imported_count, warning_count, report_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(record.import_batch_id), str(record.project_id), str(record.revision_id),
             record.source_path, record.source_sha256, record.importer, record.imported_count,
             record.warning_count, _dump(record.report), _iso(record.created_at)),
        )

    def _raw_from_row(self, row: sqlite3.Row) -> RawEntityRecord:
        return RawEntityRecord.model_validate({
            "entity_id": row["entity_id"], "project_id": row["project_id"],
            "schema_version": row["schema_version"], "entity_type": row["entity_type"],
            "geometry": _load(row["geometry_json"], {}),
            "coordinate_system_id": row["coordinate_system_id"], "storey_id": row["storey_id"],
            "layer_id": row["layer_id"], "style_id": row["style_id"],
            "provenance": _load(row["provenance_json"], {}), "confidence": row["confidence"],
            "review_status": row["review_status"], "properties": _load(row["properties_json"], {}),
            "revision_id": row["revision_id"], "content_hash": row["content_hash"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "deleted_at": row["deleted_at"],
        })

    def _semantic_from_row(self, row: sqlite3.Row) -> SemanticObjectRecord:
        box = None if row["min_x"] is None else {
            "min_x": row["min_x"], "max_x": row["max_x"],
            "min_y": row["min_y"], "max_y": row["max_y"],
        }
        return SemanticObjectRecord.model_validate({
            "object_id": row["object_id"], "project_id": row["project_id"],
            "schema_version": row["schema_version"], "object_type": row["object_type"],
            "name_or_mark": row["name_or_mark"], "storey_id": row["storey_id"],
            "geometry_reference": row["geometry_reference"], "bounding_box": box,
            "properties": _load(row["properties_json"], {}),
            "source_entity_ids": _load(row["source_entity_ids_json"], []),
            "confidence": row["confidence"], "review_status": row["review_status"],
            "revision_id": row["revision_id"], "content_hash": row["content_hash"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "deleted_at": row["deleted_at"],
        })

    def _relationship_from_row(self, row: sqlite3.Row) -> RelationshipRecord:
        return RelationshipRecord.model_validate({
            "relationship_id": row["relationship_id"], "project_id": row["project_id"],
            "schema_version": row["schema_version"], "relationship_type": row["relationship_type"],
            "source_id": row["source_id"], "target_id": row["target_id"],
            "properties": _load(row["properties_json"], {}),
            "review_status": row["review_status"], "revision_id": row["revision_id"],
            "content_hash": row["content_hash"], "created_at": row["created_at"],
            "updated_at": row["updated_at"], "deleted_at": row["deleted_at"],
        })

    def _document_from_row(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord.model_validate(dict(row))

    def _page_from_row(self, row: sqlite3.Row) -> PageRecord:
        value = dict(row)
        value["properties"] = _load(value.pop("properties_json"), {})
        return PageRecord.model_validate(value)


class RevisionSession(AbstractContextManager["RevisionSession"]):
    def __init__(
        self,
        repository: DatasetRepository,
        *,
        project_id: UUID,
        actor_id: str,
        actor_role: ActorRole,
        reason: str,
        parent_revision_id: Optional[UUID],
    ) -> None:
        self.repository = repository
        self.connection = repository.connection
        self.project_id = _uuid(project_id)
        self.actor_id = actor_id
        self.actor_role = ActorRole(actor_role)
        self.reason = reason.strip()
        if not self.reason:
            raise ValueError("revision reason must not be empty")
        if parent_revision_id is None:
            project = repository.get_project(self.project_id)
            parent_revision_id = project.current_revision_id
        self.revision = RevisionRecord(
            project_id=self.project_id,
            parent_revision_id=parent_revision_id,
            actor_id=actor_id,
            actor_role=self.actor_role,
            reason=self.reason,
        )
        self._entered = False

    @property
    def revision_id(self) -> UUID:
        return self.revision.revision_id

    def __enter__(self) -> "RevisionSession":
        if self._entered:
            raise RuntimeError("revision session cannot be entered twice")
        self.connection.execute("BEGIN IMMEDIATE")
        self.repository._insert_revision(self.revision)
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self._entered:
            return
        if exc_type is not None:
            self.connection.rollback()
            return
        committed_at = utc_now()
        self.connection.execute(
            "UPDATE revisions SET status = 'committed', committed_at = ? WHERE revision_id = ?",
            (_iso(committed_at), str(self.revision_id)),
        )
        self.connection.execute(
            "UPDATE projects SET current_revision_id = ?, updated_at = ? WHERE project_id = ?",
            (str(self.revision_id), _iso(committed_at), str(self.project_id)),
        )
        self.connection.commit()

    def add_document(self, draft: DocumentDraft) -> DocumentRecord:
        self._require_project(draft.project_id)
        validate_initial_status(ReviewStatus.UNREVIEWED, self.actor_role)
        now = utc_now()
        record = DocumentRecord(
            **draft.model_dump(), revision_id=self.revision_id,
            review_status=ReviewStatus.UNREVIEWED, created_at=now, updated_at=now,
        )
        self.repository._insert_document(record)
        self._audit("create", RecordType.DOCUMENT, record.document_id, tuple(draft.model_fields_set))
        return record

    def add_page(self, draft: PageDraft) -> PageRecord:
        self._require_project(draft.project_id)
        validate_initial_status(ReviewStatus.UNREVIEWED, self.actor_role)
        now = utc_now()
        record = PageRecord(
            **draft.model_dump(), revision_id=self.revision_id,
            review_status=ReviewStatus.UNREVIEWED, created_at=now, updated_at=now,
        )
        self.repository._insert_page(record)
        self._audit("create", RecordType.PAGE, record.page_id, tuple(draft.model_fields_set))
        return record

    def add_raw_entity(self, draft: RawEntityDraft) -> RawEntityRecord:
        self._require_project(draft.project_id)
        validate_initial_status(draft.review_status, self.actor_role)
        now = utc_now()
        digest = content_hash(draft.model_dump(mode="json", exclude={"review_status"}))
        record = RawEntityRecord(
            **draft.model_dump(), revision_id=self.revision_id, content_hash=digest,
            created_at=now, updated_at=now,
        )
        self.repository._insert_raw(record)
        self._audit("create", RecordType.RAW_ENTITY, record.entity_id, tuple(draft.model_fields_set))
        return record

    def add_semantic_object(self, draft: SemanticObjectDraft) -> SemanticObjectRecord:
        self._require_project(draft.project_id)
        validate_initial_status(draft.review_status, self.actor_role)
        now = utc_now()
        record = SemanticObjectRecord(
            **draft.model_dump(), revision_id=self.revision_id, content_hash=content_hash(draft.model_dump(mode="json", exclude={"review_status"})),
            created_at=now, updated_at=now,
        )
        self.repository._insert_semantic(record)
        self._audit("create", RecordType.SEMANTIC_OBJECT, record.object_id, tuple(draft.model_fields_set))
        for entity_id in draft.source_entity_ids:
            self.add_object_entity_link(record.object_id, entity_id, role="source")
        return record

    def add_object_entity_link(self, object_id: UUID, entity_id: UUID, *, role: str = "source") -> ObjectEntityLink:
        link = ObjectEntityLink(
            project_id=self.project_id, object_id=object_id, entity_id=entity_id,
            role=role, revision_id=self.revision_id,
        )
        self.repository._insert_link(link)
        self._audit("create", RecordType.OBJECT_ENTITY_LINK, link.link_id, ("object_id", "entity_id", "role"))
        return link

    def add_relationship(self, draft: RelationshipDraft) -> RelationshipRecord:
        self._require_project(draft.project_id)
        validate_initial_status(draft.review_status, self.actor_role)
        now = utc_now()
        record = RelationshipRecord(
            **draft.model_dump(), revision_id=self.revision_id, content_hash=content_hash(draft.model_dump(mode="json", exclude={"review_status"})),
            created_at=now, updated_at=now,
        )
        self.repository._insert_relationship(record)
        self._audit("create", RecordType.RELATIONSHIP, record.relationship_id, tuple(draft.model_fields_set))
        return record

    def add_import_batch(self, record: ImportBatchRecord) -> None:
        if record.project_id != self.project_id or record.revision_id != self.revision_id:
            raise ValueError("import batch must belong to the active project and revision")
        self.repository._insert_import_batch(record)
        self._audit("create", RecordType.IMPORT_BATCH, record.import_batch_id, ("source_path", "source_sha256", "imported_count", "warning_count"))

    def update_review_status(self, record_type: RecordType, record_id: UUID, target: ReviewStatus) -> None:
        table, id_column = {
            RecordType.DOCUMENT: ("documents", "document_id"),
            RecordType.PAGE: ("pages", "page_id"),
            RecordType.RAW_ENTITY: ("raw_entities", "entity_id"),
            RecordType.SEMANTIC_OBJECT: ("semantic_objects", "object_id"),
            RecordType.RELATIONSHIP: ("relationships", "relationship_id"),
        }.get(record_type, (None, None))
        if table is None:
            raise ValueError(f"review status is not supported for {record_type.value}")
        row = self.connection.execute(
            f"SELECT project_id, review_status FROM {table} WHERE {id_column} = ?",
            (str(record_id),),
        ).fetchone()
        if row is None:
            raise KeyError(f"record {record_id} not found")
        self._require_project(_uuid(row["project_id"]))
        current = ReviewStatus(row["review_status"])
        target = ReviewStatus(target)
        validate_review_transition(current, target, self.actor_role)
        assignments = "review_status = ?, revision_id = ?"
        parameters: List[object] = [target.value, str(self.revision_id)]
        if table in {"documents", "pages", "raw_entities", "semantic_objects", "relationships"}:
            assignments += ", updated_at = ?"
            parameters.append(_iso(utc_now()))
        parameters.append(str(record_id))
        self.connection.execute(
            f"UPDATE {table} SET {assignments} WHERE {id_column} = ?",
            tuple(parameters),
        )
        self._audit(
            "review_status",
            record_type,
            record_id,
            ("review_status",),
            {"from": current.value, "to": target.value},
        )

    def _audit(
        self,
        action: str,
        record_type: RecordType,
        record_id: UUID,
        changed_fields: Sequence[str],
        details: Optional[Dict[str, object]] = None,
    ) -> AuditEventRecord:
        event = AuditEventRecord(
            project_id=self.project_id,
            revision_id=self.revision_id,
            actor_id=self.actor_id,
            actor_role=self.actor_role,
            action=action,
            record_type=record_type,
            record_id=record_id,
            changed_fields=tuple(sorted(set(changed_fields))),
            details=details or {},
        )
        self.repository._insert_audit_event(event)
        return event

    def _require_project(self, project_id: UUID) -> None:
        if _uuid(project_id) != self.project_id:
            raise ValueError("record belongs to a different project")
