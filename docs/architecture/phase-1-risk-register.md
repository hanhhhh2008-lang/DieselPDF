# Phase 1 Risk Register

Status: open for Aaron Han's review
Scale: likelihood (L) and impact (I) are 1 low to 5 critical; exposure = L × I
Treatment priority: 15–25 critical, 8–14 high, 4–7 medium, 1–3 low

## Register

| ID | Risk | L | I | Exposure | Treatment / evidence required | Owner | Gate |
|---|---|---:|---:|---:|---|---|---|
| R-001 | Canvas pixel coordinates continue to act as permanent geometry | 5 | 5 | 25 | prohibit new domain meaning in Canvas records; introduce project-coordinate entities and projection map | Tech lead | before Phase 2 entity work |
| R-002 | Legacy .dieselpdf.json conversion drops or moves markups | 4 | 5 | 20 | immutable source hash, deterministic importer, side-by-side output, golden fixtures, reconciliation report and rollback | Tech + Aaron | before default migration |
| R-003 | Incorrect page calibration, Y reversal, rotation or units corrupts engineering geometry | 4 | 5 | 20 | explicit affine transforms, residuals, unit types, forward/inverse tests and engineer confirmation | Tech + Aaron | Phase 2 acceptance |
| R-004 | Monolithic DieselPDF.pyw changes cause behaviour regressions | 5 | 4 | 20 | select baseline branch; retain/expand smoke tests; characterization tests before extraction | Tech lead | before refactor |
| R-005 | FEA results are accepted without adequate independent validation | 4 | 5 | 20 | closed-form, cross-solver and SpaceGass benchmark gates; approved capability manifest; version hashes | Aaron | before any production analysis |
| R-006 | Wrong solver element/formulation is silently substituted | 3 | 5 | 15 | typed formulation intent; adapter support validation; hard failure on unsupported mappings | FEA lead | adapter contract |
| R-007 | Australian Standards logic is mixed into solver scripts or foreign code checks | 3 | 5 | 15 | separate deterministic design-code package and neutral ResultSet interface | Aaron + design lead | before Phase 8 |
| R-008 | PyMuPDF AGPL obligations conflict with a closed commercial product | 4 | 5 | 20 | choose AGPL-compatible distribution or obtain Artifex commercial terms; legal review | Product owner | before commercial packaging |
| R-009 | ODA File Converter is used commercially without appropriate membership/redistribution rights | 3 | 5 | 15 | written ODA terms, approved membership tier and packaging design | Product owner | before DWG release |
| R-010 | OpenSeesPy is commercially redistributed without required licence | 3 | 5 | 15 | obtain UC Berkeley terms or exclude from distributed product | Product owner | before adapter distribution |
| R-011 | GPL/LGPL solver or IFC components create unplanned distribution obligations | 3 | 4 | 12 | component-by-component licence/SBOM review; source/notice/relinking plan; legal advice | Product owner | packaging gate |
| R-012 | Vendored dependencies are stale, vulnerable or platform-incompatible | 4 | 4 | 16 | remove committed site-packages from normal build, lock versions/hashes, reproducible Windows/macOS builds and vulnerability scanning | Release lead | before beta |
| R-013 | In-process parsing of untrusted PDF/CAD/IFC files crashes or compromises the app | 3 | 5 | 15 | size/path checks, immutable copies, subprocess isolation, time/resource limits and fuzz corpus | Security owner | before external pilot |
| R-014 | PDF curve, clip, font, block or dimension fidelity is lost during import/export | 4 | 4 | 16 | preserve exact source geometry/attributes; unsupported report; golden round-trip corpus | Adapter lead | before Phase 4 exit |
| R-015 | DXF/DWG/IFC re-import duplicates objects due to absent identity mapping | 4 | 4 | 16 | Diesel IDs in XDATA/metadata, external handles, fingerprints and conflict UI | Adapter lead | before round-trip merge |
| R-016 | R-Tree precision or indexing is mistaken for exact geometry truth | 3 | 3 | 9 | canonical double-precision geometry, outward query tolerance and exact Shapely predicate after candidate search | Data lead | schema review |
| R-017 | Source files are moved/changed after a project records only a local path | 4 | 4 | 16 | content-addressed immutable source copies, hashes, manifest and missing-source QA state | Data lead | importer acceptance |
| R-018 | Open interaction PR and handoff branch diverge, invalidating line-level assumptions or tests | 4 | 3 | 12 | Aaron selects code baseline; rebase architecture branch only after review; rerun audit delta | Aaron + Tech | before Phase 2 branch |
| R-019 | CODEX_HANDOFF.md and Project Bible chapters 09–17 are missing; roadmap is truncated | 4 | 3 | 12 | recover or recreate authoritative context after Phase 1 review; use Issue #2 as current scope source | Aaron | Phase 1 review |
| R-020 | AI proposals are promoted to geometry/design without human approval | 3 | 5 | 15 | proposal records, confidence/provenance, explicit accept command and approval-state tests | Product + Aaron | before AI feature |
| R-021 | Preliminary outputs are mistaken for construction documents | 3 | 5 | 15 | immutable preliminary banner, issue-state watermark tests and role-based final gate | Aaron + QA | every drawing release |
| R-022 | Unknown inputs are silently inferred | 4 | 5 | 20 | nullable/unknown states, blocking QA flags, assumption register and approval requirement | Domain lead | schema and UI |
| R-023 | Solver crash or partial output corrupts the project database | 2 | 5 | 10 | isolated working directory/process, read-only input snapshot, atomic ResultSet transaction | FEA lead | solver runner |
| R-024 | A converged result is numerically or physically wrong due to sign, axis or unit mapping | 4 | 5 | 20 | adapter unit/axis contract, equilibrium invariants, sign tests and benchmark comparisons | FEA lead | each adapter release |
| R-025 | Code editions, clauses or proprietary standards content are stale/misused | 3 | 5 | 15 | Aaron-approved edition register, licensed standards access, clause traceability and change-control | Aaron | before Phase 8 |
| R-026 | Initial product scope expands beyond validated NSW Class 1/10 cases | 4 | 5 | 20 | machine-enforced eligibility screen, explicit exclusions and manual fallback | Aaron + Product | before production |
| R-027 | SQLite corruption, interrupted migration or concurrent writes lose project history | 2 | 5 | 10 | transactions, backups, integrity checks, forward-only migrations, single-writer policy and recovery drills | Data lead | persistence release |
| R-028 | NetworkX derived graph diverges from durable relationship records | 3 | 4 | 12 | graph keyed by relationship_id and source revision; rebuild rather than persist opaque graph state | Domain lead | topology implementation |
| R-029 | Validation tolerances are tuned after seeing results to conceal discrepancies | 2 | 5 | 10 | pre-register metrics/tolerances and require written discrepancy dispositions | Aaron + QA | benchmark approval |
| R-030 | Engineering review becomes a checkbox without evidence | 3 | 5 | 15 | role, timestamp, reviewed revision/hash, scope, comments and supersession semantics in audit event | Aaron + QA | approval workflow |

## Immediate critical treatments

Before Phase 2:

1. Aaron selects the implementation baseline: handoff/main or the interaction PR branch.
2. Recover or explicitly supersede the missing CODEX_HANDOFF and Project Bible chapters.
3. Approve project coordinates, calibration records and tolerance policy.
4. Supply representative legacy projects and expected rendered outputs.
5. Decide PyMuPDF and ODA commercial licensing direction.
6. Approve the initial solver pilot and benchmark/reference data.
7. Freeze initial residential eligibility and exclusions.

## Risk acceptance policy

Only Aaron can accept an engineering-safety risk or approve a capability gate. Technical owners may reduce or close risks by attaching test evidence. Licence risks require qualified legal review; this register is not legal advice.

No critical open risk may be bypassed by a UI warning alone. If required information is unknown, the downstream command must stop or remain preliminary.
