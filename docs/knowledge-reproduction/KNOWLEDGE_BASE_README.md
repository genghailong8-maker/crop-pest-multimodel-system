# Knowledge assets in the public release

This directory documents the knowledge assets copied from the `COMPETITION_FINAL_20261009` frozen source into this public-source release. Runtime data files remain under `knowledge/`; this guide does not replace or normalize them. The excluded `knowledge/baidu-baike-20260818/` directory is not redistributed because its text and image rights were not established.

## Plant taxonomy

| ID | Canonical disease | Stable key |
|---:|---|---|
| 0 | 水稻稻瘟病 | `official_10class_20260917::rice_blast` |
| 1 | 水稻褐斑病 | `official_10class_20260917::rice_brown_spot` |
| 2 | 玉米大斑病 | `official_10class_20260917::northern_corn_leaf_blight` |
| 3 | 水稻东格鲁病毒病 | `official_10class_20260917::rice_tungro` |
| 4 | 玉米灰斑病 | `official_10class_20260917::gray_leaf_spot` |

The plant package contains five records, source registry metadata, source-backed treatment data, and 15 mild/moderate/severe illustration mappings (three per disease). `uncertain` has no treatment.

## Official insect-host scope

| Official class ID | Insect | Canonical key | Host | Pair ID |
|---:|---|---|---|---|
| 5 | 芫菁 | `blister_beetle` | 大豆 | 01 |
| 5 | 芫菁 | `blister_beetle` | 甜菜 | 04 |
| 5 | 芫菁 | `blister_beetle` | 花生 | 03 |
| 5 | 芫菁 | `blister_beetle` | 苜蓿 | 05 |
| 5 | 芫菁 | `blister_beetle` | 马铃薯 | 02 |
| 6 | 蚜虫 | `aphid` | 大豆 | 07 |
| 6 | 蚜虫 | `aphid` | 小麦 | 08 |
| 6 | 蚜虫 | `aphid` | 桃 | 10 |
| 6 | 蚜虫 | `aphid` | 棉花 | 09 |
| 6 | 蚜虫 | `aphid` | 玉米 | 06 |
| 7 | 盲蝽科 | `miridae` | 枣 | 13 |
| 7 | 盲蝽科 | `miridae` | 核桃 | 14 |
| 7 | 盲蝽科 | `miridae` | 棉花 | 12 |
| 7 | 盲蝽科 | `miridae` | 葡萄 | 11 |
| 8 | 蝼蛄 | `mole_cricket` | 小麦 | 16 |
| 8 | 蝼蛄 | `mole_cricket` | 水稻 | 19 |
| 8 | 蝼蛄 | `mole_cricket` | 玉米 | 15 |
| 8 | 蝼蛄 | `mole_cricket` | 花生 | 17 |
| 8 | 蝼蛄 | `mole_cricket` | 马铃薯 | 18 |
| 9 | 蛴螬 | `white_grub` | 大豆 | 30 |
| 9 | 蛴螬 | `white_grub` | 小麦 | 33 |
| 9 | 蛴螬 | `white_grub` | 玉米 | 29 |
| 9 | 蛴螬 | `white_grub` | 花生 | 32 |
| 9 | 蛴螬 | `white_grub` | 马铃薯 | 31 |

The frozen control-evidence contract declares 24 official insect-host pairs, 72 pair-by-severity tiers, and 216 cells across the three control categories. The current status totals are SUPPORTED=127, UNAVAILABLE=89, UNKNOWN=0, INVALID=0. Unavailable cells remain unavailable; this release does not fill them by inference.

The R3.1 source corpus separately describes eight historical insect classes and 38 legacy host pairs. It is preserved as a historical evidence/reference asset, not the definition of the official five-insect scope. Crosswalking uses canonical identity, not raw class IDs across taxonomies.

## Data boundaries

- Severity and Treatment JSON files under `knowledge/official_10class_20260917/` are frozen runtime assets.
- `knowledge/insect-host-r3.1/` contains its cited source registry, evidence/capability records, formal delivery artifacts, and validators. The excluded Baidu directory is not part of this release.
- Public-source source metadata records only facts present in the frozen registries; missing DOI, date, authorship, or license is `NOT_VERIFIED`/blank.
- Runtime Tavily results are transient evidence, not local curated knowledge.
- Illustration assets are reference aids, not diagnostic evidence. Their status and paths are listed in `KNOWLEDGE_ASSET_SHA256.csv`.
- Third-party publication licensing is not established globally by this release. Review each linked source's own terms before redistribution or reuse.

## Manifests

- [`SEVERITY_V2_RESEARCH_METADATA_README.md`](SEVERITY_V2_RESEARCH_METADATA_README.md): sanitized project review metadata tables; not runtime rules.

- [`KNOWLEDGE_SOURCE_MANIFEST.csv`](KNOWLEDGE_SOURCE_MANIFEST.csv): available source metadata and where it is referenced.
- [`KNOWLEDGE_ASSET_SHA256.csv`](KNOWLEDGE_ASSET_SHA256.csv): hashes of published knowledge files and severity imagery.
- [`KNOWLEDGE_COMPLETENESS_REPORT.md`](KNOWLEDGE_COMPLETENESS_REPORT.md): included/excluded scope and impact.
- [`KNOWLEDGE_REPRODUCTION_GUIDE.md`](KNOWLEDGE_REPRODUCTION_GUIDE.md): local validation steps.
- [`SEVERITY_MAPPING_REFERENCE.md`](SEVERITY_MAPPING_REFERENCE.md) and [`TREATMENT_MAPPING_REFERENCE.md`](TREATMENT_MAPPING_REFERENCE.md): contract summaries.
