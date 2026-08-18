import assert from "node:assert/strict";
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
  assert.match(html, /发现了什么，风险多大，下一步怎么做/);
  assert.match(html, /拍照或选图/);
  assert.match(html, /病例历史/);
  assert.match(html, /病例长期保存在当前电脑/);
  assert.match(html, /手机主导航/);
  assert.match(html, /证据不足时会提示“无法可靠判断”，不会把候选当作确诊/);
  assert.doesNotMatch(html, /建议人工复核/);
  assert.doesNotMatch(html, /我同意图片、田间备注和诊断报告在公共历史中展示 30 天/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/i);
});

test("server-renders local history, trends, case and report routes", async () => {
  for (const [pathname, marker] of [
    ["/history", "当前电脑保存的诊断记录"],
    ["/trends", "本机保存的诊断记录"],
    ["/cases/example-case", "正在读取病例"],
    ["/reports/example-case", "正在生成报告"],
    ["/admin", "正在检查管理端会话"],
  ]) {
    const response = await render(pathname);
    assert.equal(response.status, 200, pathname);
    assert.match(await response.text(), new RegExp(marker));
  }
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
