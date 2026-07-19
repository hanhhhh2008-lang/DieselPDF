# Phase 1 Decision Log

Status: proposed decisions require Aaron Han's review
States: accepted by governing brief, proposed, deferred, rejected, superseded

## Decisions

| ID | State | Decision | Rationale | Consequence / review trigger |
|---|---|---|---|---|
| D-001 | accepted | Diesel engineering dataset is the single source of truth | required by AGENTS.md and Issue #2 | Canvas/PDF/DXF/IFC/FEA cannot own permanent data |
| D-002 | accepted | project coordinates default to millimetres, X right, Y up, Z up | stable engineering convention independent of display | all adapters declare transforms and units |
| D-003 | accepted | raw geometry and semantic engineering objects remain separate but linked | preserves evidence and avoids premature classification | accepting a proposal creates/updates semantic state only |
| D-004 | accepted | all entities/objects have stable identity, schema, revision, provenance and review status | required for traceability and round trip | numeric Canvas IDs are ephemeral |
| D-005 | accepted | generic FEA and Australian Standards checks are separate deterministic layers | solver convergence is not design compliance | design checks consume neutral results |
| D-006 | accepted | AI output is a proposal and cannot silently become final geometry/design | engineer-in-the-loop safety boundary | explicit acceptance and audit event required |
| D-007 | accepted | generated drawings remain PRELIMINARY — NOT FOR CONSTRUCTION — ENGINEER REVIEW REQUIRED | Issue #2 constraint | no later UI/export path may omit the mark before final gate design |
| D-008 | proposed | use a modular monolith with ports and adapters | lowest-risk migration from the current desktop prototype | revisit only if scale/deployment evidence justifies services |
| D-009 | proposed | retain Tkinter during controlled migration | preserves familiar workflows and avoids unauthorised rewrite | future UI may change without domain changes |
| D-010 | proposed | adopt Pydantic v2 for strict boundary/domain schemas | typed validation, JSON Schema and migration support | pin version; forbid silent coercion of engineering-critical fields |
| D-011 | proposed | adopt SQLite plus R-Tree as .diesel.db primary store | transactional, local, portable and spatially queryable | exact geometry remains outside R-Tree bounds |
| D-012 | proposed | use Shapely for derived planar geometry, not canonical serialization | strong predicates/topology, but no units/curve truth | preserve exact arcs/splines and declare tessellation tolerance |
| D-013 | proposed | use NetworkX only as a derived graph view | excellent algorithms without duplicating database authority | rebuild from revisioned relationship rows |
| D-014 | proposed | use ezdxf for DXF and a separately licensed ODA bridge for DWG | strongest Python DXF fit; DWG requires controlled commercial path | DWG release blocked pending terms |
| D-015 | proposed | use IfcOpenShell behind an optional IFC adapter | capable semantic IFC API with component licence distinctions | screen exact LGPL/GPL components |
| D-016 | proposed | retain PyMuPDF technically, conditional on product licence decision | current functionality and capability are strong | commercial/AGPL decision is a packaging gate |
| D-017 | proposed | adopt a tiered FEA architecture behind neutral AnalysisModel | initial and advanced problems have different solver/validation needs | every adapter publishes capabilities and rejects unsupported cases |
| D-018 | proposed | pilot PyNite for initial residential frames; prototype Kratos for advanced future work | PyNite offers low-friction bounded scope; Kratos offers broad commercial-friendly capability | neither is production-approved until benchmark gates pass |
| D-019 | accepted | use CODEX_HANDOFF.md, Project Bible 00–34, AGENTS.md and Issue #2 as the reconciled governing set; Project Bible chapter 15 supersedes the older roadmap stub | complete handoff was merged from fe55104 before final publication and all sources agree on the Phase 1-only boundary | future work must preserve the same reading order and Aaron approval gate |
| D-020 | proposed | use strangler migration and immutable legacy import | minimizes loss/regression and preserves current projects | never overwrite a .dieselpdf.json during migration |
| D-021 | proposed | run external parsers/solvers in isolated subprocesses where practical | protects UI/database and records reproducible runs | define time/resource limits and artefact manifest |
| D-022 | proposed | store source and solver artefacts by content hash | protects traceability when local paths move | retention/privacy policy required |
| D-023 | deferred | replace Tkinter with web/Qt UI | no domain need and outside Phase 1 | reconsider after dataset migration and measured UX need |
| D-024 | deferred | select one advanced shell/nonlinear solver for production | no prototype or Diesel benchmark evidence yet | Kratos/Code_Aster/OpenSeesPy spike in later authorised phase |
| D-025 | deferred | support direct commercial DWG read/write | licensing, packaging and fidelity not approved | DXF remains primary editable exchange meanwhile |
| D-026 | deferred | choose exact Australian Standards editions/modules | requires Aaron's engineering/licensing input | block design-code implementation until edition register approved |
| D-027 | rejected | rewrite the application before protecting behaviour | high regression risk and explicitly outside Issue #2 | use characterization tests and gradual extraction |
| D-028 | rejected | direct PDF-to-DXF as central architecture | loses provenance and bypasses dataset | import to source entities, then export views |
| D-029 | rejected | store permanent geometry in Canvas pixels | zoom/page/UI changes are not engineering transforms | Canvas becomes a renderer |
| D-030 | rejected | make IFC or a solver-native model the internal database | creates external-format/vendor coupling | neutral domain and AnalysisModel remain authoritative |
| D-031 | rejected | claim solver equivalence to SpaceGass from feature lists or a few matching examples | unsafe and unsupported | only bounded, documented benchmark evidence may support a claim |

## Architecture decision records required after approval

Convert approved proposals into focused ADRs before implementation:

- ADR-001 project coordinate, unit and tolerance policy;
- ADR-002 identity, revision and review-status model;
- ADR-003 SQLite/R-Tree physical schema;
- ADR-004 legacy project migration;
- ADR-005 PDF/DXF/DWG/IFC adapter contracts;
- ADR-006 AnalysisModel and ResultSet;
- ADR-007 solver process/licensing strategy;
- ADR-008 engineering approval and preliminary issue gates;
- ADR-009 dependency packaging and supported platforms.

## Unresolved decisions for Aaron

1. Which branch is the Phase 2 implementation baseline?
2. Is the product intended to remain closed source, and what third-party licence budget is available?
3. Is DWG mandatory for the first commercial release or can DXF be the editable exchange?
4. What Windows/macOS versions and CPU architectures must be supported?
5. Which SpaceGass projects and result types form the acceptance suite?
6. What initial analysis cases are mandatory: linear only, P-Delta, modal?
7. What standards editions and clause-content rights apply?
8. What engineering review states and roles match Aaron's actual office workflow?
9. What coordinate tolerances are acceptable for native CAD, vector PDF and scanned plans?
