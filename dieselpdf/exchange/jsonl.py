from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from dieselpdf.domain.dataset import (
    AuditEvent,
    DocumentRecord,
    GeometryEntity,
    PageRecord,
    ProjectRecord,
    RelationshipRecord,
    ReviewDecision,
    RevisionRecord,
    SemanticObject,
    require_review_transition,
)
from dieselpdf.persistence import ProjectStore


FORMAT_NAME = "diesel.jsonl"
FORMAT_VERSION = 1


def export_jsonl(store: ProjectStore, path: str) -> None:
    """Write a deterministic, complete, human-readable Phase 3 exchange stream."""
    records: List[Dict[str, Any]] = [
        {
            "record_type": "manifest",
            "format": FORMAT_NAME,
            "format_version": FORMAT_VERSION,
        },
        {"record_type": "project", "payload": store.project().model_dump(mode="json")},
    ]
    records.extend(
        {"record_type": "revision", "payload": value.model_dump(mode="json")}
        for value in store.revisions()
    )
    records.extend(
        {"record_type": "document", "payload": value.model_dump(mode="json")}
        for value in store.documents()
    )
    records.extend(
        {"record_type": "page", "payload": value.model_dump(mode="json")}
        for value in store.pages()
    )
    for table, record_type, id_column in (
        ("entity_versions", "entity_version", "entity_id"),
        ("semantic_object_versions", "semantic_object_version", "object_id"),
        ("relationship_versions", "relationship_version", "relationship_id"),
    ):
        rows = store.connection.execute(
            f"SELECT payload_json FROM {table} ORDER BY {id_column}, version_sequence"
        ).fetchall()
        records.extend(
            {"record_type": record_type, "payload": json.loads(row[0])} for row in rows
        )
    records.extend(
        {"record_type": "review_decision", "payload": value.model_dump(mode="json")}
        for value in store.review_decisions()
    )
    records.extend(
        {"record_type": "audit_event", "payload": value.model_dump(mode="json")}
        for value in store.audit_events()
    )
    records.extend(
        {
            "record_type": "import_run",
            "payload": {
                "import_id": row["import_id"],
                "project_id": row["project_id"],
                "revision_id": row["revision_id"],
                "source_path": row["source_path"],
                "source_hash": row["source_hash"],
                "source_payload": json.loads(row["source_payload_json"]),
                "report": json.loads(row["report_json"]),
                "created_at": row["created_at"],
            },
        }
        for row in store.import_runs()
    )
    records.extend(
        {
            "record_type": "legacy_id_map",
            "payload": {
                "project_id": row["project_id"],
                "source_hash": row["source_hash"],
                "legacy_key": row["legacy_key"],
                "record_kind": row["record_kind"],
                "stable_id": row["stable_id"],
            },
        }
        for row in store.legacy_id_map()
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(
                    json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    + "\n"
                )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def import_jsonl(path: str, dataset_path: str) -> ProjectStore:
    """Validate and atomically rebuild a dataset from Diesel JSONL."""
    target = Path(dataset_path)
    if target.exists():
        raise FileExistsError(target)
    records = _read_records(path)
    manifest = records[0]
    if manifest != {
        "record_type": "manifest",
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
    }:
        raise ValueError("unsupported or malformed Diesel JSONL manifest")
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for record in records[1:]:
        record_type = record.get("record_type")
        if record_type not in {
            "project",
            "revision",
            "document",
            "page",
            "entity_version",
            "semantic_object_version",
            "relationship_version",
            "review_decision",
            "audit_event",
            "import_run",
            "legacy_id_map",
        }:
            raise ValueError(f"unknown Diesel JSONL record type: {record_type!r}")
        if "payload" not in record or not isinstance(record["payload"], dict):
            raise ValueError(f"{record_type} record must contain an object payload")
        grouped.setdefault(str(record_type), []).append(record["payload"])
    if len(grouped.get("project", [])) != 1:
        raise ValueError("Diesel JSONL must contain exactly one project record")
    project = ProjectRecord.model_validate(grouped["project"][0])
    revisions = sorted(
        (RevisionRecord.model_validate(value) for value in grouped.get("revision", [])),
        key=lambda value: value.sequence,
    )
    if not revisions or revisions[0].sequence != 1:
        raise ValueError("Diesel JSONL requires an initial revision")

    temporary = target.with_name(f".{target.name}.import-{os.getpid()}")
    store: ProjectStore | None = None
    try:
        store = ProjectStore.create(temporary, project, revisions[0])
        for revision in revisions[1:]:
            store.add_revision(revision)
        for value in grouped.get("document", []):
            store.add_document(DocumentRecord.model_validate(value))
        for value in sorted(
            (PageRecord.model_validate(item) for item in grouped.get("page", [])),
            key=lambda item: (item.document_id, item.page_index),
        ):
            store.add_page(value)
        for value in sorted(
            (GeometryEntity.model_validate(item) for item in grouped.get("entity_version", [])),
            key=lambda item: (item.entity_id, item.version_sequence),
        ):
            store.add_entity(value)
        for value in sorted(
            (
                SemanticObject.model_validate(item)
                for item in grouped.get("semantic_object_version", [])
            ),
            key=lambda item: (item.object_id, item.version_sequence),
        ):
            store.add_semantic_object(value)
        for value in sorted(
            (
                RelationshipRecord.model_validate(item)
                for item in grouped.get("relationship_version", [])
            ),
            key=lambda item: (item.relationship_id, item.version_sequence),
        ):
            store.add_relationship(value)
        decisions = [
            ReviewDecision.model_validate(item) for item in grouped.get("review_decision", [])
        ]
        for decision in decisions:
            require_review_transition(
                decision.previous_status, decision.decision, decision.actor
            )
            with store.transaction():
                store.connection.execute(
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
        for value in grouped.get("audit_event", []):
            store.record_audit_event(AuditEvent.model_validate(value))
        maps_by_hash: Dict[str, List[tuple[str, str, str]]] = {}
        for value in grouped.get("legacy_id_map", []):
            maps_by_hash.setdefault(str(value["source_hash"]), []).append(
                (str(value["legacy_key"]), str(value["record_kind"]), str(value["stable_id"]))
            )
        for value in grouped.get("import_run", []):
            store.record_import_run(
                import_id=str(value["import_id"]),
                project_id=str(value["project_id"]),
                revision_id=str(value["revision_id"]),
                source_path=str(value["source_path"]),
                source_hash=str(value["source_hash"]),
                source_payload=value["source_payload"],
                report=value["report"],
                created_at=str(value["created_at"]),
                legacy_ids=maps_by_hash.get(str(value["source_hash"]), []),
            )
        if store.integrity_check() != ("ok",):
            raise RuntimeError("SQLite integrity check failed after JSONL import")
        store.close()
        store = None
        os.replace(temporary, target)
        return ProjectStore.open(target)
    except Exception:
        if store is not None:
            store.close()
        for candidate in (temporary, Path(f"{temporary}-wal"), Path(f"{temporary}-shm")):
            if candidate.exists():
                candidate.unlink()
        raise


def _read_records(path: str) -> List[Mapping[str, Any]]:
    records: List[Mapping[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL on line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"JSONL line {line_number} must contain an object")
            records.append(record)
    if not records:
        raise ValueError("Diesel JSONL is empty")
    return records
