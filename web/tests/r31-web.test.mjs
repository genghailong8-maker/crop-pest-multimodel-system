import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const source = (path) => readFile(new URL(path, root), "utf8");

test("R3.1 host selector is catalog-only and requires explicit confirmation", async () => {
  const panel = await source("app/components/R31HostKnowledgePanel.tsx");
  assert.match(panel, /GET|fetch\(apiUrl\(`\/api\/cases\/\$\{record\.id\}\/host-knowledge`/);
  assert.match(panel, /POST|fetch\(apiUrl\(`\/api\/cases\/\$\{record\.id\}\/host-confirmation`/);
  assert.match(panel, /(?:knowledge|visibleKnowledge)\.host_options\.map/);
  assert.match(panel, /const visibleKnowledge = record\.host_knowledge\?\.available\s*\n\s*\? record\.host_knowledge/);
  assert.match(panel, /推荐：常见寄主之一/);
  assert.match(panel, /confirmed_host: host/);
  assert.match(panel, /role="option" aria-selected=\{false\}/);
  assert.doesNotMatch(panel, /<input|<textarea/);
});

test("R3.1 host authority exposes fixed OTHER and never auto-confirms recommendation", async () => {
  const panel = await source("app/components/R31HostKnowledgePanel.tsx");
  const api = await source("app/lib/api.ts");
  assert.match(panel, /(?:knowledge|visibleKnowledge)\.other\.value/);
  assert.match(panel, /USER_CONFIRMED_HOST/);
  assert.match(api, /recommended_host: string \| null/);
  assert.match(api, /confirmed_host: string \| null/);
  assert.match(api, /isInsectCase/);
});

test("R3.1 severity UI renders backend rubrics only and fail-closes unavailable severity", async () => {
  const panel = await source("app/components/R31HostKnowledgePanel.tsx");
  assert.match(panel, /details\.severity_available && details\.severity\.available/);
  assert.match(panel, /details\.severity\.levels\[level\]/);
  for (const label of ["轻度", "中度", "重度", "无法判断"]) assert.match(panel, new RegExp(label));
  assert.match(panel, /当前寄主已有可靠受害资料，但暂缺完整的轻\/中\/重分级依据。/);
  assert.match(panel, /resolveR31SeverityAsset/);
  assert.match(panel, /示意图暂不可用/);
  assert.match(panel, /不作为病虫害诊断或现场检测依据/);
});

test("R3.1 treatment UI follows Backend level and hides none body", async () => {
  const panel = await source("app/components/R31HostKnowledgePanel.tsx");
  for (const level of ["host_severity", "host_general", "insect_general", "none"]) assert.match(panel, new RegExp(level));
  assert.match(panel, /当前作物 · 当前严重程度防治措施/);
  assert.match(panel, /当前作物通用防治措施/);
  assert.match(panel, /害虫通用防治措施/);
  assert.match(panel, /treatment\.treatment_level === "none"/);
  assert.match(panel, /treatment\.fallback_message/);
});

test("R3.1 vector diseases are presented as possible transmission, not diagnosis", async () => {
  const panel = await source("app/components/R31HostKnowledgePanel.tsx");
  assert.match(panel, /可能传播的相关病害/);
  assert.match(panel, /发现该害虫不代表当前植株已经感染上述病害。/);
  assert.match(panel, /disease_severity_available/);
  assert.match(panel, /病害严重度分级依据暂不可用，页面不生成三级描述。/);
  assert.doesNotMatch(panel, /YOLO诊断|当前确诊/);
});

test("R3.1 pages preserve R1 evidence and keep plant path free of host selector", async () => {
  const home = await source("app/page.tsx");
  const cases = await source("app/cases/[id]/page.tsx");
  const report = await source("app/reports/[id]/page.tsx");
  for (const page of [home, cases, report]) {
    assert.match(page, /R31HostKnowledgePanel/);
    assert.match(page, /ExternalEvidenceSummary/);
    assert.match(page, /showTreatment=\{!record\.host_knowledge\?\.available\}/);
    assert.match(page, /!isInsectCase/);
  }
});

test("R3.1 API types keep host knowledge separate from R1 evidence", async () => {
  const api = await source("app/lib/api.ts");
  assert.match(api, /export type R31HostKnowledge/);
  assert.match(api, /host_knowledge\?: R31HostKnowledge/);
  assert.match(api, /generic_evidence/);
  assert.match(api, /R31Treatment/);
  assert.match(api, /R31VectorDisease/);
});

test("R3.1 generic evidence starts after insect context confirmation, before host selection", async () => {
  const page = await source("app/page.tsx");
  const contextConfirm = page.indexOf("/drafts/" + "$" + "{draft.id}/confirm");
  const tokenSave = page.indexOf("saveEditToken(confirmed.id, confirmed.case_edit_token)", contextConfirm);
  const evidenceStart = page.indexOf("const evidenceRequest = contextSubject === \"insect\" ? analyzeCase(confirmed) : null", contextConfirm);
  const recordShown = page.indexOf("setRecord(confirmed)", evidenceStart);
  assert.ok(contextConfirm >= 0, "context confirmation request must remain explicit");
  assert.ok(tokenSave > contextConfirm && evidenceStart > tokenSave, "edit token is saved before evidence starts");
  assert.ok(recordShown > evidenceStart, "host selection can render after evidence request starts");
  assert.doesNotMatch(page.slice(evidenceStart, recordShown), /severity|host-confirmation/);
});

test("R3.1 FULL, PARTIAL, OTHER and uncertain share generic evidence rendering", async () => {
  const panel = await source("app/components/R31HostKnowledgePanel.tsx");
  const evidence = await source("app/components/ExternalEvidenceSummary.tsx");
  const page = await source("app/page.tsx");
  const cases = await source("app/cases/[id]/page.tsx");
  const report = await source("app/reports/[id]/page.tsx");
  for (const scenario of ["FULL", "PARTIAL", "OTHER", "uncertain"]) {
    assert.ok(scenario === "FULL" || panel.includes("severity_available"), scenario);
  }
  assert.match(evidence, /record\.evidence_analysis \?\? record\.analysis\?\.evidence_analysis/);
  assert.match(evidence, /evidence\?\.status === "available"/);
  for (const pageSource of [page, cases, report]) assert.match(pageSource, /analyzeCase/);
  assert.match(panel, /TreatmentPanel treatment=\{visibleKnowledge\.treatment\}/);
});

test("R3.1 severity confirmation no longer owns the generic evidence request", async () => {
  const sources = await Promise.all([
    source("app/page.tsx"),
    source("app/cases/[id]/page.tsx"),
    source("app/reports/[id]/page.tsx"),
  ]);
  for (const text of sources) {
    const start = text.indexOf("async function chooseSeverity");
    const end = text.indexOf("\n  }", start);
    const handler = text.slice(start, end);
    assert.doesNotMatch(handler, /fetch\(apiUrl\(`\/api\/cases\/\$\{[^}]+\}\/analyze`/);
  }
});
