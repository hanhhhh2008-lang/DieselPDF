# Human Inputs and Approval Gates

## Principle

The goal is to reduce Aaron's work to high-value engineering decisions, not to remove engineering responsibility. The software should automate extraction, repetitive calculations, drafting and consistency checks while requiring human confirmation for ambiguous, project-specific or safety-critical matters.

## Inputs needed to develop the platform

### Historical paired projects

For each selected project, preferably provide:

- final architectural drawings;
- final issued structural drawings;
- calculations or analysis models;
- geotechnical information;
- design assumptions;
- engineer markups and drafting revisions;
- construction-stage RFIs or corrections;
- final adopted member and footing schedules.

Start with approximately 10 to 20 conventional, high-quality residential projects. Curated data is more valuable than a large unstructured archive.

### Company drafting standards

Aaron needs to provide or approve:

- title blocks;
- standard sheet layouts;
- layers, lineweights and linetypes;
- fonts and text sizes;
- member-mark conventions;
- drawing and revision numbering;
- schedule formats;
- general notes;
- typical details;
- issue-status and approval conventions.

### Engineering preferences

The system needs explicit preferences such as:

- when to prefer timber, LVL, steel or masonry support;
- preferred standard sections and products;
- maximum acceptable beam depths;
- preference for hidden beams or minimum posts;
- common footing systems;
- bracing and tie-down systems;
- connection families;
- solutions normally rejected by the practice;
- constructability and supplier constraints.

### QA knowledge

Convert Aaron's review questions into rules, for example:

- what supports this beam or wall below;
- where does this reaction terminate;
- are upper and lower supports aligned;
- is the member mark consistent with its schedule;
- does the post clash with a door, window, stair or service;
- is footing support confirmed by geotechnical information;
- are truss reactions and concentrated loads included;
- is the lateral and tie-down path complete;
- are construction-stage restraints and propping addressed.

## Inputs required for each new project

### Mandatory project information

- project address and jurisdiction;
- building classification;
- latest architectural drawings and revision;
- project type: new, addition, alteration or existing assessment;
- number of storeys and key levels;
- structural design scope;
- proposed materials and construction systems;
- geotechnical report and site classification where foundations are in scope;
- known existing structural information for alterations.

### Actions and design basis

- importance level and design working life;
- wind classification or AS/NZS 1170.2 parameters;
- earthquake parameters where required;
- permanent and imposed actions;
- floor, roof and wall weights;
- masonry, stone and façade loads;
- water tanks, plant, solar panels and other equipment;
- concentrated and impact loads;
- retaining or soil pressures;
- truss or proprietary-system reactions;
- serviceability and vibration requirements.

The program may propose defaults, but defaults remain visible assumptions requiring approval.

### Architectural and construction constraints

- zones where columns are prohibited or preferred;
- maximum beam depth and available ceiling zones;
- areas requiring flush framing;
- large openings and sliding doors;
- stairs, voids and set-downs;
- service corridors and penetrations;
- wet areas and waterproofing coordination;
- cantilevers and architectural features;
- builder preferences and construction access;
- temporary support and sequencing constraints.

### Existing structures

For alterations, input or verify:

- existing drawings;
- site inspection observations;
- actual member sizes and materials;
- footing and support conditions;
- deterioration or damage;
- demolition and retained works;
- intrusive investigation results;
- uncertainty and temporary-propping requirements.

Unverified existing conditions must remain explicitly uncertain.

## Approval gates

### Gate 1 — source and geometry

Engineer confirms:

- correct documents and revisions;
- calibration and scale;
- relevant plan regions;
- grids, storeys and levels;
- unresolved source conflicts.

### Gate 2 — architectural semantics

Engineer confirms:

- walls, openings, rooms and slab edges;
- roof and floor boundaries;
- loadbearing status assumptions;
- important architectural constraints.

### Gate 3 — structural topology

Engineer selects or approves:

- framing directions;
- beams, posts and loadbearing walls;
- transfers;
- bracing and tie-down concept;
- foundation concept;
- complete load paths.

### Gate 4 — design basis

Engineer approves:

- loads and combinations;
- materials and grades;
- restraints and support assumptions;
- standards and editions;
- geotechnical basis;
- serviceability limits.

### Gate 5 — analysis and design

Engineer reviews:

- model connectivity and releases;
- deformed shape and reactions;
- governing combinations;
- member utilisation;
- deflection and vibration;
- connection demands;
- footing reactions;
- warnings and sensitivities.

### Gate 6 — drawings and QA

Engineer confirms:

- plans, sections, schedules and details agree;
- architectural coordination;
- assumptions and limitations are documented;
- all critical QA items are resolved;
- issue status is appropriate.

### Gate 7 — final issue

Only the authorised engineer may approve formal construction issue or certification.

## Feedback capture

Every correction should be classified:

- source-reading error;
- geometry error;
- semantic classification error;
- structural topology error;
- load or calculation error;
- drafting error;
- preference or constructability adjustment;
- project-specific exception.

Use this classification to decide whether the correction becomes a global rule, a model-training example, a project preference or a one-off exception.