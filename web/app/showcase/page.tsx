import type { Metadata } from "next";
import Link from "next/link";

import ShowcaseReveal from "./ShowcaseReveal";
import styles from "./showcase.module.css";

export const metadata: Metadata = {
  title: "田诊协同｜农业智能病虫害诊断系统",
  description: "融合田间图片、目标定位、田间信息与知识参考，形成可复核的农作物病虫害诊断证据链。",
};

const diagnosisSteps = [
  ["田间采样", "图片与现场信息进入同一病例"],
  ["目标定位", "定位可疑病斑或害虫目标"],
  ["信息核对", "独立读取图片并核对田间条件"],
  ["证据综合", "逐条绑定观察、定位与田间依据"],
  ["诊断结果", "先回答问题、风险与下一步"],
  ["诊断报告", "保存可追溯的病例结果快照"],
] as const;

const evidenceSources = [
  ["田间图片", "原图中直接可观察的症状、虫体或受害位置"],
  ["目标定位", "检测类别、位置与置信度形成视觉候选"],
  ["田间信息", "作物、部位、阶段、环境与扩散情况"],
  ["知识参考", "16 类版本化知识文档用于解释与防治参考"],
] as const;

const metrics = [
  ["16 类", "病虫害识别目录", "类别清单与知识文档逐类对应"],
  ["4,164 张", "已审计训练图片", "5,920 个目标框提供定位学习依据"],
  ["833 张", "官方冻结评测集", "与训练数据隔离，用于统一比较模型"],
  ["0.5482", "主模型 mAP50-95", "同时衡量类别判断与目标框位置的严格指标"],
] as const;

function BrandMark() {
  return <span className={styles.brandMark} aria-hidden="true"><i /><i /><i /><i /></span>;
}

