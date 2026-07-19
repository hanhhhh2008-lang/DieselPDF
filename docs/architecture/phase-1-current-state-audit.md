# Phase 1 Current-State Audit

Status: Phase 1 complete; awaiting Aaron Han's architecture review
Code audit baseline: commit 5b0c5b0 on branch origin/agent/codex-project-handoff, 19 July 2026
Context reconciliation baseline: commit fe55104 on branch origin/agent/codex-project-handoff, 19 July 2026
Authorised scope: architecture review only; no production feature implementation

## Executive finding

DieselPDF is a useful document-markup and CAD-exchange prototype, not yet an engineering model. Its strongest reusable assets are the proven Tkinter interaction patterns, PyMuPDF rendering/extraction, ezdxf export, measurement workflow and legacy project reader. Its central architectural constraint is that a 3,231-line DieselPDF class owns UI state, geometry, calibration, persistence and import/export. Canvas item IDs and pixel coordinates are therefore functioning as the project model.

The correct migration is a strangler migration: preserve the current UI, put a schema-validated engineering dataset beside it, make Canvas a projection of that dataset, and migrate one object category at a time. A full UI rewrite is neither required nor authorised.

## Context and repository state

The checkout contains 1,982 tracked working-tree files, dominated by vendored Python packages. The main application and bundled artefacts are:

| Item | Observed state | Audit implication |
|---|---|---|
| DieselPDF.pyw | 3,231 lines; one Tkinter root class with more than 150 methods | UI, domain, persistence and adapters are tightly coupled |
| DieselPDFApp-upload.zip | about 48 MB compressed and 155 MB uncompressed | release content duplicates source and dependencies; provenance/SBOM is needed |
| vendor_pymupdf | PyMuPDF 1.24.14, Windows .pyd/.dll binaries | Windows-specific bundle; local metadata declares AGPL-3.0 |
| vendor_cad_py311 | ezdxf 1.4.4 plus NumPy 2.4.6, fontTools, pyparsing and typing_extensions | dependency set is committed wholesale, including upstream tests and platform binaries |
| launch scripts | hard-coded AaronHan Hermes Python path, then a pythonw.exe fallback in CMD; VBS has no fallback | not portable, reproducible or macOS-compatible |
| dieselpdf-library.json | repeated Canvas-object snapshots and local numeric IDs | library records share the same display-owned data model |
| first-party tests | none on the audited branch | behaviour is unprotected on this baseline |

The open origin/codex/dieselpdf-interactions branch was also inspected because it is 2,506 additions and 282 deletions ahead of main in DieselPDF.pyw and adds tests/smoke.py. It improves per-page calibration, markup metadata, interactions and smoke coverage, but continues to serialize Canvas objects without a schema version or domain identity. The Phase 1 architecture remains applicable. Before implementation begins, Aaron must nominate whether that branch/PR is the Phase 2 code baseline.

## Context reconciliation

The initial code-audit snapshot at 5b0c5b0 contained AGENTS.md, Project Bible chapters 00–08 and an incomplete docs/project/ROADMAP_10_PHASES.md stub, but did not yet contain CODEX_HANDOFF.md or the remaining Project Bible. While Phase 1 was being closed, origin/agent/codex-project-handoff advanced to fe55104 with the complete handoff. That update was merged into this branch before final publication.

