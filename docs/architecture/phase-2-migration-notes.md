# Phase 2 Migration Notes

## Baseline

Phase 2 branches from commit `492900e883bd9be287324a1b198c984d2a2ee5d6`, the head of Draft PR #4 containing the completed Phase 1 audit, Project Bible reconciliation, regression fixes and nine passing pre-Phase-2 tests.

## Strangler migration

`DieselPDF.pyw` remains the composition root. New coordinate and grid logic lives under `dieselpdf/domain` and does not enlarge the monolith. The existing Canvas/PDF/CAD functions remain operational until later application services replace them one controlled path at a time.

## Legacy coordinate characterisation

The current application uses:

- `PAGE_ORIGIN = (60, 46)`;
- A4 display size `630 x 891` pixels from a fixed 3 px/mm paper-display factor;
- Canvas Y increasing downward;
- CAD/project Y increasing upward from the page bottom;
- `scale_units_per_px` as selected project units per Canvas pixel.

`LegacyCanvasCoordinateAdapter` reproduces the current `_canvas_to_cad` and `_cad_to_canvas` formulas and provides forward/inverse tests. It is an adapter, not the new source of truth.

## Existing project files

Phase 2 does not rewrite `.dieselpdf.json`. Existing files continue to store Canvas coordinates. A future immutable Phase 3 importer will:

1. read the legacy file without modifying it;
2. record the legacy page geometry and scale;
3. create a legacy Canvas coordinate system;
4. create the corresponding Canvas-to-project transform;
5. generate new stable entities and a reconciliation report.

A synthetic A4 fixture is used for current formula characterisation because no representative client `.dieselpdf.json` fixture was supplied. Real-project migration acceptance remains an explicit Phase 3 gate.
