# Knowledge reproduction guide

## 1. Start from the release identity

Use the public branch's `COMPETITION_FINAL_20261009` release description. Do not replace the public files with Phase B, an older 2026-10-02 package, or an unverified candidate. This public release intentionally excludes restricted assets and model binaries, so exact production deployment is not turnkey.

## 2. Verify published files

From the repository root, recompute SHA256 for files listed in `docs/knowledge-reproduction/KNOWLEDGE_ASSET_SHA256.csv` and compare the digest. The rows distinguish frozen-file identity matches from public documentation and other release additions.

## 3. Verify plant taxonomy and assets

Read `knowledge/official_10class_20260917/taxonomy.json`, `knowledge_candidate.json`, `source_registry.json`, `treatment_v4.json`, and `severity_image_manifest.json`. Expect official disease IDs 0–4, five disease records, 15 mild/moderate/severe image entries, and four severity keys in the treatment schema. Confirm `uncertain` has no treatment as specified by the source contract.

## 4. Verify official insect-host scope

Use `knowledge/insect-host-r3.1/control-evidence-status.json` and keep only records with `official_class_id` 5–9. Deduplicate by `official_class_id`, `canonical_key`, and `host`: expect 24 pairs. Three severity tiers per pair produce 72 pair-tier combinations. Each tier has agricultural, physical, and biological control cells; those 216 cells include explicitly `UNAVAILABLE` states. Do not interpret unavailable as a recommendation or fill it by inference.

`knowledge/insect-host-r3.1/manifest.json`, `capability-fallback.json`, and its eight insect markdown records are legacy R3.1 source assets. They contain 38 historical host combinations over legacy IDs. Use the canonical key crosswalk; never equate old numeric IDs directly with official class IDs.

## 5. Verify Severity images

Read the two manifests under the official plant and R3.1 knowledge folders, then verify each referenced file exists and matches its declared digest. For insects, compare official class IDs through the frozen canonical mapping (5→legacy 8, 6→9, 7→10, 8→11, 9→14) and host/severity tuple; do not assume all 114 historical images are official. The images are illustrative aids, not evidence from a real field sample.

## 6. Verify Treatment mappings

Plant mappings are in `knowledge/official_10class_20260917/treatment_v4.json`; its rules require `uncertain` to have no Treatment and require locally registered products and label-compliant use. Insect fallbacks are declared as `host_severity → host_general → insect_general`; unavailable evidence must remain unavailable. Read the matching canonical entity and confirmed host before interpreting a mapping.

## 7. Re-run existing validators

Use the Python version compatible with the frozen project dependencies, then run the validators already included in the respective knowledge folders. For example, run the R3.1 validator from its directory using its documented CLI/help and run the official asset checks referenced by the repository's test documentation. Do not guess flags; inspect each script's `--help` or argument parser first.

## 8. Restore excluded or external material legally

The Baidu encyclopedia directory and its images are not included. Obtain a license or written redistribution permission directly from the rights holder before restoring copies to a public distribution. Model weights must be obtained from their authorized provider and checked against `docs/MODEL_IDENTITIES.md`. Never place private API credentials in the repository; provide them through a deployment secret manager.

## 9. Source traceability limits

`KNOWLEDGE_SOURCE_MANIFEST.csv` exports only fields present in frozen registries. Blank or `NOT_VERIFIED` values are genuine gaps, not values inferred by this guide. Check the linked source's own page and terms before reusing third-party material. Search evidence produced live by Tavily is not a substitute for the frozen local knowledge corpus.
