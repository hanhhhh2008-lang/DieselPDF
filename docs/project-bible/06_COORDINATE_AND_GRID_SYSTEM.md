# Coordinate and Grid System

## Master coordinate convention

Use project millimetres as the default engineering unit, with:

- global X positive to the right;
- global Y positive upward in plan;
- global Z positive upward by level;
- explicit right-handed local axes for structural elements.

Never derive permanent geometry from current zoom or Canvas pixels.

## Coordinate spaces

Required spaces:

1. project coordinates;
2. storey-local coordinates;
3. PDF page coordinates;
4. source raster pixel coordinates;
5. CAD modelspace coordinates;
6. CAD paperspace and viewport coordinates;
7. screen Canvas coordinates;
8. solver coordinates where a backend requires a different axis convention.

Each conversion must be represented by an explicit transform record with source, target, units, matrix, provenance and tolerance.

## Transform model

Use homogeneous affine transforms for 2D and 3D where applicable. Support:

- translation;
- uniform and non-uniform scale;
- rotation;
- axis reflection;
- skew only when required to rectify scanned drawings;
- composed transforms;
- reversible conversion with recorded numerical tolerance.

The system must flag a calibration that creates unacceptable distortion or inconsistent dimensions.

## Calibration methods

- one known dimension plus selected origin and axis;
- two-point scale and direction calibration;
- three-point affine calibration;
- matching two or more grid intersections;
- matching CAD reference points;
- automatic proposal from dimension strings, followed by engineer confirmation.

## Grid data model

A Grid is a semantic engineering object, not merely a line.

Required properties:

```text
grid_id
label
axis_family
geometry
storey_or_vertical_extent
rotation
offset
bubble_positions
locked_status
source_entities
review_status
revision
```

Support:

- lettered grids;
- numbered grids;
- secondary and offset grids;
- radial grids in future;
- grid intersections;
- automatic labels;
- grid copying and alignment between storeys;
- snapping to lines and intersections;
- member and column references to grids.

## Storeys and levels

Separate storeys from physical levels. A storey may reference:

- finished floor level;
- structural slab level;
- ceiling level;
- roof bearing level;
- footing or ground levels;
- local step-downs and split levels.

Do not infer all structural Z coordinates from a single storey height.

## Drawing sheets and views

A drawing sheet has its own coordinate space and may contain viewports. The structural model remains in project coordinates; a drawing view defines:

- crop region;
- scale;
- rotation;
- sheet placement;
- visible layers and object filters;
- annotation scale.

## Tolerances

Define central tolerance policies rather than scattered magic numbers. Categories should include:

- coordinate equality;
- endpoint snapping;
- collinearity;
- wall-pair spacing;
- grid alignment;
- source-to-revision matching;
- DXF/PDF round-trip drift;
- structural node merging.

Tolerance values must be unit-aware and appropriate to source quality. A scanned plan needs different confidence and tolerances from a native DXF.

## Required tests

- forward and inverse transform tests;
- composed transform tests;
- rotated and reflected sheet tests;
- grid intersection and snapping tests;
- multi-storey alignment tests;
- PDF-to-project-to-PDF round trip;
- DXF-to-project-to-DXF round trip;
- no cumulative coordinate drift after repeated save and export cycles.