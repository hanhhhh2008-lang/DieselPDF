# ADR-003 — Project Bundle and Persistence Policy

Status: accepted as the Phase 3 implementation default; reversible before production release

Date: 24 July 2026

## Decision

DieselPDF projects use a directory bundle rather than a single opaque file:

```text
<Project Name>.diesel/
├── manifest.json
├── project.diesel.db
├── sources/
├── artifacts/
└── exports/
```

- `project.diesel.db` is the SQLite source of truth for engineering records.
- `sources/` stores immutable source copies or future content-addressed source references.
- `artifacts/` stores reconciliation reports, solver manifests and generated non-authoritative artefacts.
- `exports/` stores user-requested PDF, DXF, IFC, JSONL and schedule exports.
- `manifest.json` identifies the project UUID, bundle schema and database filename.

## SQLite policy

- foreign keys enabled;
- WAL journalling;
- full synchronous writes;
- atomic revision transactions;
- forward-only numbered migrations with SHA-256 checksums;
- fail on migration checksum drift;
- R-Tree is an acceleration index, not the exact geometry source;
- JSON payloads are deterministic and schema-validated at adapter boundaries;
- unsupported newer schema versions are not silently modified.

## Exchange policy

`.diesel.jsonl` is the readable, streamable exchange format. It preserves stable IDs, revisions, audit events, raw/semantic separation and relationships. CSV is not an authoritative project exchange format.

## Legacy policy

Legacy `.dieselpdf.json` files are read without modification. The importer hashes the source before and after import, records every source object, preserves unsupported objects as opaque geometry with original payload, and emits a reconciliation report. A source object may not disappear silently.

## Consequences

- A project can be backed up and inspected with standard filesystem and SQLite tools.
- Large source and analysis artefacts do not bloat the transactional database.
- A future packaged single-file transport can zip the bundle without changing internal engineering semantics.
- The database remains portable across Windows and macOS.

## Deferred decisions

Encryption, client-specific retention, cloud synchronisation, multi-user locking and content-addressed source copying require a later security and deployment policy.
