import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("B2-I1 request contract submits only diagnosis context; V2 severity follows exact detection", async () => {
  const page = await source("app/page.tsx");
  const form = await source("app/lib/diagnosis-form.ts");
  for (const field of ["image", "crop", "growth_stage"]) {
    assert.match(form, new RegExp(`append\\(\\"${field}\\"`));
  }
  assert.doesNotMatch(form, /affected_ratio_percent|spread_speed/);
  assert.doesNotMatch(page, /environment_json|setScene|sceneOptions/);
  assert.doesNotMatch(form, /environment_json|severity_score|severity_label|temperature_c|relative_humidity_percent/);
});

test("B2-I1 keeps only growth-stage input enums", async () => {
  const form = await source("app/lib/diagnosis-form.ts");
  for (const value of ["seedling", "vegetative", "flowering", "fruiting_or_seed_setting", "maturity", "uncertain"]) assert.match(form, new RegExp(`\\[\\"${value}\\"`));
  assert.doesNotMatch(form, /validateSeverityPair|SPREAD_SPEED_OPTIONS|affectedRatio|spreadSpeed/);
});

test("D presentation trusts backend Case Context and does not calculate severity", async () => {
  const context = await source("app/components/CaseContextCard.tsx");
  const page = await source("app/page.tsx");
  const detail = await source("app/cases/[id]/page.tsx");
  const report = await source("app/reports/[id]/page.tsx");
  for (const marker of ["record.case_context", "context?.crop", "context?.growth_stage", "context?.severity", "context?.environment", "系统预设参考环境", "田间实测数据", "发病诱因"]) assert.ok(context.includes(marker), marker);
  for (const file of [page, detail, report]) assert.match(file, /CaseContextCard/);
  assert.doesNotMatch(context, /0\.8|0\.2|P\s*[><=]|score\s*[><=]/);
  assert.doesNotMatch(page, /severity ===|severity_score|severity_label/);
});

test("D effective crop and treatment presentation do not recreate backend rules", async () => {
  const context = await source("app/components/CaseContextCard.tsx");
  const evidence = await source("app/components/ExternalEvidenceSummary.tsx");
  const report = await source("app/reports/[id]/page.tsx");
  assert.match(context, /crop\.status === "available"/);
  assert.match(context, /暂无法确定/);
  assert.match(await source("app/lib/api.ts"), /ongoing: "持续扩散"/);
  assert.match(evidence, /record\.treatment/);
  assert.match(evidence, /severity_uncertain|severity_not_selected/);
  assert.match(report, /report-source-url/);
  assert.match(report, /source\.url/);
});
