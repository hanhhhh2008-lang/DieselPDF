# Architectural Recognition Strategy

## Objective

Convert imported geometric and textual entities into an architectural semantic model that is sufficiently reliable for structural layout generation.

Recognition is not a single AI call. Use a layered pipeline that preserves source evidence, deterministic rules and engineer review.

## Recognition priority

1. IFC semantic objects where available and trustworthy.
2. DXF or DWG layers, blocks, dimensions and exact geometry.
3. Vector PDF paths and positioned text.
4. Deterministic geometry grouping and topology.
5. Machine-learning or vision-language classification.
6. Raster recognition for scanned plans.
7. Engineer confirmation and correction.

## Stage 1 — Source extraction

Extract without assigning architectural meaning:

- line and curve geometry;
- stroke and fill styles;
- layers or optional-content groups;
- text, font, size and rotation;
- dimensions and leaders;
- repeated symbols and blocks;
- view extents and scale indicators;
- image regions.

## Stage 2 — Deterministic preprocessing

- remove exact duplicates while preserving provenance;
- snap endpoints within source-appropriate tolerance;
- split at intersections where required;
- detect collinearity and parallel line pairs;
- repair closed polygons;
- identify repeated dimensions and symbols;
- distinguish annotation geometry from likely model geometry;
- propose storey and drawing-region classification.

## Stage 3 — Rule-based semantic proposals

Initial recognisers should propose:

- wall pairs and wall centre-lines;
- single-line walls where drawing conventions support them;
- doors and windows from gaps, arcs, blocks and labels;
- room polygons and room names;
- slab edges, voids and stair openings;
- roof outlines, ridges, valleys and falls;
- grids and levels;
- dimensions and datum references;
- likely loadbearing versus non-loadbearing walls only as an unconfirmed property.

## Stage 4 — AI assistance

AI may assist with:

- classifying ambiguous line groups;
- interpreting symbols and abbreviations;
- associating text labels with geometry;
- resolving raster plan objects;
- suggesting room and element types;
- comparing architectural revisions;
- identifying low-confidence or conflicting regions.

Every AI proposal requires:

```text
proposal_id
model_and_version
input_entity_ids
proposed_object_type
proposed_properties
confidence
reason_or_evidence_summary
created_at
review_status
```

Do not overwrite raw geometry. Accepting a proposal creates or updates a semantic object through an auditable command.

## Stage 5 — Engineer review interface

Display overlays for:

- confirmed objects;
- unconfirmed proposals;
- conflicting classifications;
- missing boundaries;
- low-confidence objects;
- geometry ignored as annotation;
- changes between revisions.

Provide fast correction tools:

- join or split walls;
- change object type;
- add or remove opening;
- redraw centre-line or boundary;
- approve by region or category;
- reject and record correction reason.

## Candidate open resources to evaluate

Research and datasets may include CubiCasa5K, CubiGraph5K, Raster-to-Graph, RoomFormer and newer floorplan graph or VLM projects. Treat them as reference implementations, datasets or optional classifiers rather than production geometry truth. Review code age, dependencies, licences, training data rights and applicability to Australian architectural drawings.

## Recognition metrics

Track more than pixel IoU:

- wall centre-line and endpoint error;
- wall thickness error;
- opening location and width error;
- room polygon correctness;
- room adjacency graph accuracy;
- grid label and coordinate accuracy;
- storey alignment accuracy;
- semantic precision, recall and confidence calibration;
- engineer correction time per sheet;
- downstream structural error caused by recognition.

## Failure policy

Unknown or ambiguous geometry must remain explicitly unresolved. The system must never fabricate missing dimensions or infer a critical support condition without flagging the assumption for engineer approval.