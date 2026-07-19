# Current DieselPDF State

## Existing application

DieselPDF is presently a native Python/Tkinter desktop prototype centred on `DieselPDF.pyw`. It already demonstrates useful foundations for an engineering document platform:

- PDF rendering with PyMuPDF;
- multiple documents and pages;
- drawing, markup and measurement tools;
- calibration and basic snapping concepts;
- layers;
- CAD-style text commands;
- PDF vector and text extraction;
- DXF output with ezdxf;
- generated PDF output;
- project save and open using `.dieselpdf.json`;
- basic Canvas-to-CAD and CAD-to-Canvas conversion.

## Current coordinate behaviour

The application currently relies on Canvas coordinates, a page origin and a scale factor. Y-axis reversal and scale conversion are applied when translating between Canvas and CAD coordinates.

This is adequate for a prototype but insufficient as a durable engineering model because:

- Canvas pixels change with zoom, rendering and viewport behaviour;
- page stacking and multiple sheets can introduce arbitrary offsets;
- a single scale and origin cannot fully represent rotated or skewed references;
- objects do not yet have a robust project-coordinate identity independent of the display;
- CAD and PDF round trips cannot reliably match modified objects without stable IDs and source metadata.

## Current storage behaviour

The project serializer primarily records Canvas object types and visual properties such as coordinates, fill, outline and width. This preserves markups but does not yet provide:

- formal schema validation;
- stable geometry IDs;
- semantic structural objects;
- relationships;
- spatial indexing;
- source-document traceability at object level;
- calculation links;
- schema migration and revision history.

## Current PDF-to-CAD behaviour

PDF vector extraction uses PyMuPDF drawing paths and text spans. Lines, rectangles, curves and text can be converted into CAD-like commands. Curves may be approximated with polylines. Multiple pages may be stacked using arbitrary vertical offsets.

This is useful extraction code and should be preserved behind a new importer interface. It must not define the future project coordinate model.

## Current DXF and PDF output

The current code can convert internal CAD commands to DXF and PDF. These functions are reusable as prototypes, but future output should be generated from the engineering dataset rather than directly from Canvas objects or transient command lists.

## Principal technical debt

- one large monolithic UI/application file;
- tightly coupled UI, persistence, geometry, import/export and business logic;
- Canvas treated as storage rather than a view;
- limited unit and coordinate abstraction;
- no database transaction model;
- no stable ID and revision architecture;
- no neutral semantic or FEA model;
- vendored dependencies and Windows-oriented launch assumptions;
- insufficient automated tests for geometry and round trips;
- no explicit engineering approval state machine.

## Reusable assets

Do not discard the working prototype. Reuse and progressively isolate:

- PyMuPDF rendering and extraction;
- current drawing and selection interactions;
- measurement workflow;
- CAD command parsing;
- DXF generation;
- PDF generation;
- existing project loading as migration input;
- launcher and packaging knowledge;
- current user-interface patterns familiar to Aaron.

## Required migration principle

Use a strangler migration rather than a full rewrite:

1. introduce schemas and services beside the existing code;
2. migrate one object category at a time from Canvas ownership to dataset ownership;
3. render migrated objects back onto the existing Canvas;
4. preserve old project loading through an explicit importer;
5. add tests before removing old code paths;
6. refactor the monolith only after behaviours are protected by tests.