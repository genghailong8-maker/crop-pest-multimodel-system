import type { SeverityLevel } from "./api";

const APPROVED_HOST_SLUGS: Readonly<Record<number, Readonly<Record<string, string>>>> = {
  8: { 大豆: "soybean" },
  9: { 玉米: "corn", 大豆: "soybean", 小麦: "wheat", 棉花: "cotton", 桃: "peach" },
  10: { 葡萄: "grape" },
  11: { 玉米: "corn", 马铃薯: "potato" },
  12: { 茶: "tea" },
  13: { 大豆: "soybean" },
  14: { 玉米: "corn" },
  15: { 大豆: "soybean" },
};

export function resolveR31SeverityAsset(
  classId: number,
  confirmedHost: string | null,
  severity: SeverityLevel,
  severityAvailable: boolean,
): string | null {
  if (!severityAvailable || !confirmedHost || severity === "uncertain" || confirmedHost === "OTHER") return null;
  const hostSlug = APPROVED_HOST_SLUGS[classId]?.[confirmedHost];
  if (!hostSlug) return null;
  return `/r31/severity/class${classId}-${hostSlug}-${severity}.webp`;
}
