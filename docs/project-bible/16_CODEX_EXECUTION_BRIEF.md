# Codex Execution Brief — Phase 1 Only

## Repository

`hanhhhh2008-lang/DieselPDF`

## Governing references

Read, in order:

1. root `AGENTS.md`;
2. all documents under `docs/project-bible/`;
3. GitHub Issue #2;
4. repository README, launch scripts, dependency folders and the complete `DieselPDF.pyw` file.

## Assignment

Calculate and document the optimum engineering implementation plan for transforming the current DieselPDF prototype into the structural autodrafting platform described in the Project Bible.

Do not begin Phase 2 implementation. Do not perform a major UI rewrite. Do not modify `main` directly.

## Required repository inspection

Map and assess:

- application startup and packaging;
- PDF loading, rendering and page management;
- Canvas object lifecycle;
- drawing, snapping and measurements;
- scale calibration and coordinate conversions;
- project save and open format;
- CAD command parser;
- PDF vector and text extraction;
- DXF export;
- PDF export;
- vendored dependencies;
- platform-specific assumptions;
- existing tests or absence of tests;
- error handling and data-loss risks.

For each reusable function or subsystem, identify:

- current location;
- current responsibility;
- dependencies;
- defects or risks;
- target interface;
- preserve, wrap, refactor or replace recommendation.

## Required technology comparison

Evaluate at minimum:

### Geometry, persistence and exchange

- PyMuPDF;
- ezdxf;
- ODA and AutoCAD-native DWG options;
- Pydantic;
- SQLite and R-Tree;
- Shapely;
- NetworkX;
- IfcOpenShell;
- JSONL and GeoParquet;
- current Tkinter UI versus controlled migration options.

### FEA

- PyNite;
- OpenSees/OpenSeesPy;
- XC;
- Frame3DD;
- CalculiX;
- Code_Aster;
- Kratos Multiphysics.

Confirm current repository activity, supported analyses, Python integration, deployment on Windows and macOS, licence implications, documentation, testing, maintenance risk and integration burden.

## FEA decision matrix

Use explicit weighted criteria. At minimum score:

- 3D frames and trusses;
- releases, offsets and springs;
- tension/compression-only elements;
- plate and shell elements;
- modal and buckling analyses;
- P-Delta and geometric nonlinearity;
- material nonlinearity;
- staged construction;
- dynamic analysis;
- API clarity;
- result extraction;
- desktop deployment;
- documentation and community;
- licence compatibility;
- validation burden;
- suitability for ordinary NSW residential work.

Provide separate recommendations for:

1. initial residential frame analysis;
2. future slab, wall and shell analysis;
3. future nonlinear and dynamic analysis;
4. independent benchmarking;
5. commercial distribution.

## Required target design

Define:

- package and dependency architecture;
- core domain interfaces;
- Pydantic schema outline;
- SQLite table and migration outline;
- coordinate-transform API;
- Grid and Storey model;
- document adapter contracts;
- Dataset and Canvas cross-selection design;
- neutral AnalysisModel and ResultSet;
- design-code module boundaries;
- QA rule architecture;
- background process or subprocess boundaries;
- error and transaction handling;
- migration from `.dieselpdf.json`;
- test and benchmark strategy.

## Deliverables

Create:

- `docs/architecture/phase-1-current-state-audit.md`
- `docs/architecture/phase-1-options-comparison.md`
- `docs/architecture/phase-1-target-architecture.md`
- `docs/architecture/phase-1-fea-solver-selection.md`
- `docs/architecture/phase-1-risk-register.md`
- `docs/architecture/phase-1-decision-log.md`
- `docs/architecture/phase-1-backlog.md`

The target-architecture document should include diagrams in Mermaid or clear text form. The backlog should contain epics, acceptance criteria, dependencies and estimated relative complexity rather than unsupported calendar promises.

## Completion rule

Stop when the seven Phase 1 review documents are complete. Do not begin production feature code.

At completion, report:

- exact files changed;
- top architecture recommendation;
- selected initial and advanced solver strategy;
- decisions requiring Aaron's approval;
- information still required from Aaron;
- major unresolved risks;
- proposed Phase 2 entry criteria.