# ADR-001 — Project Coordinate, Unit and Tolerance Policy

Status: accepted with engineering conditions; Phase 2 implementation complete

Date: 22 July 2026  
Engineering review incorporated: 24 July 2026

## Decision

1. Canonical project geometry uses millimetres with X right, Y up and Z up.
2. The permanent project origin must be a stable engineering reference: normally an approved Grid intersection, survey control point, building corner or another explicit project datum. A PDF page origin or Tk Canvas origin must not become the permanent project origin.
3. All storeys share the same project X/Y coordinate system. Storeys and physical levels differ by Z elevation, not by unrelated plan origins.
4. Project-relative Z may be linked to AHD or another approved survey datum. The project model records both the relative elevation and the reversible survey-datum relationship.
5. PDF page, Tk Canvas, CAD modelspace, survey, storey and project coordinates are explicit coordinate systems connected by reversible transforms.
6. Pixel coordinates are not physical lengths and cannot be converted without an approved transform.
7. Phase 2 uses immutable, strictly validated value objects for units, points, coordinate systems, transforms, calibration records, datums, levels and grids.
8. Calibration stores control points and reports per-point residuals, RMS error and maximum error.
9. Calibration assessment has three explicit outcomes:
   - `pass`: RMS and maximum residuals are within the selected profile;
   - `warning`: RMS exceeds the target but maximum residual remains below the rejection limit; engineer confirmation is required;
   - `reject`: maximum residual exceeds the rejection limit and the calibration is blocked.
10. Snapping and node merging use named source-quality tolerance profiles.
11. Pointer snapping uses a screen radius, initially 8 pixels, converted through the current view scale and capped by a profile-specific project distance. Fixed model-space snapping remains available for deterministic non-UI operations.
12. Node proximity is separated into:
   - automatic merge;
   - suggested merge requiring review;
   - keep separate.
   Only the automatic band may merge nodes without confirmation.
13. Raster drawing tolerance should be derived from scan DPI and drawing scale where those values are known. Unknown raster metadata uses a conservative prototype profile and must be treated as lower-confidence input.
14. Manual typed coordinates and manual pointer input are separate source-quality profiles.
15. Initial tolerance values are configurable software-processing defaults only. They are not construction tolerances, survey tolerances or structural acceptance criteria.
16. The existing Canvas convention is characterised, not adopted as permanent geometry: origin `(60, 46)`, Y down, project Y up from the page bottom, and `scale_units_per_px` as selected project units per pixel.

## Project origin and datum policy

The preferred project origin selection order is:

1. approved primary Grid intersection;
2. survey control point coordinated with the architectural Grid;
3. stable building corner where no Grid exists;
4. explicit engineer-approved project datum.

The project X-axis should follow the primary building or structural Grid direction unless an approved survey/CAD coordinate basis is required. Any rotation to MGA, survey bearing or another external coordinate system is represented by a transform rather than by changing the internal engineering convention.

Example vertical mapping:

```text
Ground Floor FFL: project Z = 0 mm, AHD RL = 52.430 m
Level 1 FFL:      project Z = 3000 mm, AHD RL = 55.430 m
```

## Initial configurable prototype profiles

| Source | Fixed model snap | Auto node merge | Suggested merge | RMS calibration target | Maximum calibration error | Round trip | Pointer cap |
|---|---:|---:|---:|---:|---:|---:|---:|
| Native CAD | 0.10 mm | 0.10 mm | 2.0 mm | 0.05 mm | 0.10 mm | 0.01 mm | 5.0 mm |
| Vector PDF | 1.0 mm | 1.0 mm | 3.0 mm | 1.0 mm | 2.0 mm | 0.5 mm | 10.0 mm |
| Raster PDF, metadata unknown | 5.0 mm | 1.0 mm | 15.0 mm | 10.0 mm | 20.0 mm | 5.0 mm | 20.0 mm |
| Manual typed | 0.10 mm | 0.10 mm | 1.0 mm | 0.10 mm | 0.20 mm | 0.05 mm | 1.0 mm |
| Manual pointer | 1.0 mm | 1.0 mm | 3.0 mm | 1.0 mm | 2.0 mm | 0.5 mm | 10.0 mm |
| Grid | 1.0 mm | 0.5 mm | 2.0 mm | 0.5 mm | 1.0 mm | 0.25 mm | 10.0 mm |

All pointer profiles use an initial 8-pixel screen radius, limited by the pointer cap shown above.

## Raster-derived profile

Where DPI and drawing scale are available:

```text
project millimetres per pixel
= 25.4 / DPI × scale denominator / scale numerator
```

For a 300 dpi scan at 1:100:

```text
project millimetres per pixel ≈ 8.47 mm
```

The implementation then uses:

- fixed raster snap: 1 pixel in project space;
- automatic node merge: the lesser of 0.25 pixel and 1 mm;
- suggested merge: 2 pixels;
- RMS calibration target: 1.5 pixels;
- maximum calibration error: 3 pixels;
- round-trip check: 1 pixel;
- pointer cap: 2 pixels.

This does not make raster geometry authoritative. It only makes uncertainty explicit and repeatable.

## Required validation before production acceptance

The prototype defaults must be reviewed against Aaron's real project corpus before Phase 4 production round-trip acceptance. The validation set should include:

1. a native CAD 10,000 mm × 8,000 mm rectangle round trip;
2. a rotated Grid system;
3. a multi-storey project with shared X/Y and differing Z;
4. a scanned drawing with known dimensions, DPI and scale;
5. at least one real legacy `.dieselpdf.json` project and its source PDF.

## Consequences

- Domain modules import no Tkinter or vendor SDKs.
- Canvas item numbers remain ephemeral UI identifiers.
- Recalibration is reversible because source points and transform records remain available.
- A stable project datum is independent of PDF replacement, zoom or page movement.
- Project and survey coordinates can coexist without forcing large survey values into every engineering calculation.
- Scanned drawings cannot silently receive the same tolerance as native CAD.
- Pointer interaction can feel consistent across zoom levels without allowing uncontrolled long-distance snapping.
- Near nodes are not automatically connected merely because they fall inside a broad cleanup range.
- Phase 3 persistence can serialize these domain values without changing their engineering meaning.

## Deferred evidence

A real legacy client project fixture was not available during Phase 2. Synthetic legacy-coordinate tests reproduce the current formulas, but production migration acceptance remains conditional on testing real de-identified projects.
