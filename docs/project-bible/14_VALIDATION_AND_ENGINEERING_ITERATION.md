# Validation and Engineering Iteration

## Objective

Establish evidence that each automated function is correct within a clearly declared scope. Validation must address geometry, data integrity, analysis, code checks, drawing coordination and engineer usability.

## Engineering iteration loop

For every feature:

1. define the engineering question and limited scope;
2. state inputs, outputs, assumptions and acceptance tolerances;
3. implement the smallest deterministic solution;
4. test against independently known answers;
5. compare against a trusted commercial or manual workflow;
6. apply it to completed real projects;
7. classify discrepancies;
8. correct algorithms, data or rules;
9. create regression tests;
10. obtain engineer approval before widening scope.

## Test hierarchy

### Unit tests

- coordinate transforms;
- geometry operations;
- units;
- schema validation;
- load combinations;
- section properties;
- member equations;
- ID and revision logic.

### Integration tests

- PDF import to dataset;
- DXF import and export;
- Canvas rendering from database;
- semantic object creation;
- analysis-model generation;
- solver execution and result normalisation;
- schedule and drawing generation.

### Engineering benchmark tests

- hand-solvable beams and trusses;
- portal frames;
- frames with releases and springs;
- load-takedown examples;
- P-Delta and modal benchmarks;
- plate patch tests;
- material and member-design examples from standards or reputable texts;
- selected SpaceGass comparison models.

### Project regression tests

Use completed project pairs:

- input only the architectural and project data available at the original design stage;
- generate the Diesel result;
- compare geometry, framing, loads, members, schedules and drawings;
- record engineer corrections;
- preserve the corrected expected outputs and reasons.

## SpaceGass comparison protocol

For each comparison model, document:

- geometry and units;
- section properties and material values;
- support conditions and releases;
- member orientation and offsets;
- self-weight treatment;
- load cases and combinations;
- analysis type and solver options;
- geometric nonlinearity settings;
- mass source and modal settings;
- output locations and sign conventions.

Compare:

- reactions and equilibrium;
- nodal translations and rotations;
- member end actions and diagrams;
- natural frequencies and mode shapes;
- buckling factors where applicable;
- convergence and warnings.

Differences must be investigated, not merely averaged or accepted.

## Geometry acceptance metrics

- transform inversion error;
- endpoint and vertex coordinate error;
- area and length error;
- stable-ID retention rate;
- unsupported entity count;
- round-trip drift after repeated export/import;
- semantic wall, opening and room accuracy;
- engineer correction time.

## Structural acceptance metrics

- equilibrium residual;
- stiffness and mechanism detection;
- result differences against closed-form solutions;
- result differences against benchmark solvers;
- governing combination agreement;
- design utilisation agreement;
- load-path completeness;
- false-pass and false-fail rate;
- critical issue detection rate.

False passes are more serious than conservative false fails and must receive separate risk tracking.

## Drawing acceptance metrics

- object and schedule consistency;
- missing tag and detail rate;
- architectural clash rate;
- number of manual drafting corrections;
- engineer review time;
- issue-blocking QA escape rate.

## Release gates

A capability may progress through:

1. Experimental;
2. Internal Prototype;
3. Benchmark Validated;
4. Project Pilot;
5. Engineer-Assisted Production;
6. Controlled Production.

Each status must state supported element types, actions, standards, limits, known defects and required human checks.

## Audit evidence

Store:

- test inputs and expected outputs;
- software and dependency versions;
- benchmark source;
- tolerance and rationale;
- test result and date;
- reviewer;
- unresolved variance;
- link to corrected issue or decision.

## No silent degradation

A dependency update, solver update or schema migration must rerun relevant benchmark and regression suites. If results change beyond tolerance, block release until the difference is understood.