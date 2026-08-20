"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import ProductMark from "./ProductMark";
import { apiUrl, HealthStatus, instanceLabel, readJson } from "../lib/api";

type PublicHeaderProps = {
  service?: "checking" | "online" | "offline";
  health?: HealthStatus | null;
  mode?: "top" | "workspace" | "legacy";
};

export const publicNavItems = [
  { href: "/", label: "田间情报工作区", index: "01" },
  { href: "/history", label: "诊断记录", index: "02" },
  { href: "/trends", label: "记录趋势", index: "03" },
] as const;

function isCurrentPath(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname.startsWith(href);
}

export default function PublicHeader({ service = "checking", health, mode = "top" }: PublicHeaderProps) {
  const pathname = usePathname();
  const [loadedHealth, setLoadedHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    if (health !== undefined) return;
    let active = true;
    fetch(apiUrl("/health"))
      .then(readJson<HealthStatus>)
      .then((payload) => { if (active) setLoadedHealth(payload); })
      .catch(() => { if (active) setLoadedHealth(null); });
    return () => { active = false; };
  }, [health]);

  const activeHealth = health === undefined ? loadedHealth : health;
  const instanceId = activeHealth?.active_instance_id || activeHealth?.instance_id;
  const serverLabel = activeHealth?.active_instance_label
    || activeHealth?.instance_label
    || (instanceId ? instanceLabel(instanceId) : undefined)
    || (activeHealth?.active_instance_mode === "cpu" ? "实验室 CPU" : activeHealth?.active_instance_mode === "gpu" ? "原 GPU" : undefined);
  const displayServerLabel = serverLabel || (service === "checking" ? "正在读取" : "当前实例");
  const serviceText = service === "online" ? "服务开放" : service === "offline" ? "服务暂未开放" : "连接中";
  const legacyNav = (label: string, className = "public-header-nav") => (
    <nav className={className} aria-label={label}>
      {publicNavItems.map((item) => <Link href={item.href} key={item.href} aria-current={isCurrentPath(pathname, item.href) ? "page" : undefined}>{item.label === "田间情报工作区" ? "开始诊断" : item.label}</Link>)}
    </nav>
  );
  const nav = (label: string) => (
    <nav className={label === "手机主导航" ? "v3-mobile-nav" : "v3-nav"} aria-label={label}>
      {publicNavItems.map((item) => <Link href={item.href} key={item.href} aria-current={isCurrentPath(pathname, item.href) ? "page" : undefined}>{item.label === "田间情报工作区" ? "开始诊断" : item.label}</Link>)}
    </nav>
  );

  if (mode === "workspace") {
    return <header className="workspace-v4-topbar">
      <div className="workspace-v4-mobile-brand"><ProductMark /><span><strong>田诊协同</strong><small>农业病虫害智能诊断</small></span></div>
      <div className={`workspace-v4-server workspace-v4-server-${service}`} aria-live="polite" aria-atomic="true"><span className="workspace-v4-server-mark" aria-hidden="true" /><span><small>当前识别服务器</small><strong>{displayServerLabel}</strong></span><em>{serviceText}</em></div>
      <nav className="workspace-v4-mobile-nav" aria-label="手机主导航">{publicNavItems.map((item) => <Link href={item.href} key={item.href} aria-current={isCurrentPath(pathname, item.href) ? "page" : undefined}>{item.label === "田间情报工作区" ? "开始诊断" : item.label}</Link>)}</nav>
    </header>;
  }

  if (mode === "legacy") {
    return <header className="public-header">
      <Link className="public-brand" href="/" aria-label="田诊协同首页">
        <ProductMark />
        <div><strong>田诊协同</strong><small>农作物病虫害辅助识别</small></div>
      </Link>
      {legacyNav("主导航")}
      <div className={`public-service ${service}`} aria-live="polite" aria-atomic="true"><i /><span><small>当前识别服务器</small><strong>{displayServerLabel}</strong></span><em>{serviceText}</em></div>
      {legacyNav("手机主导航", "public-mobile-nav")}
    </header>;
  }

  return (
    <header className="v3-header">
      <div className="v3-header-inner">
        <Link className="v3-brand" href="/" aria-label="田诊协同首页">
          <ProductMark />
          <span><strong>田诊协同</strong><small>农业病虫害智能诊断</small></span>
        </Link>
        {nav("主导航")}
        <div className={`v3-instance v3-instance-${service}`} aria-live="polite" aria-atomic="true">
          <span className="v3-instance-mark" aria-hidden="true" />
          <span><small>当前识别服务器</small><strong>{displayServerLabel}</strong></span>
          <em>{serviceText}</em>
        </div>
      </div>
      {nav("手机主导航")}
    </header>
  );
}
