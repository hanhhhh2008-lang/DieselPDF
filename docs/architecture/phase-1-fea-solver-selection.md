# Phase 1 FEA Solver Selection

Status: provisional recommendation for Aaron Han's review
Conclusion: use a tiered solver architecture behind a neutral AnalysisModel; do not couple DieselPDF to one solver

## Recommendation

1. Initial conventional residential frame analysis: pilot PyNite for elastic 3D frames/trusses/springs, load combinations, modal analysis and member P-Delta. It is Python-native and MIT licensed. Production use remains blocked by Diesel-specific benchmark gates.
2. Independent early comparator: use closed-form solutions and approved SpaceGass models as primary references; optionally add Frame3DD as a subprocess comparator for linear frame/modal cases after GPL distribution review.
3. Future slab, wall and shell analysis: run a focused Kratos versus Code_Aster prototype. Kratos is the preferred commercial-friendly shortlist because its core is BSD-4, multi-platform and has an extensive Python interface. Code_Aster is a technically capable GPL alternative with high packaging and validation burden. PyNite plates may support bounded exploratory cases but are not the default slab/wall production recommendation.
4. Future nonlinear and dynamic analysis: shortlist Kratos and OpenSeesPy technically. OpenSeesPy is highly capable, but its current official documentation requires a commercial redistribution licence; do not ship it until terms are obtained. XC is a capable staged-construction research option but is GPL-3 and deployment-heavy.
5. Do not embed Australian Standards checks in any solver. They remain a separate deterministic Diesel design-code layer.

## Evaluation method

Scores are a Phase 1 desktop study, not solver validation. Rating scale: 0 absent/not credible, 1 poor, 2 limited, 3 adequate, 4 strong, 5 excellent. A higher validation-burden score means easier for Diesel to validate. A higher licence score means easier for a closed commercial desktop product.

| Criterion | Weight |
|---|---:|
| Frame elements | 10 |
| Truss elements | 5 |
| Springs/links/support nonlinearity | 6 |
| Plate/shell capability | 9 |
| Modal capability | 6 |
| P-Delta/geometric nonlinearity | 8 |
| Material/solution nonlinearity | 10 |
| Staged construction/activation | 6 |
| Python API quality | 10 |
| Windows + macOS deployment | 10 |
| Diesel validation burden | 12 |
| Commercial licence compatibility | 8 |
| Total | 100 |

Weighted result = sum(weight × rating) / 100, producing a score out of 5.

## Scored decision matrix

| Solver | Frame | Truss | Spring | Plate/shell | Modal | P-Delta | Nonlinear | Staged | Python | Deploy | Validate | Licence | Weighted / 5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PyNite | 5 | 4 | 5 | 3 | 4 | 4 | 2 | 1 | 5 | 5 | 4 | 5 | 3.97 |
| OpenSeesPy | 5 | 5 | 5 | 4 | 5 | 5 | 5 | 4 | 5 | 4 | 2 | 2 | 4.15 |
| XC | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 2 | 1 | 2 | 3.98 |
| Frame3DD | 5 | 5 | 2 | 0 | 5 | 4 | 1 | 0 | 1 | 4 | 4 | 2 | 2.73 |
| CalculiX | 3 | 3 | 4 | 5 | 5 | 4 | 5 | 4 | 1 | 3 | 1 | 2 | 2.88 |
| Code_Aster | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 3 | 2 | 1 | 2 | 3.63 |
| Kratos | 4 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 1 | 5 | 4.21 |

The ranking measures broad portfolio fit. It does not mean Kratos should be the first solver: PyNite scores better on near-term simplicity and validation burden, which matters for the narrow initial residential scope. Capability-rich solvers impose a larger element/material/algorithm validation surface.

## Candidate assessments

### PyNite

Current official material describes elastic 3D structural analysis, frames, trusses, tension/compression-only elements and springs, plates/quads, modal analysis and member P-Delta. Newer releases also describe nonlinear steel-frame pushover, which must be treated as immature for Diesel until benchmarked. PyNite notes that P-Delta is not applied to plates.

Fit:

- best initial API and packaging fit;
- transparent Python objects simplify neutral-adapter development;
- MIT licensing suits commercial distribution;
- bounded feature set reduces, but does not remove, validation burden.

Limits:

- not the strategic engine for general nonlinear shell/dynamic problems;
- plates and foundation/shear-wall helpers need independent verification;
- staged activation is not a demonstrated core capability;
- no software warranty or equivalence to SpaceGass.

