# Owner Engineering Context

## Engineering owner

Aaron Han is a NSW structural, forensic and remedial engineer. The platform should support practical engineering judgement, transparent calculations and efficient production of coordinated drawings rather than research-only demonstrations.

## Response and documentation preferences

For engineering design and calculation work:

- use Australian Standards and NCC requirements as the primary basis;
- cite relevant clauses wherever practicable;
- show calculation steps and assumptions;
- distinguish preliminary checks from formal design documentation;
- identify critical missing information that may affect capacity or certification;
- make conservative preliminary assumptions only where appropriate and visible;
- do not hide uncertainty behind confident language;
- favour practical calculation notes and engineering workflows over generic report prose unless a report is specifically required.

## Established engineering domains

The broader engineering workflow has established reference directions for:

- timber framing and engineered timber;
- reinforced concrete;
- residential slabs and footings;
- masonry and brickwork;
- cold-formed steel;
- aluminium;
- stormwater and NSW drainage coordination;
- structural, forensic and remedial inspection reporting.

DieselPDF should eventually consume these as separate versioned engineering rule modules rather than embedding all standards logic into the UI or FEA adapter.

## Drawing and QA expectations

Generated drawings should be suitable for a structural consultancy workflow and should support:

- clear member tags and schedules;
- Australian engineering terminology;
- traceable assumptions and notes;
- architect and services coordination;
- preliminary and construction issue states;
- consistent plan, section, schedule and detail references;
- post-QA issue rather than uncontrolled automatic export.

When a previous approved company drawing set or report template is provided, derive the presentation system from that reference while preserving engineering data independently from formatting.

## Structural modelling expectations

The platform must make modelling assumptions visible, including:

- member local axes;
- releases and support conditions;
- effective lengths and restraint;
- self-weight treatment;
- load cases and combinations;
- serviceability criteria;
- diaphragm and bracing assumptions;
- connection and footing load paths.

A visually correct model is not sufficient. Aaron must be able to inspect the deformed shape, reactions, member diagrams, governing combinations, stability warnings and downstream load transfer.

## Australian supply and constructability

Where the platform recommends sections, products or connections, it should eventually check:

- standard Australian section availability;
- supplier and manufacturer data;
- project location and procurement constraints;
- site fit-up and access;
- installation and temporary-stability requirements;
- compatibility with architecture, waterproofing, services and supporting structures.

## Engineer-in-the-loop behaviour

The software should minimise repetitive work while keeping Aaron responsible for:

- approving source geometry;
- confirming project inputs;
- choosing the structural system;
- resolving abnormal or existing conditions;
- reviewing analysis assumptions and results;
- approving member and connection strategies;
- completing final engineering issue and certification.