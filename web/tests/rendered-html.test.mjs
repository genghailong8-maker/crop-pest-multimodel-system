import assert from "node:assert/strict";
import test from "node:test";

async function render(pathname = "/") {
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
  assert.match(html, /从一张田间图片，建立完整诊断证据链/);
  assert.match(html, /智能诊断/);
  assert.match(html, /训练监控/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/i);
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
