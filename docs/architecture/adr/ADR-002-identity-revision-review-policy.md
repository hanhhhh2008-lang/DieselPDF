# ADR-002 — Stable Identity, Revision, Audit and Review Policy

Status: accepted as the Phase 3 implementation default; Aaron may amend before Phase 4

Date: 24 July 2026

## Decision

1. Every durable project, document, page, raw entity, semantic object and relationship uses a UUID that is independent of Tk Canvas item numbers and external CAD handles.
2. A stable identity survives ordinary edits and format round trips. Split, merge and replacement operations must be explicit lineage events rather than silent ID reuse.
3. Every write occurs inside a `RevisionSession` with project, parent revision, actor, role and reason.
4. A successful revision commits atomically, advances the project's current revision and appends audit events. A failed revision rolls back all records and leaves no partial revision.
5. Review states are:
   - `unreviewed`: imported evidence not yet reviewed;
   - `proposed`: human or AI proposal awaiting review;
   - `reviewed`: technically reviewed but not approved for downstream reliance;
   - `approved`: approved for the authorised downstream workflow;
   - `rejected`: not accepted;
   - `superseded`: previously approved record replaced by an explicit later record or revision.
6. Roles are:
   - `system_importer`: may create unreviewed imported evidence;
   - `proposer`: may create proposals;
   - `reviewer`: may mark proposed or unreviewed records reviewed or rejected;
   - `approver`: may approve, reject or supersede reviewed/approved records;
   - `admin`: controlled recovery and migration authority.
7. Approved records are not silently edited. A change is performed in a new revision, with audit details and stable identity retained where it remains the same engineering object.
8. Rejected and superseded states are terminal for that recorded state. A revised proposal is created through a later revision rather than reopening history.
9. Raw imported geometry and semantic engineering objects remain separate but linked through explicit `object_entity_links`.
10. Relationships are durable typed records, not inferred solely from screen proximity or Canvas grouping.

## Review transition matrix

| Current | Reviewer | Approver | Result |
|---|---|---|---|
| unreviewed | reviewed or rejected | — | imported evidence reviewed |
| proposed | reviewed or rejected | — | proposal reviewed |
| reviewed | — | approved or rejected | engineering approval decision |
| approved | — | superseded | replacement recorded |
| rejected | — | — | terminal |
| superseded | — | — | terminal |

## Consequences

- Canvas redraws do not affect identity.
- Every downstream calculation or drawing can identify the exact dataset revision it used.
- AI output cannot become approved geometry without a role-authorised transition.
- Audit history records who changed what, why and in which revision.
- Phase 4 import reconciliation can match stable IDs while preserving external handles as provenance only.

## Deferred refinement

A future office-user and permission system may map named staff to these roles. Phase 3 stores actor IDs and roles but does not implement authentication or digital signatures.
