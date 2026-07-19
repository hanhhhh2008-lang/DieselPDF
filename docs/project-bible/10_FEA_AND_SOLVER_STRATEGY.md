# FEA and Solver Strategy

## Objective

Provide reliable structural analysis without coupling DieselPDF to one solver or confusing generic finite-element analysis with Australian Standards design compliance.

## Neutral analysis model

Create a solver-independent `AnalysisModel` with explicit units and axis conventions.

Minimum content:

```text
model_id and revision
unit_system
nodes and coordinates
materials
sections
frame, truss, spring, cable, plate, shell and link elements
member local axes and offsets
end releases and partial fixity
supports and multi-point constraints
masses
diaphragms
load cases and load combinations
nodal, member, area, temperature, settlement and prestress actions
analysis type
solver settings
requested results
source Diesel object IDs
assumptions and warnings
```

Results should be normalised into a neutral `AnalysisResultSet` containing displacements, reactions, element forces, stresses, modes, buckling factors, convergence information and solver diagnostics.

## Solver adapter contract

Each adapter must implement:

- capability declaration;
- model validation;
- translation from neutral model;
- isolated solver execution;
- log and error capture;
- result translation;
- unsupported-feature reporting;
- solver and adapter version recording;
- deterministic test fixtures.

Never silently approximate an unsupported element, release or load. Require an explicit documented fallback.

## Candidates for Phase 1 evaluation

### PyNite

Strengths:

- Python-native and easy to embed;
- 3D elastic frame analysis;
- load cases and combinations;
- P-Delta for frame structures;
- modal frame analysis;
- springs and tension/compression-only elements;
- basic plate/quad meshes;
- accessible code and MIT licence;
- suitable for transparent residential prototypes and benchmarks.

Risks:

- not a full ETABS or SpaceGass replacement;
- limited advanced nonlinear, shell, staged-construction and dynamic scope;
- some advanced features are comparatively new or beta;
- requires independent engineering validation.

### OpenSees / OpenSeesPy

Strengths:

- mature research-grade nonlinear structural analysis;
- extensive material, element and dynamic analysis capability;
- strong earthquake, fibre-section and nonlinear modelling ecosystem;
- Python interface available.

Risks:

- steep modelling and result-processing complexity;
- not a building-design GUI or code-check package;
- higher validation and deployment burden;
- modelling choices can materially affect results and require expert control.

### XC

Strengths:

- structural-engineering-oriented open-source FEA;
- Python interface;
- 0D, 1D, 2D and 3D elements;
- linear/nonlinear, static/dynamic and construction-stage capabilities;
- code-checking infrastructure for several non-Australian standards.

Risks:

- installation and dependency complexity;
- limited user manual and smaller community;
- existing design-code modules do not remove the need for Australian modules;
- deployment on desktop platforms requires careful testing.

### Frame3DD

Strengths:

- focused 3D frame analysis;
- transparent and relatively compact;
- static and dynamic frame capability;
- useful independent benchmark backend.

Risks:

- narrow element scope;
- limited shell and advanced nonlinear capability;
- integration and modern maintenance need review.

### CalculiX

Strengths:

- mature general-purpose implicit FEA;
- solid, shell and contact capabilities;
- Abaqus-like input concepts;
- useful for specialised detailed analysis.

Risks:

- not naturally aligned with a lightweight residential frame workflow;
- preprocessing and result translation complexity;
- code design checks remain separate;
- desktop packaging and licence implications need formal review.

### Code_Aster

Strengths:

- extensive general-purpose nonlinear and multiphysics analysis;
- mature capabilities for advanced structural problems.

Risks:

- very high deployment and learning complexity;
- unsuitable as the initial embedded residential engine;
- substantial adapter, verification and support burden.

### Kratos Multiphysics

Strengths:

- modern extensible multiphysics framework;
- advanced nonlinear, parallel and research capabilities;
- Python orchestration around a C++ core.

Risks:

- very large and complex framework;
- excessive for initial frame design;
- significant deployment, modelling and validation effort.

## Recommended architecture to validate

Use a tiered solver strategy:

### Tier 1 — ordinary structural frames

Evaluate PyNite as the initial embedded frame/truss/spring engine because it is transparent, Python-native and easy to test. Restrict its certified internal scope to validated functions only.

### Tier 2 — advanced nonlinear and dynamic work

Evaluate OpenSeesPy as the leading advanced backend for nonlinear frames, fibre sections and dynamic analysis. XC may be compared as a structural-engineering-oriented alternative.

### Tier 3 — specialised continuum and shell analysis

Keep CalculiX, Code_Aster or Kratos as optional specialist adapters rather than core dependencies. Do not include them in the initial desktop package without a demonstrated project need.

### Independent benchmark

Use Frame3DD and closed-form solutions as independent comparison tools for selected frame and modal cases.

## Required decision matrix

Phase 1 must score candidates against weighted criteria:

- frame and truss capability;
- spring and tension/compression-only capability;
- plate and shell capability;
- modal and buckling analysis;
- P-Delta and large displacement;
- material nonlinearity;
- staged construction;
- Python API and adapter clarity;
- result extraction;
- Windows and macOS deployment;
- documentation and community;
- maintenance activity;
- test and benchmark evidence;
- licence compatibility;
- total validation and support burden.

Do not select by feature count alone. The initial solver should minimise unverified complexity.

## Analysis types to phase

1. linear static 2D and 3D frames and trusses;
2. load combinations and envelopes;
3. springs, releases and tension/compression-only members;
4. first-order modal analysis;
5. geometric stiffness and P-Delta;
6. elastic plate and shell behaviour;
7. linear buckling;
8. material nonlinearity and pushover;
9. transient dynamic analysis;
10. staged construction and specialised analysis.

Each capability requires its own verification gate.

## Verification requirements

- direct stiffness hand examples;
- simply supported, fixed and continuous beam cases;
- 2D and 3D trusses;
- portal frames with releases;
- torsional and biaxial frame cases;
- spring support cases;
- P-Delta benchmark;
- modal frequency and mode-shape cases;
- plate patch tests;
- buckling benchmarks;
- comparison with SpaceGass models using identical assumptions;
- tolerance-based result reconciliation;
- sign-convention and local-axis tests.

The application must show model assumptions and solver warnings. A converged solution is not automatically a correct engineering model.