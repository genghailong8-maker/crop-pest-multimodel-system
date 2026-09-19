/** Cloudflare Worker entry point for the vinext-starter template. */
import { handleImageOptimization, DEFAULT_DEVICE_SIZES, DEFAULT_IMAGE_SIZES } from "vinext/server/image-optimization";
import handler from "vinext/server/app-router-entry";

interface Env {
  ASSETS: Fetcher;
  CROP_API_ORIGIN?: string;
  CROP_ORIGIN_SECRET?: string;
  CROP_PUBLIC_MODE?: string;
  IMAGES: {
    input(stream: ReadableStream): {
      transform(options: Record<string, unknown>): {
        output(options: { format: string; quality: number }): Promise<{ response(): Response }>;
      };
    };
  };
}

interface ExecutionContext {
  waitUntil(promise: Promise<unknown>): void;
  passThroughOnException(): void;
}

// Image security config. SVG sources with .svg extension auto-skip the
// optimization endpoint on the client side (served directly, no proxy).
// To route SVGs through the optimizer (with security headers), set
// dangerouslyAllowSVG: true in next.config.js and uncomment below:
// const imageConfig: ImageConfig = { dangerouslyAllowSVG: true };

const worker = {
  async fetch(request: Request, env?: Env, ctx?: ExecutionContext): Promise<Response> {
    const runtimeEnv = env ?? ({} as Env);
    const runtimeContext = ctx ?? {
      waitUntil() {},
      passThroughOnException() {},
    };
    const url = new URL(request.url);

    if (runtimeEnv.CROP_PUBLIC_MODE === "true" && (url.pathname === "/admin" || url.pathname === "/review" || url.pathname === "/training")) {
      return new Response("Not found", { status: 404 });
    }

    if (url.pathname === "/health" || url.pathname.startsWith("/api/")) {
      if (!runtimeEnv.CROP_API_ORIGIN || !runtimeEnv.CROP_ORIGIN_SECRET) {
        return Response.json(
          { detail: "识别服务暂时未开放，请稍后再试" },
          { status: 503, headers: { "Cache-Control": "no-store" } },
        );
      }
      const target = new URL(`${url.pathname}${url.search}`, runtimeEnv.CROP_API_ORIGIN);
      const headers = new Headers(request.headers);
      headers.set("X-Crop-Origin-Secret", runtimeEnv.CROP_ORIGIN_SECRET);
      const connectingIp = request.headers.get("CF-Connecting-IP");
      if (connectingIp) headers.set("CF-Connecting-IP", connectingIp);
      headers.delete("Host");
      const proxied = await fetch(target, new Request(request, { headers }));
      const responseHeaders = new Headers(proxied.headers);
      responseHeaders.set("Cache-Control", "no-store");
      return new Response(proxied.body, {
        status: proxied.status,
        statusText: proxied.statusText,
        headers: responseHeaders,
      });
    }

    if (url.pathname === "/_vinext/image") {
      const allowedWidths = [...DEFAULT_DEVICE_SIZES, ...DEFAULT_IMAGE_SIZES];
      return handleImageOptimization(request, {
        fetchAsset: (path) => runtimeEnv.ASSETS.fetch(new Request(new URL(path, request.url))),
        transformImage: async (body, { width, format, quality }) => {
          const result = await runtimeEnv.IMAGES.input(body).transform(width > 0 ? { width } : {}).output({ format, quality });
          return result.response();
        },
      }, allowedWidths);
    }

    return handler.fetch(request, runtimeEnv, runtimeContext);
  },
};

export default worker;
