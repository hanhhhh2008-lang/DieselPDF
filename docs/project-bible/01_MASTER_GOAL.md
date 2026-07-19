# Master Goal

## Primary objective

Build DieselPDF into an engineering software platform that can receive architectural drawings and produce a coordinated preliminary structural drawing set with traceable calculations, assumptions and QA for structural engineer review.

## Target workflow

Architectural PDF, DXF, DWG or IFC
→ coordinate and grid calibration
→ engineering geometry dataset
→ architectural semantic model
→ structural framing and load-path generation
→ deterministic FEA
→ Australian Standards member and system checks
→ structural drawing generation
→ automated QA
→ engineer approval and issue.

## Long-term outputs

The target system should be capable of producing, where applicable:

- footing and slab plans;
- ground-floor and upper-floor framing plans;
- roof framing plans;
- beams, posts, lintels and footing schedules;
- bracing and tie-down layouts;
- structural sections and standard details;
- editable DXF or DWG;
- vector PDF drawings;
- neutral analysis model and solver inputs;
- calculation dataset and calculation summaries;
- assumptions and missing-information registers;
- clash, load-path and drafting QA reports.

## Product position

The initial product is a Structural Engineering Design and Drafting Copilot. It assists with repetitive geometry processing, option generation, analysis orchestration, calculations, drafting and checking. It does not replace the registered engineer's judgement, responsibility, project verification or certification.

## Engineering development method

Use controlled engineering iteration:

1. define a narrow function;
2. implement a deterministic prototype;
3. verify it against hand calculations and known benchmarks;
4. test it against completed real projects;
5. capture engineer corrections and failure modes;
6. convert corrections into rules and regression tests;
7. expand scope only after the previous scope is demonstrably reliable.

## Initial controlled domain

Start with conventional NSW Class 1 and Class 10 residential buildings, normally one or two storeys, conventional geometry, no basement, no major transfers and no unusual foundation or dynamic conditions. Out-of-scope projects must fall back to a manual engineering workflow.