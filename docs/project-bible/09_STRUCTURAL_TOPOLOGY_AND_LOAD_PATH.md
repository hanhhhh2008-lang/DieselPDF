# Structural Topology and Load Path

## Objective

Generate structurally coherent framing proposals from the approved architectural semantic model. The system must reason about support, continuity, stability, constructability and downstream reactions rather than drawing isolated beams.

## Directed load-path graph

Represent gravity and lateral load transfer explicitly. A typical gravity path is:

```text
roof or floor load area
→ rafter, truss, joist or slab
→ beam or loadbearing wall
→ post, column, lower wall or slab
→ footing, pile or ground-bearing slab
→ soil
```

A lateral path may be:

```text
wind pressure
→ cladding and framing
→ roof or floor diaphragm
→ bracing wall, frame or portal
→ hold-down and footing
→ ground
```

Every node and relationship must link to approved geometry, design inputs and calculations.

## Structural objects

Initial object set:

- load area;
- tributary region;
- rafter, truss and joist direction;
- beam and lintel;
- loadbearing wall;
- post and column;
- slab and thickening;
- bracing wall and diaphragm;
- footing, strip footing and pad footing;
- support, release and connection;
- transfer object;
- temporary stability requirement.

## Candidate generation

Generate multiple feasible schemes rather than one opaque answer. Candidate objectives may include:

- minimum estimated structural cost;
- minimum number of posts;
- minimum beam depth;
- maximum alignment with walls and grids;
- minimum transfers;
- minimum disruption to services or architecture;
- preferred materials and standard details;
- robustness and ease of construction.

The scoring function must expose its weights and reasons.

## Deterministic structural rules

Examples of rules to implement and test:

- beam ends require defined supports or approved cantilevers;
- upper posts and loadbearing walls require a verified support chain;
- members must not terminate inside openings;
- major concentrated reactions require downstream member and footing checks;
- wall, beam and post alignment should respect project tolerances;
- bracing must exist in both principal directions where required;
- tie-down must form a continuous path;
- roof and floor systems require known span directions and restraints;
- framing around stairs and voids must be explicit;
- construction-stage stability cannot be assumed from the completed structure;
- purlins, cladding, sheeting or plasterboard are not structural restraints unless their load path, stiffness and fixings are demonstrated.

## Load takedown

Use geometric tributary areas and explicit load-transfer relationships. Record:

- source load case;
- load area and coefficient;
- one-way or two-way distribution assumption;
- tributary width or polygon;
- transferred reactions;
- downstream receiving object;
- combination and analysis revision.

Avoid duplicating loads when architectural areas overlap or when solver self-weight is enabled.

## Engineer interaction

The engineer must be able to:

- lock an architectural or structural object;
- require or prohibit supports in selected zones;
- set maximum beam depths;
- select preferred materials;
- approve or reject framing options;
- manually add or alter members;
- mark uncertain existing supports;
- request alternate schemes;
- inspect the full load path from any selected load area to ground.

## Structural option QA

Reject or flag:

- floating columns;
- unsupported beam ends;
- incomplete support chains;
- transfer loads omitted from lower structure;
- footings without soil parameters;
- unresolved architectural clashes;
- unsupported non-standard connections;
- discontinuous bracing or tie-down;
- excessive reliance on assumptions;
- members without calculation records;
- results based on a stale architectural or analysis revision.

## Future optimisation

Only after deterministic correctness is established should the system use optimisation, search or AI to improve framing layouts. Feasibility and code compliance remain hard constraints; cost and convenience are secondary objectives.