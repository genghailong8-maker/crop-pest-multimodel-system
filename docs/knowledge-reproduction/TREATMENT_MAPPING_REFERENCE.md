# Treatment mapping reference

## Plant diseases

The formal five-disease Treatment dataset is `knowledge/official_10class_20260917/treatment_v4.json`. It stores disease-keyed tiers `mild`, `moderate`, `severe`, and `uncertain`, source IDs, evidence levels, display categories, and a global safety notice. The frozen rules state `uncertain_has_treatment=false`, require local registration and label compliance for products, forbid treating research strains as products, and do not escalate doses solely by severity. Empty unsupported categories must not be fabricated.

## Insects

The R3.1 capability/fallback data preserves the resolver order `host_severity → host_general → insect_general`, with `uncertain` mapped to no Treatment. Availability and source IDs are represented per entity/host. The 38 host records in the R3.1 corpus are historical taxonomy scope; the final official scope is the separate 24-pair official set. The published control evidence file exposes SUPPORTED and UNAVAILABLE status cells for the official scope; do not infer an unavailable cell from another host or insect.

## Reproduction cautions

Use canonical identity plus confirmed host, severity and status. Never index the legacy knowledge directly with a new official class ID. Tavily search results are evidence inputs, not Treatment generation inputs. Check each cited source's own reuse terms before republishing source text.