export default function ShowcasePage() {
  return (
    <div className={styles.page}>
      <ShowcaseReveal />
      <header className={styles.header}>
        <Link href="/showcase" className={styles.brand} aria-label="田诊协同比赛展示首页">
          <BrandMark />
          <span><strong>田诊协同</strong><small>农业智能病虫害诊断系统</small></span>
        </Link>
        <nav aria-label="比赛展示页导航">
          <a href="#workflow">诊断原理</a>
          <a href="#architecture">技术架构</a>
          <a href="#results">项目成果</a>
        </nav>
        <Link href="/" className={styles.headerAction}>进入智能诊断</Link>
      </header>
      <nav className={styles.mobileDock} aria-label="手机展示页快捷导航">
        <a href="#innovations">项目亮点</a>
        <a href="#results">验证结果</a>
        <Link href="/">进入诊断</Link>
      </nav>

      <main>
        <section className={styles.hero}>
          <div className={styles.heroCopy} data-showcase-reveal>
            <p className={styles.heroContext}>农业视觉诊断，不止给出一个名称</p>
            <h1><span>让田间图片形成证据</span><span>让诊断结论可被复核</span></h1>
            <p className={styles.heroLead}>融合目标定位、图片核对、田间信息与知识参考，帮助用户看清可能是什么、风险如何、现在该做什么，以及结论依据什么。</p>
            <div className={styles.heroActions}>
              <Link href="/" className={styles.primaryAction}>进入智能诊断<span aria-hidden="true">→</span></Link>
              <a href="#architecture" className={styles.secondaryAction}>了解系统原理</a>
            </div>
            <dl className={styles.heroFacts}>
              <div><dt>多源证据</dt><dd>图片、定位与田间信息</dd></div>
              <div><dt>可信边界</dt><dd>结论可复核，也可拒答</dd></div>
              <div><dt>算力适配</dt><dd>CPU / GPU 双实例</dd></div>
            </dl>
          </div>

          <div className={styles.heroVisual} data-showcase-reveal aria-label="田间图片形成诊断证据链的视觉示意">
            {/* Direct static delivery avoids the unavailable Vinext image optimizer in the laboratory runtime. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/phase9-social-preview.png" alt="玉米叶片病斑田间图像" width="1536" height="1024" loading="eager" decoding="async" fetchPriority="high" />
            <div className={styles.scanFrame} aria-hidden="true"><span /><span /><span /><span /></div>
            <div className={`${styles.evidenceNode} ${styles.nodeImage}`}><small>输入</small><strong>田间图片</strong></div>
            <div className={`${styles.evidenceNode} ${styles.nodeLocation}`}><small>定位</small><strong>可疑病斑</strong></div>
            <div className={`${styles.evidenceNode} ${styles.nodeConclusion}`}><small>综合</small><strong>形成证据链</strong></div>
            <div className={styles.heroThread} aria-hidden="true" />
          </div>
        </section>

        <section className={styles.valueBand} aria-label="项目价值">
          <p data-showcase-reveal>系统不是只看一张图片直接给答案。</p>
          <strong data-showcase-reveal>每个可靠结论，都应当能沿着证据回到图片、定位结果或真实田间信息。</strong>
        </section>

        <section className={styles.section} id="workflow">
          <div className={styles.sectionHeading} data-showcase-reveal>
            <h2>从田间采样，到可保存的诊断报告</h2>
            <p>六个阶段构成同一条诊断路径。系统只展示真实处理状态，不用假进度制造确定感。</p>
          </div>
          <ol className={styles.workflow} data-showcase-reveal>
            {diagnosisSteps.map(([title, detail], index) => (
              <li key={title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div><strong>{title}</strong><p>{detail}</p></div>
              </li>
            ))}
          </ol>
        </section>

        <section className={`${styles.section} ${styles.innovationSection}`} id="innovations">
          <div className={styles.sectionHeading} data-showcase-reveal>
            <h2>三项能力，让诊断从“像什么”走向“为什么”</h2>
            <p>普通用户先看到结论和行动，技术用户与评委可以继续核查证据来源与处理边界。</p>
          </div>
          <div className={styles.innovationGrid}>
            <article className={styles.multiSource} data-showcase-reveal>
              <div>
                <h3>多源证据诊断</h3>
                <p>图片负责呈现现场，目标定位负责寻找可疑对象，田间信息补充单张照片看不到的条件，知识库提供独立参考。任何一个来源都不会被包装成全部答案。</p>
              </div>
              <div className={styles.sourceMap} aria-label="多源证据汇入综合诊断">
                {evidenceSources.map(([name]) => <span key={name}>{name}</span>)}
                <strong>综合诊断</strong>
              </div>
            </article>
            <article className={styles.evidenceFeature} data-showcase-reveal>
              <h3>证据驱动结果</h3>
              <p>危害和可能诱因逐条关联依据。证据不足时明确返回“无法判断”，不补写看不见的事实。</p>
              <a href="#evidence">查看证据如何组织<span aria-hidden="true">↓</span></a>
            </article>
            <article className={styles.serverFeature} data-showcase-reveal>
              <h3>双服务器适配</h3>
              <p>CPU 与 GPU 实例独立保存病例，可按算力条件手动切换，病例归属始终清楚。</p>
              <a href="#architecture">查看实例架构<span aria-hidden="true">↓</span></a>
            </article>
          </div>
        </section>

        <section className={`${styles.section} ${styles.evidenceSection}`} id="evidence">
          <div className={styles.evidenceIntro} data-showcase-reveal>
            <h2>一条结论，由哪些真实信息支撑？</h2>
            <p>证据语言把“观察到什么”和“为什么形成当前结论”连接起来。知识参考独立展示，不冒充当前病例的现场证据。</p>
          </div>
          <div className={styles.evidenceNetwork} data-showcase-reveal>
            <div className={styles.evidenceSources}>
              {evidenceSources.map(([name, detail], index) => (
                <article key={name} style={{ "--node-order": index } as React.CSSProperties}>
                  <span aria-hidden="true" />
                  <div><strong>{name}</strong><p>{detail}</p></div>
                </article>
              ))}
            </div>
            <div className={styles.networkBridge} aria-hidden="true"><i /><i /><i /><i /></div>
            <article className={styles.conclusionPanel}>
              <span>证据综合</span>
              <h3>当前结论</h3>
              <p>先呈现问题名称和风险，再给出下一步行动。用户可以继续展开综合分析、知识参考和技术详情。</p>
              <dl>
                <div><dt>结论依据</dt><dd>逐条可回查</dd></div>
                <div><dt>证据不足</dt><dd>明确拒答</dd></div>
              </dl>
            </article>
          </div>
        </section>

        <section className={`${styles.section} ${styles.architectureSection}`} id="architecture">
          <div className={styles.sectionHeading} data-showcase-reveal>
            <h2>同一入口，适应两种算力环境</h2>
            <p>实验室 CPU 与原 GPU 是两个独立识别实例。切换改变新病例的处理位置，不会把两端病例混在一起。</p>
          </div>
          <div className={styles.serverArchitecture} data-showcase-reveal>
            <div className={styles.entryNode}><span>用户入口</span><strong>Web 诊断界面</strong><small>图片 + 田间信息</small></div>
            <div className={styles.splitLine} aria-hidden="true" />
            <article>
              <span className={styles.serverStatus}>可独立运行</span>
              <h3>实验室 CPU</h3>
              <p>完整 CPU 部署，适合现有实验室硬件与低依赖运行环境。</p>
              <small>病例、图片与报告保存在本实例</small>
            </article>
            <article>
              <span className={styles.serverStatus}>高算力实例</span>
              <h3>原 GPU</h3>
              <p>提供完整 GPU 推理能力，适合更快的多模态分析。</p>
              <small>病例、图片与报告保存在本实例</small>
            </article>
            <div className={styles.ownershipNote}><strong>病例归属明确</strong><span>已有病例始终返回创建它的识别服务器，新病例进入当前选中的实例。</span></div>
          </div>
          <details className={styles.technicalDetails} data-showcase-reveal>
            <summary>展开查看 30 秒技术架构</summary>
            <div className={styles.technicalFlow}>
              {[
                "Web 诊断界面", "图片与田间信息", "目标定位模型", "多模态证据核对", "知识参考", "综合诊断", "病例与报告",
              ].map((item, index, array) => <div key={item}><span>{item}</span>{index < array.length - 1 ? <i aria-hidden="true">→</i> : null}</div>)}
            </div>
          </details>
        </section>

        <section className={`${styles.section} ${styles.productSection}`}>
          <div className={styles.productCopy} data-showcase-reveal>
            <h2>展示的是实际系统，不是概念原型</h2>
            <p>真实诊断界面已经包含条件采样、缺项提示、服务器归属、长任务预期、诊断路径、证据摘要、病例详情与可打印报告。</p>
            <ul>
              <li><strong>面向普通用户：</strong>先看问题、风险和下一步。</li>
              <li><strong>面向技术评审：</strong>可继续展开证据来源和模型细节。</li>
              <li><strong>面向长期使用：</strong>病例与报告按识别实例独立保存。</li>
            </ul>
            <Link href="/" className={styles.textAction}>打开真实诊断界面<span aria-hidden="true">→</span></Link>
          </div>
          <figure className={styles.productFrame} data-showcase-reveal>
            <div className={styles.browserBar}><i /><i /><i /><span>田诊协同 · 智能诊断</span></div>
            {/* This is a real system capture and is intentionally served without runtime transformation. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/showcase/diagnosis-workspace.png" alt="田诊协同真实诊断输入界面" width="1440" height="1000" loading="lazy" decoding="async" />
            <figcaption>实验室服务器实际运行界面，截图生成于 2026-08-20</figcaption>
          </figure>
        </section>

        <section className={`${styles.section} ${styles.resultsSection}`} id="results">
          <div className={styles.sectionHeading} data-showcase-reveal>
            <h2>用冻结评测和完整链路验证结果</h2>
            <p>所有数字都来自项目内可追溯清单、评测 JSON 或复测记录，不使用虚构用户量和满意度。</p>
          </div>
          <dl className={styles.metricsLedger} data-showcase-reveal>
            {metrics.map(([value, label, note]) => <div key={label}><dt>{value}</dt><dd><strong>{label}</strong><span>{note}</span></dd></div>)}
          </dl>
          <div className={styles.validationStrip} data-showcase-reveal>
            <p><strong>固定 160 张真实复测</strong><span>160/160 成功，Top-1 87.50%，说明固定复测图中多数目标名称判断正确；15/17 次冲突被识别，说明系统能发现图片判断与定位结果不一致。</span></p>
            <p><strong>工程回归</strong><span>后端 41 项测试、前端 8 项页面测试、Production Build 与 ESLint 通过，覆盖核心接口与页面渲染。</span></p>
          </div>
          <p className={styles.metricBoundary}>评测结果用于说明当前固定数据与配置下的系统表现，不代表任意田间场景均能获得相同结果。</p>
        </section>

        <section className={styles.finalCta} data-showcase-reveal>
          <div><h2>把一张田间照片，变成一份有依据的诊断记录</h2><p>进入真实系统，完成图片上传、田间信息填写、证据核对与诊断报告生成。</p></div>
          <Link href="/" className={styles.finalAction}>进入智能诊断<span aria-hidden="true">→</span></Link>
        </section>
      </main>

      <footer className={styles.footer}>
        <div><BrandMark /><span><strong>田诊协同</strong><small>基于多模型协同的农作物病虫害识别与防治系统</small></span></div>
        <p>比赛展示页 · 真实诊断入口位于当前系统首页</p>
      </footer>
    </div>
  );
}
