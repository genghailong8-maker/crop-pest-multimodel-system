"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import ProductMark from "./ProductMark";
import PublicHeader, { publicNavItems } from "./PublicHeader";
import { apiUrl, readJson, type HealthStatus } from "../lib/api";

type WorkspaceShellProps = {
  children: ReactNode;
  service?: "checking" | "online" | "offline";
  health?: HealthStatus | null;
  visualMode?: "workbench" | "legacy";
};

function isCurrentPath(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname.startsWith(href);
}

export default function WorkspaceShell({ children, service = "checking", health, visualMode = "workbench" }: WorkspaceShellProps) {
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

  return (
    <div className={`workspace-v4-shell ${visualMode === "legacy" ? "workspace-v4-shell-legacy" : ""}`}>
      <aside className="workspace-v4-rail" aria-label="诊断工作区">
        <Link className="workspace-v4-rail-brand" href="/" aria-label="返回田诊协同首页">
          <ProductMark />
          <span><strong>田诊协同</strong><small>田间情报工作区</small></span>
        </Link>

        <nav className="workspace-v4-rail-nav" aria-label="公共诊断导航">
          {publicNavItems.map((item) => (
            <Link href={item.href} key={item.href} aria-current={isCurrentPath(pathname, item.href) ? "page" : undefined}>
              <span className="workspace-v4-nav-index" aria-hidden="true">{item.index}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="workspace-v4-rail-note">
          <span className="workspace-v4-rail-note-line" aria-hidden="true" />
          <p>图片、田间信息与目标定位共同构成一份可回看的诊断记录。</p>
        </div>

        <div className="workspace-v4-rail-footer">
          <span>当前识别归属</span>
          <strong>{activeHealth?.active_instance_label || activeHealth?.instance_label || "按病例固定"}</strong>
        </div>
      </aside>

      <div className={`workspace-v4-main ${visualMode === "legacy" ? "workspace-v4-main-legacy" : ""}`}>
        <PublicHeader mode={visualMode === "legacy" ? "legacy" : "workspace"} service={service} health={activeHealth} />
        {children}
      </div>
    </div>
  );
}
