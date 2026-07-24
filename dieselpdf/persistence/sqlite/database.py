from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional, Sequence, Tuple
from uuid import UUID

from dieselpdf.domain.dataset import ProjectDraft


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


_INITIAL_SCHEMA = r"""
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    current_revision_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    title TEXT NOT NULL,
    source_path TEXT,
    source_sha256 TEXT,
    media_type TEXT,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_documents_project ON documents(project_id);

CREATE TABLE pages (
    page_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    page_index INTEGER NOT NULL CHECK(page_index >= 0),
    name TEXT NOT NULL,
    width REAL,
    height REAL,
    coordinate_system_id TEXT,
    properties_json TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(document_id, page_index)
);
CREATE INDEX idx_pages_project ON pages(project_id);

CREATE TABLE coordinate_systems (
    coordinate_system_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL
);

CREATE TABLE transforms (
    transform_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    source_coordinate_system_id TEXT NOT NULL,
    target_coordinate_system_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL
);

CREATE TABLE levels (
    level_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL
);

CREATE TABLE storeys (
    storey_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL
);

CREATE TABLE grids (
    grid_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    review_status TEXT NOT NULL
);

CREATE TABLE revisions (
    revision_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    parent_revision_id TEXT REFERENCES revisions(revision_id),
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    committed_at TEXT
);
CREATE INDEX idx_revisions_project ON revisions(project_id, created_at);

CREATE TABLE raw_entities (
    spatial_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    geometry_json TEXT NOT NULL,
    coordinate_system_id TEXT NOT NULL,
    storey_id TEXT,
    layer_id TEXT,
    style_id TEXT,
    min_x REAL NOT NULL,
    max_x REAL NOT NULL,
    min_y REAL NOT NULL,
    max_y REAL NOT NULL,
    provenance_json TEXT NOT NULL,
    confidence REAL,
    review_status TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX idx_raw_entities_project_type ON raw_entities(project_id, entity_type);
CREATE INDEX idx_raw_entities_revision ON raw_entities(revision_id);
CREATE INDEX idx_raw_entities_review ON raw_entities(project_id, review_status);

CREATE VIRTUAL TABLE raw_entity_rtree USING rtree(
    spatial_id,
    min_x, max_x,
    min_y, max_y
);
CREATE TRIGGER raw_entities_ai AFTER INSERT ON raw_entities
WHEN NEW.deleted_at IS NULL
BEGIN
    INSERT INTO raw_entity_rtree VALUES (NEW.spatial_id, NEW.min_x, NEW.max_x, NEW.min_y, NEW.max_y);
END;
CREATE TRIGGER raw_entities_au AFTER UPDATE OF min_x, max_x, min_y, max_y, deleted_at ON raw_entities
BEGIN
    DELETE FROM raw_entity_rtree WHERE spatial_id = OLD.spatial_id;
    INSERT INTO raw_entity_rtree
    SELECT NEW.spatial_id, NEW.min_x, NEW.max_x, NEW.min_y, NEW.max_y
    WHERE NEW.deleted_at IS NULL;
END;
CREATE TRIGGER raw_entities_ad AFTER DELETE ON raw_entities
BEGIN
    DELETE FROM raw_entity_rtree WHERE spatial_id = OLD.spatial_id;
END;

CREATE TABLE semantic_objects (
    spatial_id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    object_type TEXT NOT NULL,
    name_or_mark TEXT,
    storey_id TEXT,
    geometry_reference TEXT,
    min_x REAL,
    max_x REAL,
    min_y REAL,
    max_y REAL,
    properties_json TEXT NOT NULL,
    source_entity_ids_json TEXT NOT NULL,
    confidence REAL,
    review_status TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX idx_semantic_project_type ON semantic_objects(project_id, object_type);
CREATE INDEX idx_semantic_review ON semantic_objects(project_id, review_status);

CREATE VIRTUAL TABLE semantic_object_rtree USING rtree(
    spatial_id,
    min_x, max_x,
    min_y, max_y
);
CREATE TRIGGER semantic_objects_ai AFTER INSERT ON semantic_objects
WHEN NEW.deleted_at IS NULL AND NEW.min_x IS NOT NULL
BEGIN
    INSERT INTO semantic_object_rtree VALUES (NEW.spatial_id, NEW.min_x, NEW.max_x, NEW.min_y, NEW.max_y);
END;
CREATE TRIGGER semantic_objects_au AFTER UPDATE OF min_x, max_x, min_y, max_y, deleted_at ON semantic_objects
BEGIN
    DELETE FROM semantic_object_rtree WHERE spatial_id = OLD.spatial_id;
    INSERT INTO semantic_object_rtree
    SELECT NEW.spatial_id, NEW.min_x, NEW.max_x, NEW.min_y, NEW.max_y
    WHERE NEW.deleted_at IS NULL AND NEW.min_x IS NOT NULL;
END;
CREATE TRIGGER semantic_objects_ad AFTER DELETE ON semantic_objects
BEGIN
    DELETE FROM semantic_object_rtree WHERE spatial_id = OLD.spatial_id;
END;

CREATE TABLE object_entity_links (
    link_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    object_id TEXT NOT NULL REFERENCES semantic_objects(object_id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES raw_entities(entity_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    UNIQUE(object_id, entity_id, role)
);

CREATE TABLE relationships (
    relationship_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    review_status TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE(project_id, relationship_type, source_id, target_id)
);
CREATE INDEX idx_relationship_source ON relationships(project_id, source_id);
CREATE INDEX idx_relationship_target ON relationships(project_id, target_id);

CREATE TABLE audit_events (
    event_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    changed_fields_json TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_audit_project ON audit_events(project_id, created_at);
CREATE INDEX idx_audit_record ON audit_events(record_type, record_id);

CREATE TABLE qa_flags (
    qa_flag_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    record_type TEXT,
    record_id TEXT,
    status TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    properties_json TEXT NOT NULL
);
"""

