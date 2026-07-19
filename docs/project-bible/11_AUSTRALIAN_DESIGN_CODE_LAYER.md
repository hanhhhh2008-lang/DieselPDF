# Australian Design-Code Layer

## Principle

A finite-element solver calculates structural response. It does not by itself demonstrate compliance with the NCC or Australian Standards. DieselPDF must implement a separate deterministic design-code layer.

## Separation of responsibilities

### Analysis layer

Produces:

- displacements and rotations;
- reactions;
- member actions;
- plate and shell actions;
- modal properties;
- buckling factors;
- convergence and solver diagnostics.

### Design layer

Consumes approved actions and checks:

- strength;
- stability;
- serviceability;
- durability;
- fire requirements where in scope;
- detailing and connection requirements;
- load path and robustness;
- project-specific limitations.

## Standards framework

Future modules should support current project-adopted editions of the following as applicable:

- NCC for statutory and building-class context;
- AS/NZS 1170.0 for structural design actions and combinations;
- AS/NZS 1170.1 for permanent, imposed and other actions;
- AS/NZS 1170.2 for wind actions;
- AS 1170.4 for earthquake actions;
- AS 4055 for housing wind classification where within scope;
- AS 1684.2 for conventional timber-framed residential construction within scope;
- AS 1720.1 for engineered timber design;
- AS 2870 for residential slabs and footings;
- AS 3600 for concrete structures;
- AS 4100 for structural steel;
- AS 3700 and current AS 4773 provisions for masonry;
- AS/NZS 4600 for cold-formed steel;
- AS/NZS 1664 for aluminium;
- relevant product, fastener, welding, durability and construction standards.

The software must identify the edition, amendment and project adoption basis rather than assuming one universal current edition.

## Design input record

Every project requires a versioned design basis containing:

```text
building class
importance level
design working life
project location
wind region and site parameters
terrain, shielding and topography
housing wind classification where applicable
earthquake parameters where applicable
permanent and imposed actions
material grades
exposure and durability conditions
fire resistance requirements
serviceability limits
geotechnical parameters
construction and restraint assumptions
selected standards and editions
```

## Calculation record

Every design check should record:

- calculation ID and revision;
- source member and analysis result IDs;
- input values and units;
- assumptions;
- load case or combination;
- governing action;
- clause and equation references;
- capacity and serviceability result;
- utilisation;
- pass, fail or review-required status;
- warnings and critical missing inputs;
- software module version;
- reviewer and approval state.

## Initial calculation modules

Recommended early modules:

1. load-case and combination generator;
2. tributary width and load takedown;
3. simple timber joist, rafter and bearer selection within AS 1684 scope;
4. engineered timber beam checks;
5. steel beam and column strength and serviceability;
6. basic steel connection demand schedule, without pretending to complete all connection design;
7. post reactions and footing actions;
8. AS 2870 scope and footing-system decision support;
9. masonry lintel and wall-support checks where appropriately scoped;
10. bracing demand, capacity and tie-down schedules.

## Scope gates

Each standards module must first check whether the project and member are within its scope. Examples:

- AS 1684 limits on building class, storeys, wind classification, geometry and conventional construction;
- AS 2870 site classification and abnormal site conditions;
- AS 4055 housing limitations;
- proprietary engineered products requiring manufacturer data;
- unusual loads, high axial forces, transfers or non-standard connections requiring engineered analysis.

Out-of-scope conditions must route to an engineered calculation path or manual review.

## Conservative assumptions

The program may make conservative preliminary assumptions only when:

- the assumption is clearly displayed;
- the sensitivity is understood;
- the missing data is not essential to the validity of the model;
- the result remains marked preliminary;
- the engineer must confirm or replace the assumption before issue.

It must not invent material grade, footing support, restraint, connection capacity or soil properties where those are essential.

## Units and numerical reliability

Use a formal units library or equivalent internal quantity system. Prevent mixing N and kN, mm and m, MPa and Pa. Store raw values with declared units or in controlled canonical units.

## Design QA

- check analysis revision matches design revision;
- check all members have material and section data;
- check all governing combinations are considered;
- check strength and serviceability separately;
- check reactions are transferred downstream;
- check member schedule agrees with calculations;
- check assumptions and warnings appear on drawings or design notes where required;
- prevent final approval when a failed or unresolved critical check exists.