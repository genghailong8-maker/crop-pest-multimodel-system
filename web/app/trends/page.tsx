"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import PublicHeader from "../components/PublicHeader";
import { apiUrl, readJson, TrendPayload } from "../lib/api";

function Bars({ values }: { values: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(values));
  return <div className="public-bars">{Object.entries(values).map(([label, value]) => <div key={label}><span>{label}</span><i><b style={{ width: `${value / max * 100}%` }} /></i><strong>{value}</strong></div>)}</div>;
}

export default function TrendsPage() {
  const [days, setDays] = useState<7 | 30>(30);
  const [data, setData] = useState<TrendPayload | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    fetch(apiUrl(`/api/trends?days=${days}`)).then(readJson<TrendPayload>).then((payload) => {
      setData(payload);
      setError(false);
    }).catch(() => setError(true));
  }, [days]);
  return <main className="public-shell"><PublicHeader service={error ? "offline" : "online"} />
    <section className="public-page-hero"><span>记录趋势</span><h1>了解本机保存的诊断记录</h1><p>这些统计只反映当前电脑保存的病例，不代表真实地区疫情，也不能用于推断流行程度。</p><div className="public-range"><button className={days === 7 ? "active" : ""} onClick={() => setDays(7)}>最近 7 天</button><button className={days === 30 ? "active" : ""} onClick={() => setDays(30)}>最近 30 天</button></div></section>
    <section className="public-page-body">{error ? <div className="public-alert warning">本地后端暂时未开放，趋势当前不可读取。</div> : !data ? <p className="public-muted">正在读取统计…</p> : <><div className="public-total"><span>本机病例</span><strong>{data.total}</strong><small>{data.scope}</small></div><div className="public-chart-grid"><article><h2>按作物</h2><Bars values={data.crops} /></article><article><h2>候选病虫害</h2><Bars values={data.candidate_classes} /></article><article><h2>田里受影响的程度</h2><Bars values={{ "较低": data.field_severity.low ?? 0, "中等": data.field_severity.medium ?? 0, "较高": data.field_severity.high ?? 0, "无法判断": data.field_severity.unknown ?? 0 }} /></article><article><h2>系统给出的处理结果</h2><Bars values={data.review_status} /></article></div><section className="public-trace"><h2>查看这些统计来自哪些病例</h2><p>每条记录都可以打开，核对作物、候选结果、受影响程度和系统建议。</p><div>{data.trace_cases.map((item) => <Link href={`/cases/${item.id}`} key={item.id}><strong>{item.candidate}</strong><span>{item.crop} · {item.review_status}</span></Link>)}</div></section></>}</section>
    <footer className="public-footer"><p>每项统计均来自当前电脑中可回看的病例记录。</p></footer></main>;
}
