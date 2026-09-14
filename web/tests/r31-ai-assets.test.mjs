import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const root = path.resolve(import.meta.dirname, "..");
const repo = path.resolve(root, "..");

test("R3.1 severity image manifest covers 38 pairs x 3 frozen severities", async () => {
  const manifest = JSON.parse(await readFile(path.join(repo, "knowledge/insect-host-r3.1/severity-image-manifest.json"), "utf8"));
  assert.equal(manifest.entries.length, 114);
  assert.equal(manifest.expected_pair_count, 38);
  assert.equal(manifest.expected_asset_count, 114);
  assert.equal(new Set(manifest.entries.map((row) => row.asset_id)).size, 114);
  assert.equal(new Set(manifest.entries.map((row) => row.asset.original_png)).size, 114);
  assert.equal(new Set(manifest.entries.map((row) => `${row.pair_id}:${row.severity}`)).size, 114);
  assert.equal(new Set(manifest.entries.map((row) => row.pair_id)).size, 38);
  assert.deepEqual(new Set(manifest.entries.map((row) => row.severity)), new Set(["mild", "moderate", "severe"]));
  assert.ok(manifest.entries.every((row) => row.display_label === "AI示意图 · 非真实照片"));
  assert.ok(manifest.entries.every((row) => row.knowledge_basis.manifestation_text && row.knowledge_basis.source_ids.length));
  assert.ok(manifest.entries.every((row) => row.prompt_basis && row.severity !== "uncertain"));
  await Promise.all(manifest.entries.map((row) => access(path.join(repo, row.asset.original_png))));
});

test("Web mapping is deterministic and fail-closed", async () => {
  const mapping = await readFile(path.join(root, "app/lib/r31SeverityAssets.ts"), "utf8");
  assert.match(mapping, /confirmedHost === "OTHER"/);
  assert.match(mapping, /!severityAvailable/);
  assert.match(mapping, /severity !== "mild"/);
  assert.match(mapping, /severity !== "moderate"/);
  assert.match(mapping, /severity !== "severe"/);
  assert.match(mapping, /if \(!pairId\) return null/);
  assert.match(mapping, /\/assets\/severity\/r31\/\$\{pairId\}\/\$\{severity\}\.png/);
  for (const pairId of ["14", "15", "35"]) assert.match(mapping, new RegExp(`\\"${pairId}\\"`));
  assert.doesNotMatch(mapping, /uncertain\.png/);
  assert.doesNotMatch(mapping, /generic/i);
});

test("R3.1 mapping projection covers every frozen class-host pair and exact paths", async () => {
  const manifest = JSON.parse(await readFile(path.join(repo, "knowledge/insect-host-r3.1/severity-image-manifest.json"), "utf8"));
  const mapping = await readFile(path.join(root, "app/lib/r31SeverityAssets.ts"), "utf8");
  const mildRows = manifest.entries.filter((row) => row.severity === "mild");
  assert.equal(mildRows.length, 38);
  for (const row of mildRows) {
    assert.match(mapping, new RegExp(`${row.class_id}\\s*:\\s*\\{[^}]*${row.host}\\s*:\\s*\\"${row.pair_id}\\"`));
    for (const severity of ["mild", "moderate", "severe"]) {
      const pathValue = `/assets/severity/r31/${row.pair_id}/${severity}.png`;
      const manifestAsset = manifest.entries.find((entry) => entry.pair_id === row.pair_id && entry.severity === severity);
      assert.equal(manifestAsset.asset.original_png.replace(/^web\/public/, ""), pathValue, pathValue);
      assert.ok(await access(path.join(repo, manifestAsset.asset.original_png)).then(() => true).catch(() => false), pathValue);
    }
  }
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
