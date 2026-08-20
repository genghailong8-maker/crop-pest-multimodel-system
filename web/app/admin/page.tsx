"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { apiUrl, CaseRecord, formatTime, readJson } from "../lib/api";

type Instance = {
  instance_id: string;
  instance_label: string;
  status: "online" | "offline";
  mode: "cpu" | "gpu";
  detector_mode?: string;
  multimodal_model?: string | null;
  storage_free_bytes?: number;
  case_count?: number;
  detail?: string;
};

type InstancePayload = {
  active_instance: string;
  instances: Instance[];
  audit: Array<{ previous: string; target: string; switched_at: string }>;
  data_policy: string;
};

const authenticatedFetch = (path: string, init?: RequestInit) =>
  fetch(apiUrl(path), { ...init, credentials: "include" });

function storageLabel(value?: number) {
  return value == null ? "未知" : `${(value / 1024 ** 3).toFixed(1)} GiB 可用`;
}

export default function AdminPage() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [scope, setScope] = useState<"all" | "user" | "test">("all");
  const [items, setItems] = useState<CaseRecord[]>([]);
  const [instances, setInstances] = useState<InstancePayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [instancePayload, records] = await Promise.all([
      readJson<InstancePayload>(await authenticatedFetch("/api/admin/instances")),
      readJson<CaseRecord[]>(await authenticatedFetch(`/api/cases?limit=200&record_scope=${scope}`)),
    ]);
    setInstances(instancePayload);
    setItems(records);
    setError(null);
  }, [scope]);

  useEffect(() => {
    authenticatedFetch("/api/admin/session")
      .then(readJson<{ authenticated: boolean }>)
      .then(async ({ authenticated: active }) => {
        if (active) await refresh();
        setAuthenticated(active);
      })
      .catch(() => setAuthenticated(false));
  }, [refresh]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await readJson(await authenticatedFetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      }));
      setPassword("");
      await refresh();
      setAuthenticated(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }

  async function activate(target: Instance) {
    if (target.status !== "online" || target.instance_id === instances?.active_instance) return;
    if (!window.confirm(`切换到“${target.instance_label}”？切换后病例历史将只显示该服务器上的病例。列表变化不代表数据丢失，切回原服务器仍可查看原病例。`)) return;
    setBusy(true);
    setError(null);
    try {
      await readJson(await authenticatedFetch("/api/admin/instances/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instance_id: target.instance_id }),
      }));
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "切换失败");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await authenticatedFetch("/api/admin/logout", { method: "POST" });
    setAuthenticated(false);
    setInstances(null);
    setItems([]);
  }

  if (authenticated === null) return <main className="admin-shell"><p>正在检查管理端会话…</p></main>;
  if (!authenticated) return <main className="admin-shell admin-login"><form onSubmit={login}><span>受保护的管理端</span><h1>管理员登录</h1><p>登录后可以查看实例状态并手动切换识别服务器。</p><label>管理员密码<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error && <div className="public-alert error">{error}</div>}<button disabled={busy}>{busy ? "正在登录…" : "登录"}</button><Link href="/">返回首页</Link></form></main>;

  return <main className="admin-shell">
    <header className="admin-header"><div><span>双服务器独立运行</span><h1>识别实例管理</h1><p>切换只影响新病例；病例、图片和报告始终保留在创建它们的服务器。</p></div><div className="admin-header-actions"><Link href="/">返回首页</Link><button onClick={logout}>退出登录</button></div></header>
    <nav className="admin-tools" aria-label="管理工具"><Link href="/training">训练监控</Link><Link href="/review">预标注复核</Link></nav>
    {error && <div className="public-alert error">{error}</div>}
    <section className="admin-instances"><div className="admin-section-head"><div><h2>识别服务器</h2><p>{instances?.data_policy}</p><p className="admin-active-status" role="status" aria-live="polite" aria-atomic="true">当前识别服务器：{instances?.instances.find((item) => item.instance_id === instances.active_instance)?.instance_label ?? "正在读取"}</p></div><button onClick={() => refresh()} disabled={busy}>刷新状态</button></div><div className="admin-switch-note" role="note">切换后，首页、病例历史和趋势将显示目标服务器的数据。原服务器病例仍会保留，切回即可查看。</div><div className="admin-instance-grid">{instances?.instances.map((item) => { const active = item.instance_id === instances.active_instance; return <article key={item.instance_id} className={active ? "active" : ""}><div><span className={`instance-status ${item.status}`}>{item.status === "online" ? "在线" : "离线"}</span>{active && <b>当前使用</b>}</div><h3>{item.instance_label}</h3><p>{item.mode === "cpu" ? "CPU 完整部署" : "GPU 完整部署"} · {item.detector_mode ?? "状态未知"}</p><dl><div><dt>病例数</dt><dd>{item.case_count ?? "—"}</dd></div><div><dt>存储</dt><dd>{storageLabel(item.storage_free_bytes)}</dd></div><div><dt>多模态</dt><dd>{item.multimodal_model ?? "未配置"}</dd></div></dl>{item.detail && <small>{item.detail}</small>}<button disabled={busy || active || item.status !== "online"} onClick={() => activate(item)}>{active ? "正在使用" : item.status === "online" ? "切换到此服务器" : "服务器不可用"}</button></article>; })}</div></section>
    <section className="admin-cases"><div className="admin-section-head"><div><h2>当前实例病例</h2><p>这里只显示当前所选服务器的数据，不进行跨服务器合并。</p></div><select aria-label="病例范围" value={scope} onChange={(event) => setScope(event.target.value as typeof scope)}><option value="all">全部记录</option><option value="user">用户记录</option><option value="test">测试记录</option></select></div><div className="admin-case-list">{items.map((item) => <Link href={`/cases/${item.id}`} key={item.id}><span>{formatTime(item.created_at)}</span><strong>{item.analysis?.primary_diagnosis || item.detector_summary?.primary_candidate?.class_name || "暂无结论"}</strong><small>{item.crop} · {item.instance_id} · {item.is_test ? "测试记录" : "用户记录"}</small></Link>)}{!items.length && <p className="public-muted">当前范围没有记录。</p>}</div></section>
    {!!instances?.audit.length && <section className="admin-audit"><h2>最近切换记录</h2>{instances.audit.map((event) => <p key={`${event.switched_at}-${event.target}`}>{formatTime(event.switched_at)}：{event.previous} → {event.target}</p>)}</section>}
  </main>;
}