The final review therefore includes CODEX_HANDOFF.md, Project Bible README and numbered chapters 00–34, root AGENTS.md and [GitHub Issue #2](https://github.com/hanhhhh2008-lang/DieselPDF/issues/2). CODEX_HANDOFF.md explicitly supersedes the older roadmap stub with docs/project-bible/15_TEN_PHASE_ROADMAP.md. These sources agree that only the seven Phase 1 review documents are authorised and Aaron must approve progression. Risk R-019 is closed and decision D-019 records the reconciled governing set.

## Existing function map

Line references describe the audited DieselPDF.pyw baseline.

| Capability | Existing functions | Current data flow | Reuse decision |
|---|---|---|---|
| PDF page discovery | _pdf_pages_metadata (2553), _pdf_page_count (2550) | PyMuPDF page rectangles become rendered width/height fields | retain behind PdfImportAdapter |
| PDF display | _pdf_renderer (2461), _render_pdf_page (2468), _update_page_surface (2421) | source PDF → cached PNG → Tk PhotoImage → Canvas | retain renderer/cache concept; isolate filesystem/cache policy |
| PDF vector/text extraction | pdf_to_cad (3150), _extract_pdf_cad_commands (3171) | page.get_drawings and get_text dict → transient command dictionaries → DXF | retain extraction mechanics; replace direct PDF-to-DXF path with source entities |
| Canvas drawing | on_press/on_drag/on_release (1409–1465), create_shape (1545), finish_pending_shape (1622), _record_entry (1731) | mouse pixels → Canvas items → page entries with item IDs | retain interaction behaviour; replace ownership with command → dataset → render |
| Measurement calibration | finish_calibration (1660), manual_scale (1676), _set_measure_unit (1691), label helpers (1714–1724) | one units-per-pixel value per document, derived from Canvas distance | reuse UX only; replace with explicit page-to-project transform and unit types |
| Snapping | snap_point (963), geometric helpers (1014–1051) | searches visible Canvas items with an 18-pixel tolerance | retain UX; move predicates/tolerances to project-coordinate geometry service |
| Canvas/CAD conversion | _cad_scale (2782), _canvas_to_cad (2785), _cad_to_canvas (2790) | page origin translation, one scale and Y reversal | migration input only; insufficient for rotation, skew, storeys or composed transforms |
| Canvas to neutral commands | _entries_to_cad_commands (2802) | visible Canvas item type/coords → line/polyline/rect/ellipse/polygon/text dictionaries | retain as legacy adapter; do not make it the new domain API |
| DXF output | _write_cad_commands_dxf (2849), export_current_page_dxf (2894) | command dictionaries → R2010 modelspace through ezdxf | retain as prototype behind DxfExportAdapter; add stable IDs/XDATA and reconciliation |
| DXF read/report | cad_to_text (2984), _dxf_to_text_lines (3008) | ezdxf modelspace → human-readable text | retain as diagnostics, not an import model |
| text CAD | text_to_cad_pdf (3038), _parse_cad_text (3068), _draw_cad_commands_on_canvas (3111) | script → command dictionaries → DXF/PDF/Canvas | retain parser as an optional command adapter |
| PDF generation | _write_cad_commands_pdf (2908), export_current_page_pdf (2970) | command dictionaries → new vector PDF sized to extents | retain proof of concept; future output comes from DrawingView and approved dataset revision |
| project open | open_project (2583), _restore_entry (2734) | unvalidated JSON → Canvas items and local page records | freeze as LegacyDieselJsonImporter |
| project save | _write_project (2674), _serialize_page (2694), _serialize_entry (2703) | live Canvas items → JSON | keep only until migrated categories have dataset persistence |

## Current project serialization

The file extension is .dieselpdf.json, but the document has no schema_version, project_id, stable entity IDs, revision, provenance, transform records, review audit or checksum. The current top-level shape is:

~~~text
app
source_file
pdf_file
scale_units_per_px
scale_unit
scale_label
unit
layers[]
current_layer
bookmarks[]
pages[]
~~~

Each page stores paper, optional PDF page index, rendered width/height and entries. Each entry stores a process-local numeric ID, kind, detail, group, flattened flag, layer and Canvas objects. Each Canvas object stores type, pixel coordinates and presentation options such as fill, outline, width, dash, arrow, text, font and stipple.

Important consequences:

- IDs are only incrementing integers within a session; they cannot support round-trip matching.
- geometry is stored after display transformations, in a Y-down pixel space;
- source paths can be absolute local paths and source files are not hashed or embedded;
- global scale cannot represent independent pages, rotations, reflections, affine rectification or storey alignment;
- measurements store their displayed label, not a traceable dimension definition;
- restoring unsupported or malformed object types is not explicitly reported;
- writes are direct, not atomic, and there is no backup or migration transaction;
- changing the source PDF after saving is not detected.

## Existing geometry and coordinate limitations

The effective transform is:

~~~text
cad_x = (canvas_x - page_origin_x) × scale
cad_y = (page_height - (canvas_y - page_origin_y)) × scale
~~~

This handles translation, uniform scale and Y reflection only. Page rotation changes Canvas items directly rather than composing a durable transform. Zoom similarly acts on Canvas coordinates. The model has no project origin, global axes, storey-local axes, physical Z level, transformation provenance, tolerance policy or reversible calibration record.

PDF extraction uses PDF points directly and vertically stacks pages using page height plus an arbitrary 80-unit gap. Cubic curve instructions are reduced to a polyline of their provided points rather than preserved as parametric Bezier geometry. This is useful conversion code but cannot define engineering truth.

## Reusable assets

Preserve and protect with characterization tests:

1. PyMuPDF page rendering, caching, page metadata and extraction entry points.
2. Current draw/select/snap/resize/group/layer interactions.
3. Calibration and measurement user flow.
4. CAD text parser and diagnostic reporting.
5. ezdxf entity-writing patterns and unit mapping.
6. vector PDF preview generation.
7. .dieselpdf.json loading as migration input.
8. familiar Tkinter layout and tool vocabulary.
9. smoke coverage on the open interaction branch, after the baseline decision.

## Technical-debt findings

### Critical

- Canvas is both view and database. A redraw, zoom or page operation can change engineering coordinates.
- There is no versioned engineering schema, stable identity, provenance or revision model.
- No automated tests exist on the audited branch for project migration, coordinate round trips or FEA.
- PyMuPDF's AGPL/commercial licensing and ODA's commercial terms require a product-level legal decision.

### High

- The single class mixes UI callbacks, geometry algorithms, file dialogs, subprocesses, JSON I/O and vendor adapters.
- Exceptions are often converted directly into message boxes, preventing service-level error handling and deterministic tests.
- imported PDF curves, styles, clipping and source identifiers are lossy;
- DXF export has no Diesel XDATA identity, paper-space/viewports, block preservation, dimensions, leaders or round-trip reconciliation;
- dependencies are platform-specific, vendored without a lockfile, hashes, build manifest or SBOM;
- source files are treated as trusted paths and parsing is in-process.

### Medium

- units are strings and floats without dimensional validation;
- snapping tolerances are display pixels and scattered constants;
- undo/redo stores mutable Canvas references rather than domain commands/events;
- library data contains duplicate groups and local IDs;
- there is no approval-state machine or enforced preliminary drawing status;
- open-branch divergence makes the implementation baseline ambiguous.

## Migration requirements for legacy projects

Legacy projects must remain readable. The importer should:

1. read bytes and retain a SHA-256 hash and immutable source copy before conversion;
2. validate the legacy top-level shape without mutating it;
3. assign a migration_run_id and deterministic UUIDv5 IDs derived from project hash, page index, legacy entry ID and object index;
4. preserve original Canvas JSON in a legacy_payload field;
5. create Document, Page and page-coordinate records;
6. create an explicit LegacyCanvasToPage transform using PAGE_ORIGIN, stored page height, scale, unit and Y reflection;
7. convert each supported Canvas object into a raw entity while preserving style and group/layer links;
8. record unsupported objects and missing source files as QA flags, never silently drop them;
9. write a new .diesel.db atomically beside the legacy file; never overwrite the source;
10. reopen the new store, render it, and compare object count, bounds, styles and displayed measurements;
11. produce a signed migration report and allow rollback by deleting only the new database.

Ambiguous legacy dimensions remain markups until an engineer confirms their coordinate system and scale. Migration must not automatically promote markups to architectural or structural semantic objects.

## Verification baseline

Before any existing code path is removed, tests must cover:

- golden legacy-project import, including missing PDF, unknown object, Unicode text and corrupt JSON cases;
- forward/inverse and composed coordinate transforms;
- repeated save/open/export without cumulative drift;
- PDF and DXF object count, stable-ID and geometry reconciliation;
- per-page and multi-storey calibration;
- atomic-save interruption and database recovery;
- representative UI characterization tests;
- dependency import on supported Windows and macOS targets;
- preliminary watermark and review-state enforcement.

FEA and Australian Standards verification are specified separately in the solver and target-architecture documents.

## Audit conclusion

The prototype should be preserved, but no new engineering meaning should be added to Canvas entries. The next implementation phase should begin only after Aaron approves the dataset schema, coordinate convention, dependency/licensing policy, code baseline and engineer-input checklist in the Phase 1 backlog.

## Phase 1 close-out maintenance

After recording the baseline above, the Phase 1 branch received two bounded maintenance fixes found during review:

- finite-segment Intersection snapping now rejects crossings outside the segment extents, while Apparent Intersection retains infinite-line behaviour; hidden layers/items are excluded and ordinary intersection candidates are filtered near the cursor;
- legacy JSON saves now serialize to a temporary file in the destination directory, flush and fsync it, then atomically replace the project file; a serialization failure preserves the prior file.

Focused regression tests cover geometry edge cases, segment versus apparent snapping, successful/failed atomic saves and application construction. These changes protect the existing prototype and do not implement the Phase 2 coordinate/grid domain.
