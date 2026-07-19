# Phase 1 Review Checklist

Aaron should not approve Phase 2 until the Phase 1 documents answer the following.

## Current system

- Has Codex inspected the complete `DieselPDF.pyw` file and all launch and dependency files?
- Are reusable functions mapped by name and responsibility?
- Are data-loss, platform and licensing risks identified?
- Is the legacy project format and migration path understood?

## Target architecture

- Is the engineering dataset clearly the source of truth?
- Are domain, UI, persistence and adapters separated?
- Are coordinate transforms, grids, storeys and units formally defined?
- Is incremental migration preferred over an uncontrolled rewrite?

## FEA

- Is the decision matrix evidence-based and weighted?
- Is a neutral AnalysisModel defined?
- Is the initial solver scope narrow and testable?
- Are advanced solvers isolated from the core product?
- Are SpaceGass and closed-form benchmark protocols defined?
- Are sign conventions, axes, releases, self-weight and modal mass addressed?

## Australian engineering

- Are FEA and standards checks separated?
- Are standards scope gates and editions recorded?
- Are critical assumptions and missing inputs prevented from becoming hidden defaults?
- Are calculations traceable to clauses, actions, capacities and revisions?

## Delivery and risk

- Are Windows and macOS deployment strategies credible?
- Are dependency licences and commercial implications documented?
- Are client confidentiality and local-first processing addressed?
- Are Phase 2 epics, acceptance criteria and dependencies clear?
- Are unresolved decisions explicitly assigned to Aaron?

## Approval outcome

Record one outcome:

- Approved for Phase 2;
- Approved subject to listed amendments;
- Phase 1 requires further investigation;
- Architecture rejected and alternative required.
