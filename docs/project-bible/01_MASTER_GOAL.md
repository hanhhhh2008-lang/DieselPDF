# Master Goal

## Primary objective

Build DieselPDF into a trusted engineer-and-AI interface that can receive architectural drawings, support repeated engineering trial and review, and produce a coordinated preliminary structural drawing set with traceable calculations, assumptions and QA for structural engineer approval.

## Ultimate engineer-AI interface

DieselPDF should be the shared working surface between the engineer and AI. The AI may extract information, propose geometry and structural options, automate repetitive calculations, prepare drawings and identify QA issues. The engineer must be able to inspect the evidence, modify inputs, compare alternatives, reject or approve proposals and retain final control over every engineering decision and issued output.

The interface must preserve:

- source-document provenance and revision history;
- visible assumptions, uncertainties and missing information;
- repeatable trial, comparison and review workflows;
- deterministic calculations and validation evidence;
- human approval gates from source geometry through final issue;
- a clear record of what was proposed by AI and what was accepted by the engineer.

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
