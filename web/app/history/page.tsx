"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import PublicHeader from "../components/PublicHeader";
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
  return <main className="public-shell"><PublicHeader service={error ? "offline" : "online"} />
    <section className="public-page-hero"><span>病例历史</span><h1>当前电脑保存的诊断记录</h1><p>这里展示本机数据库中的病例，可用于回看识别过程；记录不代表真实地区疫情。</p></section>
    <section className="public-page-body">
      <div className="public-filterbar"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索作物或候选病虫害" /><select value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">全部严重度</option><option value="low">较低</option><option value="medium">中等</option><option value="high">较高</option><option value="unknown">无法判断</option></select></div>
      {error ? <div className="public-alert warning">本地后端暂时未开放，病例历史当前不可读取。</div> : <div className="public-history-list">{filtered.map((item) => <Link href={`/cases/${item.id}`} key={item.id}><div><span>{formatTime(item.created_at)}</span><strong>{userDiagnosisTitle(item)}</strong><small>{item.crop} · {item.part} · {item.growth_stage}</small></div><b>{severityLabel(item.field_severity)}</b></Link>)}{!filtered.length && <p className="public-muted">没有符合筛选条件的本地病例。</p>}</div>}
    </section><footer className="public-footer"><p>病例和上传图片长期保存在当前电脑，直到用户主动清理或恢复备份。</p></footer></main>;
}
