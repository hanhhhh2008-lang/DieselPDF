from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple, Union

from dieselpdf.domain.dataset import (
    AuditEvent,
    DocumentRecord,
    GeometryEntity,
    PageRecord,
    ProjectRecord,
    RelationshipRecord,
    ReviewDecision,
    ReviewStatus,
    RevisionRecord,
    SemanticObject,
    require_review_transition,
)

from .migrations import apply_migrations


class StoreError(RuntimeError):
    pass


Record = Union[GeometryEntity, SemanticObject, RelationshipRecord]


class ProjectStore:
    """Transactional SQLite owner for the Phase 3 engineering dataset."""

    def __init__(self, path: Union[str, os.PathLike[str]], connection: sqlite3.Connection):
        self.path = Path(path)
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def create(
        cls,
        path: Union[str, os.PathLike[str]],
        project: ProjectRecord,
        initial_revision: RevisionRecord,
    ) -> "ProjectStore":
        target = Path(path)
        if target.exists() and target.stat().st_size:
            raise FileExistsError(f"dataset already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(target))
        store = cls(target, connection)
        try:
            apply_migrations(connection)
            if initial_revision.project_id != project.project_id:
                raise StoreError("initial revision belongs to a different project")
            if initial_revision.sequence != 1 or initial_revision.parent_revision_id is not None:
                raise StoreError("initial revision must be sequence 1 without a parent")
            with store.transaction():
                connection.execute(
                    """
                    INSERT INTO projects(
                        project_id, schema_version, name, description, created_at,
                        metadata_json, current_revision_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.project_id,
                        project.schema_version,
                        project.name,
                        project.description,
                        project.created_at.isoformat(),
                        json.dumps(project.metadata, sort_keys=True, separators=(",", ":")),
                        initial_revision.revision_id,
                    ),
                )
                store._insert_revision(initial_revision)
            return store
        except Exception:
            connection.close()
            if target.exists():
                target.unlink()
            raise

    @classmethod
    def open(cls, path: Union[str, os.PathLike[str]]) -> "ProjectStore":
        target = Path(path)
        if not target.is_file():
            raise FileNotFoundError(target)
        connection = sqlite3.connect(str(target))
        store = cls(target, connection)
        apply_migrations(connection)
        return store

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ProjectStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self.connection.in_transaction:
            yield
            return
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def project(self) -> ProjectRecord:
        row = self.connection.execute("SELECT * FROM projects LIMIT 1").fetchone()
        if row is None:
            raise StoreError("dataset contains no project")
        return ProjectRecord(
            project_id=row["project_id"],
            schema_version=row["schema_version"],
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def current_revision_id(self) -> str:
        row = self.connection.execute(
            "SELECT current_revision_id FROM projects LIMIT 1"
        ).fetchone()
        if row is None or row[0] is None:
            raise StoreError("project has no current revision")
        return str(row[0])

    def revisions(self) -> Tuple[RevisionRecord, ...]:
        rows = self.connection.execute(
            "SELECT * FROM revisions ORDER BY sequence"
        ).fetchall()
        return tuple(self._revision_from_row(row) for row in rows)

    def add_revision(self, revision: RevisionRecord) -> RevisionRecord:
        project = self.project()
        if revision.project_id != project.project_id:
            raise StoreError("revision belongs to a different project")
        rows = self.revisions()
        expected_sequence = len(rows) + 1
        expected_parent = rows[-1].revision_id if rows else None
        if revision.sequence != expected_sequence:
            raise StoreError(f"revision sequence must be {expected_sequence}")
        if revision.parent_revision_id != expected_parent:
            raise StoreError("revision parent must be the current project revision")
        with self.transaction():
            self._insert_revision(revision)
            self.connection.execute(
                "UPDATE projects SET current_revision_id = ? WHERE project_id = ?",
                (revision.revision_id, project.project_id),
            )
        return revision

    def add_entity(self, entity: GeometryEntity) -> GeometryEntity:
        with self.transaction():
            self._put_entity(entity)
        return entity

    def add_document(self, document: DocumentRecord) -> DocumentRecord:
        self._assert_project(document.project_id)
        self._assert_revision(document.project_id, document.revision_id)
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO documents(
                    document_id, project_id, revision_id, source_hash, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    document.document_id,
                    document.project_id,
                    document.revision_id,
                    document.source_hash,
                    document.model_dump_json(),
                    document.created_at.isoformat(),
                ),
            )
        return document

    def add_page(self, page: PageRecord) -> PageRecord:
        self._assert_project(page.project_id)
        self._assert_revision(page.project_id, page.revision_id)
        document = self.document(page.document_id)
        if document.project_id != page.project_id:
            raise StoreError("page document belongs to a different project")
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO pages(
                    page_id, project_id, document_id, revision_id,
                    page_index, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page.page_id,
                    page.project_id,
                    page.document_id,
                    page.revision_id,
                    page.page_index,
                    page.model_dump_json(),
                    page.created_at.isoformat(),
                ),
            )
        return page

    def add_semantic_object(self, value: SemanticObject) -> SemanticObject:
        with self.transaction():
            self._put_semantic_object(value)
        return value

    def add_relationship(self, value: RelationshipRecord) -> RelationshipRecord:
        with self.transaction():
            self._put_relationship(value)
        return value

    def entity(self, entity_id: str) -> GeometryEntity:
        row = self.connection.execute(
            """
            SELECT payload_json FROM entity_versions
            WHERE entity_id = ? ORDER BY version_sequence DESC LIMIT 1
            """,
            (entity_id,),
        ).fetchone()
        if row is None:
            raise KeyError(entity_id)
        return GeometryEntity.model_validate_json(row[0])

    def document(self, document_id: str) -> DocumentRecord:
        row = self.connection.execute(
            "SELECT payload_json FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise KeyError(document_id)
        return DocumentRecord.model_validate_json(row[0])

    def documents(self) -> Tuple[DocumentRecord, ...]:
        rows = self.connection.execute(
            "SELECT payload_json FROM documents ORDER BY document_id"
        ).fetchall()
        return tuple(DocumentRecord.model_validate_json(row[0]) for row in rows)

    def page(self, page_id: str) -> PageRecord:
        row = self.connection.execute(
            "SELECT payload_json FROM pages WHERE page_id = ?", (page_id,)
        ).fetchone()
        if row is None:
            raise KeyError(page_id)
        return PageRecord.model_validate_json(row[0])

    def pages(self, document_id: Optional[str] = None) -> Tuple[PageRecord, ...]:
        if document_id is None:
            rows = self.connection.execute(
                "SELECT payload_json FROM pages ORDER BY document_id, page_index"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT payload_json FROM pages WHERE document_id = ? ORDER BY page_index",
                (document_id,),
            ).fetchall()
        return tuple(PageRecord.model_validate_json(row[0]) for row in rows)

    def semantic_object(self, object_id: str) -> SemanticObject:
        row = self.connection.execute(
            """
            SELECT payload_json FROM semantic_object_versions
            WHERE object_id = ? ORDER BY version_sequence DESC LIMIT 1
            """,
            (object_id,),
        ).fetchone()
        if row is None:
            raise KeyError(object_id)
        return SemanticObject.model_validate_json(row[0])

    def relationship(self, relationship_id: str) -> RelationshipRecord:
        row = self.connection.execute(
            """
            SELECT payload_json FROM relationship_versions
            WHERE relationship_id = ? ORDER BY version_sequence DESC LIMIT 1
            """,
            (relationship_id,),
        ).fetchone()
        if row is None:
            raise KeyError(relationship_id)
        return RelationshipRecord.model_validate_json(row[0])

    def item(self, item_kind: str, item_id: str) -> Record:
        return self._item(item_kind, item_id)

    def entities(self, include_superseded: bool = False) -> Tuple[GeometryEntity, ...]:
        rows = self._latest_rows("entity_versions", "entity_id")
        values = tuple(GeometryEntity.model_validate_json(row[0]) for row in rows)
        if include_superseded:
            return values
        return tuple(value for value in values if value.review_status is not ReviewStatus.SUPERSEDED)

    def semantic_objects(self, include_superseded: bool = False) -> Tuple[SemanticObject, ...]:
        rows = self._latest_rows("semantic_object_versions", "object_id")
        values = tuple(SemanticObject.model_validate_json(row[0]) for row in rows)
        if include_superseded:
            return values
        return tuple(value for value in values if value.review_status is not ReviewStatus.SUPERSEDED)

    def relationships(self, include_superseded: bool = False) -> Tuple[RelationshipRecord, ...]:
        rows = self._latest_rows("relationship_versions", "relationship_id")
        values = tuple(RelationshipRecord.model_validate_json(row[0]) for row in rows)
        if include_superseded:
            return values
        return tuple(value for value in values if value.review_status is not ReviewStatus.SUPERSEDED)

    def entities_in_bounds(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> Tuple[GeometryEntity, ...]:
        if min_x > max_x or min_y > max_y:
            raise ValueError("query minimums must not exceed maximums")
        rows = self.connection.execute(
            """
            WITH latest AS (
                SELECT entity_id, MAX(version_sequence) AS version_sequence
                FROM entity_versions GROUP BY entity_id
            )
            SELECT versions.payload_json
            FROM latest
            JOIN entity_versions AS versions
              ON versions.entity_id = latest.entity_id
             AND versions.version_sequence = latest.version_sequence
            JOIN entity_rtree AS spatial ON spatial.version_pk = versions.version_pk
            WHERE spatial.max_x >= ? AND spatial.min_x <= ?
              AND spatial.max_y >= ? AND spatial.min_y <= ?
            ORDER BY versions.entity_id
            """,
            (min_x, max_x, min_y, max_y),
        ).fetchall()
        return tuple(GeometryEntity.model_validate_json(row[0]) for row in rows)

    def record_audit_event(self, event: AuditEvent) -> AuditEvent:
        self._assert_project(event.project_id)
        if event.revision_id is not None:
            self._assert_revision(event.project_id, event.revision_id)
        with self.transaction():
            self._insert_audit_event(event)
        return event

    def audit_events(self) -> Tuple[AuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events ORDER BY created_at, event_id"
        ).fetchall()
        return tuple(
            AuditEvent(
                event_id=row["event_id"],
                project_id=row["project_id"],
                revision_id=row["revision_id"],
                event_type=row["event_type"],
                actor=json.loads(row["actor_json"]),
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        )

    def record_import_run(
        self,
        *,
        import_id: str,
        project_id: str,
        revision_id: str,
        source_path: str,
        source_hash: str,
        source_payload: object,
        report: object,
        created_at: str,
        legacy_ids: Sequence[Tuple[str, str, str]],
    ) -> None:
        """Persist the immutable source payload, report, and deterministic ID map."""
        self._assert_project(project_id)
        self._assert_revision(project_id, revision_id)
        source_payload_json = json.dumps(
            source_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        report_json = json.dumps(report, sort_keys=True, separators=(",", ":"))
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO import_runs(
                    import_id, project_id, revision_id, source_path, source_hash,
                    source_payload_json, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_id,
                    project_id,
                    revision_id,
                    source_path,
                    source_hash,
                    source_payload_json,
                    report_json,
                    created_at,
                ),
            )
            for legacy_key, record_kind, stable_id in legacy_ids:
                self.connection.execute(
                    """
                    INSERT INTO legacy_id_map(
                        project_id, source_hash, legacy_key, record_kind, stable_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (project_id, source_hash, legacy_key, record_kind, stable_id),
                )

    def import_runs(self) -> Tuple[sqlite3.Row, ...]:
        return tuple(
            self.connection.execute(
                "SELECT * FROM import_runs ORDER BY created_at, import_id"
            ).fetchall()
        )

    def legacy_id_map(self) -> Tuple[sqlite3.Row, ...]:
        return tuple(
            self.connection.execute(
                """
                SELECT project_id, source_hash, legacy_key, record_kind, stable_id
                FROM legacy_id_map ORDER BY source_hash, legacy_key
                """
            ).fetchall()
        )

    def apply_review_decision(self, decision: ReviewDecision) -> Record:
        self._assert_project(decision.project_id)
        self._assert_revision(decision.project_id, decision.revision_id)
        updated = self._updated_review_item(decision)
        with self.transaction():
            self._put_review_item(updated)
            self._insert_review_decision(decision)
        return updated

    def apply_review_revision(
        self, revision: RevisionRecord, decision: ReviewDecision
    ) -> Record:
        """Atomically append a review revision, version, and human decision."""
        project = self.project()
        revisions = self.revisions()
        expected_sequence = len(revisions) + 1
        expected_parent = revisions[-1].revision_id if revisions else None
        if revision.project_id != project.project_id:
            raise StoreError("review revision belongs to a different project")
        if revision.sequence != expected_sequence or revision.parent_revision_id != expected_parent:
            raise StoreError("review revision is not the next linear project revision")
        if decision.project_id != project.project_id or decision.revision_id != revision.revision_id:
            raise StoreError("review decision must belong to the appended revision")
        updated = self._updated_review_item(decision)
        with self.transaction():
            self._insert_revision(revision)
            self.connection.execute(
                "UPDATE projects SET current_revision_id = ? WHERE project_id = ?",
                (revision.revision_id, project.project_id),
            )
            self._put_review_item(updated)
            self._insert_review_decision(decision)
        return updated

    def review_decisions(self, item_id: Optional[str] = None) -> Tuple[ReviewDecision, ...]:
        if item_id is None:
            rows = self.connection.execute(
                "SELECT * FROM review_decisions ORDER BY created_at, decision_id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM review_decisions WHERE item_id = ? ORDER BY created_at, decision_id",
                (item_id,),
            ).fetchall()
        return tuple(
            ReviewDecision(
                decision_id=row["decision_id"],
                project_id=row["project_id"],
                revision_id=row["revision_id"],
                item_kind=row["item_kind"],
                item_id=row["item_id"],
                previous_status=row["previous_status"],
                decision=row["decision"],
                actor=json.loads(row["actor_json"]),
                comment=row["comment"],
                created_at=row["created_at"],
            )
            for row in rows
        )

    def integrity_check(self) -> Tuple[str, ...]:
        return tuple(row[0] for row in self.connection.execute("PRAGMA integrity_check"))

    def _insert_revision(self, revision: RevisionRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO revisions(
                revision_id, project_id, sequence, parent_revision_id,
                author_json, reason, status, created_at, source_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.revision_id,
                revision.project_id,
                revision.sequence,
                revision.parent_revision_id,
                revision.author.model_dump_json(),
                revision.reason,
                revision.status.value,
                revision.created_at.isoformat(),
                revision.source_revision,
            ),
        )

    def _put_entity(self, entity: GeometryEntity) -> None:
        self._assert_project(entity.project_id)
        self._assert_revision(entity.project_id, entity.revision_id)
        if entity.source.source_document_id is not None:
            try:
                source_document = self.document(entity.source.source_document_id)
            except KeyError as exc:
                raise StoreError(
                    f"entity source document does not exist: {entity.source.source_document_id}"
                ) from exc
            if source_document.project_id != entity.project_id:
                raise StoreError("entity source document belongs to a different project")
        if entity.source.source_page_id is not None:
            try:
                source_page = self.page(entity.source.source_page_id)
            except KeyError as exc:
                raise StoreError(
                    f"entity source page does not exist: {entity.source.source_page_id}"
                ) from exc
            if source_page.project_id != entity.project_id:
                raise StoreError("entity source page belongs to a different project")
            if (
                entity.source.source_document_id is not None
                and source_page.document_id != entity.source.source_document_id
            ):
                raise StoreError("entity source page does not belong to its source document")
        self.connection.execute(
            """
            INSERT OR IGNORE INTO entities(entity_id, project_id, entity_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                entity.entity_id,
                entity.project_id,
                entity.entity_type.value,
                entity.created_at.isoformat(),
            ),
        )
        identity = self.connection.execute(
            "SELECT project_id, entity_type FROM entities WHERE entity_id = ?",
            (entity.entity_id,),
        ).fetchone()
        if identity["project_id"] != entity.project_id or identity["entity_type"] != entity.entity_type.value:
            raise StoreError("stable entity identity cannot change project or type")
        self._require_next_version("entity_versions", "entity_id", entity.entity_id, entity.version_sequence)
        bbox = entity.bounding_box
        self.connection.execute(
            """
            INSERT INTO entity_versions(
                entity_id, revision_id, version_sequence, review_status,
                content_hash, min_x, max_x, min_y, max_y, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.entity_id,
                entity.revision_id,
                entity.version_sequence,
                entity.review_status.value,
                entity.content_hash,
                bbox.min_x,
                bbox.max_x,
                bbox.min_y,
                bbox.max_y,
                entity.model_dump_json(),
                entity.updated_at.isoformat(),
            ),
        )

    def _put_semantic_object(self, value: SemanticObject) -> None:
        self._assert_project(value.project_id)
        self._assert_revision(value.project_id, value.revision_id)
        for entity_id in value.source_entity_ids:
            if self.connection.execute(
                "SELECT 1 FROM entities WHERE entity_id = ?", (entity_id,)
            ).fetchone() is None:
                raise StoreError(f"semantic source entity does not exist: {entity_id}")
        self.connection.execute(
            """
            INSERT OR IGNORE INTO semantic_objects(object_id, project_id, object_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (value.object_id, value.project_id, value.object_type, value.created_at.isoformat()),
        )
        identity = self.connection.execute(
            "SELECT project_id, object_type FROM semantic_objects WHERE object_id = ?",
            (value.object_id,),
        ).fetchone()
        if identity["project_id"] != value.project_id or identity["object_type"] != value.object_type:
            raise StoreError("stable semantic identity cannot change project or type")
        self._require_next_version(
            "semantic_object_versions", "object_id", value.object_id, value.version_sequence
        )
        self.connection.execute(
            """
            INSERT INTO semantic_object_versions(
                object_id, revision_id, version_sequence, review_status,
                content_hash, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                value.object_id,
                value.revision_id,
                value.version_sequence,
                value.review_status.value,
                value.content_hash,
                value.model_dump_json(),
                value.updated_at.isoformat(),
            ),
        )
        for entity_id in value.source_entity_ids:
            self.connection.execute(
                """
                INSERT INTO object_entity_links(object_id, object_version_sequence, entity_id)
                VALUES (?, ?, ?)
                """,
                (value.object_id, value.version_sequence, entity_id),
            )

    def _put_relationship(self, value: RelationshipRecord) -> None:
        self._assert_project(value.project_id)
        self._assert_revision(value.project_id, value.revision_id)
        for item_id in (value.source_id, value.target_id):
            if not self._stable_item_exists(item_id):
                raise StoreError(f"relationship endpoint does not exist: {item_id}")
        self.connection.execute(
            """
            INSERT OR IGNORE INTO relationships(
                relationship_id, project_id, relationship_type, source_id, target_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                value.relationship_id,
                value.project_id,
                value.relationship_type.value,
                value.source_id,
                value.target_id,
                value.created_at.isoformat(),
            ),
        )
        identity = self.connection.execute(
            """
            SELECT project_id, relationship_type, source_id, target_id
            FROM relationships WHERE relationship_id = ?
            """,
            (value.relationship_id,),
        ).fetchone()
        if tuple(identity) != (
            value.project_id,
            value.relationship_type.value,
            value.source_id,
            value.target_id,
        ):
            raise StoreError("stable relationship identity cannot change type or endpoints")
        self._require_next_version(
            "relationship_versions", "relationship_id", value.relationship_id, value.version_sequence
        )
        self.connection.execute(
            """
            INSERT INTO relationship_versions(
                relationship_id, revision_id, version_sequence, review_status,
                content_hash, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                value.relationship_id,
                value.revision_id,
                value.version_sequence,
                value.review_status.value,
                value.content_hash,
                value.model_dump_json(),
                value.updated_at.isoformat(),
            ),
        )

    def _item(self, item_kind: str, item_id: str) -> Record:
        if item_kind == "entity":
            return self.entity(item_id)
        if item_kind == "semantic_object":
            return self.semantic_object(item_id)
        if item_kind == "relationship":
            return self.relationship(item_id)
        raise ValueError(f"unsupported review item kind: {item_kind}")

    def _updated_review_item(self, decision: ReviewDecision) -> Record:
        current = self._item(decision.item_kind, decision.item_id)
        if current.project_id != decision.project_id:
            raise StoreError("review item belongs to a different project")
        if current.review_status is not decision.previous_status:
            raise StoreError("review decision previous status is stale")
        require_review_transition(current.review_status, decision.decision, decision.actor)
        updated = current.model_copy(
            update={
                "revision_id": decision.revision_id,
                "version_sequence": current.version_sequence + 1,
                "review_status": decision.decision,
                "updated_at": decision.created_at,
                "content_hash": None,
            }
        )
        return type(current).model_validate(updated.model_dump())

    def _put_review_item(self, value: Record) -> None:
        if isinstance(value, GeometryEntity):
            self._put_entity(value)
        elif isinstance(value, SemanticObject):
            self._put_semantic_object(value)
        else:
            self._put_relationship(value)

    def _insert_review_decision(self, decision: ReviewDecision) -> None:
        self.connection.execute(
            """
            INSERT INTO review_decisions(
                decision_id, project_id, revision_id, item_kind, item_id,
                previous_status, decision, actor_json, comment, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.project_id,
                decision.revision_id,
                decision.item_kind,
                decision.item_id,
                decision.previous_status.value,
                decision.decision.value,
                decision.actor.model_dump_json(),
                decision.comment,
                decision.created_at.isoformat(),
            ),
        )

    def _latest_rows(self, table: str, id_column: str) -> Sequence[sqlite3.Row]:
        allowed = {
            ("entity_versions", "entity_id"),
            ("semantic_object_versions", "object_id"),
            ("relationship_versions", "relationship_id"),
        }
        if (table, id_column) not in allowed:
            raise ValueError("unsupported version table")
        return self.connection.execute(
            f"""
            WITH latest AS (
                SELECT {id_column}, MAX(version_sequence) AS version_sequence
                FROM {table} GROUP BY {id_column}
            )
            SELECT versions.payload_json
            FROM latest JOIN {table} AS versions
              ON versions.{id_column} = latest.{id_column}
             AND versions.version_sequence = latest.version_sequence
            ORDER BY versions.{id_column}
            """
        ).fetchall()

    def _require_next_version(
        self, table: str, id_column: str, stable_id: str, proposed: int
    ) -> None:
        row = self.connection.execute(
            f"SELECT COALESCE(MAX(version_sequence), 0) FROM {table} WHERE {id_column} = ?",
            (stable_id,),
        ).fetchone()
        expected = int(row[0]) + 1
        if proposed != expected:
            raise StoreError(f"version sequence for {stable_id} must be {expected}")

    def _assert_project(self, project_id: str) -> None:
        row = self.connection.execute(
            "SELECT project_id FROM projects WHERE project_id = ?", (project_id,)
        ).fetchone()
        if row is None:
            raise StoreError(f"unknown project: {project_id}")

    def _assert_revision(self, project_id: str, revision_id: str) -> None:
        row = self.connection.execute(
            "SELECT project_id FROM revisions WHERE revision_id = ?", (revision_id,)
        ).fetchone()
        if row is None or row[0] != project_id:
            raise StoreError(f"revision {revision_id} does not belong to project {project_id}")

    def _stable_item_exists(self, stable_id: str) -> bool:
        return any(
            self.connection.execute(
                f"SELECT 1 FROM {table} WHERE {column} = ?", (stable_id,)
            ).fetchone()
            is not None
            for table, column in (
                ("entities", "entity_id"),
                ("semantic_objects", "object_id"),
            )
        )

    def _insert_audit_event(self, event: AuditEvent) -> None:
        self.connection.execute(
            """
            INSERT INTO audit_events(
                event_id, project_id, revision_id, event_type,
                actor_json, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.project_id,
                event.revision_id,
                event.event_type,
                event.actor.model_dump_json(),
                json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
                event.created_at.isoformat(),
            ),
        )

    @staticmethod
    def _revision_from_row(row: sqlite3.Row) -> RevisionRecord:
        return RevisionRecord(
            revision_id=row["revision_id"],
            project_id=row["project_id"],
            sequence=row["sequence"],
            parent_revision_id=row["parent_revision_id"],
            author=json.loads(row["author_json"]),
            reason=row["reason"],
            status=row["status"],
            created_at=row["created_at"],
            source_revision=row["source_revision"],
        )
