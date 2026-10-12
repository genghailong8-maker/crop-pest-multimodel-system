# Severity mapping reference

## Runtime values

The system's user-selected values are `mild`, `moderate`, `severe`, and `uncertain`. Detector confidence and CLIP suggestions do not select severity. The plant frozen manifest contains 15 illustration entries: three levels for each official disease. No plant `uncertain` illustration is represented as an evidence image.

For insects, the official catalog is class IDs 5–9 and the official host list is the 24-pair set in `KNOWLEDGE_BASE_README.md`. The R3.1 severity image manifest has 114 entries across its historical scope; the verified official-pair crosswalk locates 72 images. Legacy-only entries are not part of the official 24-pair runtime scope.

The plant severity reference fields live in `knowledge/official_10class_20260917/knowledge_candidate.json`; evidence-backed and historical host severity records live in `knowledge/insect-host-r3.1/severity-evidence.json`. `KNOWLEDGE_ASSET_SHA256.csv` lists all included image assets and file hashes.

## Evidence and safety contract

Severity descriptions are agronomic aids, not an automated diagnosis and not a substitute for field assessment. Illustrations are explicitly not real pathology evidence. For insects, host and severity evidence can be unavailable on a per-cell basis; preserve those statuses. `uncertain` must not yield Treatment.

## Versioned source records

The source assets are copied from the frozen `official_10class_20260917` and `insect-host-r3.1` directories. Mapping tables and statuses are version-specific. Do not use raw numeric class IDs to crosswalk between the official and legacy taxonomies.
