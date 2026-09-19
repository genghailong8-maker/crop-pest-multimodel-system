import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("V2 form removes percent and spread-speed fields", async () => {
  const page = await source("app/page.tsx");
  const form = await source("app/lib/diagnosis-form.ts");
  assert.doesNotMatch(page, /受害比例|扩散速度|affectedRatio|spreadSpeed/);
  assert.doesNotMatch(form, /affected_ratio_percent|spread_speed/);
});

test("V2 selector renders all user-guided options from backend rubric", async () => {
  const page = await source("app/page.tsx");
  const selector = await source("app/components/SeveritySelector.tsx");
  for (const level of ["mild", "moderate", "severe", "uncertain"]) assert.match(selector, new RegExp(level));
  assert.match(selector, /当前样本判断/);
  assert.match(selector, /rubric\.rubric\[level\]/);
  assert.match(selector, /reference\?\.image_asset/);
  assert.match(selector, /AI示意图 · 仅供辅助判断/);
  assert.doesNotMatch(page, /玉米叶枯病|番茄斑枯病|READY_KEEP|NEEDS_RESEARCH/);
});

test("V2 tier markdown is rendered as the exact treatment surface", async () => {
  const evidence = await source("app/components/ExternalEvidenceSummary.tsx");
  assert.match(evidence, /markdown_html/);
  assert.match(evidence, /data-treatment-tier/);
  for (const route of ["app/cases/[id]/page.tsx", "app/reports/[id]/page.tsx"]) {
    assert.match(await source(route), /SeveritySelector/);
    assert.match(await source(route), /severity_level/);
  }
});

test("blocked treatment states use Chinese user messages and no internal state labels", async () => {
  const evidence = await source("app/components/ExternalEvidenceSummary.tsx");
  for (const message of ["知识库暂缺足够可靠", "重新查看参考图和症状说明", "尚未确定"]) assert.match(evidence, new RegExp(message));
  assert.match(evidence, /treatmentResult\?\.status/);
  assert.doesNotMatch(evidence, /READY_KEEP|READY_ADJUST|NEEDS_RESEARCH|alignment_pending|SSOT/);
});