Sources: [PyNite capabilities and MIT licence](https://github.com/JWock82/PyNite), [plates](https://pynite.readthedocs.io/en/stable/plate.html), [P-Delta limitations](https://pynite.readthedocs.io/en/stable/PDelta.html), [modal analysis](https://pynite.readthedocs.io/en/latest/modal.html).

### OpenSees / OpenSeesPy

OpenSees supports broad beam-column, truss, zero-length/link, continuum and shell elements plus nonlinear static/dynamic algorithms and eigen analysis. It is especially strong for nonlinear and seismic research. OpenSeesPy provides the required Python surface and current wheels for Windows, Linux and macOS ARM64.

Fit:

- technically strong for future nonlinear and dynamic cases;
- extensive element/material library and academic benchmark base;
- good adapter target because model construction is command based.

Limits:

- selecting correct formulations, algorithms and convergence settings demands expert validation;
- output/sign conventions and failure states require careful normalization;
- current OpenSeesPy documentation says commercial redistribution requires a licence from UC Berkeley;
- breadth increases the risk of exposing unvalidated combinations.

Sources: [OpenSees features](https://opensees.berkeley.edu/OpenSees/manuals/usermanual/3214.htm), [OpenSeesPy platform/licensing notice](https://openseespydoc.readthedocs.io/en/latest/), [element catalogue](https://openseespydoc.readthedocs.io/en/stable/src/element.html), [eigen analysis](https://openseespydoc.readthedocs.io/en/stable/src/eigen.html).

### XC

XC is a civil-structural FEA system built around Python, OpenSees and a large C++/scientific stack. Its repository documents 0D/1D/2D/3D elements, linear/nonlinear static/dynamic analysis, element activation/deactivation for construction phases and code-check utilities.

Fit:

- strongest explicit staged-construction feature in the screened group;
- broad civil-engineering preprocessing and verification examples;
- capable research/reference backend.

Limits:

- GPL-3 licensing;
- large native dependency set and *nix/Docker-first deployment;
- documentation itself acknowledges missing user-manual coverage;
- embedded foreign design-code helpers are not used by Diesel's Australian layer.

Sources: [XC repository capabilities and GPL-3 licence](https://github.com/xcfem/xc), [XC documentation](https://xcfem.github.io/XCmanual/).

### Frame3DD

Frame3DD performs static and dynamic analysis of 2D/3D frames and trusses with elastic and geometric stiffness, modal results and command-line packages for Windows, macOS and Linux.

Fit:

- narrow, inspectable independent comparator for linear frames and modal cases;
- simple text/subprocess integration;
- lower validation surface than general FEA suites.

Limits:

- no plate/shell scope;
- no native Python API;
- limited nonlinear/staged capability;
- GPL-3 distribution implications;
- old release lineage and smaller maintenance footprint.

Source: [Frame3DD project, features and GPL-3 licence](https://sourceforge.net/projects/frame3dd/).

### CalculiX

CalculiX provides linear/nonlinear static, dynamic and thermal FEA using an Abaqus-style input deck and supports continuum plus structural element families.

Fit:

- credible future shell/solid and nonlinear comparison backend;
- file-based subprocess boundary is robust;
- Windows builds exist.

Limits:

- no first-party Python modelling API;
- official description is Unix-oriented and macOS packaging requires investigation;
- beam/shell formulation choices and output parsing add high validation cost;
- GPL-2-or-later licensing must be reviewed for distribution.

Source: [CalculiX official overview and licence](https://www.calculix.de/).

### Code_Aster

Code_Aster is a broad structural/multiphysics solver with linear/nonlinear statics, modal/transient dynamics, beams, shells, solids, contact and staged workflows through command files.

Fit:

- mature advanced capability and extensive documented test cases;
- strong candidate for future slab/shell/nonlinear benchmarking;
- isolated file/subprocess integration is feasible.

Limits:

- very high modelling and validation burden;
- Linux/Salome-Meca-oriented deployment is unsuitable for the first lightweight desktop package;
- Python-like command language is not a simple in-process domain API;
- GPL licensing and component notices require review.

Sources: [Code_Aster capabilities](https://code-aster.org/IMG/UPLOAD/DOC/Presentation/plaquette_aster_en.pdf), [Code_Aster GPL clarification](https://forum.code-aster.org/public/d/21664-license).

### Kratos Multiphysics

Kratos provides beam, shell and solid structural mechanics with linear/nonlinear static/dynamic behaviour, an extensive Python interface, multi-platform support and a BSD-4 core licence.

Fit:

- strongest commercial-friendly advanced shortlist;
- Python API and plugin architecture align with an isolated adapter;
- current repository documents Windows, Linux and macOS support.

Limits:

- large multiphysics framework and solver/application combinations create the highest Diesel validation burden;
- some applications can have different licences and must be screened;
- residential frame ergonomics and result mapping require a prototype;
- capability does not imply Australian building-design validation.

Source: [Kratos repository, capabilities, platforms and licence](https://github.com/KratosMultiphysics/Kratos).

## Tiered architecture

~~~text
Neutral AnalysisModel
        |
        +-- ResidentialFrameAdapter → PyNite pilot
        +-- FrameComparatorAdapter → Frame3DD or approved reference
        +-- AdvancedStructuralAdapter → Kratos prototype
        +-- ResearchNonlinearAdapter → OpenSeesPy, after licence
        +-- FileDeckAdapter → Code_Aster/CalculiX, if justified
~~~

Each adapter must publish a capability manifest. BuildAnalysisModel can request engineering behaviour, but an adapter must reject unsupported formulations; it cannot silently replace a shell with a membrane, nonlinear analysis with linear, or staged analysis with a single load case.

## Validation and verification plan

### Gate A — adapter mechanics

- unit and axis mapping tests;
- releases, offsets, local axes and sign conventions;
- load and combination translation;
- deterministic model/input hashes;
- result completeness and structured failure parsing.

### Gate B — closed-form benchmarks

At minimum:

- simply supported and cantilever beam deflection/reactions;
- continuous beam;
- 2D and 3D truss;
- portal frame sway and moment distribution;
- axial/torsional spring systems;
- member end releases and rigid offsets;
- P-Delta benchmark with known analytical/AISC reference;
- eigenfrequency of simple beam/frame;
- plate patch test and simply supported plate for any 2D adapter;
- rigid-body mode and equilibrium checks.

Use at least two mesh densities/formulations where discretization applies. State tolerances before running tests.

### Gate C — cross-solver comparison

Run identical neutral models through the selected adapter and at least one independent solver/reference. Compare:

- reactions and global equilibrium;
- nodal translations/rotations;
- member end forces and diagrams;
- eigenvalues/mode-shape correlations;
- convergence/failure classification;
- sensitivity to node merge, orientation and units.

Agreement between two solvers is supporting evidence, not proof; both can share a modelling error.

### Gate D — SpaceGass comparison

Aaron selects de-identified completed projects and supplies the approved SpaceGass model/result exports. Freeze:

- geometry, supports, releases and offsets;
- material/section properties;
- load cases/combinations and self-weight;
- solver/version/settings;
- comparison quantities and tolerances.

Investigate differences rather than tune hidden factors. Every discrepancy receives a disposition: Diesel defect, reference-model issue, formulation difference, modelling assumption or acceptable numerical tolerance.

### Gate E — engineering release

- Aaron reviews benchmark evidence and known limitations;
- only explicitly validated element/analysis combinations are enabled;
- every run records solver, adapter and binary versions/hashes;
- production regressions rerun before release;
- results remain preliminary and cannot bypass design-code checks or engineer approval.

## Commercial licence implications

| Solver | Observed licence position | Phase 1 consequence |
|---|---|---|
| PyNite | MIT | favourable; retain notices |
| OpenSeesPy | official docs require licence for commercial redistribution | blocker until written terms |
| XC | GPL-3 | legal/packaging review; isolate does not automatically resolve distribution obligations |
| Frame3DD | GPL-3 | legal/packaging review before bundling |
| CalculiX | GPL-2-or-later | legal/packaging/source-offer review |
| Code_Aster | GPL | legal/packaging/component review |
| Kratos core | BSD-4; applications may differ | favourable core; screen selected applications/transitives |

This is a technical screen, not legal advice.

## Decisions required from Aaron

- approve PyNite as the initial pilot rather than as a pre-approved production solver;
- nominate SpaceGass reference projects and acceptable tolerances;
- identify the required initial element types, releases, springs and analysis cases;
- confirm whether modal or P-Delta is needed in the first residential release;
- define when slab/wall analysis becomes in-scope;
- approve licence budget/investigation for OpenSeesPy and ODA;
- confirm whether GPL solver executables may be distributed, downloaded separately or used only internally;
- nominate engineering reviewers for each benchmark family.
