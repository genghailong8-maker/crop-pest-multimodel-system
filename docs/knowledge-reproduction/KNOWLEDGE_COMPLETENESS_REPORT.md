# Knowledge publication completeness

## Frozen inventory and release result

- Frozen baseline: `COMPETITION_FINAL_20261009`; source archive is not modified by this release preparation.
- Plant disease runtime records: 5/5.
- Plant severity illustration entries: 15/15 expected mild/moderate/severe entries.
- Official insect scope: 24/24 host pairs and 72/72 host-pair severity tiers.
- Insect control-evidence cells: 216/216; statuses SUPPORTED=127, UNAVAILABLE=89.
- R3.1 historical source corpus: 8 historical insect documents, 38 legacy capabilities, 114 legacy image manifest entries. This historical count is not the current official 24-pair range.
- Official pair-to-R3.1 illustration matches verified by actual file path/hash: 72/72.
- Candidate severity image files under `web/public/assets/severity/`: 129 (R3.1 path files: 114; see per-file manifest; not all are official runtime mappings).
- Plant source registry rows: 24; insect source registry rows: 175.

## Excluded and limited assets

1. `knowledge/baidu-baike-20260818/` and its 98 images are excluded in full because redistribution permission was not verified. Runtime configuration and Resolver code are unchanged in the public candidate; installations that rely on that directory need the lawful source assets restored outside this public repository. Impact details are in `docs/MISSING_RUNTIME_DEPENDENCIES.md`.
2. Model binaries (E2, Frozen and CLIP) are omitted; identity and SHA references are in `docs/MODEL_IDENTITIES.md`. The repository is not a turnkey inference bundle.
3. P1 has 140 added training images in the original project record; this public copy contains only the 24-image/24-label Mendeley subset previously verified for CC BY 4.0. The remaining 116 images are omitted because the referenced record's redistribution permission was not established.
4. Training reproduction: the frozen source snapshot does not include a clearly attributable, complete training code/config package for the final E2 P1 weight. Related experiments elsewhere in the workspace were not imported because their identity as the producing pipeline is unverified. Training reproduction is therefore PARTIAL/NOT_VERIFIED.
5. Per-source publication licenses and several bibliographic fields are absent from the frozen registries. The manifest preserves known titles, organizations, IDs, URLs, access/reachability fields and source associations; unknown fields are explicitly marked. The resulting redistribution review is PARTIAL, not blanket permission.

## Impact

- Source code and included formal JSON/image assets permit inspection and validation of the published subset.
- Removing the Baidu directory can prevent runtime knowledge lookups that depend on the default configured directory; no fallback implementation was introduced.
- Missing model weights prevent direct E2/Frozen/CLIP inference until independently obtained from authorized sources and hash-verified.
- Missing 116 P1 images limits exact training-data reconstruction.
- Missing training pipeline prevents a complete claim of end-to-end training reproduction.
- The official 24-pair crosswalk and control statuses remain inspectable; R3.1's 38 legacy pairs must not be conflated with it.
