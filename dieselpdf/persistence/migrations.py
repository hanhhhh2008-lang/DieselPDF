from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Tuple


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS: Tuple[Migration, ...] = (
    Migration(
        1,
        "phase_3_engineering_dataset",
        r"""
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
            name TEXT NOT NULL CHECK (length(trim(name)) > 0),
            description TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            current_revision_id TEXT
        );

        CREATE TABLE revisions (
            revision_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            parent_revision_id TEXT REFERENCES revisions(revision_id),
            author_json TEXT NOT NULL,
            reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source_revision TEXT,
            UNIQUE(project_id, sequence)
        );

        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            source_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, source_hash)
        );

        CREATE TABLE pages (
            page_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            document_id TEXT NOT NULL REFERENCES documents(document_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            page_index INTEGER NOT NULL CHECK (page_index >= 0),
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(document_id, page_index)
        );

        CREATE TABLE entities (
            entity_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            entity_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE entity_versions (
            version_pk INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            version_sequence INTEGER NOT NULL CHECK (version_sequence >= 1),
            review_status TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            min_x REAL NOT NULL,
            max_x REAL NOT NULL,
            min_y REAL NOT NULL,
            max_y REAL NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(entity_id, version_sequence),
            UNIQUE(entity_id, revision_id)
        );

        CREATE VIRTUAL TABLE entity_rtree USING rtree(
            version_pk,
            min_x, max_x,
            min_y, max_y
        );

        CREATE TRIGGER entity_versions_insert_rtree
        AFTER INSERT ON entity_versions
        BEGIN
            INSERT INTO entity_rtree(version_pk, min_x, max_x, min_y, max_y)
            VALUES (NEW.version_pk, NEW.min_x, NEW.max_x, NEW.min_y, NEW.max_y);
        END;

        CREATE TABLE semantic_objects (
            object_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            object_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE semantic_object_versions (
            version_pk INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id TEXT NOT NULL REFERENCES semantic_objects(object_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            version_sequence INTEGER NOT NULL CHECK (version_sequence >= 1),
            review_status TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(object_id, version_sequence),
            UNIQUE(object_id, revision_id)
        );

        CREATE TABLE object_entity_links (
            object_id TEXT NOT NULL REFERENCES semantic_objects(object_id),
            object_version_sequence INTEGER NOT NULL,
            entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            PRIMARY KEY(object_id, object_version_sequence, entity_id)
        );

        CREATE TABLE relationships (
            relationship_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            relationship_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE relationship_versions (
            version_pk INTEGER PRIMARY KEY AUTOINCREMENT,
            relationship_id TEXT NOT NULL REFERENCES relationships(relationship_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            version_sequence INTEGER NOT NULL CHECK (version_sequence >= 1),
            review_status TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(relationship_id, version_sequence),
            UNIQUE(relationship_id, revision_id)
        );

        CREATE TABLE review_decisions (
            decision_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            item_kind TEXT NOT NULL,
            item_id TEXT NOT NULL,
            previous_status TEXT NOT NULL,
            decision TEXT NOT NULL,
            actor_json TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE audit_events (
            event_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            revision_id TEXT REFERENCES revisions(revision_id),
            event_type TEXT NOT NULL,
            actor_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE import_runs (
            import_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            source_path TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            source_payload_json TEXT NOT NULL,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, source_hash)
        );

        CREATE TABLE legacy_id_map (
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            source_hash TEXT NOT NULL,
            legacy_key TEXT NOT NULL,
            record_kind TEXT NOT NULL,
            stable_id TEXT NOT NULL,
            PRIMARY KEY(project_id, source_hash, legacy_key),
            UNIQUE(project_id, stable_id)
        );

        CREATE INDEX entity_versions_revision_idx ON entity_versions(revision_id);
        CREATE INDEX semantic_versions_revision_idx ON semantic_object_versions(revision_id);
        CREATE INDEX relationship_versions_revision_idx ON relationship_versions(revision_id);
        CREATE INDEX relationships_source_idx ON relationships(source_id);
        CREATE INDEX relationships_target_idx ON relationships(target_id);
        CREATE INDEX review_decisions_item_idx ON review_decisions(item_kind, item_id);
        CREATE INDEX audit_events_project_idx ON audit_events(project_id, created_at);

        CREATE TRIGGER revisions_no_update BEFORE UPDATE ON revisions
        BEGIN SELECT RAISE(ABORT, 'revisions are append-only'); END;
        CREATE TRIGGER revisions_no_delete BEFORE DELETE ON revisions
        BEGIN SELECT RAISE(ABORT, 'revisions are append-only'); END;
        CREATE TRIGGER documents_no_update BEFORE UPDATE ON documents
        BEGIN SELECT RAISE(ABORT, 'source documents are immutable'); END;
        CREATE TRIGGER documents_no_delete BEFORE DELETE ON documents
        BEGIN SELECT RAISE(ABORT, 'source documents are immutable'); END;
        CREATE TRIGGER pages_no_update BEFORE UPDATE ON pages
        BEGIN SELECT RAISE(ABORT, 'source pages are immutable'); END;
        CREATE TRIGGER pages_no_delete BEFORE DELETE ON pages
        BEGIN SELECT RAISE(ABORT, 'source pages are immutable'); END;
        CREATE TRIGGER entity_versions_no_update BEFORE UPDATE ON entity_versions
        BEGIN SELECT RAISE(ABORT, 'entity versions are immutable'); END;
        CREATE TRIGGER entity_versions_no_delete BEFORE DELETE ON entity_versions
        BEGIN SELECT RAISE(ABORT, 'entity versions are immutable'); END;
        CREATE TRIGGER semantic_versions_no_update BEFORE UPDATE ON semantic_object_versions
        BEGIN SELECT RAISE(ABORT, 'semantic object versions are immutable'); END;
        CREATE TRIGGER semantic_versions_no_delete BEFORE DELETE ON semantic_object_versions
        BEGIN SELECT RAISE(ABORT, 'semantic object versions are immutable'); END;
        CREATE TRIGGER relationship_versions_no_update BEFORE UPDATE ON relationship_versions
        BEGIN SELECT RAISE(ABORT, 'relationship versions are immutable'); END;
        CREATE TRIGGER relationship_versions_no_delete BEFORE DELETE ON relationship_versions
        BEGIN SELECT RAISE(ABORT, 'relationship versions are immutable'); END;
        CREATE TRIGGER review_decisions_no_update BEFORE UPDATE ON review_decisions
        BEGIN SELECT RAISE(ABORT, 'review decisions are append-only'); END;
        CREATE TRIGGER review_decisions_no_delete BEFORE DELETE ON review_decisions
        BEGIN SELECT RAISE(ABORT, 'review decisions are append-only'); END;
        CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events
        BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
        CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events
        BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
        CREATE TRIGGER import_runs_no_update BEFORE UPDATE ON import_runs
        BEGIN SELECT RAISE(ABORT, 'import runs are immutable'); END;
        CREATE TRIGGER import_runs_no_delete BEFORE DELETE ON import_runs
        BEGIN SELECT RAISE(ABORT, 'import runs are immutable'); END;
        """,
    ),
)

CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version


def apply_migrations(
    connection: sqlite3.Connection,
    migrations: Iterable[Migration] = MIGRATIONS,
) -> int:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations")
    }
    for migration in migrations:
        if migration.version in applied:
            continue
        applied_at = datetime.now(timezone.utc).isoformat()
        try:
            connection.executescript("BEGIN IMMEDIATE;\n" + migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, applied_at),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return max(applied | {migration.version for migration in migrations if migration.version in applied or migration.version <= CURRENT_SCHEMA_VERSION})
