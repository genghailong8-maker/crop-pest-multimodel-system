import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const root = path.resolve(import.meta.dirname, "..");
const repo = path.resolve(root, "..");

test("R3.1 AI manifest is exactly 13 FULL hosts x 3 TRACEABLE severities", async () => {
  const manifest = JSON.parse(await readFile(path.join(repo, "knowledge/insect-host-r3.1/ai-illustration-manifest.json"), "utf8"));
  assert.equal(manifest.records.length, 39);
  assert.equal(new Set(manifest.records.map((row) => row.asset_id)).size, 39);
  assert.equal(new Set(manifest.records.map((row) => row.target_relative_path)).size, 39);
  assert.equal(new Set(manifest.records.map((row) => `${row.class_id}:${row.host}`)).size, 13);
  assert.deepEqual(new Set(manifest.records.map((row) => row.severity)), new Set(["mild", "moderate", "severe"]));
  assert.ok(manifest.records.every((row) => row.prompt_evidence_status === "TRACEABLE"));
  assert.ok(manifest.records.every((row) => !["OTHER", "uncertain"].includes(row.host) && row.severity !== "uncertain"));
  await Promise.all(manifest.records.map((row) => access(path.join(repo, row.target_relative_path))));
});

test("Web mapping is deterministic and fail-closed", async () => {
  const mapping = await readFile(path.join(root, "app/lib/r31SeverityAssets.ts"), "utf8");
  assert.match(mapping, /severity === "uncertain"/);
  assert.match(mapping, /confirmedHost === "OTHER"/);
  assert.match(mapping, /!severityAvailable/);
  assert.match(mapping, /if \(!hostSlug\) return null/);
  assert.match(mapping, /\/r31\/severity\/class\$\{classId\}-\$\{hostSlug\}-\$\{severity\}\.webp/);
  assert.doesNotMatch(mapping, /generic/i);
});

test("R3.1 panel renders approved assets with disclaimer and image-error fallback", async () => {
  const panel = await readFile(path.join(root, "app/components/R31HostKnowledgePanel.tsx"), "utf8");
  assert.match(panel, /resolveR31SeverityAsset/);
  assert.match(panel, /onError=/);
  assert.match(panel, /AI示意图 · 非真实照片 · 仅供辅助判断/);
  assert.match(panel, /不作为病虫害诊断或现场检测依据/);
  assert.match(panel, /示意图暂不可用/);
});

test("plant disease reference path remains untouched", async () => {
  const selector = await readFile(path.join(root, "app/components/SeveritySelector.tsx"), "utf8");
  assert.match(selector, /reference\.image_asset/);
  assert.doesNotMatch(selector, /r31SeverityAssets/);
});
