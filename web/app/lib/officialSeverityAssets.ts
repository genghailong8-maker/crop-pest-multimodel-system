import type { CaseRecord, SeverityLevel } from "./api";

const IMAGE_KEYS: Record<string, string> = {
  rice_blast: "rice_blast",
  rice_brown_spot: "rice_brown_spot",
  northern_corn_leaf_blight: "northern_corn_leaf_blight",
  rice_tungro: "rice_tungro",
  corn_gray_leaf_spot: "corn_gray_leaf_spot",
};

export function resolveOfficialSeverityAsset(
  record: Pick<CaseRecord, "taxonomy_version" | "canonical_key">,
  level: SeverityLevel,
): string | null {
  if (record.taxonomy_version !== "official_10class_20260917" || !(level in { mild: 1, moderate: 1, severe: 1 })) return null;
  const imageKey = record.canonical_key ? IMAGE_KEYS[record.canonical_key] : undefined;
  return imageKey ? `/assets/severity/official_10class_20260917/${imageKey}/${level}.png` : null;
}
