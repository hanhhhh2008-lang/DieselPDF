# Engineering Data Model

## Principle

Every visible object must correspond to a durable data record. The Canvas is a renderer and interaction surface, not the permanent source of truth.

## Two linked data layers

### Raw geometry entities

Raw entities preserve what was imported or drawn without claiming engineering meaning.

Minimum entity types:

- point;
- line;
- polyline;
- polygon;
- rectangle;
- circle;
- arc;
- ellipse;
- Bezier or spline;
- hatch;
- text;
- dimension;
- leader;
- image;
- block reference.

Required fields:

```text
entity_id
schema_version
entity_type
geometry
coordinate_system_id
storey_id
layer_id
style_id
bounding_box
source_document_id
source_page_id
source_external_id
source_method
revision_id
content_hash
confidence
review_status
created_at
updated_at
```

Preserve exact parametric curve definitions where possible. A tessellated display or analysis representation must not replace the source curve definition.

### Engineering semantic objects

Semantic objects attach meaning to one or more raw entities.

Initial types:

- Project, Document, Page, CoordinateSystem and Transform;
- Storey, Level and Grid;
- Wall, Opening, Room, SlabEdge, Void, FloorArea and RoofArea;
- Beam, Lintel, Column, Post, BracingWall, Slab, Footing and Pile;
- Support, Connection, Load, LoadArea and LoadPath;
- AnalysisModel, AnalysisElement and ResultSet;
- DesignCheck, DrawingView, Schedule and QAFlag.

Required fields:

```text
object_id
schema_version
object_type
name_or_mark
geometry_reference
storey_id
properties
source_entity_ids
relationships
confidence
review_status
calculation_ids
revision_id
```

## Relationships

Use explicit typed relationships rather than hidden assumptions:

- DERIVED_FROM;
- CONNECTED_TO;
- SUPPORTED_BY;
- SUPPORTS;
- LOADS_ONTO;
- CONTAINS;
- BOUNDS;
- ALIGNS_WITH;
- LOCATED_ON_GRID;
- LOCATED_ON_STOREY;
- CLASHES_WITH;
- REPRESENTED_BY;
- CALCULATED_BY;
- SUPERSEDES.

NetworkX may support analysis and graph algorithms, but the durable relationship records should remain in the project database.

## Database direction

Recommended tables:

```text
projects
documents
pages
coordinate_systems
transforms
storeys
levels
grids
layers
styles
entities
entity_vertices
semantic_objects
object_entity_links
relationships
load_cases
load_combinations
analysis_models
analysis_results
design_checks
drawing_views
schedules
revisions
audit_events
qa_flags
```

Use SQLite R-Tree indices for entity and object bounding boxes.

## Revision and identity

Stable IDs survive display changes and format round trips. A geometry modification creates a new revision state but does not create an unrelated identity unless the object is genuinely new.

Store:

- revision author;
- timestamp;
- source revision;
- reason;
- changed fields;
- approval status;
- superseded record link.

## Input and output formats

Support:

- `.diesel.db` as the primary project store;
- `.diesel.jsonl` for readable and streamable exchange;
- GeoParquet for large geometry and machine-learning datasets;
- CSV for schedules and summaries only;
- DXF, vector PDF and IFC through adapters.

## Dataset interface

The UI should provide:

- Raw Geometry;
- Semantic Objects;
- Relationships;
- Grids and Storeys;
- Documents and Revisions;
- QA Flags.

Cross-selection is mandatory:

- select drawing object → highlight dataset record;
- select dataset record → highlight drawing object.

## Import modes

- Import as New Source;
- Import as Reference Layer;
- Merge by Stable ID;
- Import as New Revision;
- Replace Dataset only with explicit destructive confirmation.

## Quality rules

- no duplicate stable IDs;
- valid geometry and units;
- every semantic object traces to source entities or an explicit engineer-created source;
- every structural object belongs to a storey or level context;
- every calculation result identifies its analysis model and input revision;
- unknown values remain unknown rather than being silently inferred.