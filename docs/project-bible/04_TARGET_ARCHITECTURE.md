# Target Architecture

## Architectural style

Use a modular, adapter-based architecture with a stable engineering domain model at the centre.

```text
Desktop UI / future web UI
        ↓ commands and queries
Application services
        ↓
Engineering domain model
        ↓
Project database and revision store
        ↓
Adapters: PDF | DXF/DWG | IFC | FEA | reports | AI
```

## Core layers

### 1. Presentation layer

Responsibilities:

- Canvas rendering and interaction;
- dataset tables and property editing;
- cross-selection between drawings and records;
- review overlays and approval gates;
- no permanent ownership of engineering geometry.

Tkinter may remain during controlled migration. A future UI change should not be allowed to redefine the domain model.

### 2. Application layer

Use explicit commands and queries such as:

- import document;
- calibrate sheet;
- create grid;
- create or modify entity;
- classify wall;
- approve structural topology;
- generate analysis model;
- run solver;
- generate drawing view;
- export revision.

Commands should validate preconditions, execute transactions and record revision events.

### 3. Domain layer

Central domain packages should include:

- geometry;
- documents and transforms;
- layers and styles;
- storeys, levels and grids;
- architectural objects;
- structural objects;
- relationships and load paths;
- actions and combinations;
- analysis models and results;
- design checks;
- drawing views and schedules;
- review status and QA issues.

The domain layer must not import Tkinter, PyMuPDF, ezdxf or a specific FEA solver.

### 4. Persistence layer

Recommended local project store:

- SQLite for transactional records;
- R-Tree for spatial queries;
- explicit schema versions and migrations;
- binary or external storage for source PDFs and large artefacts where appropriate;
- append-only audit events for important engineering approvals and changes.

### 5. Adapter layer

Adapters translate external formats to and from the domain model:

- PyMuPDF PDF adapter;
- ezdxf DXF adapter;
- ODA or AutoCAD-native DWG bridge;
- IfcOpenShell IFC adapter;
- solver adapters for PyNite, OpenSees or other selected engines;
- JSONL, CSV and GeoParquet exchange;
- AI recognition service that returns proposals with confidence and provenance.

### 6. Deterministic engineering services

Separate services should cover:

- units and tolerances;
- geometry repair and topology;
- tributary areas and widths;
- load takedown;
- load combinations;
- analysis model construction;
- member design;
- structural option scoring;
- drawing generation;
- QA rules.

## Suggested repository structure

```text
dieselpdf/
  app/
  domain/
    geometry/
    documents/
    architecture/
    structure/
    analysis/
    design/
    drawings/
    qa/
  services/
  persistence/
  adapters/
    pdf/
    dxf/
    dwg/
    ifc/
    fea/
    ai/
  ui/
  migrations/
  schemas/
  tests/
    unit/
    integration/
    benchmarks/
    regression/
```

## Dependency direction

Dependencies point inward:

- UI depends on application services;
- adapters depend on domain interfaces;
- persistence implements domain repositories;
- domain never depends on UI or vendors;
- Australian design modules consume neutral analysis results rather than solver-native objects.

## Deployment direction

Initial priority is reliable local desktop operation on Windows and macOS. Heavy solvers may run through isolated subprocesses or containers. Solver crashes must not corrupt the project database.

## Security and reliability

- treat uploaded files as untrusted;
- isolate parsing and solver processes where practical;
- validate file size, format and paths;
- never execute embedded scripts or macros from source documents;
- use atomic saves and backups;
- preserve source documents unchanged;
- record import hashes;
- require explicit confirmation for destructive migrations or replacements.