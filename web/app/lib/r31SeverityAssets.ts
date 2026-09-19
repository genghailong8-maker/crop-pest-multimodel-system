import type { SeverityLevel } from "./api";

// Generated from knowledge/insect-host-r3.1/severity-image-manifest.json.
// The manifest remains the source of truth; this small projection keeps the
// Web bundle from maintaining a second severity-text/source inventory.
const R31_PAIR_IDS: Readonly<Record<number, Readonly<Record<string, string>>>> = {
  8: { 大豆: "01", 马铃薯: "02", 花生: "03", 甜菜: "04", 苜蓿: "05" },
  9: { 玉米: "06", 大豆: "07", 小麦: "08", 棉花: "09", 桃: "10" },
  10: { 葡萄: "11", 棉花: "12", 枣: "13", 核桃: "14" },
  11: { 玉米: "15", 小麦: "16", 花生: "17", 马铃薯: "18", 水稻: "19" },
  12: { 茶: "20", 芒果: "21", 水稻: "22", 苜蓿: "23" },
  13: { 玉米: "24", 水稻: "25", 小麦: "26", 大豆: "27", 苜蓿: "28" },
  14: { 玉米: "29", 大豆: "30", 马铃薯: "31", 花生: "32", 小麦: "33" },
  15: { 大豆: "34", 玉米: "35", 花生: "36", 马铃薯: "37", 苜蓿: "38" },
};

export function resolveR31SeverityAsset(
  classId: number,
  confirmedHost: string | null,
  severity: SeverityLevel,
  severityAvailable: boolean,
): string | null {
  if (
    !severityAvailable ||
    !confirmedHost ||
    confirmedHost === "OTHER" ||
    (severity !== "mild" && severity !== "moderate" && severity !== "severe")
  ) return null;
  const pairId = R31_PAIR_IDS[classId]?.[confirmedHost];
  if (!pairId) return null;
  return `/assets/severity/r31/${pairId}/${severity}.png`;
}
