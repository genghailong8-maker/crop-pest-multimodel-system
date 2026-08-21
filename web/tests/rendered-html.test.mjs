import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render(pathname = "/", extraEnv = {}) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${pathname}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${pathname}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
      ...extraEnv,
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the crop diagnosis workspace", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>田诊协同｜农作物病虫害识别与防治系统<\/title>/);
  assert.match(html, /拍照并告诉我们田里的情况/);
  assert.match(html, /拍照或选择图片/);
  assert.match(html, /第一步/);
  assert.match(html, /第二步/);
  assert.match(html, /诊断记录/);
  assert.match(html, /病例保存在创建它的识别服务器/);
  assert.match(html, /手机主导航/);
  assert.match(html, /系统会先定位可疑病斑或害虫/);
  assert.match(html, /作物 \/ 识别对象/);
  assert.match(html, /种植环境/);
  assert.match(html, /大约有多少叶片或植株受影响/);
  assert.match(html, /扩散速度/);
  assert.match(html, /还需完成：上传图片、作物 \/ 识别对象、种植环境、受害比例、扩散速度/);
  assert.match(html, /当前识别服务器/);
  assert.match(html, /补充说明（可选）/);
  assert.doesNotMatch(html, /现在建议你|这个结果有多可靠/);
  assert.doesNotMatch(html, /建议人工复核/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/i);
});

test("server-renders local history, trends, case and report routes", async () => {
  for (const [pathname, marker] of [
    ["/history", "当前识别服务器上的诊断记录"],
    ["/trends", "当前识别服务器的诊断记录"],
    ["/cases/example-case", "正在读取病例"],
    ["/reports/example-case", "正在生成报告"],
    ["/admin", "正在检查管理端会话"],
  ]) {
    const response = await render(pathname);
    assert.equal(response.status, 200, pathname);
    assert.match(await response.text(), new RegExp(marker));
  }
});

test("server-renders the competition showcase with verified project evidence", async () => {
  const response = await render("/showcase");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /让田间图片形成证据/);
  assert.match(html, /让诊断结论可被复核/);
  assert.match(html, /系统不是只看一张图片直接给答案/);
  assert.match(html, /实验室 CPU/);
  assert.match(html, /原 GPU/);
  assert.match(html, /4,164 张/);
  assert.match(html, /5,920 个目标框/);
  assert.match(html, /0\.5482/);
  assert.match(html, /固定 160 张真实复测/);
  assert.match(html, /diagnosis-workspace\.png/);
  assert.match(html, /手机展示页快捷导航/);
  assert.match(html, /结论可复核，也可拒答/);
  assert.match(html, /进入智能诊断/);
  assert.doesNotMatch(html, /99\.9%|10,000\+|10000\+|用户满意度/);
});

test("case and report surfaces use the curated knowledge labels", async () => {
  const homeSource = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const caseSource = await readFile(new URL("../app/cases/[id]/page.tsx", import.meta.url), "utf8");
  const reportSource = await readFile(new URL("../app/reports/[id]/page.tsx", import.meta.url), "utf8");
  const groundedSource = await readFile(new URL("../app/components/ComprehensiveAnalysis.tsx", import.meta.url), "utf8");
  const knowledgeSource = await readFile(new URL("../app/components/KnowledgeSummary.tsx", import.meta.url), "utf8");
  const legacyStyles = await readFile(new URL("../app/product-legacy.css", import.meta.url), "utf8");
  const headerSource = await readFile(new URL("../app/components/PublicHeader.tsx", import.meta.url), "utf8");
  assert.match(knowledgeSource, /症状、特征和防治建议/);
  assert.match(knowledgeSource, /防治建议/);
  assert.doesNotMatch(caseSource, /查看技术证据|症状、危害与可能原因/);
  assert.match(homeSource, /Link href=\{`\/reports\/\$\{record\.id\}`\}>打开诊断报告/);
  assert.match(homeSource, /Link href=\{`\/cases\/\$\{record\.id\}`\}>查看病例详情/);
  assert.match(legacyStyles, /\.legacy-public-shell/);
  assert.match(legacyStyles, /\.legacy-public-shell \.public-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(360px, \.86fr\) minmax\(520px, 1\.32fr\)/);
  assert.match(homeSource, /alt="待分析图片预览"[^>]*loading="eager"[^>]*decoding="async"/);
  assert.match(caseSource, /alt="病例原图及目标定位结果"/);
  assert.match(reportSource, /alt="病例原图及目标定位结果"/);
  assert.match(homeSource, /植物部位/);
  assert.match(homeSource, /生长阶段/);
  assert.match(homeSource, /综合分析通常需要约 1–2 分钟/);
  assert.match(homeSource, /病例编号/);
  assert.match(homeSource, /稍后从.*病例历史.*查看结果/);
  assert.match(headerSource, /aria-current/);
  assert.match(headerSource, /aria-live="polite"/);
  assert.match(legacyStyles, /\.public-brand/);
  assert.match(headerSource, /service === "checking" \? "正在读取" : "当前实例"/);
  assert.match(legacyStyles, /@media print/);
  assert.match(homeSource, /!conclusive/);
  assert.match(homeSource, /这个结果有多可靠/);
  assert.match(groundedSource, /支持危害/);
  assert.match(groundedSource, /支持可能诱因/);
  assert.match(groundedSource, /图片观察/);
  assert.match(groundedSource, /目标定位/);
  assert.match(groundedSource, /田间信息/);
  assert.doesNotMatch(groundedSource, /yolo: "YOLO"/);
  assert.match(caseSource, /病例属于/);
  assert.match(reportSource, /病例属于/);
  assert.match(caseSource, /当前识别服务器暂时无法读取这份病例/);
  assert.doesNotMatch(caseSource, /setError\(reason\.message\)/);
  assert.match(reportSource, /综合信息展示/);
  assert.match(reportSource, /知识内容来源：百度百科/);
  assert.doesNotMatch(reportSource, /查看技术证据|下一步与防治方向|独立多模态判断/);
  const externalEvidenceSource = await readFile(new URL("../app/components/ExternalEvidenceSummary.tsx", import.meta.url), "utf8");
  assert.match(externalEvidenceSource, /暂未检索到可靠资料/);
  assert.match(externalEvidenceSource, /可能诱因/);
  assert.match(externalEvidenceSource, /local_knowledge_base/);
  assert.match(externalEvidenceSource, /noopener noreferrer/);
});

test("public worker hides local admin routes", async () => {
  for (const pathname of ["/admin", "/review", "/training"]) {
    const response = await render(pathname, { CROP_PUBLIC_MODE: "true" });
    assert.equal(response.status, 404);
  }
});

test("public worker reports a closed recognition service without proxy configuration", async () => {
  const response = await render("/api/cases", { CROP_PUBLIC_MODE: "true" });
  assert.equal(response.status, 503);
  assert.match((await response.json()).detail, /暂时未开放/);
});

test("server-renders the human annotation review route", async () => {
  const response = await render("/review");
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /Pest65/);
  assert.match(html, /review-layout/);
  assert.match(html, /review-queue-panel/);
  assert.match(html, /review-canvas-panel/);
});

test("server-renders the live training monitor route", async () => {
  const response = await render("/training");
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /模型训练实时监控/);
  assert.match(html, /训练与验证误差/);
  assert.match(html, /识别性能/);
  assert.match(html, /GPU 利用率/);
  assert.match(html, /最近训练轮次/);
});
