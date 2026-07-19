# Phase 1 Technology Options Comparison

Status: review draft for Aaron Han
Decision horizon: architecture approval before Phase 2
Scoring: 0 unsuitable, 1 poor, 2 weak, 3 acceptable, 4 strong, 5 preferred

## Recommendation summary

Adopt a Python-first modular stack centred on Pydantic v2 schemas and SQLite with R-Tree, using Shapely for planar geometry, NetworkX as an in-memory graph algorithm tool, ezdxf for DXF and IfcOpenShell for IFC. Continue with PyMuPDF only after resolving AGPL versus commercial licensing. Treat DWG as a licensed external adapter, not a native internal format. Keep all libraries behind interfaces so licence, deployment or fidelity issues can be addressed without changing the engineering dataset.

## Core stack decision matrix

Weights reflect the initial desktop product: domain fit 25%, fidelity 20%, Python integration 15%, Windows/macOS deployment 15%, maturity/documentation 10%, commercial-licence fit 15%.

| Candidate | Role | Domain fit | Fidelity | Python | Deploy | Maturity | Licence | Weighted / 5 | Recommendation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| PyMuPDF | PDF rendering/extraction/output | 5 | 4 | 5 | 5 | 5 | 1 | 4.15 | technically preferred; commercial licence gate |
| pypdf + pdfplumber | fallback PDF metadata/text | 3 | 2 | 5 | 5 | 4 | 5 | 3.85 | useful fallback, not equivalent vector renderer |
| ezdxf | DXF read/write | 5 | 4 | 5 | 5 | 5 | 5 | 4.80 | adopt |
| ODA SDK/File Converter | DWG bridge | 5 | 5 | 3 | 4 | 5 | 2 | 4.05 | licensed adapter only |
| Pydantic v2 | domain/schema validation | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | adopt |
| SQLite + R-Tree | transactional project store/spatial index | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | adopt |
| Shapely | 2D topology and geometric predicates | 5 | 4 | 5 | 5 | 5 | 4 | 4.55 | adopt with explicit precision/tolerance policy |
| NetworkX | graph algorithms/load-path working graph | 5 | 4 | 5 | 5 | 5 | 5 | 4.80 | adopt as derived in-memory view |
| IfcOpenShell | IFC read/write/geometry | 5 | 4 | 5 | 4 | 4 | 3 | 4.30 | adopt behind optional adapter |

The scores are architecture-selection scores, not claims that every format feature is supported. Adapter conformance tests remain mandatory.

## PDF handling

### PyMuPDF

Strengths:

- already working in DieselPDF for rendering, page metadata, vector paths, text spans and vector output;
- high-performance Python API with page transforms, annotations, optional content and drawing primitives;
- wheels are available for target desktop platforms.

Constraints:

- the committed 1.24.14 metadata declares GNU AGPL 3.0;
- current official documentation states that PyMuPDF/MuPDF are offered under AGPL or a commercial Artifex licence;
- the current repository bundles Windows binaries and must not be assumed macOS-compatible;
- path extraction must preserve clipping, curves, text orientation and page coordinate provenance rather than immediately emit DXF commands.

Decision: keep PdfAdapter and PdfRenderer interfaces. Use PyMuPDF for the controlled prototype only after Aaron selects an AGPL-compatible distribution model or obtains commercial terms. Maintain a narrow fallback for metadata/text if licensing is unresolved, but do not assume pypdf/pdfplumber can replace rendering and vector extraction.

