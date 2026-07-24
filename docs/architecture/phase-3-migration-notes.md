# Phase 3 Migration Notes

## Legacy input

The Phase 3 importer reads `.dieselpdf.json` as immutable evidence. It does not overwrite, normalise or rewrite the source file.

For each legacy page, entry and Canvas object it records:

- deterministic stable UUID;
- source file SHA-256;
- page and entry provenance;
- original object payload;
- legacy layer, detail, group and style data;
- converted project geometry where supported;
- opaque lossless payload where unsupported;
- warning and object-count reconciliation.

## Coordinate conversion

The importer uses the Phase 2 characterised convention:

- Canvas origin `(60, 46)`;
- Canvas Y down;
- project Y up from page bottom;
- `scale_units_per_px` converted to millimetres;
- page height retained per legacy page.

## No-silent-loss rule

Import succeeds only when:

```text
source object count
= supported converted entities
+ unsupported entities preserved as opaque payloads
```

A reconciliation JSON artefact is written under `artifacts/imports/` when importing into a Project Bundle.

## Known limitation

The test suite uses representative synthetic legacy fixtures because no real de-identified client `.dieselpdf.json` file was supplied. Production migration acceptance remains conditional on at least one real project comparison covering visual position, measurement, layers, unsupported objects and source immutability.
