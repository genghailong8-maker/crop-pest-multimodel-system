# Pre-manual acceptance candidate — 2026-10-02

This branch is a traceable recovery candidate assembled from the certified `competition-dev` release baseline and the source files whose hashes match the accepted temporary runtime. It is not a Formal deployment or final product acceptance release.

## Status

- `VERSION_STATE = PRE_MANUAL_ACCEPTANCE_CANDIDATE`
- `SYSTEM_ENGINEERING_ACCEPTANCE = PASS`
- `CONTEXT_PRODUCT_QUALITY = REVIEW_REQUIRED`
- `FINAL_BROWSER_SYSTEM_ACCEPTANCE = BLOCKED`
- `READY_FOR_USER_MANUAL_ACCEPTANCE = NO`
- `THIS_IS_FORMAL = NO`

The CLIP Context service contract and engineering integration pass, but its observed product quality still has material limits: subject top-1 28/31, crop top-1 13/15, leaf-part top-1 10/15 (one additional image is visually ambiguous), and exact insect-label top-1 11/16. Three clear rice-leaf cases ranked insect above plant. ChineseCLIP and SigLIP 2 were evaluated separately and neither met promotion criteria. Context suggestions remain user-confirmable/correctable; they must not be treated as confirmed facts without user action. Frozen YOLO identity remains authoritative.

Do not describe this candidate as Formal-accepted, Context-quality PASS, or ready for user acceptance. The decision record and full case matrix are kept in the separately backed-up local audit package; this repository note intentionally contains no private local paths or runtime records.

Dependency audit also reports known advisories; see [`DEPENDENCY_SECURITY_REVIEW_20261002.md`](DEPENDENCY_SECURITY_REVIEW_20261002.md). Dependency pins are preserved to keep this backup faithful to the accepted runtime; this candidate is not represented as security-cleared for production deployment.

## Source basis

- Parent baseline: `ab37e51a88d14bb1b37a068d9cac36c2a33e7e24` (`origin/competition-dev` at candidate creation).
- The candidate overlays the provenance-manifested Phase 4.1 Final RC runtime files, including the accepted Evidence relevance/attribution fix and ISSUE-005 Treatment visibility fix, plus focused regression tests.
- Candidate changes are limited to runtime source paths and this candidate’s version/asset/recovery documentation. The dirty local development checkout was not used as a source and remains untouched.
- Frozen YOLO SHA256: `e233fc1971f88288fabed8d37af32047f6d1cb643213d9de0ee61385666479ba`.
- Recovery source SHA256: `ba386dcd7cc32ebec1ff7ee0649ede247b4048dabacf3091b7d57b2da55fa342`.

## External assets

Large model weights are intentionally not stored in Git. Exact sizes, revisions, hashes, and the locally backed-up asset bundle layout are listed in [`PRE_MANUAL_ACCEPTANCE_EXTERNAL_ASSETS_20261002.json`](assets/PRE_MANUAL_ACCEPTANCE_EXTERNAL_ASSETS_20261002.json), with the full reconstructed CLIP manifests beside it. Follow [`RECOVERY_PRE_MANUAL_ACCEPTANCE_CANDIDATE_20261002.md`](RECOVERY_PRE_MANUAL_ACCEPTANCE_CANDIDATE_20261002.md) to restore and verify them.
