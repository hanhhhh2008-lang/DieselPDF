# PDF, CAD and IFC Pipeline

## Principle

External formats are inputs and outputs, not the internal engineering database.

```text
PDF / DXF / DWG / IFC
        ↓ import adapters
Diesel engineering dataset
        ↓ output adapters
PDF / DXF / DWG / IFC
```

Do not use direct PDF-to-DXF conversion as the central architecture. Import source objects into the project model, preserve provenance, then export the selected engineering view.

## PDF adapter

Use PyMuPDF to support:

- page metadata and boxes;
- rendering for display;
- vector path extraction;
- text spans, orientation, fonts and bounding boxes;
- image references;
- annotations;
- page transforms;
- vector PDF output.

### Vector PDF import

For every path or text item:

- preserve page-local geometry;
- assign a stable Diesel entity ID;
- retain source page and extraction object reference where available;
- record stroke, fill, width, dash and clipping information;
- transform into project coordinates only after calibration;
- retain the source geometry so recalibration is reversible.

Curves should retain exact control points where available. Display tessellation must be separate.

### Raster PDF import

For scans:

- preserve the source image unchanged;
- record resolution and page transform;
- rectify rotation or skew through an explicit transform;
- use OCR sparingly for labels and dimensions;
- use AI recognition as a proposal layer;
- require confidence and engineer review.

## DXF adapter

Use ezdxf for:

- modelspace and paperspace;
- lines, polylines, arcs, circles and splines;
- text, MText, leaders and dimensions;
- layers, linetypes and styles;
- blocks and inserts;
- handles and extension data;
- viewports and layouts where supported.

### Stable identity

Export Diesel IDs through XDATA, extension dictionaries or a documented metadata scheme. Re-import should attempt matching in this order:

1. Diesel stable ID;
2. source DXF handle and revision;
3. geometry and attribute fingerprint;
4. spatial and semantic matching with a conflict report.

Never silently duplicate matched objects.

## DWG adapter

Preferred controlled approaches:

- ODA File Converter for DWG-to-DXF and DXF-to-DWG workflows;
- AutoCAD-native plugin or Autodesk automation where licensed and necessary.

Treat LibreDWG or similar libraries as optional experimental adapters only after licence and object-coverage review.

## IFC adapter

Use IfcOpenShell for semantic BIM exchange.

Potential imports:

- storeys and levels;
- grids;
- walls and openings;
- slabs, roofs, beams and columns;
- placements and coordinate systems;
- materials and property sets;
- structural analysis model objects when present.

IFC must not be the internal raw geometry database. Export only objects with sufficient semantic confidence and approved mappings.

## Exchange package

A formal export should be able to include:

- vector PDF drawing set;
- DXF modelspace and sheets;
- optional DWG conversion;
- optional IFC;
- Diesel JSONL or SQLite dataset;
- schedules in CSV;
- calculation and QA summaries;
- source and output revision manifest.

## Round-trip QA

For every adapter test:

- object count and type reconciliation;
- stable ID reconciliation;
- coordinate tolerance check;
- layer and style mapping check;
- text and dimension orientation check;
- block transform check;
- unsupported object report;
- changed, added, removed and conflicting object report;
- source and output hashes.

## Licence review

Before commercial distribution, document licences and obligations for PyMuPDF, ezdxf, ODA, IfcOpenShell and all transitive dependencies. Do not assume an open-source package is automatically compatible with a closed commercial desktop product.