_IMPORT_SCHEMA = r"""
CREATE TABLE import_batches (
    import_batch_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    source_path TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    importer TEXT NOT NULL,
    imported_count INTEGER NOT NULL CHECK(imported_count >= 0),
    warning_count INTEGER NOT NULL CHECK(warning_count >= 0),
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_import_batches_project ON import_batches(project_id, created_at);
"""

MIGRATIONS: Tuple[Migration, ...] = (
    Migration(1, "engineering dataset core", _INITIAL_SCHEMA),
    Migration(2, "import batch records", _IMPORT_SCHEMA),
)


class UnsupportedSchemaVersion(RuntimeError):
    pass


class MigrationManager:
    def __init__(self, migrations: Sequence[Migration] = MIGRATIONS) -> None:
        versions = [migration.version for migration in migrations]
        if versions != sorted(set(versions)):
            raise ValueError("migration versions must be unique and ordered")
        self.migrations = tuple(migrations)

    @property
    def latest_version(self) -> int:
        return self.migrations[-1].version if self.migrations else 0

    def apply(self, connection: sqlite3.Connection) -> int:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        current = self.current_version(connection)
        if current > self.latest_version:
            raise UnsupportedSchemaVersion(
                f"database schema {current} is newer than supported {self.latest_version}"
            )
        existing = {
            int(row["version"]): row
            for row in connection.execute(
                "SELECT version, name, checksum FROM schema_migrations"
            )
        }
        for migration in self.migrations:
            applied = existing.get(migration.version)
            if applied is not None:
                if applied["checksum"] != migration.checksum:
                    raise RuntimeError(
                        f"migration {migration.version} checksum mismatch"
                    )
                continue
            name = migration.name.replace("'", "''")
            checksum = migration.checksum.replace("'", "''")
            applied_at = _utc_iso().replace("'", "''")
            script = (
                "BEGIN IMMEDIATE;\n"
                + migration.sql
                + "\nINSERT INTO schema_migrations(version, name, checksum, applied_at) "
                + f"VALUES ({migration.version}, '{name}', '{checksum}', '{applied_at}');\n"
                + "COMMIT;"
            )
            try:
                connection.executescript(script)
            except Exception:
                with contextlib.suppress(sqlite3.Error):
                    connection.execute("ROLLBACK")
                raise
        return self.current_version(connection)

    @staticmethod
    def current_version(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
        ).fetchone()
        return int(row["version"])


class Database:
    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = Path(path)
        self.read_only = read_only
        self.connection: Optional[sqlite3.Connection] = None

    def open(self) -> sqlite3.Connection:
        if self.connection is not None:
            return self.connection
        if self.read_only:
            uri = f"file:{self.path.as_posix()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            if not self.read_only:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = FULL")
                MigrationManager().apply(connection)
        except Exception:
            connection.close()
            raise
        self.connection = connection
        return connection

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> sqlite3.Connection:
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


@dataclass(frozen=True, slots=True)
class ProjectBundle:
    root: Path
    database_name: str = "project.diesel.db"

    @property
    def database_path(self) -> Path:
        return self.root / self.database_name

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    @property
    def sources_path(self) -> Path:
        return self.root / "sources"

    @property
    def artifacts_path(self) -> Path:
        return self.root / "artifacts"

    @property
    def exports_path(self) -> Path:
        return self.root / "exports"

    @classmethod
    def create(cls, root: Path, project: ProjectDraft) -> "ProjectBundle":
        root = Path(root)
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("project bundle directory must be empty")
        root.mkdir(parents=True, exist_ok=True)
        bundle = cls(root)
        for directory in (bundle.sources_path, bundle.artifacts_path, bundle.exports_path):
            directory.mkdir(parents=True, exist_ok=True)
        manifest = {
            "bundle_schema_version": "1.0",
            "project_id": str(project.project_id),
            "project_name": project.name,
            "database": bundle.database_name,
            "created_at": _utc_iso(),
        }
        bundle._write_json_atomic(bundle.manifest_path, manifest)
        database = Database(bundle.database_path)
        try:
            from .repository import DatasetRepository

            repository = DatasetRepository(database.open())
            repository.create_project(
                project,
                actor_id="project-bundle",
                reason="Create project bundle",
            )
        finally:
            database.close()
        return bundle

    @classmethod
    def open(cls, root: Path) -> "ProjectBundle":
        bundle = cls(Path(root))
        if not bundle.manifest_path.exists() or not bundle.database_path.exists():
            raise FileNotFoundError("project bundle manifest or database is missing")
        with bundle.manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest.get("database") != bundle.database_name:
            raise ValueError("project bundle manifest references an unexpected database")
        return bundle

    def write_artifact_json(self, relative_path: str, payload: object) -> Path:
        target = self.artifacts_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        self._write_json_atomic(target, payload)
        return target

    @staticmethod
    def _write_json_atomic(path: Path, payload: object) -> None:
        descriptor, temporary = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise
