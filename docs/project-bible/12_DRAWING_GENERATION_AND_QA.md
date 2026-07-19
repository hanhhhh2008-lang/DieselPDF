# Drawing Generation and QA

## Drawing generation principle

Generate drawings from approved engineering objects and drawing views. Do not draw structural plans directly from AI text or from transient Canvas graphics.

```text
Engineering objects and calculations
→ drawing-view rules
→ symbols, tags, schedules and annotations
→ sheet layout
→ DXF and vector PDF
→ automated QA
```

## Initial drawing outputs

Where applicable:

- cover sheet and general notes;
- footing and slab plan;
- ground-floor framing plan;
- upper-floor framing plan;
- roof framing plan;
- bracing and tie-down plan;
- beam, post, lintel and footing schedules;
- structural sections;
- standard and project-specific details;
- design assumptions and limitations.

## Drawing object traceability

Every visible structural item should link to:

- semantic object ID;
- member mark;
- calculation ID;
- design revision;
- source architectural revision;
- schedule row;
- relevant detail references.

A drawing tag is a view of an object, not a separate uncontrolled identity.

## Drawing views

A view defines:

- storey and level;
- crop region;
- scale and orientation;
- visible object classes and layers;
- lineweight and linetype mapping;
- annotation scale;
- tag placement rules;
- hidden or overhead element conventions;
- section and detail callouts.

## Drafting standards required from Aaron

The project needs approved company standards for:

- title block;
- fonts and text sizes;
- layer names and colours;
- lineweights and linetypes;
- member tags;
- drawing numbering and revisions;
- schedule formats;
- standard notes;
- standard details;
- sheet sizes and layouts;
- preliminary, tender, construction and as-built statuses.

## Automatic plan annotation

The generator should support:

- member tags positioned to avoid clashes;
- spans and dimensions;
- support and post marks;
- RLs and levels;
- grid references;
- fall and direction arrows;
- section and detail references;
- opening and penetration notes;
- design loads or special notes where required.

Automated placement must allow manual adjustment without breaking object identity.

## QA categories

### Geometry QA

- scale and coordinate consistency;
- grids and storeys aligned;
- invalid or self-intersecting geometry;
- duplicate or near-duplicate entities;
- beam and wall alignment;
- posts or footings outside valid support regions;
- structural elements through doors, windows, stairs or service zones;
- inconsistent plan, section and schedule geometry.

### Data QA

- missing or duplicate IDs;
- broken source links;
- missing units or materials;
- stale calculations;
- unresolved revisions;
- inconsistent member marks;
- semantic objects without approved source or engineer creation record.

### Structural QA

- unsupported beams or posts;
- incomplete gravity load paths;
- incomplete lateral and tie-down paths;
- omitted transfer reactions;
- missing footing or soil support;
- failed strength or serviceability checks;
- missing restraints or releases;
- load combinations not generated or not analysed;
- connection demand without a connection strategy.

### Drawing QA

- missing tags and schedule entries;
- member mark differs between plan, section and schedule;
- missing detail or section targets;
- tags outside view or overlapping critical geometry;
- incorrect drawing scale;
- missing revision, status or preliminary warning;
- notes inconsistent with the selected system;
- non-standard detail lacking project-specific dimensions or levels.

## Issue severity

Recommended severity levels:

- Critical — unsafe, invalid load path, failed design or issue blocker;
- Major — material coordination or calculation problem requiring engineer resolution;
- Minor — drafting, metadata or low-risk inconsistency;
- Information — assumption, suggestion or future improvement.

Only an authorised engineer can close a critical engineering issue by accepting the resolution or documented limitation.

## Output status gates

- Working;
- AI Proposed;
- Engineer Reviewed;
- Preliminary;
- Tender or Coordination;
- Construction Issue;
- Superseded;
- Work-as-Executed.

The software must not permit a Construction Issue status while critical QA items, unresolved design assumptions or failed calculations remain.

## Standard details

Maintain a controlled library with:

- detail ID and revision;
- applicable materials and conditions;
- scope limitations;
- design parameters;
- linked calculations or manufacturer data;
- approval status.

Do not paste a generic detail into a project unless its applicability has been checked.