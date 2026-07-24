# ADR-002 — Engineering Dataset Identity, Revision, Review and Storage Policy

Status: accepted for Phase 3 implementation by Aaron Han's instruction to start and finish the next phase

Date: 22 July 2026

## Context

Phase 3 must make the Diesel engineering dataset the source of truth while the
existing Canvas remains a projection. The dataset needs stable identity,
source-document provenance, immutable revision evidence, spatial queries,
human approval gates and a tested path from legacy `.dieselpdf.json` projects.

## Decision

1. Use a local `.diesel.db` SQLite database as the Phase 3 project store.
2. Use Pydantic 2.13.4 models as the validation boundary for project,
   document, page, raw geometry, semantic object, relationship, revision,
   review-decision and audit-event records.
3. Use opaque, kind-prefixed UUID identities. New records use UUID4. Immutable
   import evidence uses UUID5 so repeat imports of the same source produce the
   same stable identities.
4. Keep stable identity rows separate from immutable version rows. A change
   retains the stable ID and appends the next version sequence under a new
   project revision.
5. Keep revisions linear during Phase 3. Every revision records its parent,
   sequence, actor, reason, timestamp, status and optional source revision.
6. Store geometry bounding boxes in a SQLite R-Tree keyed to immutable entity
   versions. Queries join the R-Tree to the latest version for each entity.
7. Store raw geometry separately from semantic objects. Semantic records must
   identify source entities or an explicit engineer-created origin.
8. Store relationships as typed durable records. In-memory graphs remain views
   over those records, not the durable source.
9. Store source documents and pages as immutable records. Entity provenance
   may not refer to a document or page that is absent from the same project.
10. Store important revisions, versions, review decisions, audit events and
    import runs append-only. Database triggers reject update or delete attempts.
11. Use `.diesel.jsonl` as the deterministic readable exchange format. Export
    includes full version history, decisions, audit events and migration
    evidence; import validates every record and rebuilds the R-Tree.
12. Preserve source files outside the database for now and record immutable
    paths, hashes and metadata. A later packaging decision may wrap the database
    and artefacts in a project directory without changing domain identities.

## Review state machine

Supported states are:

- `working`;
- `ai_proposed`;
- `engineer_review_required`;
- `engineer_approved`;
- `rejected`;
- `superseded`.

AI and system actors cannot approve or reject human-review items. An
`engineer_approved` decision requires both the `engineer` role and explicit
engineering-approval authority. Each decision appends, in one SQLite
transaction:

1. a project revision;
2. the next immutable item version;
3. the review decision with actor and reason.

Failure before commit leaves all three absent.

## Legacy migration

The importer never edits the source JSON. It records the SHA-256, complete
parsed source payload, deterministic ID map, object counts, warnings and every
unknown field path. Each legacy Canvas object becomes one raw entity. Unsupported
Canvas types remain unresolved block-reference records with their raw data; they
are not silently discarded or reclassified as trusted geometry.

Calibrated geometry is converted through the characterised Phase 2 legacy
Canvas transform into project millimetres. Uncalibrated geometry remains in an
explicit page-local pixel coordinate system and requires engineer review.

## Consequences

- Canvas item IDs remain ephemeral and can be rebuilt from the database.
- Stable source provenance is queryable and cannot silently dangle.
- Review history is reproducible and human authority is machine-enforced.
- SQLite and JSONL can be tested without starting Tkinter.
- Phase 4 adapters can target one repository boundary rather than Canvas.
- Real client projects are still required for a migration pilot; the committed
  fixture proves the schema and loss-reporting contract, not every historic
  project variation.
