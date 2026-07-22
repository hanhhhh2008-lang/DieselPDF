# Phase 3 Migration Notes

## Baseline and branch lineage

Phase 3 is implemented on `agent/phase-3-engineering-dataset`, stacked on the
completed Phase 2 head `cf51073`. The branch also merges
`agent/improving-dieselpdf-engineer-ai-interface` so the coordinate/dataset
programme does not discard the latest document interactions, macOS support,
tests or mandatory preliminary-output banner.

`main` is not modified directly.

## Legacy project migration workflow

Use DieselPDF File → Migrate Legacy Project to Dataset, or call:

```python
from dieselpdf.adapters.legacy import LegacyProjectImporter

report = LegacyProjectImporter().import_file(
    "project.dieselpdf.json",
    "project.diesel.db",
)
```

The importer:

1. reads the source once and records its SHA-256;
2. refuses invalid top-level JSON or invalid page structure;
3. creates deterministic project, document, page and entity IDs;
4. creates one raw entity for every Canvas object;
5. converts calibrated Canvas coordinates through the Phase 2 adapter;
6. leaves uncalibrated geometry in an explicit page-local pixel space;
7. marks every migrated entity `engineer_review_required`;
8. records source document/page links for every entity;
9. stores the complete source JSON, ID map, counts, warnings and unmapped paths;
10. verifies the original hash again and runs `PRAGMA integrity_check`.

The source JSON is never modified or replaced.

## Current legacy mapping

| Tk Canvas type | Dataset raw entity |
|---|---|
| line with two endpoints | line |
| line with more points | polyline |
| rectangle | rectangle |
| equal-width oval | circle |
| other oval | ellipse |
| polygon | polygon |
| text | text |
| arc | arc |
| image | image |
| unknown or malformed | unresolved block reference with raw evidence |

Visual properties, legacy entry metadata and raw coordinates remain in the
geometry parameters even after coordinate conversion.

## JSONL exchange

`export_jsonl` writes a deterministic UTF-8 stream atomically. `import_jsonl`
validates the manifest and every Pydantic record, reconstructs all immutable
versions and decisions, rebuilds the R-Tree through database triggers, runs an
integrity check and atomically replaces the destination only after success.

## Compatibility boundary

Legacy `.dieselpdf.json` open/save remains available for existing document
work. `.diesel.db` is the engineering source-of-truth format. Phase 3 does not
silently rewrite a legacy project in place or pretend uncalibrated pixels are
approved project millimetres.
