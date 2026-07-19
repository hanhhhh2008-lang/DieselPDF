# Resource and Dependency Shortlist

## Purpose

This is a shortlist for Phase 1 evaluation. Inclusion does not mean automatic adoption. Codex must verify current activity, documentation, licences, deployment and suitability before recommending production use.

## PDF and document geometry

### PyMuPDF

Potential role:

- PDF rendering;
- page and coordinate metadata;
- vector path and text extraction;
- annotations;
- vector PDF output.

Key review items:

- commercial licensing and AGPL implications;
- fidelity of curves, clipping and transformed content;
- performance and error handling on complex architectural sets.

## CAD

### ezdxf

Potential role:

- DXF read/write;
- modelspace and paperspace;
- layers, blocks, text and dimensions;
- metadata for stable Diesel IDs;
- ODA integration.

### ODA File Converter / ODA SDK

Potential role:

- controlled DWG↔DXF conversion;
- broader DWG version support.

Review licensing, desktop redistribution and automation restrictions.

### Autodesk Platform Services or AutoCAD-native adapter

Potential future role:

- native AutoCAD/Revit automation;
- high-fidelity DWG workflows;
- cloud or licensed desktop execution.

This is optional and should not become the internal data model.

## Geometry and spatial data

### Shapely

Potential role:

- intersections, distances and buffers;
- polygon repair and topology;
- spatial predicates;
- wall and room grouping.

Retain parametric CAD curves separately because Shapely primarily operates on linearised planar geometry.

### SQLite and R-Tree

Potential role:

- local transactional project database;
- spatial bounding-box queries;
- revisions, relationships, calculations and QA issues.

### Pydantic

Potential role:

- domain and exchange schemas;
- validation;
- JSON Schema generation;
- migration boundary validation.

### NetworkX

Potential role:

- room adjacency;
- structural connectivity;
- directed load paths;
- cycle, reachability and unsupported-node checks.

Do not use an in-memory graph as the sole durable store.

### GeoParquet

Potential role:

- large analytical datasets;
- machine-learning training datasets;
- efficient batch processing.

May be deferred from the first migration if SQLite and JSONL are sufficient.

## BIM and collaboration

### IfcOpenShell

Potential role:

- IFC parsing and authoring;
- storeys, grids and building objects;
- geometry conversion;
- IFC validation and optional IDS workflows.

### Speckle

Potential future role:

- object-based AEC collaboration;
- connectors to AutoCAD, Revit, Rhino, Civil 3D and IFC;
- versioned exchange and review.

Do not make Speckle a required first-phase dependency.

### Hypar Elements

Potential reference role:

- lightweight building-element modelling;
- JSON, IFC and DXF-oriented object concepts;
- inspiration for a clear element kernel.

## Architectural recognition resources

### CubiCasa5K

Potential role:

- floorplan dataset and class taxonomy;
- wall, room, door and window benchmark examples.

Review dated dependencies and dataset/licence conditions.

### CubiGraph5K

Potential role:

- room adjacency and graph representation.

### Raster-to-Graph and related graph-based work

Potential role:

- direct prediction of wall nodes, edges and topology;
- representation ideas closer to engineering data than pixel masks.

### RoomFormer

Potential role:

- ordered room polygons and transformer-based floorplan reconstruction research.

### New floorplan VLM research

Potential role:

- semantic and topology proposals for difficult raster drawings.

Treat recent research as experimental. Production geometry must be validated and engineer-reviewable.

## FEA

### PyNite

Initial candidate for transparent Python-native elastic frame analysis and controlled plates, springs, P-Delta and modal features.

### OpenSees / OpenSeesPy

Leading candidate for advanced nonlinear frame, fibre-section and dynamic analysis.

### XC

Alternative structural-engineering-oriented platform with Python interface, broad elements and code-checking infrastructure.

### Frame3DD

Potential independent frame and modal benchmark backend.

### CalculiX

Potential specialist general-purpose solid, shell and contact backend.

### Code_Aster

Potential specialist advanced nonlinear and multiphysics backend; high integration burden.

### Kratos Multiphysics

Potential research and high-performance multiphysics framework; likely excessive for the initial product.

### sectionproperties

Potential role:

- geometric and warping section properties;
- custom sections;
- section-property verification.

### structuralcodes

Potential reference architecture for modular structural-code calculations. Australian code coverage must be built and validated separately.

## Selection rules

For every dependency, record:

- exact version;
- licence and redistribution obligations;
- supported operating systems;
- Python and binary dependencies;
- maintenance activity;
- API stability;
- test evidence;
- known limitations;
- isolation or replacement strategy;
- whether it is core, optional, development-only or benchmark-only.

Prefer replaceable adapters and well-tested narrow dependencies over a single large framework controlling the entire product.