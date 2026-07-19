# Ten-Phase Engineering Roadmap

## Phase 1 — Architecture audit and optimum implementation plan

### Purpose

Inspect the complete repository and establish the target architecture before major coding.

### Deliverables

- current-state and technical-debt audit;
- reusable-function map;
- options comparison for geometry, storage, CAD, BIM, FEA and UI;
- FEA scored decision matrix;
- target package architecture;
- project-file migration strategy;
- licence and deployment review;
- risk register and decision log;
- implementation backlog.

### Gate

Aaron approves the architecture and initial solver strategy.

---

## Phase 2 — Coordinate, storey and grid core

### Deliverables

- project and storey coordinates;
- affine transform registry;
- units and tolerance service;
- numbered and lettered Grid Manager;
- levels and storeys;
- PDF, CAD and Canvas transform tests;
- visual calibration and alignment tools.

### Gate

Repeated coordinate conversions and exports remain within approved tolerances.

---

## Phase 3 — Engineering dataset and persistence

### Deliverables

- Pydantic domain schemas;
- SQLite database and migrations;
- R-Tree spatial indexing;
- stable IDs, revisions and relationships;
- dataset table and cross-selection;
- legacy `.dieselpdf.json` importer;
- JSONL export and import.

### Gate

Canvas renders selected object classes from database ownership, and old projects migrate without silent data loss.

---

## Phase 4 — PDF, DXF, DWG and IFC round trip

### Deliverables

- vector PDF importer with provenance;
- DXF importer and exporter with stable IDs;
- conflict-aware re-import;
- vector PDF generator from drawing views;
- DWG bridge proof of concept;
- IFC storey, grid and basic object adapter;
- round-trip reconciliation report.

### Gate

No unacceptable coordinate drift, object duplication or unsupported-object silence.

---

## Phase 5 — Architectural semantic extraction

### Deliverables

- wall, opening, room and slab-edge proposals;
- roof and floor boundaries;
- text and dimension association;
- AI proposal schema and confidence;
- engineer review overlays and correction tools;
- recognition metrics and curated test set.

### Gate

Engineer correction time and critical semantic error rate meet agreed thresholds on pilot projects.

---

## Phase 6 — Structural topology and load-path generation

### Deliverables

- structural object model;
- framing direction proposals;
- beams, posts, loadbearing walls and footings;
- gravity and lateral load-path graph;
- support and transfer validation;
- alternative scheme scoring;
- engineer approval workflow.

### Gate

No candidate can pass with an incomplete support or stability path.

---

## Phase 7 — Neutral FEA model and solver adapters

### Deliverables

- solver-independent AnalysisModel;
- Tier 1 solver adapter;
- neutral result schema;
- model viewer and diagnostic checks;
- benchmark harness;
- SpaceGass comparison suite;
- advanced solver proof of concept.

### Gate

Validated scope and result tolerances are documented and approved.

---

## Phase 8 — Australian Standards design layer

### Deliverables

- design-basis records;
- AS/NZS 1170 action and combination modules;
- controlled timber, steel, footing, bracing and other selected checks;
- calculation traceability and clause references;
- schedule generation;
- scope and assumption gates.

### Gate

No design module is released beyond its tested standard scope.

---

## Phase 9 — Structural drawing generation

### Deliverables

- footing, slab, floor and roof plans;
- schedules and tags;
- sections and standard-detail placement;
- title blocks and issue statuses;
- editable DXF and vector PDF;
- drawing-object-calculation links;
- drafting QA.

### Gate

Plans, schedules, sections and calculations reconcile automatically and pass engineer review on pilot projects.

---

## Phase 10 — Project validation, learning and controlled release

### Deliverables

- curated historical project benchmark set;
- regression tests from engineer corrections;
- reliability metrics;
- supported-scope statement;
- user documentation and training;
- backup, security and audit procedures;
- controlled production release process.

### Gate

Aaron approves the supported production scope and mandatory human checks.

## Programme rules

- do not skip approval gates;
- do not solve a later phase by embedding unstructured data into an earlier layer;
- preserve stable IDs and source traceability throughout;
- keep generic analysis separate from design-code compliance;
- prefer a narrow validated scope over a broad unverified feature set;
- convert every meaningful defect into a regression test or documented limitation.