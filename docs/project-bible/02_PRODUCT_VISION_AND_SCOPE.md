# Product Vision and Scope

## Vision

DieselPDF should become a structural engineering workbench in which drawings, engineering objects, calculations and review comments are different views of one coordinated project model.

The engineer should be able to upload an architectural package, calibrate or verify the geometry, review detected architectural objects, select or adjust a structural scheme, run transparent calculations and obtain a coordinated preliminary structural drawing set.

## Users

Primary users:

- structural engineers;
- engineering drafters;
- forensic and remedial engineers reviewing existing drawings;
- engineering QA reviewers.

Secondary users may include builders or architects viewing preliminary coordination outputs, but they must not be able to mistake preliminary outputs for construction-certified documentation.

## Initial in-scope work

The first controlled production scope should focus on conventional NSW Class 1 and Class 10 buildings:

- one or two storeys;
- common timber, steel, masonry and slab-on-ground construction;
- ordinary roof trusses or conventional roof framing;
- conventional openings and beam/post arrangements;
- straightforward wind and gravity actions;
- ordinary footing systems supported by project-specific geotechnical information.

## Explicit early exclusions

The system must not force automated solutions for:

- high-rise or Class 2 buildings;
- major transfer structures;
- basements and complex retaining systems;
- highly irregular architecture;
- long-span or vibration-critical structures;
- significant seismic, fatigue or impact design;
- post-tensioned structures;
- complex soil-structure interaction;
- Class P foundation conditions without project-specific engineering;
- proprietary systems without verified technical data;
- existing structures where critical geometry, materials or support conditions are unverified.

## System modes

Recommended modes:

1. **Document mode** — PDF review, markup, measurement and revision comparison.
2. **Geometry mode** — coordinates, grids, entities, layers and CAD/PDF round trip.
3. **Semantic mode** — walls, openings, rooms, slabs, roofs and structural objects.
4. **Structural mode** — supports, load paths, framing options and analysis model.
5. **Design mode** — actions, combinations, member checks and schedules.
6. **Drawing mode** — sheet generation, details, schedules and annotations.
7. **QA mode** — clashes, unsupported objects, missing data and issue gates.

## Success definition

Success is not merely producing a visually similar structural plan. A successful output must be:

- geometrically aligned;
- structurally coherent;
- supported by a complete load path;
- traceable to inputs and assumptions;
- calculation-backed;
- editable;
- automatically checked;
- clearly marked preliminary;
- efficient for an engineer to review and correct.