Sources: [PyMuPDF licensing](https://pymupdf.readthedocs.io/en/latest/about.html), [PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/index.html).

## DXF and DWG

### ezdxf

ezdxf is the preferred DXF adapter. Its official documentation identifies MIT licensing, OS-independent Python operation, modelspace/paperspace support and DXF read/write coverage through R2018. It also explicitly says it is not a DWG converter or CAD kernel. DieselPDF should use entity handles and XDATA/extension metadata to carry stable Diesel IDs.

Decision: adopt for DXF import/export; add a formal unsupported-entity report and round-trip reconciliation. Do not flatten blocks, dimensions, splines or paper-space constructs unless the export profile explicitly requests it.

Sources: [ezdxf quick information](https://ezdxf.readthedocs.io/en/stable/), [ezdxf limitations](https://ezdxf.readthedocs.io/en/stable/introduction.html).

### ODA

ODA provides the most credible controlled DWG bridge, but its File Converter is not a free commercial redistribution path. ODA states that non-members may use Viewer/File Converter only for non-commercial applications, while SDK membership provides redistribution rights subject to tier and copy limits.

Decision: define a DwgAdapter interface now, but make DWG production support conditional on written ODA terms and packaging design. For early internal evaluation, an installed converter may be invoked as an isolated external process only if its terms permit the use. Never make DWG the Diesel source of truth.

Sources: [ODA File Converter FAQ](https://www.opendesign.com/faq/question/what-are-oda-viewer-and-oda-file-converter), [ODA membership and redistribution](https://www.opendesign.com/oda-membership).

## Schemas and validation

Pydantic v2 is preferred for immutable value objects at boundaries, discriminated geometry unions, JSON Schema generation, strict unit/status enums and migration validation. The project must not place ORM or Tkinter objects inside domain models. Persistence records may be translated to Pydantic models at repository boundaries.

Decision: adopt Pydantic v2, pin versions and prohibit silent coercion for identifiers, units, review states and engineering quantities. Pydantic is MIT licensed.

Source: [Pydantic repository and licence](https://github.com/pydantic/pydantic).

## Persistence and spatial indexing

SQLite is preferred because it is local, transactional, stable, portable and public domain. R-Tree provides efficient 2D/3D bounding-box searches and is included in SQLite's amalgamation, subject to build configuration.

Design constraints:

- UUIDs remain TEXT/BLOB domain identifiers; R-Tree requires a separate signed 64-bit integer row key;
- R-Tree bounds use 32-bit floats and outward rounding, so exact geometry remains in canonical records and exact predicates run in Shapely;
- R-Tree scans cannot be modified mid-query; collect IDs, close the scan, then mutate in a transaction;
- use foreign keys, write-ahead logging where validated, integrity checks, migrations, backups and atomic export;
- large source files may be content-addressed beside the database, with hashes and manifests inside it.

Decision: adopt SQLite with R-Tree. Do not store the relationship graph only in NetworkX or raw geometry only in R-Tree.

Sources: [SQLite characteristics](https://sqlite.org/about.html), [SQLite public-domain status](https://www.sqlite.org/copyright.html), [SQLite R-Tree module](https://www.sqlite.org/rtree.html).

## Geometry

Shapely is preferred for 2D set operations, validity repair, spatial predicates, intersections, buffering and affine operations. It is based on GEOS and has a BSD-3-Clause package licence; GEOS is LGPL-2.1. Shapely does not manage coordinate systems or engineering units.

Decision: adopt for derived planar operations, not as the serialized schema. Preserve parametric arcs/Bezier/splines in domain records and generate Shapely approximations with a declared chord tolerance. Centralize precision grids and source-specific tolerances; never scatter buffer-based fixes through adapters.

Sources: [Shapely project](https://shapely.readthedocs.io/en/1.8.2/project.html), [Shapely geometry manual](https://shapely.readthedocs.io/en/stable/manual.html).

## Relationships and load paths

NetworkX is suitable for traversals, cycle detection, connected components, topological ordering, shortest paths and load-path diagnostics. It is BSD-3-Clause licensed.

Decision: persist typed relationships in SQLite and build versioned NetworkX graphs as disposable derived views. Every graph edge must retain the durable relationship_id and source revision. NetworkX results are proposals/QA results, not the database of record.

Sources: [NetworkX repository](https://github.com/networkx/networkx), [NetworkX licence](https://networkx.org/documentation/networkx-2.5/license.html).

## IFC

IfcOpenShell offers Python/C++ parsing, writing, semantic queries, geometry and utilities for IFC. The project identifies the Python library and most core components as LGPL-3.0-or-later, while some ecosystem components are GPL. Packaging must select components deliberately.

Decision: adopt an optional IfcAdapter using only reviewed LGPL components. Preserve GlobalId, placements, schema version, property-set provenance and source relationships. IFC imports remain external evidence; exports include only approved semantic objects.

Sources: [IfcOpenShell repository and component licences](https://github.com/IfcOpenShell/IfcOpenShell), [IfcOpenShell Python API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/index.html).

## Dependency and packaging policy

Before commercial distribution:

1. create a lockfile for each supported Python/platform combination;
2. build or download wheels through a reproducible process with SHA-256 hashes;
3. generate an SBOM and third-party notices;
4. scan transitive licences, not only top-level packages;
5. isolate parsers and solvers in subprocesses where practical;
6. test Windows x64 and macOS Apple Silicon from clean machines;
7. stop committing complete site-packages trees and upstream test suites;
8. document source-offer and relinking obligations for any copyleft component;
9. obtain legal review for PyMuPDF, ODA, OpenSeesPy and any GPL solver distribution.

This document is a technical licence screen, not legal advice.

## Alternatives deliberately deferred

- PostGIS is unnecessary for the initial single-user desktop project and adds operational burden.
- a graph database duplicates SQLite authority before relationship scale justifies it;
- a general CAD kernel is not required for Phase 2 coordinate/grid work;
- direct DWG libraries with uncertain coverage/licensing are not approved;
- IFC is not the internal schema;
- a UI rewrite is deferred until domain services and characterization tests make it safe.

## Approval decisions required

Aaron must approve:

- PyMuPDF AGPL-compatible product strategy versus commercial licence;
- ODA membership/budget and whether DWG is required in the initial commercial release;
- Windows and macOS minimum versions and supported CPU architectures;
- permission to ship or invoke GPL/LGPL solver components;
- whether the interaction PR becomes the implementation baseline;
- acceptable dependency update and security-support policy.
