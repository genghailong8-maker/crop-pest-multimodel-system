import Link from "next/link";

export default function PublicHeader({ service = "checking" }: { service?: "checking" | "online" | "offline" }) {
  return (
    <header className="public-header">
      <Link className="public-brand" href="/" aria-label="田诊协同首页">
        <span aria-hidden="true">田</span>
        <div><strong>田诊协同</strong><small>农作物病虫害辅助识别</small></div>
      </Link>
      <nav aria-label="主导航">
        <Link href="/">开始诊断</Link>
        <Link href="/history">病例历史</Link>
        <Link href="/trends">记录趋势</Link>
      </nav>
      <div className={`public-service ${service}`}><i />{service === "online" ? "服务开放" : service === "offline" ? "服务暂未开放" : "连接中"}</div>
      <nav className="public-mobile-nav" aria-label="手机主导航">
        <Link href="/">开始诊断</Link>
        <Link href="/history">病例历史</Link>
        <Link href="/trends">记录趋势</Link>
      </nav>
    </header>
  );
}
