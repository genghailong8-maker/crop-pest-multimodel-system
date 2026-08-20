"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import WorkspaceShell from "../components/WorkspaceShell";
import { apiUrl, CaseRecord, formatTime, readJson, severityLabel, userDiagnosisTitle } from "../lib/api";

export default function HistoryPage() {
  const [items, setItems] = useState<CaseRecord[]>([]);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(apiUrl("/api/cases?limit=200")).then(readJson<CaseRecord[]>)
      .then(setItems).catch((reason) => setError(reason.message));
  }, []);
  const filtered = useMemo(() => items.filter((item) => {
    const text = `${item.crop}${item.part}${item.analysis?.primary_diagnosis ?? ""}${item.detector_summary?.primary_candidate?.class_name ?? ""}`;
    return (!query || text.includes(query)) && (severity === "all" || item.field_severity === severity);
  }), [items, query, severity]);
  return <WorkspaceShell service={error ? "offline" : "online"} visualMode="legacy">
    <main className="legacy-public-shell">
      <section className="public-page-hero"><span>病例历史</span><h1>当前识别服务器上的诊断记录</h1><p>这里展示当前识别服务器保存的病例。切换服务器后列表会变化，原病例仍保留在创建它的服务器，切回即可查看。</p></section>
      <section className="public-page-body">
        <div className="public-filterbar"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索作物或候选病虫害" /><select value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">全部严重度</option><option value="low">较低</option><option value="medium">中等</option><option value="high">较高</option><option value="unknown">无法判断</option></select></div>
        {error ? <div className="public-alert warning">当前识别服务器暂时不可用，病例历史无法读取。</div> : <div className="public-history-list">{filtered.map((item) => <Link href={`/cases/${item.id}`} key={item.id}><div><span>{formatTime(item.created_at)}</span><strong>{userDiagnosisTitle(item)}</strong><small>{item.crop} · {item.part} · {item.growth_stage}</small></div><b>{severityLabel(item.field_severity)}</b></Link>)}{!filtered.length && <p className="public-muted">当前识别服务器没有符合筛选条件的病例。</p>}</div>}
      </section>
      <footer className="public-footer"><p>病例和上传图片长期保存在创建它们的识别服务器，切换服务器不会删除数据。</p></footer>
    </main>
  </WorkspaceShell>;
}
