# ADR-001 — Project Coordinate, Unit and Tolerance Policy

Status: accepted for Phase 2 implementation by Aaron Han's instruction to complete Phase 2

Date: 22 July 2026

## Decision

1. Canonical project geometry uses millimetres with X right, Y up and Z up.
2. PDF page, Tk Canvas, CAD modelspace, storey and project coordinates are explicit coordinate systems connected by reversible transforms.
3. Pixel coordinates are not physical lengths and cannot be converted without an approved transform.
4. Phase 2 uses immutable, strictly validated value objects for units, points, coordinate systems, transforms, calibration records, levels and grids.
5. Calibration stores control points and reports per-point residuals, RMS error and maximum error.
6. Snapping and node merging use named source-quality tolerance profiles.
7. Initial tolerance values are configurable software-processing defaults only. They are not construction tolerances, survey tolerances or structural acceptance criteria.
8. The existing Canvas convention is characterised, not adopted as permanent geometry: origin (60, 46), Y down, project Y up from the page bottom, and `scale_units_per_px` as selected project units per pixel.

## Initial configurable profiles

| Source | Snap | Node merge | Calibration residual | Round trip |
|---|---:|---:|---:|---:|
| Native CAD | 0.10 mm | 0.10 mm | 0.05 mm | 0.01 mm |
| Vector PDF | 1.0 mm | 1.0 mm | 1.0 mm | 0.5 mm |
| Raster PDF | 5.0 mm | 5.0 mm | 10.0 mm | 5.0 mm |
| Manual | 1.0 mm | 1.0 mm | 1.0 mm | 0.5 mm |
| Grid | 1.0 mm | 0.5 mm | 0.5 mm | 0.25 mm |

These defaults must be reviewed against Aaron's real project corpus before Phase 4 production round-trip acceptance.

## Consequences

- Domain modules import no Tkinter or vendor SDKs.
- Canvas item numbers remain ephemeral UI identifiers.
- Recalibration is reversible because source points and transform records remain available.
- Scanned drawings cannot silently receive the same tolerance as native CAD.
- Phase 3 persistence can serialize these domain values without changing their engineering meaning.
