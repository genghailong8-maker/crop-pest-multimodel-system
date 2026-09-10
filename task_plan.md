# Task Plan: 第三届“农信杯”农作物病虫害识别与防治系统

## Source-Neutral Backend Candidate Build + Validation（2026-08-28）

### Objective / hard constraints

- 基于当前 Windows working tree 构建隔离 Backend-only candidate，并完成 candidate-only validation 与 Work Formal Update Review Bundle。
- 不修改 production code；不替换正式 Backend；不修改 Web/Gateway/Detector/VLM/SQLite；禁止 commit/push。

### Gates

- [ ] 1. 核对 source identity、Dockerfile、正式 runtime contract 与 SQLite safety。
- [ ] 2. Build Backend-only candidate，记录 image identity/parity/build log。
- [ ] 3. Candidate-only runtime、health/Tavily/8-case/safety/E2E/storage validation。
- [ ] 4. 观察当前 5 个 browser cases，不新增修复。
- [ ] 5. 生成脱敏 bundle、MANIFEST、secret scan、ZIP self-test。

### Status

- 当前阶段：complete。

## Source-Neutral Selection Minimum Fix（2026-08-28）

### Objective / hard constraints

- 仅移除 Normalizer 最终 5-slot selection 的 authority score 偏置；普通来源与政府/高校/科研来源按有效内容和原始 provider 顺序公平选择。
- 优先仅改 `backend/app/search/normalizer.py::_reliability_key()` 与必要 `backend/tests/test_search.py`；保留 reliability metadata、低质量过滤、每域2条、总数5条。
- 不改 Extractor、Tavily/query/schema/SQLite/Web/Gateway/Detector/VLM；禁止 build/deploy/restart/commit/push。

### Gates

- [x] 1. 固化 authority crowd-out 与 provider-order targeted tests。
- [x] 2. 最小修改 Normalizer selection，保持现有过滤与容量限制。
- [x] 3. 通过 Normalizer、8-case、T-08/T-08B/T-08C/T-08D、backend full、diff-check。
- [ ] 4. 生成脱敏 Work Review Bundle、MANIFEST、secret scan、ZIP self-test。

### Status

- 当前阶段：complete（official 2B staging、Windows/LAB full parity、static readability PASS；未推理；等待 Work 独立审核）。

## 2026-09-04 — R1-R3 Final Git Closure

- [x] Final Git audit performed on safety branch `r1-r3-final-safety-20260904`; approved R1/R2/R3 source, tests, resources, configuration, and planning records identified for the final commit.
- [x] Generated caches, validation staging, artifacts, databases, model weights, secrets, and temporary review outputs excluded from the commit set.
- [ ] Commit and push to `competition-dev` remain the final integration steps.

## E1-2B — InternVL3-2B Model Evaluation（2026-08-30）

### Objective / hard constraints

- 使用 E1-2A 已冻结的官方 `OpenGVLab/InternVL3-2B` LAB artifact、冻结 Prompt/Decoding/Schema/S1H harness 和 clean four-Pilot dataset，按 Pilot 1→4 各执行一次。
- LAB CPU-only/offline/native、无量化；不修改 prompt/decoding/schema/harness/pilots，不改 production/test/backend/Web/SQLite/dependency，不 build/deploy/restart/commit/push。
- 仅当 4-Pilot 4/4 PASS 才进入冻结 16-class Main；仅当 Main PASS 才进入 Stability/CPU performance；任一 hard failure 立即停止后续阶段。

### Gates

- [ ] 1. 2B identity/parity、frozen contract、dataset SHA、runtime preflight PASS。
- [ ] 2. Pilot 1→4 simple-contract functional gates PASS，或保留首次失败的完整 raw evidence 并停止。
- [ ] 3. 仅 4/4 Pilot PASS 时执行 Main；记录 16 类 schema/responsibility/grounding/latency。
- [ ] 4. 仅 Main PASS 时执行 Stability/performance；记录 success/latency/p50/p95/RAM/CPU/timeout/crash/consistency。
- [ ] 5. 生成完整脱敏 E1-2 Review Bundle、MANIFEST、secret scan、ZIP self-test 后停止。

### Status

- 当前阶段：complete（4-Pilot hard stop；Pilot 1–3 PASS，Pilot 4 functional FAIL；Main/Stability 未进入；Review Bundle 已生成）。

### E1-2B result（2026-08-30）

- [x] 1. 2B identity/parity、frozen contract、dataset SHA、runtime preflight PASS。
- [x] 2. Pilot 1→4 completed once each after preflight；Pilot 1–3 PASS，Pilot 4 JSON/schema PASS 但 canonical/diagnosis leakage 各 1，按 hard-stop 停止。
- [x] 3. Main 未进入：4/4 Pilot functional gate 未通过。
- [x] 4. Stability/performance 未进入：Main 未运行。
- [x] 5. 已保存 raw/parsed/scanner/runtime/latency/stop evidence，生成脱敏 Review Bundle；无生产变更。

## D0 — Legacy Environment Optional Contract Bridge 完成（2026-08-29）

- 仅修改 `backend/app/main.py` 的 upload `environment_json` optional parsing，并在 `backend/tests/test_case_context.py` 增加真实 API regression；省略时使用既有 JSON 持久化 `{}`，不改 SQLite schema，不生成 fake scene。
- D0 targeted=24/24，完整 backend=306/306；Knowledge/Curated/Severity/B integration/Phase9/C Context/8-case/T-08/T-08B/T-08C/T-08D/Five-pair/Grub-Early-blight/Low-confidence/Storage 全部 PASS，Research/Management pollution=0/0。
- 真实 omitted-environment POST=201；system_default preset exact、旧 `温室` scene compatibility、malformed/non-object/incomplete rejection、Severity moderate/28 与 Case Context 一致均 PASS；SQLite integrity=`ok`、case_count=66、schema unchanged、frozen knowledge/assets/manifest unchanged。
- D0 Review Bundle=`competition-d0-legacy-environment-optional-review-20260829.zip`，待最终 MANIFEST/secret scan/ZIP self-test 后交 Work；不进入 D Web implementation，不 build/deploy/restart/commit/push。

## C-R1 — Case Context Severity Consistency + Analyze Round-Trip Closure（2026-08-29）

- Work 两个 P1 已定位：`build_case_context()` 在无 analysis 时错误返回静态 `not_provided`；既有 C persistence test 未调用真实 `/analyze`。
- 最小修复：`case_context.py::build_case_context()` 复用 `severity_for_record(record).as_dict()`；新增可选已计算 severity 参数，`main.py::present_case()` 先计算同一 B result 后同时用于 top-level 与 context。
- 已扩展 C tests：no-input/mild/moderate/severe/upload consistency；真实 upload→persist→GET→`POST /analyze` growth round-trip；historical missing-growth read/analyze compatibility。
- 当前状态：C-R1 targeted=29/29 PASS，待完整门禁、secret scan 和新 Review Bundle。
- C-R1 完成：production 仅调整 `backend/app/case_context.py`，复用 B `severity_for_record()` 统一 top-level/context severity；真实 upload→persist→GET→`POST /analyze` growth round-trip 与 historical missing-growth analyze 均通过。
- Final gates：C-R1 targeted=29/29、knowledge=6/6、curated=9/9、severity=66/66、B integration=6/6、Phase9=5/5、8-case=8/8、T-08=31/31、T-08B=34/34、T-08C=11/11、T-08D=14/14、five-pair=4/4、Grub/Early-blight=36/36、low-confidence=3/3、storage=8/8、backend=300/300；pollution=0/0；diff-check/secret/frozen/SQLite PASS。
- Bundle=`competition-c-case-context-r1-review-20260829.zip`，size=34638，SHA256=`1c0865164dce6ebddaab8226af57b84b580854820b91136404b5c0d10d44c085`，MANIFEST=42/42，ZIP self-test=43/43。

## C-R2 — Real Upload Severity Consistency Evidence（2026-08-29）

- Work 唯一剩余 P1 是真实 upload evidence 缺失；本轮只新增 `backend/tests/test_case_context.py::test_real_upload_response_keeps_severity_consistent_with_case_context`，未修改 production。
- 真实 `POST /api/cases` 使用 `affected_ratio_percent=20`、`spread_speed=ongoing`，HTTP 201；top-level 与 `case_context.severity` direct equality PASS，均为 available/moderate/中度/score 28。
- C-R1/C Context targeted=30/30、Case Context=19/19、全部历史/安全/storage gates PASS；backend=301/301，pollution=0/0，frozen/SQLite/diff-check/secret PASS。
- Bundle=`competition-c-case-context-r2-review-20260829.zip`，size=28633，SHA256=`4400ae2c056c9077f95ae2f03c0c90f7ded1b99d9b8b86a7eae32e6632e22b6a`，MANIFEST=43/43，ZIP self-test=44/44。

## D — Diagnosis Input Wiring + Result / Detail / Print Context Display preflight blocked（2026-08-29）

- 已读取 D 全部规格并确认 branch=`competition-dev`、HEAD=`0075f63325ec2a5f8515586039458ebdbd135a9c`；当前 Web 既有 `scene` 选择器和 `environment_json` 提交逻辑属于 D-start dirty baseline，本轮未修改。
- 只读确认 Backend `upload_case()` 仍要求 `environment_json`，并强制 `environment["scene"]` 为有效 legacy scene 后才接受 upload；新 D UI 又明确要求移除环境选择、不得伪造环境值、不得修改 Backend。
- 因此当前真实 API 没有“无用户环境选择且不伪造 scene”的合规请求契约；继续实现会导致 422 或违反 D 约束。按 stop condition 停止，不修改 Web/backend/tests，不运行 build/deploy，不生成 Review Bundle。
- 精确 blocker 证据：`artifacts/d-context-display-20260829/preflight-blocker.md`。

## C — Case Context + Fixed Environment + Growth Stage Implementation preflight（2026-08-29）

### Findings / blocker

- 当前用户消息在 `Case Context` 示意图后结束，未包含固定环境 preset 的具体值、字段命名/API contract、允许修改文件、测试门禁、Bundle 文件名及最终报告格式。
- 现有 backend 已有 `growth_stage TEXT NOT NULL`、`environment_json TEXT NOT NULL` 与 `crop` 持久化，并在 `upload_case()` 返回病例；`growth_stage` 目前按植物枚举校验，昆虫归一为 `不适用`。
- 现有环境是用户提交的 `environment_json.scene`，经 `ENVIRONMENT_OPTIONS` 校验后保存为 `{"scene": scene}`；代码中未发现独立的系统 fixed-environment preset。
- `crop` 当前是用户输入的五项受限值；YOLO primary class 另行保存在 detections/detector_summary，尚无用户 crop 与 YOLO crop 的明确冲突/权威决策 contract。

### Stop / next action

- 在缺少 preset 与 context contract 的情况下不猜测，不修改 production code、schema、SQLite、Web 或测试；等待 C 阶段剩余规格后继续。

## B-R1A final

- Production code changed: NO；仅修改 `backend/tests/test_phase9_public_api.py::test_unknown_spread_forces_unknown_severity`。
- Phase9=5/5、Severity=66/66、B integration=6/6、backend=282/282；所有历史 gates、pollution、freeze proof、diff-check、secret scan 均 PASS。
- Review Bundle=`C:\Users\genghailong\Documents\编程大赛\competition-b-severity-partial-input-fix-review-20260829.zip`；MANIFEST=42/42，ZIP self-test PASS，secret scan PASS；Build/Deploy/Restart/Commit/Push=NO。

## C — authoritative implementation plan（2026-08-29）

- C-SPEC 已完整读取：fixed environment 为 server-owned `system_default` preset；growth stage 使用现有 `growth_stage` 列；crop 由现有 catalog 派生，病害类使用唯一 YOLO crop，generic pest 只允许 user fallback。
- Preflight 已保存至 `artifacts/c-case-context-20260829/`；branch=`competition-dev`；不修改 frozen knowledge/assets/manifest，不修改 SQLite schema。
- 实施范围：新增 `backend/app/case_context.py`；最小调整 `backend/app/main.py` 的 growth input compatibility 与 `present_case` context；新增 C tests；更新一条现有 API stale expectation 以匹配“缺省 growth stage 仍成功”。
- 当前状态：最小实现已完成，待 targeted tests、全量门禁、冻结基线复核和脱敏 Review Bundle。
- C 阶段已完成：C targeted=13/13、backend full=295/295、knowledge/assets/manifest=115/115 hash match、SQLite integrity=ok/schema unchanged、diff-check PASS、secret scan PASS；Review Bundle 已生成并自检 52/52。

## B-R1A — Stale Phase9 Severity Contract Test Update（2026-08-29）

### Objective / hard constraints

- 仅把 `backend/tests/test_phase9_public_api.py::test_unknown_spread_forces_unknown_severity` 的过时 expectation 更新为真实新 contract：`ratio=10 + spread_speed="unknown"` → HTTP 422。
- Production code 必须保持不变；不得修改其他测试、知识库/assets/manifest、SQLite、Web、Tavily、Extractor 或任何服务；不得 build/deploy/restart/commit/push。

### Gates

- [x] 已确认 stale test 唯一冲突点及当前 API/B-R1 integration contract。
- [x] 仅 Phase9 指定测试变更并通过 targeted（5/5）。
- [x] B-R1/B contract、历史回归、diff-check、secret scan 全通过。
- [x] 生成并独立验证 B-R1 Review Bundle。

### Errors encountered

- 初次独立 ZIP verifier 将嵌入报告的 `status` 字符串误计入布尔检查，误报 self-test；收窄检查字段后同一 ZIP 重读 PASS。

### Status

- 当前阶段：complete。

### Final

- Source-neutral selection fix completed with only `backend/app/search/normalizer.py` and `backend/tests/test_search.py` changed for this task.
- Normalizer=29/29, 8-case=8/8, T-08=31/31, T-08B=34/34, T-08C=11/11, T-08D=14/14, backend=201/201, diff-check PASS.
- Review Bundle created with MANIFEST=28/28, ZIP self-test=29/29, secret scan PASS; no build/deploy/restart/commit/push.
- 当前阶段：complete。

## Source Policy Relaxation — Read-only Audit（2026-08-28）

### Objective / hard constraints

- 只读审计当前 Tavily → Normalizer → EvidenceExtractor 来源策略，区分来源身份限制、内容安全、垃圾质量和实体/关系安全。
- 基于现有代码与已保存的 8-case/replay evidence，评估豆芫菁、马铃薯早疫病、芫菁、叶蝉科、玉米叶枯病的来源放宽影响。
- 禁止修改 production code/tests、Tavily provider/query matrix、API schema、SQLite、Web/Gateway/Detector/VLM；禁止 build/deploy/restart/commit/push；不得放宽已 PASS safety guards。

### Gates

- [x] 1. 盘点 Normalizer、provider/models/config 与 Extractor 的全部直接相关规则和调用边界。
- [x] 2. 将每条规则分类为 SOURCE_TYPE_RESTRICTION / CONTENT_SAFETY_FILTER / QUALITY_SPAM_FILTER / ENTITY_RELATION_SAFETY / OTHER。
- [x] 3. 用已保存 raw/normalized/filter trace 分析五个剩余病例，并区分来源策略与语言/内容问题。
- [x] 4. 给出精确 RELAX/KEEP 建议、最小 candidate code scope 和 safety impact；更新 findings/progress 后停止。

### Status

- 当前阶段：complete（read-only audit）。
- 结论：无官方/高校/科研 whitelist；普通网页已进入候选池。残余 source-type bias 仅为 authority soft ranking，5 个病例均无 source-type hard drop 证据。

## Locust Single-P1 Minimum Fix（2026-08-28）

### Objective / hard constraints

- 只关闭蝗总科 P1：自然 cause 不得因 source title 的“防控/蝗虫”误杀；真实 source-5 research-analysis 必须拒绝。
- 仅允许改 `backend/app/search/evidence_extractor.py` 与 `backend/tests/test_two_p1_minimum_fix.py`；豆芫菁和所有其他通过的逻辑不改。
- 禁止 build、deploy、restart、commit、push、SQLite/Web/Gateway/Detector/VLM/Tavily/query/API schema 变更；Research/Management pollution 任一大于 0 即失败。

### Gates

- [x] 复现标题级自然 cause 误杀和 source-5 research-analysis 泄漏。
- [x] 收窄为候选句语义 guard，并增加自然、research、intervention 三类回归。
- [x] 通过 Locust/豆芫菁/8-case/T-08/T-08B/T-08C/T-08D/backend/diff-check 全部门禁。

### Findings

- `Locust targeted=4/4`：source title 中的 `防控/蝗虫` 不再参与 intervention 判断；指定沙漠蝗自然 cause ACCEPT。
- 真实 source-5 citation `巩爱歧、Lockwood 等[19-20]的研究也均指出` 由句内模式拒绝；农药/改生境 intervention 也拒绝；两类 pollution=0。

### Error log

- 2026-08-28：首次批量 gate helper 的参数名使用 PowerShell 自动变量 `$args`，每个子门禁都意外跑成全量 199/199；结果仍 PASS，但没有产生逐项计数。已改用命名参数 `pytestArgs` 后重跑。
- 2026-08-28：首次 pollution 汇总把自然正例的“据专家分析”按字符串误计为 research pollution；production 输出并未包含 source-5 研究句。计数器收窄为 citation-research/人类活动信号后，语义核验 Research=0、Management=0。

### Final

- 仅修改 `backend/app/search/evidence_extractor.py` 与 `backend/tests/test_two_p1_minimum_fix.py`。Locust guard 不再读取 source title，只匹配 candidate sentence；新增真实 source-5 citation research-analysis 负例。
- Locust=4/4、豆芫菁=2/2、8-case=8/8、T-08=31/31、T-08B=34/34、T-08C=11/11、T-08D=14/14、backend=199/199；自然沙漠蝗 ACCEPT、source-5 research REJECT、intervention REJECT、Research=0、Management=0、diff-check PASS。
- 未 build/deploy/restart/commit/push；Ready for Work re-review=YES。

### Status

- Work Re-Review：Overall FAIL；New P0=0；New P1=1；禁止 candidate build。
- 当前阶段：in_progress。

## 2-P1 Minimum Fix（2026-08-28）

### Objective / hard constraints

- 只关闭 Work 已确认的 P1-1 豆芫菁 Extractor recall 与 P1-2 蝗总科 research/management pollution；不扩大 scope。
- 允许修改仅限 `backend/app/search/evidence_extractor.py` 与必要 targeted tests；不再修改 `normalizer.py`、`main.py`。
- 禁止 build、deploy、restart、commit、push、SQLite/Web/Gateway/Detector/VLM/Tavily/query/API schema 变更；任一既有 safety regression 立即停止。

### Gates

- [x] 读取真实豆芫菁 raw→Normalizer→Extractor evidence 与蝗总科 source-5 negative evidence。
- [x] 添加窄规则与完整/负向 regression，保持已 PASS guards。
- [x] 通过 targeted、T-08/T-08B/T-08C/T-08D、backend regression、pollution、diff-check。
- [x] 生成干净 Work Review Bundle，targeted test unified diff 不含日志/warning，并完成 secret scan/MANIFEST/ZIP self-test。

### Error log

- 2026-08-28：蝗总科负向正则初版把自然正例“据专家分析，当前蝗虫……”误拒；收窄为明确研究结果词后，P1 targeted 与 8-case targeted 均通过。
- 2026-08-28：生成 bundle 文档 patch 时误创建了一个错误日期的空目录；确认无文件后已精确清理，未进入项目或 bundle。

### Final

- P1-1/P1-2 修复仅改 `backend/app/search/evidence_extractor.py`，新增 `backend/tests/test_two_p1_minimum_fix.py`；Normalizer/main.py 未因本任务改动。
- P1 targeted=4/4、8-case=8/8、T-08=31/31、T-08B=34/34、T-08C=11/11、T-08D=14/14、backend=199/199；Research pollution=0、Management pollution=0；T-08D factual ACCEPT / management REJECT。
- Bundle=`C:\Users\genghailong\Documents\competition-2-p1-minimum-fix-review-20260828`; MANIFEST=32/32；ZIP self-test=33/33；secret scan=PASS。
- ZIP=`C:\Users\genghailong\Documents\competition-2-p1-minimum-fix-review-20260828.zip`; size=28,105 bytes; SHA256=`03a3e5f8becc9ffb41e4dd331175f7f6fbeaef0a536da83beb8c26d3d523bcf1`；build/deploy/restart/commit/push=NO。

### Status

- 当前 Work Review：Overall FAIL；New P0=0；New P1=2；禁止 candidate build。
- 当前阶段：in_progress。

## 8-Case Minimum Fix Review Bundle（2026-08-27）

### Objective / hard constraints

- 只读收集当前 8-Case Minimum Production Fix 的独立 Code Review 证据，生成 ZIP；不修改 production/SQLite/Web/Gateway/Detector/VLM，不 build/deploy/commit/push。

### Gates

- [x] 收集四个本轮 changed files 完整 diff、Git status、diff check。
- [x] 收集 targeted、T-08/T-08B/T-08C/T-08D、backend regression、management pollution 证据。
- [x] 生成 scope/immutability/secret-scan/README、MANIFEST，完成 ZIP self-test。

### Final

- Review bundle=`C:\Users\genghailong\Documents\competition-8case-minimum-fix-review-20260827`; MANIFEST=26/26; ZIP self-test=27/27; secret scan=PASS (0 matches)。
- ZIP size=28,293 bytes; SHA256=`786703093286e94599c28d847f61c8f83b3982470b609aaf7d982ddd827e6509`。
- Bundle generation was read-only with respect to production/SQLite/Web/Gateway/Detector/VLM; no build/deploy/restart/commit/push。


## 5-Case Controlled Replay + 3-Case Regression Baseline（2026-08-27）

### Objective / hard constraints

- 只读补齐 5 个病例的 `raw Tavily → production Normalizer → EvidenceExtractor trace`，并创建 3 个明确问题的 deterministic regression baseline；不修改 production logic。
- 禁止修改 EvidenceExtractor/Normalizer/Tavily/query/prompt/API/frontend/safety guards/SQLite/容器；禁止 build/deploy/restart/recreate/commit/push；不新增搜索 API、不更换 Tavily。
- Live retrieval 如有必要，只通过现有 production query/provider 逻辑的独立、无写入路径；若无法证明层级，标记 `NOT_PROVEN`，不猜测。

### Gates

- [x] 1. 读取现有 planning 与 8-case evidence，确认 5 个 replay case/query/source/fixture 输入。
- [x] 2. 通过独立只读 replay 获得 5 组 raw Tavily、production Normalizer 输出和逐候选 Extractor trace。
- [x] 3. 保存 3 个 regression baseline fixture，明确当前现状 FAIL 与后续 expectations，不改变 production behavior。
- [x] 4. 叶蝉科 T-08D factual-clause retain / management-clause reject regression remains PASS。
- [x] 5. 生成 summary、secret scan、MANIFEST、ZIP self-test，并确认 code/build/deploy/commit/push 均 NO。

### Error log

- 2026-08-27：新 replay-baseline 任务开始；沿用上一轮 8-case 证据，未执行写 API、未修改 production 或正式环境。
- 2026-08-27：系统 `python` launcher 不可用，bundled Python 缺少项目 `httpx`；未安装依赖，改用正式 Backend 容器现有运行环境处理。
- 2026-08-27：容器 helper 首次导入 `app` 因 Python 执行 `/tmp` 脚本未自动加入 cwd；只读定位确认 cwd=`/opt/ghl/backend` 后改为插入 cwd，成功。
- 2026-08-27：容器输出复制首次把 PowerShell `-LiteralPath` 与通配符混用，未复制文件；改为枚举明确子项后成功，未重复 Tavily replay。
- 2026-08-27：叶蝉 T-08D 辅助 fixture 首次用分号导致事实 clause 尾部标点保留；改为现有安全 comma-clause split，仅重跑 `/tmp` trace，最终 factual ACCEPT / management REJECT。
- 2026-08-27：远端临时清理首次用 `rm -f` 处理目录返回“Is a directory”；确认目标为本轮唯一 `/tmp/replay-output-<run-id>` 临时输出后，用同一远端 shell 的精确目录删除完成。
- 2026-08-27：新增 public formatter 首次 targeted pytest 在 collection 阶段因 `str.maketrans` 多字符 key 失败；未执行业务断言，已改为逐字符映射，待重跑。
- 2026-08-27：既有 T-08 回归首次发现 1 个蝼蛄正向 fixture 被初版 TOC 规则误拒（把 `11月份/10厘米` 误识别为目录编号）；暂停门禁并将规则收窄为多个管道符与已知章节标签编号，待从 T-08 重跑。

### 8-Case Minimum Fix result

- [x] 1. 豆芫菁 Normalizer 窄 parent-name overlap 修复；不放宽全局来源黑名单。
- [x] 2. 番茄细菌性斑点病窄 cause pattern 与独立 wrong-context guard 修复。
- [x] 3. 蝗总科 possible-causes 窄 alias/cause pattern 修复。
- [x] 4. Potato/Pumpkin/Corn public/extraction regression 修复；raw Tavily、normalized source、persisted evidence snapshot 未改写。
- [x] 5. Targeted 8/8、T-08 31/31、T-08B 34/34、T-08C 11/11、T-08D 14/14、完整 backend 195/195、`git diff --check` 全部通过；未 build/deploy/restart/commit/push。

### Final

- Five-case controlled replay complete: 10 raw Tavily responses captured with existing production query payload; same formal image code executed production Normalizer and EvidenceExtractor traces in an isolated temporary path.
- Three deterministic baseline fixtures created with current FAIL observations; T-08D exact blocker regression PASS.
- Package=`C:\Users\genghailong\Documents\competition-browser-8case-replay-baseline-20260827`; MANIFEST=56/56; ZIP=`C:\Users\genghailong\Documents\competition-browser-8case-replay-baseline-20260827.zip`; size=1,202,699 bytes; SHA256=`f180bd111466a6598b1d427c5bb2d9c725bb19ec69916ab51a11752ccf6d6fe0`; round-trip=57/57; final secret scan=PASS。
- Production code/build/deploy/restart/recreate/commit/push 均 NO；停止等待 Work replay review。

## 8-Case Browser Trace（2026-08-27）

### Objective / hard constraints

- 只读追溯浏览器人工验收失败的 8 个类别，尽可能还原真实 case ID、图片、持久化 evidence 与 evidence chain；不修代码、不重开既有 PASS 门禁。
- Formal Backend 当前保持已通过状态；禁止 production code、EvidenceExtractor、Normalizer、Tavily、query/prompt、frontend、API schema、SQLite、容器和服务状态变更；禁止 build/deploy/restart/recreate/commit/push。
- 不创建新病例、不调用写接口、不覆盖/删除 evidence；不把历史 retrieval-only fixture 当作浏览器病例；找不到则明确 `REAL BROWSER CASE NOT FOUND` / `NEED USER ORIGINAL IMAGE`。

### Gates

- [x] 1. Formal SQLite/API/uploads 只读盘点与 8 类病例候选索引。
- [x] 2. 逐病例保存脱敏 case/image/API/source/snapshot/raw/normalized/extractor evidence，缺失项明确标记。
- [x] 3. 马铃薯早疫病 canonical fixture SHA 与完整链路只读复现，定位英文 possible_causes 首次出现层级。
- [x] 4. 生成 summary/report、Git/secret evidence；确认代码/build/deploy/commit/push 均 NO。
- [x] 5. 新证据目录 ZIP self-test 后停止，等待最小修复规划。

### Error log

- 2026-08-27：追溯任务开始；沿用 formal deployment PASS 状态，不执行任何写操作。
- 2026-08-27：首次 `scp` 直接读取容器 `/tmp` 失败；导出文件实际在容器而非 Docker host，随后仅用 `docker cp` 取出，无 mounted data 影响。
- 2026-08-27：初次 PowerShell 嵌套数组筛选把盲蝽科记录误选为蝗总科；改用 `detections_json[0].class_name` 明确 primary detection 后纠正，误选未进入 evidence。
- 2026-08-27：canonical case 导出首次把 host shell 重定向文件误当作容器文件调用 `docker cp`；直接从 host `/tmp` 取出后成功，未影响 formal storage。
- 2026-08-27：首次 ZIP+自测复合命令被执行器安全策略拦截，未执行打包或删除；随后拆分为明确目标的打包、解压校验与 .NET 临时目录清理，最终通过。

### Final

- Evidence directory=`C:\Users\genghailong\Documents\competition-browser-8case-trace-20260827`；84 个 payload manifest entries，independent size/SHA256 verification=PASS。
- ZIP=`C:\Users\genghailong\Documents\competition-browser-8case-trace-20260827.zip`；size=1,905,044 bytes；SHA256=`f7d41d18abd76ffcdc84c14e21fa85b88cde90cfc3c73ddfa886e8fe1ed297a1`；round-trip=85/85 files PASS。
- Final secret scan=PASS（85 files，0 secret-pattern match，0 forbidden file）；production code/build/deploy/commit/push 均 NO；完成后停止。

## Qwen3-VL 移除与轻量证据架构（2026-08-24）

- 状态：in_progress；分支 `competition-dev`，启动 HEAD `1819b2a9e7ebc4dbb7b5d8465fea31d0a6c1035b`，工作区开始时干净。本轮不 commit、不 push。
- 目标：以纯 Python、可重复的 `EvidenceExtractor` 取代 Qwen3-VL/8890 图文服务；保留 YOLO、Tavily、EvidenceNormalizer、来源快照与历史病例兼容；将 16 类本地 Markdown 全文、图片、表格和化学防治风险提示完整接入结果、病例和报告。
- 约束：UI 视觉基线冻结，只做知识全文、化学风险提示、提取结果和不可用状态的必要改动；GPU 只在本地测试全绿后做一次最小真实 E2E。Qwen 模型/服务仅在新链路 E2E 后按已确认的项目专属路径隔离并删除。

### 阶段

- [x] 审计 Qwen、8890、病例快照、知识库 16 类文档、启动脚本与实验室部署边界。
- [x] 实施并测试确定性 `EvidenceExtractor`，移除运行时 Qwen 配置、调用、健康与上下文构建。
- [x] 完整渲染知识 Markdown、静态资源安全边界和化学防治提示；兼容历史 Qwen 病例。
- [x] 更新启动/隧道/环境示例/比赛文档与相关测试，完成后端和前端全部回归。
- [x] 审计历史 77 项与当前 69 项后端测试：删除项仅覆盖已移除的 Qwen/VLM 协议与上下文预算，新增项覆盖置信度门、确定性证据提取、类别相关性和知识库风险提示。
- [x] 仅在本地门禁全绿后执行三病例真实 E2E；8870 通过现有 `lab-detector-1` 的只读健康确认和本机回环 SSH 转发恢复。8890 仅做归属与零调用验证，不停止、删除或变更 `cpolar.service`。
- [x] 最终实验室验收：后端、YOLO、Tavily、抽取、持久化和旧病例兼容均通过；生产前端静态资源路由已解阻，浏览器可水合病例和报告。

### 生产前端静态资源 404 解阻（2026-08-24）

- 状态：in_progress；唯一范围为 production frontend build/server/asset routing。禁止触碰后端、诊断链、知识库、GPU、Qwen 迁移或 UI 结构；不 commit、不 push。
- [x] 已复核 Git：`competition-dev` / `1819b2a9e7ebc4dbb7b5d8465fea31d0a6c1035b`，保留既有未提交迁移改动且 `git diff --check` 通过。
- [x] 建立 HTML 引用、build 磁盘产物、HTTP 路由与实际 3000 进程的对照，确认根因：最新 `vinext start` 同样将全部真实 `/assets/*` 返回 404；Windows 上 Vinext `StaticFileCache` 以反斜杠 key 索引，浏览器请求为正斜杠，查找失败。
- [x] 已确认 `web/dist/client/assets/`、manifest 与 Cloudflare worker 的 `assets.directory: ../client` 均存在；Cloudflare Worker runtime (`wrangler dev --local`) 对相同 HTML 引用与全部资源返回 200。
- [x] 仅在根因已证实后作最小修复：生产入口改用项目生成的 Cloudflare Worker + assets runtime，比赛脚本同步 `--ip`、精确 wrangler 清理标记及本地 Worker API proxy bindings；已完成多次 stop → clean build → formal start。
- [x] 完成资源 HTTP、浏览器 hydration、蛴螬结果/报告、全量回归与最终 Git 验收：前端 8/8、lint、后端 69、PowerShell 测试、带比赛 API 基址的 production build/restart、三页资源映射和浏览器验收均通过。

### 582046f Work P0 解阻（2026-08-24）

- 状态：in_progress；起点 `competition-dev` / `582046f150f81880e512c793f433ec01e70b7f32`，Git 工作区干净，禁止 commit/push、GPU/SSH 与范围外改动。
- [x] P0-1：修复多实体标题归属与弱 harm 句误收录；新增 Work 精确复现、单主体上下文、possible cause、damage action/effect 回归，定点 22/22 与手工 A-D 通过。
- [x] P0-2：移除 `deploy/lab` 与 `deploy/gpu` 当前可执行配置中的 Qwen/VLM/8890 依赖；deploy 全目录静态回归通过、搜索零命中。
- [x] P1 评估：不修改。摘要 warning 与完整知识库化学章节 warning 位于不同的展示层级，保留两处安全边界而不在同一展开区域连续重复。
- [ ] 运行 frontend/PowerShell 回归、全仓 runtime/deploy Qwen 分类、安全和 Git 检查（backend 已 75 passed）。

## 外部证据增强诊断（2026-08-21）

- 状态：complete（provider/mock、分析接入、页面、测试完成；真实 Google Search 待配置密钥后单独验收）；严格工作在 `competition-dev`，不修改 `master/main`，不自动 push。
- 目标：增加可替换的 Web Evidence 检索层，让外部资料只支持“危害/可能诱因”的 Qwen3-VL 整理；防治措施继续只来自本地 `knowledge/`。
- 当前基线：工作树干净，当前分支为 `competition-dev`；已有病例分析协议使用 `grounded_assessment.harms/causes`，证据来源目前限于 image/yolo/field。
- 关键假设：本轮没有可提交的真实 Google/Gemini API 密钥，因此先完成 provider 抽象、disabled/mock、标准化、持久化协议、前端展示和测试；真实 Google 调用只在配置密钥后启用，禁止伪造成功。
- 最小变更范围：`backend/app/search/`、现有 `config/database/main/multimodal/reports` 的直接接入、现有结果/详情/报告页面与 TypeScript 类型、backend/frontend 测试及 `.env.example`；不改模型、检测器、Admin、双服务器路由和数据库表结构。

### 阶段

- [x] 读取现有诊断链、病例序列化、知识库、防治展示和前端组件，确定兼容字段。
- [x] 定义 `SearchProvider`、来源模型、Normalizer、disabled/mock provider 与可靠性排序规则。
- [x] 接入分析流程：YOLO → Web Evidence → Normalizer → Qwen synthesis；搜索失败不阻断诊断。
- [x] 扩展病例/报告快照保存 `evidence_analysis`、`sources`、本地 `treatment`，保留旧字段兼容。
- [x] 更新首页、病例详情、报告的危害/可能诱因/防治/来源展示和类型。
- [x] 补充后端 provider、解析、API、降级和前端回归测试，运行完整验证。

### 本轮验收

- [x] 无 API key 时使用 disabled/mock，测试明确不声称真实 Web Search 已接入。
- [x] 每条外部结论仅允许引用规范化来源 `source_ids`；非法 ID 或空证据不能生成结论。
- [x] “诱因”用户可见文案统一为“可能诱因”；防治措施返回来源固定为 `local_knowledge_base`。
- [x] 搜索超时/失败时病例 API 不返回 500，前端显示“暂未检索到可靠资料”。
- [x] backend pytest、frontend lint/build/test、`git diff --check` 通过；typecheck 仅有修改范围外的既有工程错误，已记录。

### Gemini Grounding provider 局部调整（2026-08-21）

- 状态：complete；不 commit、不 push。
- 目标：将默认可选的 Google 外部证据实现改为 Gemini API 的 `google_search` Grounding；保留 Custom Search JSON provider 但仅作为 legacy，不再作为 `google`/默认实现。
- 约束：不改 SearchProvider、EvidenceNormalizer、Qwen evidence_analysis、knowledge/ 防治措施、前端来源展示、历史兼容和降级逻辑；不新增第三方依赖、不写入真实密钥。
- 官方接口依据：Gemini 当前文档提供 REST `POST /v1beta/interactions`、`x-goog-api-key`、`tools: [{"type":"google_search"}]`，结果含 `model_output` 的 `url_citation`；同时兼容解析旧 Generate Content 的 `groundingMetadata`。
- 验收：Gemini citation→SearchSource、URL/title/引用关系、原文抓取、来源 ID、无引用/非法引用/超时/失败降级、防治措施仅来自 knowledge/；backend pytest、frontend tests/lint/build、`git diff --check` 通过。
- 结果：`google_grounding` 已接入官方 REST Grounding，Custom Search 已分离到 legacy provider；后端 `58 passed`，前端 `8 passed`、ESLint、production build 和 `git diff --check` 通过。未配置真实密钥，未执行真实 Google/Gemini E2E。

### Gemini Grounding 真实端到端验收（2026-08-21）

- 状态：blocked_pending_local_runtime；保持 `competition-dev`，不 commit、不 push。
- 已确认：当前 PowerShell/工具进程不存在 `GEMINI_API_KEY`、`CROP_SEARCH_PROVIDER`、Gemini endpoint/model 等真实运行变量；本地 backend `127.0.0.1:8000` 健康，但 YOLO `8870` 与 Qwen3-VL `8890` 未监听。
- 未执行：真实 Gemini 请求、三病例链路和前端真实结果检查；禁止用 mock/历史数据宣称 PASS。
- 继续条件：用户在本机安全设置运行环境变量（不发送密钥），并启动/恢复 8870 与 8890 推理服务；随后重新执行三类真实病例、失败降级和全量回归。

### Gemini Grounding 独立真实连通性测试（2026-08-21）

- 状态：complete_with_external_permission_failure；不启动 YOLO/Qwen，不 commit、不 push。
- 已使用真实临时环境变量和真实类别“蛴螬”分别发起 `harms`、`possible_causes` 两次 Gemini Interactions 请求。
- endpoint HTTP 连接成功，但两次均返回 `403 permission_denied`：`Your project has been denied access. Please contact support.`；请求未进入 Grounding，因此没有 citation、URL 或原网页抓取。
- 当前结论：FAIL，失败类别为 Gemini 项目访问权限被拒绝；不是本地 citation parser、网页抓取或 EvidenceNormalizer 失败。

### Tavily SearchProvider 独立真实连通性测试（2026-08-21）

- 状态：in_progress；不启动 YOLO/Qwen，不 commit、不 push。
- 目标：在现有 SearchProvider 架构中局部新增 `tavily` provider，分别执行“危害”和“可能诱因/发生条件”检索；只验证 Tavily→SearchSource→EvidenceNormalizer，不调用 Qwen或完整病例流程。
- 官方接口依据：Tavily Search 为 `POST https://api.tavily.com/search`，使用 `Authorization: Bearer`；请求显式设置 `include_answer=false`、`include_raw_content=true`、`max_results`，不使用 Tavily LLM answer 作为证据。
- 验收：真实 HTTP、结果数量、title/URL/content/raw_content、Normalizer 来源数和 source-1…ID、低质量过滤、timeout/API/parser/Normalizer 失败分类。
- 结果：Tavily 两次 HTTP 200、每次 5 条结果、raw_content/content 可用、Normalizer 各保留 5 个来源、source-1…source-5 正确、Tavily answer 未进入证据；但知乎/3456.tv/jin-cang.com 等低质量信号均未被当前 Normalizer 过滤，过滤数量为 0，整体 FAIL。未进行大规模修复。

## 参考图驱动诊断工作台改造（2026-08-20）

- 状态：in_progress。
- 目标：以用户提供的“田诊协同”工作台截图为视觉目标，重组公共诊断全链路；保留现有 API、病例/报告数据、模型、数据库和双服务器归属。
- 已确认范围：`/`、`/cases/[id]`、`/reports/[id]`、`/history`、`/trends`；不修改 Admin、训练监控、showcase、backend、detector、VLM 或 GPU 服务器。
- 服务器边界：只接入并部署实验室 CPU `192.168.15.133:8080`，保持 `lab_cpu` 活动实例；GPU 与 Windows 中继不变。
- 参考图仅定义布局与信息层级；其中示例日期、姓名、地块、诊断内容及额外菜单不作为业务数据或新功能。
- 两个 P2：统一历史/趋势页面视觉；使用实验室真实链路完成上传→检测→分析→病例→报告→历史/趋势验收。
- 直接成功标准：桌面为左侧工作区导航+顶部诊断路径+三栏证据工作台，移动端自然纵向布局；现有页面测试、构建、Lint、后端回归、无横向溢出、ARIA 与 reduced-motion 检查通过。

### 实施假设

1. 公共页面继续通过现有 gateway 同源访问 API；本地预览只用于视觉检查，实验室服务器用于真实联调。
2. 参考图左侧导航只映射现有“开始诊断/病例历史/记录趋势”路由，不创建图中不存在的“任务、知识库、团队”等页面。
3. 真实联调优先复用实验室已有病例和项目已有非个人测试图片；不删除既有病例，不修改 GPU 数据。

## UI Redesign V3 验证更新（2026-08-20）

- 已完成 V3 代码构建、前后端测试、浏览器响应式检查，并修复报告页头部/打印按钮的样式类冲突。
- 已将 `DESIGN.md` 更新为实际 V3 视觉系统；下一步只剩 Impeccable 独立评估、必要的低风险 polish 和最终验收汇报。
- 本阶段已完成：核心公共诊断页、病例详情、报告的 V3 视觉重构与回归；Design Health 33/40，Audit 17/20，无 P0/P1。
- 待用户开启识别服务后，以真实病例补做在线成功态/长任务/报告资源联动验收；不在本阶段伪造结果数据。

## Goal

完成一个可复现、可演示、可解释的多模型协同农作物病虫害识别与防治系统：在冻结的官方验证集上可靠评估，针对弱类定向优化，将真实模型接入网页与后端，并形成比赛提交材料。

## Next Step

2026-08-19：Phase 9.12 上传必填信息、证据绑定综合分析与诊断页面改造已完成实验室 CPU 部署与植物/昆虫真实验收。下一步由用户测试实验室页面；GPU 端仍保持原版本，待实验室验收后再更新。

2026-08-19：Phase 9.11 图片信息自动匹配与上传表单精简已完成实验室 CPU 实施和真实蛴螬验收。原 GPU 尚未更新，等待用户开启 GPU 服务器和 Windows 中继后发布同一版本。

2026-08-18：Phase 9.10 病例详情知识栏目纵向布局调整已完成；“症状→特征→防治建议”在所有视口均为单列上下排列，已部署实验室 CPU，GPU 实例未修改。

2026-08-18：实验室服务器知识库展示改造已完成并验收。16 类百度百科 Markdown 与 61 张引用图片已打包为 `baidu-baike-20260818`；详情页、完整报告、知识接口和 v2 快照均已上线实验室 CPU。下一步仅在用户开启 GPU 服务器并明确通知后，将同一版本部署到 GPU 实例。

双服务器部署已于 2026-08-17 验收完成：实验室 CPU 与原 GPU 均为独立完整实例，Admin 双向切换、病例归属、文件/SQLite/报告隔离、重启持久化、目标离线拒绝和恢复均通过。当前活动实例为 `lab_cpu`；GPU 通过 Windows 临时中继在线，Windows 必须保持开机、联网且不休眠。

2026-08-16 更新：离线镜像、Qwen3-VL、Python wheels、npm cache 和部署代码均已上传，兼容性门已通过，Admin 配置已在本地安全生成。当前电脑连接 `172.20.10.0/24` 而非实验室局域网，`192.168.15.133:22` 不可达；下一步是在重新连接实验室网络后合并 Admin `.env`、离线构建并执行 CPU 单机验收。GPU 服务器仍无需开启。

Phase 9 的真实 GPU 与当前问题整改自动验收已完成：普通流程采用自动判断或拒答，测试数据与用户历史隔离，本机 `/admin` 集中管理；六模型公平对照完成但新 YOLO12s 未通过冻结晋级门，现网主模型 + shadow 专家保持不变。恢复后固定 160 张双阶段评估、本机正常/无目标 E2E、隧道与四服务恢复、SQLite 检查和自动回归均通过。下一步由用户在当前电脑 Chrome/Edge 亲自验证关键用例并反馈；用户确认后进入 9.9，与用户先冻结最终 UI/UX 需求，再实施界面重构。

## Current Phase

Phase 9.12 — 条件必填表单、证据绑定综合分析与页面改造（complete on lab CPU; GPU pending user acceptance）

## Resume Check — 2026-08-14

- 已使用工作区 Python 成功运行 `session-catchup.py`；未报告未同步上下文。
- 已完整读取三个规划文件并检查 Git 状态；现有代码、证据、未跟踪 `CLAUDE.md` 和其他用户改动均保留，不做清理或回滚。
- 当前旧 GPU 主机 `connect.bjb2.seetacloud.com:10373` TCP 不可达；本机仅 FastAPI `127.0.0.1:8000` 返回健康，前端 `3000`、detector `8870`、Qwen3-VL `8890` 均不可达。
- 因此不能把自动/GPU 证据当作本轮 Chrome/Edge 人工验收，也不启动新的模型评测、训练或 UI 重构；下一入口是用户在控制台恢复 GPU 主机或提供新的有效 SSH 地址后，重新核对模型/服务并启动本机验收链路。

## Mandatory Karpathy Guidelines

后续所有代码与配置工作必须遵守：

1. 修改代码前先列出并核对假设；存在高影响歧义时先停止并说明。
2. 优先采用满足需求的最简单实现，不添加未要求的抽象或配置。
3. 避免无关重构；每一处修改都必须能直接追溯到当前任务。
4. 所有修改必须有明确、可重复的验证方法，并在修改后立即执行。
5. 修改范围只包含任务直接相关文件；保留用户已有改动，尤其不修改或提交未跟踪的 `CLAUDE.md`。

### Enforcement Status — 2026-08-10

- **Audit result:** 项目已经使用 Karpathy Guidelines；本节规则已存在于本文件，并在 Phase 8/9 的工作日志和计划中被引用。
- **User-mandated wording:** 后续开发必须在修改代码前分析假设；优先简单实现；避免无关重构；所有修改必须可验证；修改范围必须与任务直接相关。
- **Scope:** 该约束适用于后续所有代码、配置、测试、部署和 UI 工作，不限于当前 Phase 9；任何新任务开始前都必须先列出假设、最小方案、直接相关文件和验证标准。
- **Evidence rule:** 历史日志能够证明该规则已被写入并作为约束使用，但不把过去每次修改自动标记为逐项合规；后续每个修改阶段都要留下可复核的假设、变更范围和验证记录。

## Resume Protocol

新对话或上下文清空后，按顺序执行：

1. 完整读取 `task_plan.md`、`findings.md`、`progress.md`；Windows PowerShell 使用 `Get-Content -Raw -Encoding UTF8`。
2. 检查 `git status --short --branch`，保留用户已有改动。
3. 确认当前服务器是否开机、地址是否仍有效；不要默认继续使用旧服务器。
4. 从本文件的 `Next Step` 继续，不要重跑已经标记 complete 的实验。
5. 每完成一个阶段，同步更新三个规划文件；完成本轮工作后的总结性回复使用下方固定模板，不只汇报局部操作。

## End-of-Task Reporting

默认每次小任务结束后的最终汇报只包含：

1. 当前小任务完成了什么。
2. 下一个小任务要做什么。

只有用户明确要求项目全局汇报，或上下文接近上限触发下方协议时，才额外包含：整体计划/目标进度、已完成优化、当前阶段及目的、后续优化、模型数量、最佳模型和数据集构成。模型数量仍须区分训练实验与保留模型角色，数据集仍须区分训练、验证、独立评测和仅审计未采用的数据。

## Context-Capacity Reporting Protocol

当上下文占用率接近上限、即将发生压缩或需要开启新对话时，任务结束汇报自动升级为项目全局状态报告，即使用户没有再次提出要求。报告必须说明：

1. 整体项目计划与最终目标目前进行到哪一步。
2. 已完成哪些阶段和优化；当前正在做哪一步、目的是什么。
3. 后续还需要完成哪些优化、验证和交付工作。
4. 当前训练实验数量与保留模型角色数量（分开统计）、目前最好的模型及依据。
5. 当前数据集组成，并区分训练、官方冻结验证、独立 tune、独立 frozen/test、仅审计未采用数据。
6. 当前所在阶段、阶段状态和下一阶段入口。

该全局报告发出前，先把最新状态、指标、模型/数据口径和下一步写入 `task_plan.md`、`findings.md`、`progress.md`；报告结尾明确提醒用户开启新的对话以继续工作。上下文未接近上限时，继续使用上面的简短小任务汇报模板。

## Phases

### Phase 1: 项目迁移与系统基础

- [x] 将既有实现谨慎迁移到当前 Git 仓库
- [x] 保留用户内容并确认工作区边界
- [x] 建立网页诊断、FastAPI 后端、远程视觉推理接口
- [x] 建立人工复核页与实时训练监控页
- **Status:** complete

### Phase 2: 官方数据审计与基线

- [x] 审计官方 4,164 张图片、5,920 个检测框、16 类
- [x] 固定随机种子 `20260729`
- [x] 固定 3,321 训练、833 验证，隔离 10 个冲突重复样本
- [x] 训练并独立验证 YOLO26n 官方基线
- [x] 导出 ONNX，保存指标、权重和复现配置
- **Status:** complete

### Phase 3: 补充数据与人工复核

- [x] 审计 `C:\编程大赛数据\Dataset\图片` 与 `pest65`
- [x] 完成自动预标注和人工标注复核流程
- [x] 仅使用有明确类别映射、检测框、许可证和低重复率的公开数据
- [x] 保存公开数据来源审计和固定清单
- **Status:** complete

### Phase 4: 弱类优化与独立校准

- [x] 完成类 8/15 专项混淆与困难样本审计
- [x] 完成类 6/12 专项混淆与困难样本审计
- [x] 建立类 10/13 专家分类器及第一轮阈值校准
- [x] 准备类 10 的 SciDB 独立 tune/test 清单
- [x] 建立类 13 ZIP 自动审计、人工复核门控和可移植冻结清单工具
- [x] 下载并独立人工复核类 13 现场检测样本
- [x] 对新样本进行哈希去重、框质量检查和候选冻结划分
- [x] 执行类 10/13 第二轮校准并与第一轮对比
- [x] 根据冻结结果决定是否继续小规模微调或从头训练
- **Status:** complete

### Phase 5: 多模型协同生产集成

- [x] 将主检测器与类 10/13 专家模型接入服务器推理链
- [x] 根据校准结果实现逐类阈值与专家路由（默认 shadow，active 需显式开启）
- [x] 在网页完成真实图片端到端识别验证（`phase5-e2e-class10.jpg`，本地网页→FastAPI→远程 shadow 推理链路成功）
- [x] 测量准确率、延迟、吞吐、显存和模型大小（官方冻结验证集 + RTX 5090 主模型基准 + shadow 路由 HTTP 压测）
- [x] 所有实验接入实时监控并保留配置、指标、权重（训练监控 20 个运行、四个保留模型角色、实时健康探测及证据清单已固化）
- **Status:** complete（`phase5-full-evidence-20260810.json` 已生成并校验；active 仍不允许）

### Phase 6: 防治知识与可信交互

- [x] 建立 16 类知识卡片、来源登记和非化学/综合防治安全边界（明确为 general IPM orientation，不输出药剂剂量）
- [x] 将知识卡片、检测框、置信度和模型路由证据接入诊断结果
- [x] 完善低置信度、无目标和候选冲突结果的人工复核闭环
- [x] 验证建议不得越过证据范围，并保留来源版本与复核审计记录
- **Status:** complete（Phase 6 安全知识/解释性/复核闭环已通过后端、网页和接口验证；后续可在有逐类权威标签时扩展知识来源）

### Phase 7: 比赛材料与最终交付

- [x] 完成系统架构、数据治理、实验对比和创新点材料（含答辩幻灯片提纲）
- [x] 固化演示流程和离线容错方案（含真实识别和无模型降级路径）
- [x] 完成最终回归测试与复现检查
- [x] 审核公开仓库和比赛提交包
- **Status:** complete（材料五件套、标准库复现门、服务探测和发布边界检查均通过；active 仍禁止）

### Phase 8: 真实多模态端点与一键完整分析

- [x] 在 RTX 5090 隔离环境部署 Qwen3-VL-8B-Instruct/vLLM，并提供可重复启动、停止、状态和隧道入口
- [x] 将后端多模态请求改为 OpenAI 兼容接口，增加严格结构校验、风险升级与模型溯源
- [x] 将网页主操作改为一键上传、检测和多模态分析，并完整展示 C 项字段与失败重试
- [x] 完成真实网页 E2E、16 类分层验证、准确率/完整率/延迟/吞吐/显存/模型大小测量
- [x] 更新比赛材料、证据清单和三份规划文件
- **Status:** complete（160/160 成功、Top-1 86.25%、结构校验 100%；冲突识别 5.88% 为已记录限制，active 仍禁止）
- **Final gate:** `phase8-final-repro-v1` 通过，25/25 必需文件、Phase 5/8 证据、公开边界和 8000/8870/8890/3000 实时探测全部通过。

### Phase 9: 面向普通用户的本机交付与最终 UI 重构（2026-08-12）

- **Status:** in_progress；本计划取消公网、Sites、Cloudflare、域名和跨电脑交付要求，在保留 A–E 评分优化目标的同时改为当前电脑完整运行与验收。
- **目标边界：** 不提前宣称满分；每个条件必须可现场操作、可观察、可复现。保留 `shadow`、禁止自动重训和污染官方 833 张冻结验证集，保留未跟踪的 `CLAUDE.md`。
- **GPU 状态：** 2026-08-12 已恢复 RTX 5090，真实 detector/Qwen3-VL、16 类冒烟、固定 160 张正式评估和本机完整 E2E 均已执行；服务与回环隧道保持运行等待用户验收。
- **本机拓扑：** 前端 `localhost:3000`、FastAPI `127.0.0.1:8000`、SQLite/图片/报告均在本机；8870/8890 仅通过回环 SSH 隧道连接服务器 GPU，不开放局域网或公网。
- **兼容边界：** 已完成的公网模式、Worker、安全字段和回归测试保留但默认关闭，不再作为 Phase 9 交付或验收条件。

#### 9.1 重建评分验收基线

- [x] 完整读取三个规划文件，运行会话恢复并检查 Git 状态；保留 CPU/静态验收和用户已有改动。
- [x] 将题目二 A–E 满分标准逐条映射到页面、接口、数据库字段、自动化测试和现场截图，并更新验收矩阵。
- [x] GPU 恢复后执行干净启动并完成正常链路、16 类、冲突、服务失败、仅分析重试、刷新与后端重启恢复；多目标、无目标、低质量和低置信路径继续由既有真实病例与确定性回归保护，待用户抽查。
- [x] 冒烟发现严重度引用、冲突识别和延迟缺口后，先记录假设与最小范围，再完成协议修正和逐轮回归；模型与数据链路未发现 P0。
- [ ] 2026-08-12 产品诊断新增 P1：正式 160 张中 102 张触发人工复核（63.75%），其中 56 张属于“非预期冲突却被标记冲突”；需在不降低安全门的前提下减少无效复核，并验证 2 个漏识别冲突样本。
- [ ] 2026-08-12 产品诊断新增 P1：病例“请求人工复核”当前只写入等待状态，普通用户端没有复核责任人、处理入口、预计反馈或结果回传；现有 `/review` 是预标注队列，不能冒充病例诊断复核闭环。

#### 9.2 本地病例、严重度、历史和数据库基础

- [x] 病例增加 `affected_ratio_percent`（0–100）、`spread_speed`、`public_consent`、`expires_at`、`diagnostic_risk` 和 `field_severity`。
- [x] 缺少受害比例或扩散速度时，田间严重度固定为“无法判断”；信息与模型结果明显矛盾时转人工复核；严重度不得等同经济阈值或现场结论。
- [x] 复用现有人工复核 `severity`，不建立第二套同义字段。
- [x] 本地模式上传不要求公开同意；历史默认读取 SQLite 全部病例，趋势统计全部本机记录。
- [x] 本地病例长期保存，不执行 30 天自动过期；仅显式公网模式继续公开过滤、编辑令牌和过期清理。
- [x] SQLite 已启用 WAL、busy timeout 和完整性检查，并提供备份、恢复及图片路径校验。
- [x] 增加趋势统计和结构化报告接口。

#### 9.3 两阶段多模态协同优化（C 项）

- [x] 阶段一只向 Qwen3-VL 提交原图和田间信息，不提供 YOLO 类别，形成独立图像判断。
- [x] 阶段二提交独立判断、YOLO 框/置信度、两位专家 shadow 证据和质量风险，比较一致、冲突和无法判断原因。
- [x] `phase9-multimodal-v2` 输出主/候选诊断、症状、危害、原因、证据、不确定性、补拍信息、模型一致性、诊断风险、田间严重度与依据、人工复核和双阶段溯源。
- [x] 后端确定性门继续保证：类别不同即冲突；无目标、低置信度、质量异常、内容不足或字段矛盾必须复核；大模型只能升级风险，不能清除已有风险。
- [x] 专家路由保持 `shadow`；不新增第二个大模型，不做无证据重训。

#### 9.4 逐类知识库与防治安全优化（D 项）

- [x] 16/16 类各补充至少一个逐类权威来源，优先农业农村部门、植保机构、国家标准或高校农技推广资料。
- [x] 来源包含标题、发布机构、网址、检索日期和适用范围；保留 FAO、法规和绿色防控原则来源。
- [x] 每类按农业、物理、生物、监测与升级处置组织；不适用时明确标注。
- [x] 根据诊断风险和田间严重度调整行动优先级，但不自动确认病原、发生程度或经济阈值。
- [x] 禁止具体产品、剂量、混配、施用次数和安全间隔；化学防治只提示当地现行登记标签与植保人员。

#### 9.5 面向普通用户的本地基础界面（A、B、E 项）

> 本阶段提供用于功能验收的用户化基础界面，不代表系统定型后的最终视觉版本；最终重构安排在 9.9。

- [x] 主流程为“拍照/选图 → 填田间情况 → 看发现/风险/下一步 → 看位置/候选/不确定性 → 保存/历史/趋势/报告”。
- [x] 将“公共历史/最近公开上传”统一改为“病例历史/最近诊断记录”，移除本地流程的公开同意与 30 天说明。
- [x] 建立首页、病例详情、历史、趋势和可打印报告页面；报告支持浏览器保存 PDF。
- [x] 默认隐藏阈值、SHA、原始 JSON 和训练指标，放入“查看技术证据”；管理页仅主机本地可访问。
- [x] 手机后置摄像头、空/加载/失败/离线状态和仅重试分析入口齐全。
- [x] 保持现有 Next/Vinext、Tailwind/CSS 和绿色品牌体系，不迁移框架、不引入无关 UI 库。

#### 9.6 本机运行与稳定性

- [x] 前端与 FastAPI 只绑定本机回环地址；8870/8890 只通过私有 SSH 隧道连接服务器，不建立公网或局域网入口。
- [x] 整理本机启动、停止、状态和健康检查步骤，覆盖前端、后端、双隧道与远程模型服务。
- [x] GPU、隧道或多模态服务不可用时不伪造结果，病例仍保存并支持恢复后仅重试分析。
- [x] 公网 Worker、`CROP_PUBLIC_MODE`、origin secret、编辑令牌和限流实现保留但默认关闭，不进入本机默认启动流程。

#### 9.7 本机趋势、报告与用户验收（E 项）

- [x] 趋势仅描述本机保存的诊断记录，展示 7/30 天数量、作物、候选病虫害、严重度和复核状态，并可追溯病例详情；不得描述为地区疫情趋势。
- [ ] 自动验证现已完成并暂停，由用户在当前电脑使用 Chrome/Edge 验证上传、两阶段分析、历史、严重度、趋势、报告、异常重试、刷新和重启恢复。
- [x] 手机尺寸只做响应式自动检查，不要求手机真机、另一台电脑或公网访问。
- [ ] 用户确认前不关闭 Phase 9；发现问题回到对应子阶段修复并重新验收。

#### 9.8 满分证据与最终交付

- [x] 更新 A–E 验收矩阵，逐项记录操作、预期、实际、截图、响应和日志。
- [x] 更新架构、演示、复现、数据库、本机运行和答辩材料，形成“满分条件 → 本机操作 → 现场演示 → 证据文件”索引；公网部署文档标记为已取消的历史方案。
- [x] 后端完整 pytest；前端 build/render/lint；数据库迁移、备份恢复和本机长期保存；两阶段 mock 与真实 GPU；内置浏览器/手机尺寸；Git diff 检查全部通过。Chrome/Edge 用户验收单列在 9.7，不由自动测试代替。
- [ ] 只有全部 P0/P1 关闭、用户关键用例通过、GPU 真实验证通过后，才完成 9.8 并进入 9.9；材料只陈述已验证事实。

#### 9.9 系统定型后的最终 UI/UX 重构

- **入口条件：** 9.1–9.8 全部完成，GPU 真实链路、数据库持久化、本机 Chrome/Edge 和用户关键用例均已通过；未满足时不得提前启动本阶段。
- [ ] 与用户确认最终使用对象、现场演示顺序、必须突出/隐藏的信息、视觉偏好和实际使用反馈，形成冻结的 UI 需求清单。
- [ ] 基于真实病例和已定型接口审计首页、上传、诊断结果、病例详情、病例历史、趋势、报告、空/加载/失败/离线状态的信息架构与操作路径。
- [ ] 在现有 Next/Vinext、Tailwind/CSS 和绿色品牌体系内重构布局、层级、组件、响应式和可访问性；不迁移框架，不修改模型、数据库或后端业务契约，除非另行记录并获得授权。
- [ ] 默认面向普通用户，确保“发现了什么、风险多大、下一步怎么做”最先可见；模型 SHA、阈值、原始 JSON 和训练指标继续放在技术证据或本地管理区。
- [ ] 使用真实数据完成当前电脑 Chrome、Edge、桌面和手机尺寸视觉/交互验收，覆盖长文本、多检测框、无目标、低质量、冲突、加载、失败、离线和打印报告。
- [ ] 运行前端 build、render tests、lint、关键流程回归和逐页截图对比；确认 UI 重构没有破坏上传、检测、两阶段分析、保存、历史、趋势、报告、隐私和复核能力。
- [ ] 用户确认最终界面满足需求后，更新截图、演示手册、答辩材料和证据索引，再将 Phase 9 标记为 complete。

#### 9.9 前置产品问题清单（2026-08-12 诊断）

- [ ] P1：移动端在 `max-width: 900px` 隐藏主导航但没有替代菜单，需保证首页、病例历史和记录趋势仍可直接互达。
- [ ] P1：建立真实病例复核闭环，或把按钮改为诚实、可执行的“记录为待咨询/导出报告咨询植保人员”，不得让用户无限等待不存在的服务。
- [ ] P1：降低无效复核负担；正式评测的人审触发率 63.75%，非预期冲突误触发 56/143，不适合作为成熟用户流程的默认状态。
- [ ] P2：将“生育阶段、受害比例、诊断风险、田间严重度、视觉候选、独立多模态判断”等术语改为普通中文并提供不知道/示例/图示辅助。
- [ ] P2：普通用户正文目前大量使用 9–11px 字号，需按可读性、键盘焦点、触控目标和 200% 缩放重新验收。
- [ ] P2：清理或隔离测试病例中的 `????` 历史字段、错误作物组合和带图库水印演示图，避免污染趋势与正式演示可信度；不得无授权改写原始病例。
- [ ] P2：逐类来源标题优先提供中文说明；英文原题和模型协议保留在技术证据区。

#### 9.10 当前问题整改与自动化交付（2026-08-12，进行中）

> 本阶段执行用户确认的“自动判断或自动拒答”方案，先解决现有产品问题并完成六模型公平对照；不提前启动 9.9 最终视觉重构。

- [x] 数据隔离：修改数据库前完成 SQLite 在线备份、完整性检查与图片路径清单；增加 `is_test`，将实施开始前的 21 条开发/评测病例标记为测试记录，普通历史与趋势默认隐藏，`/admin` 可查看全部。
- [x] 自动收口：病例统一映射为 `conclusive`、`retake_required`、`no_supported_target`、`service_unavailable`；普通用户不再进入不存在处理人的“等待人工复核”，冲突时展示候选和补拍建议。
- [x] 用户/管理分层：新增本机 `/admin` 管理入口；普通导航只保留首页、病例历史、趋势和报告，原 `/training`、`/review` 保持兼容入口。
- [x] 易用性：补齐移动导航、普通中文解释、置信度边界、正文/辅助文字字号、44px 触控目标、键盘焦点和 200% 缩放；来源中文说明优先，技术协议留在折叠区。
- [x] 统一数据治理：生成 4,490 张合格图片的统一清单（开发训练 3,816、内部验证 674）；官方冻结 833 张、crop 分类数据和不可靠数据均未进入选型。Pest65 11 张空标签、4 张损坏 JPEG 和 1 张重复框图片被明确排除；OpenCV 独立复核 4,490/4,490 无解码问题。服务器缺少 Roboflow 类 13 原始训练 445 张，未使用 tune/frozen 替代。
- [x] 六模型对照：统一 640、120 epochs、batch 32、固定种子与同一开发验证门完成 YOLO26n/26s/11s/12s/v8s/v5su 对照，6/6 无失败且未使用官方冻结 833 张选型。综合分前两名为 YOLO11s `0.495082`、YOLO12s `0.493887`；差值 `0.001196 <= 0.005`，按预设接近候选规则由 Recall 更高的 YOLO12s（`0.756101` 对 `0.750980`）进入最终重训。
- [x] 模型晋级判定：YOLO12s 用全部 4,490 张允许数据完成 120 轮重训，并且只对官方 833 张冻结集评测一次。候选 Recall `0.798434`、16 类证据通过，但 mAP50-95 `0.523463 < 0.548224`、mAP50 `0.809507 < 0.827517`、弱类增益与单类下降门失败，因此拒绝晋级；保留现有主模型 + shadow 专家链与 Qwen3-VL，不继续利用冻结集调参。
- [x] 自动全量回归：后端 24 passed；前端 build + 6/6 tests、lint 0 errors；SQLite `integrity=ok`、22/22 图片有效；固定 160 张恢复后复测 160/160、Top-1 87.50%、Schema/内容/严重度引用 100%、冲突 15/17、安全输出与风险错误清除均 0、E2E P95 5.105 秒、峰值显存 23,088 MiB；无目标自动拒答和正常“可参考结论”两条本机 E2E 均通过。3000/8000/8870/8890 已恢复，等待用户 Chrome/Edge 人工验收。

**本阶段修改前假设与成功标准**

- 当前 21 条 SQLite 记录全部是开发、自动评测或演示数据；迁移采用可恢复标记，不删除或改写原始病例内容。
- “全自动”不等于强制猜测；证据不足时自动拒答、解释原因并引导补拍。
- 新模型候选在开发验证集选择，官方 833 张只用于最终胜出架构的冻结验证；未通过硬门则保留当前模型。
- 服务器当前 RTX 5090 运行 detector 与 Qwen3-VL，约占 23 GiB 显存；训练前必须记录 PID 并安全停服，训练后恢复同一服务边界。

#### Phase 9 接口与硬门

- `POST /api/cases` 保留田间严重度输入；本地模式不要求公开同意，公网兼容模式仍强制同意。
- `POST /api/cases/{id}/detect|analyze|review` 公开模式要求病例编辑令牌。
- `GET /api/cases` 本地模式默认返回全部病例，公网兼容模式仅返回 30 天内已同意记录；`GET /api/trends?days=7|30` 跟随相同范围，`GET /api/cases/{id}/report` 保持可用。
- C 项真实 160 张硬门：成功/Schema/内容完整率 100%，不安全输出 0，风险错误清除 0，17 个冲突识别率至少 80%，Top-1 不低于 86.25%，双阶段 E2E P95 不高于 7 秒。
- D 项硬门：16/16 逐类权威来源、防治分类和安全提示；不得出现具体产品、剂量、混配或安全间隔。
- E/本机硬门：缺失田间输入严重度必须未知；本地历史和趋势与 SQLite 全部记录一致；报告可打印；超过 30 天的病例不会自动删除；重启后记录可恢复。公网兼容模式的 30 天过滤、无令牌 403、限流 429 和管理隔离继续由回归测试保护。

## Decision Gates

1. 类 13 独立样本未完成许可证审计、人工复核和去重前，不启动第二轮校准。
2. 第二轮校准只使用独立 tune 集选阈值，frozen test 仅作一次最终比较。
3. 是否从头训练由冻结验证提升、弱类召回、误报和部署成本共同决定，不因新增数据而自动重训。
4. 官方 833 张验证集保持冻结，禁止因弱类结果调整划分。
5. 原始图片、标注、模型权重、私钥和大归档不进入公开 Git 仓库。
6. Phase 8 只补齐解释端点和一键闭环；类 10/13 独立 frozen 门未通过前，任何多模态结果都不能批准 detector active 路由。

## Key Questions

1. 类 13 候选公开数据能否合法下载、检测框质量是否足够、与官方数据重复率是否可接受？
2. 第二轮校准是否能改善类 10/13，同时不损害其他类别和总体指标？
3. 专家模型路由带来的准确率收益是否大于延迟与维护成本？
4. 是否需要第二轮从头训练，还是阈值校准与专家路由已经满足比赛需求？

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 官方划分使用种子 `20260729` 并永久冻结 | 保证实验可比较，避免验证集泄漏 |
| 当前生产候选使用补充弱类数据训练的 16 类模型 | 相比官方基线更适合作为后续协同主模型 |
| 类 10/13 使用专家分类器和独立校准 | 两类存在专项混淆，逐类路由比盲目全量重训风险低 |
| 先小规模试验，再决定从头训练 | 节省 GPU 成本并避免低质量公开数据破坏整体性能 |
| GitHub 只发布代码与可公开元数据 | 避免泄漏原始数据、权重、密钥并控制仓库体积 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| GitHub CLI 的 `ghu_` GitHub App 令牌无 `CreateRepository`/写入权限 | 1 | 用户在 GitHub 网页创建公开仓库，随后使用 Git Credential Manager 标准授权推送 |
| Chrome 自动控制 GitHub 创建页多次超时 | 2 | 停止重复自动尝试，明确让用户手动点击一次“创建存储库” |
| PowerShell 双引号提前展开远程 Bash 命令 | 1 | 改用 PowerShell here-string 通过 SSH 标准输入发送脚本 |
| SSH here-string 的 CRLF 影响最后一条 Bash 命令 | 2 | 对关键检查改用单行远程命令或避免续行末尾参数 |
| 恢复服务器时首条远程命令再次被 PowerShell 提前展开 `$f`，随后标准输入脚本末尾受行尾影响 | 2 | 停止使用远程循环/here-string；改用不含远程变量的单行命令并成功完成检查 |
| 远程 `/root/autodl-tmp/crop-pest-system` 不是 Git 工作树 | 1 | 将本地仓库作为代码真源，只向远程同步经过验证的训练工具和必要数据 |
| 长内联合成测试被本机安全策略拒绝 | 1 | 改为仓库内可重复运行的标准 `unittest`，本机与服务器均通过 |
| 服务器非交互 shell 中 `python` 不在 PATH | 1 | 改用明确解释器 `/root/miniconda3/bin/python` 完成编译和测试 |
| GHCID 类 13 全量数据约 31.2GB，当前服务器空间和选择性下载条件不合适 | 1 | 暂不下载，改为审计更小且有 CC BY 4.0 的检测数据候选 |
| Windows PowerShell 默认 `Get-Content` 将无 BOM UTF-8 中文显示为乱码 | 1 | 后续读取规划文件显式使用 `-Encoding UTF8` |
| Windows `python.exe` 命中 Microsoft Store 占位启动器，`session-catchup.py` 无输出并退出 1 | 1 | 改用 Codex 工作区依赖提供的 Python，恢复检查成功完成且无未同步输出 |
| 本次 Windows `session-catchup.py` 调用再次命中 Microsoft Store `python.exe` 占位启动器并退出 1 | 1 | 未修改项目；明天恢复时使用规划日志中记录的 Codex 工作区 Python，并先重新执行恢复检查 |
| Roboflow 动态页面 DOM 在内置浏览器中连续超时 | 2 | 停止重复 DOM 抓取，改用精确公开搜索核对数据集元数据；下载仍保留为登录后人工/浏览器步骤 |
| Roboflow 选择 YOLOv11 后点击 Continue，完整 DOM 读取超时并重置控制连接 | 1 | 改用轻量标签定位；发现流程短暂进入 `/fork`，推断下载前需要创建账户内副本，等待用户确认该外部变更 |
| 重连后 `/fork` 标签页已不在可接管列表，仅剩原数据集页 | 1 | 不臆测页面状态；回到原数据集页，在获得 Fork 授权后重新走直接 YOLOv11 路径 |
| Fork 对话框的 DOM 节点在点击时变为 stale | 1 | 未重复旧节点；重新读取页面并改用可访问角色定位对话框中的最后一个 `Fork Dataset` 按钮 |
| Playwright 角色定位未识别 Fork 对话框中的第二个同名按钮 | 2 | 未提交；第三次改为同一调用内读取可见 DOM、提取末尾 Fork 节点并立即点击，避免跨调用失效 |
| Web 工具直接打开 Roboflow 版本 URL 被安全层拒绝，随后打开搜索结果出现解析错误 | 2 | 使用一次精确搜索结果作为公开元数据证据，不再重复直接打开 |
| 推送规划日志小修时 HTTPS 重置，随后 443 不可达 | 3 | DNS 正常但 HTTPS 超时；停止重复尝试，本地保留领先提交，网络恢复后补推 |
| 类 13 审计扫描外部对比库时遇到截断图片并中止 | 1 | 保持目标 ZIP 严格校验；外部对比库坏图改为记录路径与错误后跳过，并增加回归测试 |
| 终结门把 16×16 平均哈希距离 0 直接当成跨 split 完全重复，合成回归测试出现误报 | 1 | 保留近重复提示；增加解码像素 SHA 硬门，并要求跨 split 距离 0 接受项有显式 `[cross-split-distinct]` 人工标记 |
| PowerShell 在 `foreach` 代码块后直接接管道时报 empty pipe element | 1 | 先将循环输出收集到任务专用变量，再单独管道格式化 |
| Git 忽略审计命令再次在 `foreach` 后直接使用管道并触发相同解析错误 | 2 | 立即停止该写法，改为 `$ignoreResults` 收集后再格式化；将该模式固定为禁止重复 |
| 最终状态检查在 PowerShell 哈希表字段中内联多语句表达式导致括号解析失败 | 1 | 将 `check-ignore` 与退出码判断拆成独立语句后再构造结果对象 |
| 从仓库根目录用模块名启动类 13 回归测试时，同目录导入不在 `sys.path` | 1 | 改用测试文件的直接脚本入口，6 项回归测试全部通过 |
| 远程组合核对命令因 PowerShell 转义/远程引号组合超时 | 1 | 拆成不含远程变量的短命令后，清单、文件和哈希核对通过 |
| 远程核对命令未引用 `grep` 管道，超时后留下孤立 grep 子进程 | 1 | 定位并清理本次命令的精确 PID；改用不含管道的短检查，确认 GPU 仍空闲 |
| 第一轮第二轮校准报告的独立数据 baseline 指标全为 0 | 1 | 诊断发现类 10 SciDB 标签仍是专家数据集本地类别 0，且类 13 首张样本在 0.05 置信度下无预测；保留报告为无效诊断，先建立官方类 10 重映射副本并重新评估 |
| 首次类 10 重映射假设源标签只有类别 0，遇到类别 1；一次 `sed` 重写也因远程引号失败 | 1 | 阅读 `TARGET_TO_EXPERT={8:0,10:1}` 后建立全新副本，正确映射 `0→8、1→10`，不修改原始 SciDB 数据 |
| 远程 Python 诊断脚本嵌套引号被 Bash 剥离 | 1 | 改用 Base64 传递只读诊断脚本；确认类 13 首样本主模型在 conf=0.05 无预测框 |
| `CLAUDE.md` 是 `Invoke-WebRequest` 序列化输出而非完整 Markdown | 1 | 保持用户文件原样，不提交；按可见的谨慎原则执行并把实际 Phase 6 约束写入规划文件 |
| 使用 `Start-Process` 重启本地后端被安全策略拦截 | 1 | 只停止已确认的本地 PID，改用 detached Python 子进程恢复 8000 端口并验证健康接口 |
| PowerShell `Get-NetTCPConnection` 不接受端口数组 | 1 | 改用逐端口 HTTP 探测和单端口查询，未影响服务状态 |
| 在 `web` 工作目录读取 `web/package.json` | 1 | 纠正为当前目录的 `package.json`，随后 lint/build/test 均通过 |
| Phase 7 GitHub push 与只读 `git ls-remote` 遇到 HTTPS 连接重置/不可达 | 2 | 停止重复网络尝试；本地 Phase 7 commit 完整保留，网络恢复后 fast-forward 推送 |

## Notes

- 2026-08-07 本次恢复已确认当前 `Next Step`（填写类 13 人工复核并运行终结器）不需要服务器；第二轮模型推理与校准才需要 RTX 5090 服务器。
- 用户已确认类 13 复核建议；`review.csv` 已写入 138 条接受、4 条带理由拒绝及 9 条必要备注，严格终结得到 69 tune + 69 frozen，且 `calibration_eligible=true`。
- 2026-08-07 终结后探测旧 AutoDL 地址：DNS 解析到 `106.38.204.136`，但端口 `10373` 的 TCP 测试失败；未执行任何远程写入或 frozen 评测，等待用户开机或提供新地址。
- 服务器恢复后已同步终结数据和六个校准/审计工具；类 10+类 13 最终合并清单为 101 tune（32+69）和 85 frozen（16+69），候选阶段的 102/88 不再作为最终规模。
- 第二轮有效报告为 `artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json`：101 tune 上 3,888 个候选中 36 个通过 tune 门，选中 `background_threshold=0.9`、`score_mode=keep`、temperature10/13=`1.25/0.75`、threshold10/13=`0.15/0.15`；85 frozen 上类 10 mAP50-95 从 baseline `0.387952` 变为 `0.363993`，类 13 仍为 `0.0`，`frozen_acceptable=false`，决策 `keep_current_main_model`。
- 首次未映射标签的 `second-round-calibration.json` 只作为诊断记录；有效 v2 报告使用官方类别映射。第一轮报告使用 214 tune/833 official frozen，与本轮 101/85 独立数据不可作直接数值排名。
- 当前服务器在 2026-08-07 已完成关机前同步；恢复时先确认新地址和 GPU 状态。
- 2026-08-07 用户重新开机后，旧地址 `connect.bjb2.seetacloud.com:10373` 已恢复可用；RTX 5090 空闲、项目盘剩余 43G。
- 服务器类 10 的 48 张图片与标签已逐项确认存在；主模型和 crop 专家哈希与关机检查点一致。
- 公开仓库：`https://github.com/genghailong8-maker/crop-pest-multimodel-system`
- 草稿 PR：`https://github.com/genghailong8-maker/crop-pest-multimodel-system/pull/1`
- 关机检查点：`artifacts/server/shutdown-checkpoint-20260807.json`
- 当前本地分支在 Phase 7 本地提交后领先远程 1 个 commit；`git push origin codex/publish-audits-and-calibration-plan` 因 GitHub HTTPS 连接重置未完成，网络恢复后补推本阶段 commit。
- 规划文件是后续对话的首要上下文来源；任何关键发现应写入文件，而不是只保留在聊天中。
- 2026-08-10 Phase 5 恢复与收尾：SSH `connect.bjb2.seetacloud.com:10373` 已重新可用，RTX 5090 当前约 729 MiB 显存占用；远程推理服务已以 `shadow` 启动，三份模型均已加载且 SHA-256 与关机检查点一致。网页真实图片 E2E、准确率/延迟/吞吐/显存/模型大小测量及全量监控/配置/指标/权重固化均已完成；证据清单为 `artifacts/server/phase5-full-evidence-20260810.json`，`active` 仍禁止，下一步进入 Phase 6。

## Phase 7 Completion — 2026-08-10

- 比赛材料已固化：`docs/competition/architecture-and-innovation.md`、`demo-runbook.md`、`reproducibility-checklist.md`、`presentation-outline.md`、`submission-package.md`；README 已提供入口和复现命令。
- 演示流程覆盖本机后端、网页、远程推理隧道、知识/复核展示、训练监控，以及后端不可达、模型不可用、远程超时时的安全降级。真实识别仍以 Phase 5 已留存的浏览器 E2E 证据为准，当前 runtime 复核再次确认推理服务 16 类、三模型加载、shadow 路由。
- `scripts/final_repro_check.py --require-services` 通过：必需文件 20/20、知识契约 16 类/4 来源、Phase 5 证据与 16 类/3,321/833/101/85 口径一致、active 禁止、公开边界无禁用跟踪文件、后端/知识接口/推理隧道/网页均可达。
- 回归结果：backend `9 passed`（1 个既有 Starlette 弃用警告）；web `npm test` 通过（构建 + 3 路由渲染）；web lint `0 errors`、3 个既有 `<img>` warnings；相关 Python `py_compile` 和 `git diff --check` 通过。
- 生成的复现 JSON 保存在被忽略的 `artifacts/release/` 下，作为本机运行证据，不进入公开提交；拟提交范围仅包含代码、材料、规划和可公开元数据。用户未跟踪的 `CLAUDE.md` 仍不修改、不暂存。
- Git 提交已创建（本阶段本地 commit，推送待网络恢复）；首次 push 与随后一次 `git ls-remote` 均因 `github.com:443` 连接失败/重置停止重试，未发生远端部分写入。

## Phase 9.11 弱类 8/10/13/15 混淆与专家 shadow 专项验证（2026-08-12，专项完成）

> 本子阶段只回答“弱类错误是什么、数据是否足够干净独立、现有专家是否真实改善”。官方 833 张冻结集只用于一次性比较；专家继续以 `shadow` 运行，不修改主模型输出。任何冻结门失败都保持当前线上配置。

- [x] 在官方 833 张冻结集上统一统计类 8、10、13、15 的真实类别、误报、漏检、低 IoU 和互相混淆关系，并区分“漏检问题”和“已检出后分类问题”。
- [x] 核验允许训练数据、内部开发验证、类 10/13 独立 tune/frozen 的数量、来源、标签质量、原图哈希交叉和官方冻结集隔离；记录类 8/15 当前没有独立专家冻结集的事实。
- [x] 复用现有类 10 检测专家与类 10/13 crop 专家，在同一冻结样本上生成 shadow 支持证据；对比主模型基线、shadow 保持主结果和候选重排结果，记录总体及 16 类指标、延迟和候选覆盖率。
- [x] 晋级门：弱类指标提升、总体 mAP50-95 不下降、16 类任一非目标类别不下降超过预设容差、独立 frozen 不下降、专家延迟与显存可接受；本轮门失败，保持 `shadow`，不启用 `active`。
- [x] 生成专项证据文件并更新 `findings.md`、`progress.md`；完成后回到 9.7–9.8 用户本机验收，不提前进入 9.9。

**9.11 修改前假设与成功标准**

- 当前服务器仍运行与健康检查中 SHA-256 一致的主模型、类 10 检测专家和类 10/13 crop 专家；若不一致，先停止评测并记录。
- 现有脚本优先；只有现有输出不能覆盖四类混淆或全 16 类非回归时，才增加最小只读评测脚本。
- 成功不等于“专家产生了支持分数”，而是必须有冻结集可复核的净收益；没有净收益时明确结论为“不上线”。

**9.11 实际结果与停止条件（2026-08-12）**

- 官方冻结集 833 张全部请求成功，四类 GT 框为 8/10/13/15=`98/87/89/83`；主要互相混淆为 8↔15（15/13 个框）和 10↔13（18/18 个框），另有类 8 漏检 18、类 10 漏检 10、类 13 漏检 9、类 15 漏检 4。
- 统一数据 4,490 张通过 OpenCV 逐图审计，训练/内部验证/专家 tune-frozen/官方冻结之间 SHA-256 交叉均为 0；官方冻结集内部存在 3 组重复内容哈希（833 张文件、830 个唯一 SHA），已写入证据作为评测局限。
- 类 10/13 独立校准清单为 101 tune、85 frozen；类 8/15 没有独立专家 frozen 集，不能据此声称四类专家均已具备上线数据条件。
- 线上 observed routing=`shadow`、`reclassify=false`，833/833 成功；主模型与 shadow_keep 输出完全相同。当前 active 规则离线反事实的同代码对照为 mAP50-95 `0.505247→0.503916`、弱类均值 `0.309752→0.304430`，类 10 `-0.002504`、类 13 `-0.018787`，晋级门失败。
- 专项证据：`artifacts/server/phase9-weak-classes-audit-20260812.json`、`artifacts/server/phase9-shadow-route-20260812.json`、`artifacts/server/phase9-weak-classes-shadow-evidence-20260812.json`。结论：保持当前主模型与专家 `shadow`，不启用 `active`，不进入额外重训或上线切换。

## Phase 9.7–9.8 本机真实链路测试记录 — 2026-08-13

**测试前假设与边界**

- 服务器 GPU 已恢复，使用现有主模型和现有 Qwen3-VL 服务；本轮不重训、不切换模型、不启用专家 `active`，不修改业务代码。
- 只使用项目已有样本；本轮新建病例均在测试完成后标记 `is_test=true`，不污染普通用户历史。
- 测试目标是确认真实链路和产品边界，不把自动化通过结果直接等同于“满分”或“用户验收通过”。

**本次实际结果**

- 服务恢复并保持在线：远程 detector PID `4842`、Qwen3-VL PID `3904`，本机 SSH 双隧道 PID `16716`；`3000/8000/8870/8890` 均健康，detector 路由仍为 `shadow`。
- 当前线上视觉主模型仍为 `official-plus-public-weak-v1-e120-b64`；类 10 检测专家和类 10/13 crop 专家已加载但不覆盖主模型。
- 正常有目标样本：上传→检测→两阶段多模态分析→保存→报告闭环通过；检测到类 10“盲蝽科”，置信度约 `0.9437`，自动状态 `conclusive`，多模态协议 `phase9-multimodal-v2`，严重度 `low`，一次完整分析约 `4.53s`，报告生成且包含 5 个来源和安全说明。
- 无目标样本：后端正确返回 `no_supported_target`、高风险、提示“无法可靠判断/请补拍”，并保留“仅重试综合分析”入口；但详情页标题仍优先展示多模态独立判断出的具体类别（例如“豆芫菁”），与“未发现系统支持目标”形成误导性不一致，记为 P1 产品/安全问题。
- detector 不可用：病例仍保存，返回 `service_unavailable`，检测数为 0，提示识别服务暂不可用；恢复 detector 后可重试识别。
- Qwen3-VL 不可用：检测结果和病例仍保留，但当前分析接口返回 HTTP `502`，不是结构化的用户态 `service_unavailable`；恢复 VLM 后仅重试分析成功，病例转为 `analyzed`，无需重新上传，记为 P1/P2 降级体验问题。
- 历史、趋势、报告、刷新和 FastAPI 重启持久化通过；SQLite `integrity_check=ok`，当前数据库 29 条记录全部为测试记录，普通历史/趋势为 0，管理区仍可追溯。
- 普通导航不显示管理入口；`/admin`、兼容的 `/training` 和 `/review` 页面可访问。390×844 视口下首页上传入口存在，检测到 17 个可聚焦元素，键盘焦点有可见轮廓；这属于响应式静态检查，不替代用户在 Chrome/Edge 中的完整手工验收。
- 自动回归：后端 `24 passed`；前端 build 和 6 个 render tests 通过；lint `0 errors`、5 个既有 `<img>` 警告；`git diff --check` 无差异错误（仅有 Windows 换行提示）。

**当前停止条件**

- Phase 9 仍保持 `in_progress`，不能宣称完全满足满分要求；Phase 9.9 最终视觉重构不启动。
- 待修 P1/P2：无目标结果页必须统一显示“无法可靠判断”，不能把多模态候选作为主诊断；VLM/检测器故障应返回并展示结构化不可用状态和重试提示，而不是仅暴露 HTTP 502。
- 待用户完成：当前电脑 Chrome、Edge 的真实上传、正常/无目标/低质量/冲突/失败重试、历史趋势报告和重启后使用；用户反馈前不关闭 Phase 9。

## 两项问题最小范围修复 — 2026-08-13

**修改前假设**

- 不训练类 8、15 或其他新的专家模型，不改变类 10/13 专家的 `shadow` 路由，不替换当前线上主模型。
- 普通用户只把 `resolution_status=conclusive` 的结果作为可参考诊断；`retake_required`、`no_supported_target`、`service_unavailable` 均不显示未经确认的具体病虫害作为主诊断。
- Qwen3-VL 未配置、网络失败、超时或协议解析失败均属于“综合分析暂时不可用”；病例、原图和已有检测框必须保留，分析接口采用结构化 HTTP 200 返回。
- 技术证据仍可在折叠区查看，但必须明确“未确认，不作为最终诊断”；管理端继续保留原始候选名称。

**根因与最小修改范围**

- 无目标误导来自普通页面直接使用 `analysis.primary_diagnosis` 作为标题；统一用户标题助手并在首页、详情、历史、报告复用。
- 多模态故障误导来自后端仅处理未配置异常，HTTP/解析异常直接返回 502；统一转换为已保存病例的 `multimodal_unavailable/service_unavailable` 状态。
- 直接相关文件限定为 `backend/app/main.py`、普通用户页面及 API 类型助手、后端/前端相关测试和本阶段记录，不修改数据库、训练和模型服务。

**验收标准**

- 非 `conclusive` 的普通页面主标题统一为无法判断、需补拍或服务不可用，不显示 Qwen3-VL 候选作为确认诊断，不展示对应病虫害防治建议。
- Qwen3-VL 异常时分析接口 HTTP 200，返回结构化状态、用户提示和仅重试分析动作；检测框和病例仍可读取。
- 服务恢复后仅重试分析成功；正常 `conclusive` 病例展示不退化；后端 pytest、前端 build/render/lint、浏览器回归和 `git diff --check` 通过。

**实施结果 — 2026-08-13**

- [x] 普通用户标题已统一按 `resolution_status` 判断；无目标真实病例首页、详情和报告均显示“无法可靠判断”，不再显示 Qwen3-VL 候选作为主诊断。
- [x] 非 `conclusive` 详情不再展示具体病虫害的症状、危害和防治方向，技术证据明确标注“未确认，不作为最终诊断”。
- [x] 多模态未配置、HTTP/超时/协议解析异常统一保存为 `multimodal_unavailable`，返回 `service_unavailable` 和结构化 HTTP 200；风险强制为 `high`，严重度为 `unknown`，避免沿用旧分析结论。
- [x] Qwen3-VL 不可用真实回归通过：页面显示“暂时无法完成判断”，病例保留并提供“仅重试综合分析”；恢复双隧道后仅重试分析返回 `analyzed/conclusive`。
- [x] 后端 25 passed；前端 build/render 6 passed；lint 0 errors、5 个既有 `<img>` warnings；语法检查和 `git diff --check` 通过。
- [x] 结束时本机 3000/8000/8870/8890 全部健康，detector 仍为 remote/shadow，Qwen3-VL 在线；本轮新建无目标病例已标记 `is_test=true`。

**本轮错误记录**

- 浏览器文件选择器第一次调用顺序错误、数据库内联 Python 查询两次被 PowerShell 引号解析；均为工具调用错误，未提交额外病例/未破坏数据，随后改用正确文件选择器顺序和 PowerShell 管道完成验证。
- 2026-08-14：Windows Store `python.exe` 占位程序运行 `session-catchup.py` 退出 1 且无输出；改用工作区依赖 Python 后成功退出，未发现未同步上下文。
- 2026-08-14：恢复检查中的 PowerShell 循环块直接接管道导致解析错误；拆分命令后完成 Git、服务和远程端口检查，未产生副作用。
- 2026-08-14：旧 GPU 主机 TCP `10373` 不可达，本机 `3000/8870/8890` 也未监听；未重试旧服务器、未启动模型任务，等待用户恢复主机或提供新地址。

## Same-Frozen-Set Detector Comparison — 2026-08-13

- [x] 在同一份官方 833 张冻结验证集上，一次性评测昨天六模型实验中的 YOLO26n 权重与当前在线主模型。
- [x] 评测期间关闭专家影响和 Qwen3-VL：直接调用 Ultralytics detector，不经过 HTTP shadow 路由、不调用多模态分析。
- [x] 评测完成后恢复 detector、Qwen3-VL、8870/8890 隧道及本机服务，并通过健康检查。
- [x] 保存两份原始指标、权重 SHA-256、冻结清单 SHA-256、评测参数和可复现命令；不修改线上模型、不调参、不重训。

### Assumptions and acceptance gates

- “昨天的六模型”本次取其中的 `phase9-yolo26n-e120-b32/weights/best.pt`；当前主模型取 `official-plus-public-weak-v1-e120-b64/weights/best.pt`。
- 两个权重必须使用同一个 `dataset-frozen-eval.yaml`、同一 `imgsz=640`、同一 Ultralytics 评测逻辑；batch 仅影响吞吐，不改变评测对象。
- 评测前后记录服务 PID、GPU 显存和健康状态；任何权重或冻结清单 SHA 不匹配则停止，不生成排名结论。
- 成功标准：两份评测 JSON 均包含总体指标、16 类指标、混淆矩阵、速度、权重 SHA 和数据清单 SHA；若服务恢复失败，保持任务未完成并记录错误。

### Results — 2026-08-13

- [x] 冻结清单共 833 张，SHA-256 `2e7f691de609c4a310549d1ac6fb98e99eedcec18160588729f8e1e38fef60b8`；两份结果均为 17×17 混淆矩阵、16 类逐类指标。
- [x] 昨天 YOLO26n：Precision `0.829715`、Recall `0.756240`、mAP50 `0.806850`、mAP50-95 `0.519087`。
- [x] 当前主模型：Precision `0.831993`、Recall `0.778327`、mAP50 `0.825132`、mAP50-95 `0.546065`。
- [x] 当前主模型相对 YOLO26n：Precision `+0.002278`、Recall `+0.022087`、mAP50 `+0.018282`、mAP50-95 `+0.026978`；16 类中 11 类提升、5 类下降。
- [x] 类 8 mAP50-95 下降 `0.054795`，类 10 下降 `0.014842`；类 13 下降 `0.003090`、类 15 下降 `0.000805`，其余主要提升。该结果支持保留当前主模型，但不支持宣称所有弱类均改善。
- [x] 评测未调用专家或 Qwen3-VL；评测后 detector PID `7017`、Qwen3-VL PID `7059` 已恢复，8870/8890 隧道以及本机 8000/3000 均返回 200，detector 仍为 `shadow/reclassify=false`。
- [x] 原始证据：`artifacts/server/phase9-same-frozen-eval-20260813-yolo26n.json`、`artifacts/server/phase9-same-frozen-eval-20260813-current-main.json`、`artifacts/server/phase9-same-frozen-eval-20260813-dataset-frozen-eval.yaml`。

### Errors recorded

- SSH 首次未显式指定项目私钥，返回 `Permission denied`；改用现有 `codex_autodl_nongxin_2026` 私钥后连接恢复。
- 首次长评测命令超过本地等待上限；确认远程进程已结束并生成第一份结果后，改用后台评测、日志和产物轮询完成第二份评测。
- 远程摘要脚本曾被 PowerShell 展开 Bash/Python 引号；未影响结果文件，改用 `scp` 原样回拷并在本机解析。

## Remaining Five Detector Comparison — 2026-08-13

- [ ] 在同一份官方 833 张冻结验证集上评测昨天六模型中的另外五个权重：YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su。
- [ ] 所有评测统一使用服务器 `phase9-unified-v4/dataset-frozen-eval.yaml`、`imgsz=640`、`batch=32`、`workers=4` 和 `training/evaluate_detector.py`。
- [ ] 评测期间停止远程 detector/Qwen3-VL，直接运行 Ultralytics 权重评测；不经过 8870 HTTP、不加载专家、不调用多模态、不调参、不重训。
- [ ] 完成后恢复 detector、Qwen3-VL、本机 8870/8890 隧道和 3000/8000 服务，核对原主模型 SHA 与 `shadow/reclassify=false`。

### Assumptions and gates

- “另外五个”明确指六模型搜索中除 YOLO26n 外的五个候选，不包含当前线上主模型的重复评测。
- 只有五份结果均使用同一冻结清单且包含 16 类指标、17×17 混淆矩阵、速度、权重 SHA 时，才汇总排名；任一权重缺失或 SHA 不匹配则停止并记录。
- 评测期间线上识别短暂不可用属于预期；历史、趋势和报告不受影响。服务恢复失败时不宣称本阶段完成。

### Results — 2026-08-13

- [x] 五份权重均存在且 SHA 已核对；统一冻结清单为 833 行，SHA-256 `2e7f691de609c4a310549d1ac6fb98e99eedcec18160588729f8e1e38fef60b8`。
- [x] YOLO26s：Precision `0.834140`、Recall `0.772209`、mAP50 `0.820916`、mAP50-95 `0.535458`。
- [x] YOLO11s：Precision `0.811513`、Recall `0.781263`、mAP50 `0.822261`、mAP50-95 `0.534951`。
- [x] YOLO12s：Precision `0.805109`、Recall `0.807891`、mAP50 `0.822365`、mAP50-95 `0.522652`。
- [x] YOLOv8s：Precision `0.824542`、Recall `0.795836`、mAP50 `0.818483`、mAP50-95 `0.530064`。
- [x] YOLOv5su：Precision `0.807224`、Recall `0.769482`、mAP50 `0.810575`、mAP50-95 `0.519336`。
- [x] 按同一 `0.7*mAP50-95 + 0.3*mean(class 8,10,13,15 mAP50-95)` 计算冻结集对照分，排序为：当前主模型 `0.487785`、YOLO26s `0.483844`、YOLO11s `0.483537`、YOLO26n `0.474415`、YOLOv8s `0.473773`、YOLO12s `0.466811`、YOLOv5su `0.464188`。该排序只用于本次同口径比较，不改变原六模型开发集选型记录。
- [x] 五份结果均为 16 类逐类指标和 17×17 混淆矩阵；评测未调用专家或 Qwen3-VL。
- [x] detector PID `8927`、Qwen3-VL PID `8969` 已恢复，GPU 约 `22110 MiB`；本机 3000/8000/8870/8890 全部返回 200，线上主模型 SHA 一致，路由仍为 `shadow/reclassify=false`。
- [x] 原始证据：`artifacts/server/phase9-same-frozen-eval-20260813-yolo26s.json`、`yolo11s.json`、`yolo12s.json`、`yolov8s.json`、`yolov5su.json`；汇总证据为 `artifacts/server/phase9-same-frozen-eval-20260813-five-model-summary.json`。

### Errors recorded

- 批量远程 SHA 命令第一次因 PowerShell/Bash 引号冲突失败；改为五个短命令逐个核对，全部通过。
- 五次前台 SSH 评测等待均超过本地命令上限，但每次随后都确认对应 JSON 已生成；未重复评测，避免重复消耗 GPU。
- 一次 JavaScript 工具调用和一次 PowerShell 汇总命令有语法错误，均发生在结果生成之后；改为分开汇总与健康检查，未影响评测产物。

## 4,490 全量训练与 833 冻结集统一比较 — 2026-08-13

- **本轮目标：** 使用统一清洗后的 4,490 张 `final-train.txt` 训练 YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su；统一 120 轮、640、batch 64、seed `20260729`、官方预训练权重，训练期间不使用验证集，训练完成后统一使用官方 833 张冻结集各评测一次。
- **当前主模型对照：** 当前线上主模型也必须使用同一冻结清单、640、batch 64 和 `training/evaluate_detector.py` 重新评测；本轮不启用专家、不调用 Qwen3-VL、不经过 detector HTTP。
- **Karpathy 假设与最小范围：** 复用 `training/train_phase9_finalist.py` 和 `training/evaluate_detector.py`；仅在必要时新增全量训练/冻结评测数据契约、重复检查和汇总证据，不修改业务链路、数据库、UI、冻结清单或线上模型配置。
- **训练选择假设：** 因训练期间不使用验证集，不使用 `best.pt` 或早停选择，六个模型统一使用完成 120 轮后的 `last.pt`；严格保持 batch 64，单模型 OOM 时停止该模型并记录，不自动降为 batch 32。
- **比较规则：** 先比较总体 mAP50-95；差值不超过 `0.005` 时比较类 8、10、13、15 平均 mAP50-95，再比较 Recall，最后比较延迟和显存。候选即使排名第一，也只形成替换建议，不自动上线。

### 训练前独立性门

- [x] 文件级 SHA-256：训练 4,490 条、路径唯一、文件缺失 0；冻结 833 条、路径唯一、文件缺失 0；跨集合精确 SHA 交集 0。
- [x] 已记录限制：官方冻结集内部为 833 个文件、830 个唯一文件 SHA，存在 3 组重复内容；这不构成训练集与冻结集交叉重复，但会在结果中作为冻结评测限制保留。
- [ ] 训练前补充解码像素 SHA-256 和 16×16 感知哈希；跨集合存在完全相同像素内容时阻止训练；感知哈希接近项输出清单供人工审查。
- [ ] 保存独立性检查 JSON，记录清单 SHA、路径计数、文件 SHA、像素 SHA、感知哈希、重复组和阻止/通过结论。

### 执行阶段

- [ ] 记录并停止远程 detector、Qwen3-VL，确认 GPU 显存释放；不删除既有运行目录或权重。
- [ ] 依次训练六个独立运行目录：`phase9-fulltrain-b64-yolo26n`、`yolo26s`、`yolo11s`、`yolo12s`、`yolov8s`、`yolov5su`；每个记录 PID、配置、日志、120/120 状态、`last.pt` SHA 和失败原因。
- [ ] 对六个 `last.pt` 与当前主模型共七个权重，统一在官方 833 张冻结集上使用 640/batch64/workers4 评测；保存 Precision、Recall、mAP50、mAP50-95、16 类指标、17×17 混淆矩阵、权重 SHA、清单 SHA、速度和显存。
- [ ] 生成统一汇总表、排名、相对当前主模型差值和替换建议；明确区分本轮新训练结果与此前 batch32/`best.pt` 结果。
- [ ] 评测后恢复 detector、Qwen3-VL、8870/8890 隧道及本机 3000/8000，确认线上仍为当前主模型、`routing.mode=shadow`、`reclassify=false`。

### 本轮停止条件与错误记录

- 任何跨集合重复像素、关键清单缺失、权重 SHA 不一致、训练配置偏离或服务恢复失败，均停止对应阶段并记录，不生成不完整的最终排名。
- OOM 只停止当前模型，保留日志并继续前先检查 GPU/PID；不得偷偷降低 batch。
- 全部证据和服务恢复通过后，本子阶段才标记完成；不因新模型排名自动进入上线或 UI 重构。

### 独立性审计阻断 — 2026-08-13

- [x] 文件 SHA-256 与解码像素 SHA-256 均未发现训练/冻结跨集合交集；训练 4,490 条、冻结清单 833 条均无解码错误；冻结集内部保留 3 组像素重复记录。
- [x] 通过 23 页复核图人工检查 91 个跨集合 pHash 配对（48 个精确 pHash 实际配对、43 个近似配对）。多组确认是同一张原始照片的重新编码、轻微裁剪或同一场景变体，不是可忽略的普通类别相似。
- [x] 发现 74 张唯一训练图片属于视觉重复候选：PlantDoc 51、SciDB 3、官方训练集 20；原 4,490 张若直接训练会使官方 833 张冻结集评测存在泄漏风险。
- **当前状态：blocked_pending_user_decision。** 按 Karpathy 原则不擅自修改用户指定的 4,490 张训练规模，也不在泄漏风险下启动训练。
- **最小修复方案：** 保持官方 833 张冻结集和原始 `final-train.txt` 不变，另生成排除 74 张后的独立训练清单（预计 4,416 张）及对应 YAML；重新执行像素/pHash 审计通过后，再依照原定 120/640/batch64/seed20260729 训练六个模型。
- **当前服务：** detector、Qwen3-VL 未停止，GPU 仍由在线服务占用；本轮尚未训练、尚未修改线上主模型。

### 用户授权与继续执行 — 2026-08-13

- [x] 用户已明确允许使用排除 74 张视觉重复候选后的 4,416 张独立训练集继续。
- [ ] 保留原始 4,490 张 `final-train.txt` 和官方 833 张冻结清单不变；新增独立清单、数据 YAML、排除报告和二次审计报告。
- [ ] 二次审计必须确认训练清单 4,416 条、无缺失/解码错误、与官方冻结集文件 SHA/像素 SHA/pHash 交集均为 0，且 pHash 距离 `<=8` 的近似配对为 0；官方冻结集内部 3 组重复继续仅作限制记录。
- [ ] 二次审计通过后，记录 detector/Qwen3-VL PID 和 GPU 显存，停止两项服务；六个模型严格按 120/640/batch64/seed20260729/`val=False` 依次训练，使用 `last.pt`。

### 二次独立性门通过 — 2026-08-13

- [x] 派生训练清单 4,416 条，全部存在且成功解码；官方冻结清单 833 条，全部存在且成功解码。
- [x] 训练/冻结文件 SHA 交集 0、解码像素 SHA 交集 0、精确 pHash 交集 0、pHash 距离 `<=8` 近似配对 0；训练集内部像素重复 0；冻结集内部 3 组重复保留为评测限制。
- [x] 训练前独立性 gate `pass`，允许进入 GPU 停服和六模型训练。
- **证据：** `artifacts/server/phase9-independent-v1-audit-20260813.json`；派生清单服务器路径为 `data/experiments/phase9-independent-v1/train-independent-v1.txt`，YAML 为 `dataset-independent-frozen-eval.yaml`。

### 服务停用与训练启动 — 2026-08-13

- [x] 停服前记录：远程 detector PID `8927`、Qwen3-VL PID `8969`；RTX 5090 `32607 MiB`，停服前使用 `22110 MiB`。
- [x] 已停止 detector/Qwen3-VL，停服后 GPU 使用降至 `0 MiB`；不删除已有运行目录、权重或数据。
- [ ] 依次执行六个模型训练；每个严格 `epochs=120`、`imgsz=640`、`batch=64`、`seed=20260729`、`val=False`、`patience=0`、官方预训练权重、独立运行目录，训练完成使用 `last.pt`。
- [ ] 训练期间不启动验证、不读取官方冻结集；每个模型完成后保存训练记录和权重 SHA。

### 训练配置偏差 — 2026-08-13

- **发现：** 首次 YOLO26n 运行虽传入 `val=False`，但数据 YAML 同时包含 `val=official-frozen-val.txt`，Ultralytics 启动阶段仍扫描了该冻结集标签缓存。
- **处理：** 该运行只到约第 5/120 轮，不计入结果；先停止并保留日志作为错误证据，改用不包含 `val` 字段的训练专用 YAML，重新启动六模型。
- **验收修正：** 训练日志不得出现官方冻结集扫描；训练结束后才使用含 `val` 的冻结评测 YAML 调用 `evaluate_detector.py`。
- **训练契约：** 派生清单生成器输出 `dataset-independent-train-only.yaml`（`train`/`val` 均指向 4,416 张独立训练清单，`val` 仅为 Ultralytics 必需占位），冻结评测继续使用 `dataset-independent-frozen-eval.yaml`。

### 训练 YAML 兼容性错误 — 2026-08-13

- **错误：** Ultralytics 启动前强制要求数据 YAML 存在 `val:` 字段；仅含 `train`/`names` 的训练 YAML 直接返回 `'val:' key missing`，该次未启动训练、GPU 仍为 0 MiB。
- **最小修正：** `val:` 改为指向 4,416 张独立训练清单作为框架必需占位；训练调用仍固定 `val=False`、`patience=0`，不计算验证指标；官方 833 张冻结清单只保留在训练后评测 YAML 中。
- **验收：** 训练日志不得扫描官方冻结路径；训练记录明确 `frozen_validation_used_during_training=false`；最终评测仍单独使用官方 833 张 YAML。

### 逐模型训练后即时评测调整 — 2026-08-13

- **用户确认：** 不必等待六个模型全部训练完成；任一模型完成 120 轮训练并生成 `last.pt` 后，立即使用同一官方 833 张冻结集、`640` 输入、`batch=64` 和统一评测脚本进行一次评测。
- **执行顺序：** `YOLO26n → YOLO26s → YOLO11s → YOLO12s → YOLOv8s → YOLOv5su`，每次只运行一个训练任务；模型完成后先保存训练记录和权重 SHA，再启动冻结评测，评测完成后才进入下一个模型。
- **评测隔离：** 评测直接加载权重，不调用 detector HTTP、专家模型或 Qwen3-VL；每个模型单独保存总体指标、16 类指标、混淆矩阵、速度、显存、评测配置和数据清单哈希。
- **比较基线：** 当前主模型也使用完全相同的 833 张冻结集和评测配置单独评测一次；不因中途结果自动切换线上主模型。
- **失败门：** 严格保持 `batch=64`；OOM、训练未完成或评测失败只记录该模型状态和日志，不自动降 batch、不伪造指标，并在 GPU 清理后继续后续模型。
- **恢复门：** 全部可执行模型完成即时评测后，恢复 detector、Qwen3-VL、8870/8890 隧道和本地前后端，核验线上仍为当前主模型、`routing.mode=shadow`、`reclassify=false`。

### 用户中止剩余训练并冻结线上模型 — 2026-08-13

- **用户决定：** 立即停止所有候选模型训练；当前线上主模型继续作为视觉检测模型，不做权重切换、专家晋级或路由变更。
- **已执行：** 终止 YOLOv5su 训练及串行编排器；YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s 已完成的独立冻结评测 JSON 和权重保留；YOLOv5su 中途停止，不纳入最终比较。
- **安全门：** 不删除任何训练产物，不修改官方冻结集，不加载候选权重到线上，不启用专家 `active`，不调用多模态模型参与权重比较。
- **验证：** 远程无 `train_phase9_finalist.py` 和串行编排器进程，GPU 显存为 `0 MiB`；恢复识别服务时只使用现有主模型，保持 `routing.mode=shadow`、`reclassify=false`。
### 最终收尾：停止全部训练并保留当前主模型 — 2026-08-13

- [x] 按用户最终决定停止全部候选模型训练；YOLOv5su 在训练中主动终止，返回 `rc=143`，不计入完成模型或最终排名。
- [x] 已完成并保存 YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s 以及当前主模型在同一官方 833 张冻结集、`imgsz=640`、`batch=64`、同一评测脚本下的独立 JSON；未调用专家和 Qwen3-VL。
- [x] 不加载候选权重、不切换线上主模型、不启用专家 `active`，当前视觉主模型 SHA 保持 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`。
- [x] 已恢复原有 detector、Qwen3-VL、8870/8890 本机隧道、FastAPI 和前端；健康检查通过，路由保持 `shadow/reclassify=false`。
- [x] 本轮相关评测 JSON 已保存到本机 `artifacts/server/phase9-fulltrain-eval-20260813-*.json`；不删除训练目录、权重、日志或数据清单。
- [ ] Phase 9 不因本轮候选评测而标记完成；后续仅在用户人工测试反馈或明确授权后继续。

### 用户确认当前模型并进入人工功能测试 — 2026-08-13

- [x] 当前视觉主模型暂定继续使用线上原主模型，SHA 保持 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`。
- [x] 当前多模态模型暂定继续使用已接入的 Qwen3-VL，不更换模型、不重新训练、不改变分析协议。
- [x] 五个候选模型仅作为对比证据保存，不加载到线上，不改变专家 `shadow` 路由。
- [ ] 下一阶段由用户集中测试上传、检测、多模态分析、病例历史、报告和异常恢复等系统功能；问题按用户反馈逐项记录和整改。
- [ ] 用户功能测试问题处理完成并确认可用后，才启动最终 UI 界面重构；本阶段不提前进行 UI 重构。

### 实验室服务器部署可行性评估 — 2026-08-14

- [x] 读取实验室服务器只读检查结果：CentOS 7、kernel 3.10、glibc 2.17、4×Tesla K80、125 GiB RAM、根分区 97%。
- [x] 核对项目实际依赖：后端 Python >=3.11；前端 Node >=22.13；detector 使用 Ultralytics；多模态服务固定 vLLM 0.26.0 + Qwen3-VL-8B。
- [x] 对照微软官方 Remote-SSH 前置条件，确定 VS Code Remote Server 的升级路径。
- [x] 对照现有 RTX 5090/CUDA 12.8 运行证据，判定 K80 是否可承载 detector 与 Qwen3-VL，并形成最低升级清单。
- **Status:** complete（只读评估，不修改服务器）
- **结论：** 仅为 VS Code 应重装/迁移到满足 kernel 4.18、glibc 2.28、libstdc++ 3.4.25 的受支持系统；完整保留当前系统则还必须更换为现代、建议 >=32 GiB 显存的 GPU，并配套 CUDA 12.8 驱动、Python 3.11+、Node 22.13+。K80 只适合保留为旧任务卡或让检测链路改走 CPU，不能承载当前 vLLM/Qwen3-VL。
# Active Implementation: 双服务器独立部署（2026-08-14）

## Goal

在不重装、不移动或删除实验室服务器现有数据的前提下，把 CPU 完整版部署到 `/data/ghl`，并为实验室 CPU 实例与原 GPU 实例实现 Admin 全局手动切换、实例归属和独立报告快照。

## Assumptions and constraints

- 优先保持 CentOS 7，通过容器/静态前端兼容门后再部署；兼容门失败才进入备份后重装方案。
- `/data` 不格式化、不重新分区；根盘已有内容不清理。
- 当前不启用 GPU 服务器，先完成本地代码和实验室 CPU 单机链路。
- 保留现有主模型和专家 `shadow` 策略，不因部署工作改变模型权重或准确率策略。
- 工作区已有修改均视为用户资产，不回滚、不覆盖无关内容。

## Implementation phases

- [x] Phase A — 核对现有接口、数据结构、测试与服务器 SSH 状态；记录兼容门
- [x] Phase B — 实现 Admin 认证、实例状态/切换、健康检查和审计日志
- [x] Phase C — 实现实例归属路由与远端 GPU 后端代理，确保病例不跨服务器
- [x] Phase D — 实现每实例不可变 JSON 报告快照
- [x] Phase E — 修改 Admin/前端流程显示并传递实例归属
- [x] Phase F — 添加并执行 `/data/ghl` 无损部署、离线兼容检查、备份清单和服务配置；五个 CPU 版容器已构建启动
- [x] Phase G — Windows 临时中继、Admin 双向切换、CPU/GPU 新病例归属、文件/历史/报告隔离、目标离线拒绝、活动实例保持及中继恢复全部通过；最终活动实例为 `lab_cpu`，GPU 在线

## GPU 联调假设与验证门（2026-08-17）

- 复用 GPU 服务器已有 `/root/autodl-tmp/crop-pest-system` detector 权重/环境和 `/root/autodl-tmp/crop-pest-vlm` vLLM 模型/环境，不复制大模型、不训练、不改权重和 `shadow` 路由。
- 只新增 `/root/autodl-tmp/ghl/app`、`storage`、`runtime`，GPU 病例只写 GPU SQLite/图片/报告；实验室 `/data/ghl/storage` 不同步。
- GPU FastAPI、detector、VLM 仅监听 GPU 回环地址；实验室服务器通过专用 SSH key 和 `127.0.0.1:18000` 隧道访问 GPU FastAPI。
- 先验证 GPU 后端本机健康与真实病例，再建立隧道；Admin 切换必须在目标健康时成功，目标离线时拒绝且当前实例不变。
- 双向切换后分别创建测试病例，确认 `instance_id`、历史、图片和报告固定回到创建服务器；完成后活动实例切回用户指定或默认 `lab_cpu`。
- 用户已选择 Windows 临时中继：Windows 本地 `18001` SSH 转发到 GPU `8000`，并通过到实验室的反向 SSH 在实验室 loopback 建立 `18000`；实验室仅在 Docker host-gateway `172.17.0.1:18000` 增加到 loopback 的受限转发。Windows 关机、休眠、断网或脚本停止后 GPU 状态应变为离线，CPU 实例不受影响。

## Verification gates

- 后端与前端自动测试通过；两个隔离存储测试证明数据不交叉。
- 目标实例离线时切换返回失败且活动实例不变。
- 报告快照重启后保持不变，并记录实例与模型来源。
- 服务器检查只在 `/data/ghl` 创建新增内容；不删除或修改已有 `/data` 数据。

## Errors encountered

- 本轮首次并行恢复调用未返回有效输出；已拆分执行。系统 `python.exe` catch-up 仍退出 1，后续改用工作区可用 Python。

## Active UI Documentation and Critique — 2026-08-20

- [x] 恢复上轮部署上下文，确认现有工作树改动均需保留。
- [x] 完整读取 `impeccable` 的 `document` 与 `critique` 工作流，并运行一次项目上下文检查。
- [x] 扫描前端设计令牌、布局、组件与响应式规则，生成根目录 `DESIGN.md` 和 `.impeccable/design.json`。
- [x] 先完成独立的人工设计审查，再运行机械检测器与浏览器证据检查。
- [x] 汇总 Nielsen 评分、认知负荷、角色风险、优先级问题，持久化 critique 快照并交付。
- **范围：** 本轮只新增设计文档、审查快照和规划记录；不修改现有前后端界面或业务逻辑。
- **降级说明：** 当前工具面没有 `spawn_agent`，critique 将按规范顺序执行 A/B 两项评估，并在最终报告首行标注单上下文降级。
- **完成结果：** 设计健康分 25/40（Acceptable）；3 个 P1 分别为双服务器归属不可见、禁用按钮不解释缺项、CPU 长耗时无预期与恢复；快照位于 `.impeccable/critique/2026-08-20T01-36-53Z__web-app.md`。
# Active UI Implementation: 三个 P1 可用性修复（2026-08-20）

## Scope and constraints

- 只关闭三个 P1：双服务器数据归属不可见、禁用按钮不解释缺失内容、CPU 长耗时没有预期管理。
- 使用现有页面、组件、接口和技术栈；不改变双服务器路由、病例归属或模型业务逻辑。
- 公共界面使用普通表达，技术术语仅保留在技术详情、管理员页或可展开内容。
- 使用 `redesign-existing-projects` 与 `design-taste-frontend` 做保留式改造；本轮不使用 `gpt-taste`。

## Implementation phases

- [x] 核对健康接口的活动实例字段、病例状态模型和公共页面复用点。
- [x] 扩展共享页头，展示当前识别服务器并为导航补充 `aria-current`。
- [x] 为上传表单增加动态缺项说明，保留现有禁用和后端校验。
- [x] 为实验室 CPU 增加 1–2 分钟预期、尽早显示病例编号和离页提示，不伪造百分比。
- [x] 统一历史、趋势和页脚中的服务器归属文案，并提示切换服务器会改变病例列表。
- [x] 运行前端构建、页面测试、ESLint、桌面/移动检查和 Impeccable 范围审计。
- [x] 用相同 10 项启发式重新评分，与修改前 Design Health Score 25/40 对比。

## Completion

- **Status:** complete
- 三个 P1 已关闭；本地前后端验证实例保持运行，实验室服务器未在本轮部署或修改。

# Active UI Implementation: P2 可读性、图片与行动层级（2026-08-20）

## Scope and constraints

- 只处理既有审计的三个 P2，以及直接相关的触控目标、CPU 提示样式和所触及颜色令牌。
- 保留业务逻辑、双服务器架构、后端接口、现有技术栈与未提交工作树；不修改 Admin、训练监控或其 `transition: width`。
- 图片按 Blob、病例 API、定位覆盖和打印约束逐张判断，不为消除 lint 警告改变真实图片链路。

## Implementation phases

- [x] 恢复上一轮规划记录与 Impeccable Audit 基线（Design Health 32/40，Audit 14/20）。
- [x] 锁定详情/报告字号层级、原生图片策略和结果页主次行动方案。
- [x] 实施最小前端修改并更新直接相关页面测试。
- [x] 运行后端/前端回归、构建、ESLint 与 `git diff --check`。
- [x] 完成桌面、390px 移动端、横向溢出和 Impeccable 公共流程复审。

## Completion

- **Status:** complete
- 三个 P2 已关闭；直接相关的触控高度、CPU 提示边框和所触及颜色令牌 P3 已关闭。
- 公共诊断流程审计为 17/20，Design Health Score 为 35/40；训练监控 `transition: width` 与全局剩余颜色令牌化继续保留为非本轮 P3。
- 本轮仅修改前端与测试；后端代码、接口、双服务器路由和数据均未修改。
# 2026-08-20 第三阶段：公共诊断流程视觉辨识度强化

## 目标与边界

- [x] 从上一轮 Design Health 35/40、Impeccable Audit 17/20 基线恢复，不重新从零审计。
- [x] 设计方向：Operate 模式；可信、专业、克制；农业相关但不乡村化；暖白与单一绿色品牌色；DESIGN_VARIANCE=4、MOTION_INTENSITY=2~3、VISUAL_DENSITY=5。
- [x] 固定范围：首页诊断流程、诊断结果、病例详情、报告、PublicHeader 及其公共样式；不改 Admin、训练监控、后端接口、模型、数据库和双服务器逻辑。
- [x] 输出《第三阶段视觉辨识度强化方案》，覆盖诊断路径、证据语言、结果层级、服务器归属、田间采样和不采用方案。
- [x] 读取 Impeccable craft-floor 后实施最小增量前端修改，并同步必要测试。
- [x] 完成静态检查、后端/前端测试、构建、ESLint、桌面和 390px 浏览器检查、横向溢出与 reduced-motion 检查。
- [x] 依次执行 Impeccable critique、polish、audit，记录最终分数及 P0/P1/P2。

## 当前实现状态

- [x] 新增单一 `DiagnosisPath` 组件，以真实状态展示田间采样、目标定位、信息核对、证据综合、诊断结果和诊断报告。
- [x] 首页按“田间图片/田间信息”重新分组，增加真实完成计数；未增加字段或改变验证。
- [x] 核心结果重排为诊断名称、证据状态、田间严重度和当前行动；技术详情降级为折叠区域。
- [x] 综合分析统一图片观察、目标定位、田间信息和综合核对来源语义；知识库明确标记为独立知识参考。
- [x] 病例详情和报告显示病例归属，并复用诊断路径；主路径过滤后端 URL 与技术错误，原始记录保留在技术详情。
- [x] 桌面、390px、病例详情和报告浏览器实测无横向溢出，路径状态真实，主要触控目标不低于 44px。
- [x] Impeccable critique 已持久化；Assessment B 独立完成，两个 Assessment A 子代理未返回并已关闭，报告按规范标注降级。
- [x] Impeccable polish 已关闭失败路径假完成、旧 health 名称兜底和报告来源触控边界。
- [x] Impeccable audit 为 18/20；Design Health 为 36/40；P0/P1/P2 均为 0，仅保留 2 个非阻断 P3。

## 验收约束

- 诊断路径只能表达真实阶段，不显示假百分比或虚构进度。
- 普通路径不暴露 YOLO、provenance 等术语；技术详情保持可展开。
- 不新增依赖，不迁移技术栈，不增加表单字段，不改变验证与推理行为。
- 最多新增一个必要的诊断路径组件，其余优先改造现有组件。
# Phase 4：比赛展示页设计与实现（2026-08-20）

## Goal

- [x] 新增独立比赛展示入口，10 秒说明项目、30 秒说明核心创新，并清晰引导进入现有智能诊断。
- [x] 仅扩展展示页面，不修改现有诊断流程、病例、报告、双服务器逻辑、后端、模型或数据库。
- [x] 只使用可复核的项目数据和真实界面资产，不编造指标或截图。

## Plan

- [x] 恢复 planning-with-files 上下文并读取第四阶段指定技能。
- [x] 补齐 PRODUCT.md，生成 Impeccable surface concept seed，并核对真实指标和图片资产。
- [x] 输出《编程大赛比赛展示页设计方案》与 gpt-taste 设计计划。
- [x] 实现独立展示路由、展示页专用组件和样式；无必要不新增依赖。
- [x] 运行测试、build、ESLint、git diff --check 与 1280/390 浏览器验收。
- [x] 依次完成 Impeccable critique、polish、audit，并记录最终评分。

## Constraints

- gpt-taste 仅用于新展示页，不触碰稳定产品页面。
- 不部署、不提交 Git。
- 动效不劫持滚动、不伪造进度，必须支持 prefers-reduced-motion。
- 保留用户已有未提交改动，所有新增修改保持局部和可回退。

## Errors recorded

- 首次运行 Impeccable concept seed 时因缺少 `PRODUCT.md` 返回 `NO_PRODUCT_MD`；按规范先建立产品事实基线后重试。
- 本地 Vinext `start` 未正确提供构建后的 CSS/图片资源；未改动产品实现，改用同一构建产物的只读静态 QA 服务完成浏览器验收。
- 首轮 Next 图片优化路径在该运行时不可用；展示页改为带明确尺寸、加载优先级和替代文本的静态图片，真实产品截图继续 lazy load。

# UI Redesign V2：真实诊断产品重构（2026-08-20）

## Goal

- [x] 仅保留现有功能、数据逻辑、API、诊断流程、表单字段、双服务器归属、病例与模型结果，允许重写公共诊断页面 JSX、文案、CSS 和视觉结构。
- [x] 将智能诊断首页重构为图片主导的左右工作区，将结果首屏重构为“问题、风险、行动”中心，将病例详情与报告重构为诊断档案和专业报告。
- [x] 视觉方向为简约、现代、专业、农业科技；DESIGN_VARIANCE=6、MOTION_INTENSITY=4、VISUAL_DENSITY=5；不使用 gpt-taste。

## Plan

- [x] 使用 redesign-existing-projects 与 Impeccable critique 审视首页、结果状态、病例详情和报告。
- [x] 使用 Impeccable layout/typeset 输出《诊断系统 UI Redesign V2》及 ASCII Wireframe。
- [x] 读取 craft-floor 后实施 JSX/CSS/文案与组件重构，不改变后端契约或业务行为。
- [x] 完成后端测试、前端测试、production build、ESLint 与 git diff --check。
- [x] 完成 1280px、1440px、390px 浏览器验收、横向溢出、移动长度和 reduced-motion 检查。
- [x] 运行 Impeccable polish 与 audit，记录评分和 P0/P1/P2。

## Completion

- **Status:** complete（本地实现与验收完成，未部署、未提交 Git）
- Design Health Score：35/40；Impeccable Audit：17/20；本轮范围 P0/P1：0。
- 本地预览保留在 `http://localhost:3101/`，等待用户检查；实验室和 GPU 服务器均未修改。

## Constraints

- 不修改 Admin、训练监控、showcase、后端、模型、数据库或双服务器路由。
- 不新增或删除表单字段，不改变字段验证和 API 参数。
- 不部署，不提交 Git；保护工作树中用户已有改动。

## Errors recorded

- 首次将旧工具名 `shell_command` 用于当前执行环境失败；已切换到可用的 `exec_command`，后续不重复该调用。
- 首次批量打开首页、病例和报告并同时截图超过 30 秒，浏览器会话被重置；改为每次只检查一个页面并立即记录结论，不重复批量路径。
- 首次将环境变量设置、归档、趋势读取和临时文件删除合并为一个 PowerShell 命令被执行策略拒绝；改为分离归档、趋势和 apply_patch 清理步骤。

# UI Redesign V3：真实诊断产品视觉世界替换（2026-08-20）

## Goal

- [ ] 在不改变现有功能、API、数据库、模型推理、双服务器切换、病例归属和历史/报告恢复逻辑的前提下，重做公共诊断首页、结果、病例详情和报告的 JSX 视觉结构与组件语言。
- [ ] 建立“临床农业工作台 + 田间情报记录”的独立视觉系统：图片证据优先、结论分层、证据来源可扫读、服务器归属低干扰但持续可见。
- [ ] 不把 `/showcase` 当作本轮主目标；不部署、不提交 Git。

## Design decision

- Product Design 已使用真实本地首页与代码做上下文检查，并生成三套独立方向参考图。
- 采用 A「临床农业工作台」70% + B「田间情报工作区」30%；报告借用 C「科研诊断记录」的排版语法。
- 保留暖白/深农业绿/炭黑/琥珀风险语义；不使用 AI 紫蓝、玻璃拟态、霓虹、GSAP 或营销式 Hero。
- gpt-taste 仅用于方向探索；Python 随机选择已记录为 `asymmetric-workbench / Geist / field-intake+record-ledger+evidence-rail / focus-lift+scroll-reveal`，Operate 语境不采用营销 AIDA。
- Impeccable concept seed assigned index 5 为黑底无边框队列，但与本产品现场可读性、证据分层和安全边界冲突，按用户明确 brief 采用临床农业方向。

## Scope

- [ ] `web/app/page.tsx`：保留表单状态和请求链，重排诊断工作区、提交状态、结果摘要、证据和知识区。
- [ ] `web/app/cases/[id]/page.tsx`：保留病例加载、重试、知识和技术详情，重排为诊断记录。
- [ ] `web/app/reports/[id]/page.tsx`：保留报告接口、打印/PDF和知识 HTML，重做报告层级与证据矩阵。
- [ ] `web/app/components/PublicHeader.tsx`、`DiagnosisSummary.tsx`、`ComprehensiveAnalysis.tsx`、`DiagnosisPath.tsx`、`KnowledgeSummary.tsx`：换用 V3 语义组件类名和视觉结构。
- [ ] `web/app/layout.tsx` 与新的 V3 CSS：移除公共页面对旧 V2 视觉文件的依赖；不影响 Admin、历史、趋势、训练页面的现有逻辑。
- [ ] `web/tests/rendered-html.test.mjs`：仅补充/调整公共页面结构断言，不修改业务测试目标。

## Verification

- [ ] `git diff --check`
- [ ] 后端现有 pytest、前端测试、production build、ESLint
- [ ] 浏览器 1280px 桌面、390px 移动、横向溢出、键盘焦点、reduced-motion
- [ ] 首页空态/离线态；有真实病例时结果、详情和报告；不提交上传表单作为设计检查依据
- [ ] Impeccable critique、polish、audit；记录新的 Design Health 与 Audit 结果

## Constraints

- 保留当前工作树中的用户改动，不使用 reset/checkout，不重写后端。
- 只新增必要的公共 UI 组件，不安装新依赖。
- 不伪造进度、指标、病例、置信度或服务状态。

# 参考图驱动的诊断工作台改造（2026-08-20）

## Status

- **Status:** complete（实验室 CPU web 已部署；未修改 GPU、backend、模型和 SQLite 结构）
- **P2 历史/趋势视觉不一致:** closed
- **P2 在线成功态未真实验收:** closed（隔离测试病例完成真实上传→检测→分析→报告→历史/趋势链路）
- **Impeccable Audit:** 18/20；P0/P1/P2 为 0；保留既有范围外 P3

## Plan

- [x] 读取参考图与既有 V3 计划，锁定公共诊断全链路和只更新实验室 CPU 的边界。
- [x] 新增工作区外壳、深绿左侧导航、顶部诊断路径、三栏图片/证据/结论工作台及移动端折叠布局。
- [x] 将首页、病例详情、报告、历史、趋势统一到同一工作台外壳，保持原 API、字段、病例归属和报告逻辑。
- [x] 本地构建、前端渲染测试、ESLint、后端测试、桌面/移动端和横向溢出检查。
- [x] 备份并仅更新实验室 CPU `web` 容器；GPU 服务、detector、VLM、gateway 和数据卷保持运行状态。
- [x] 使用非个人样本完成线上隔离病例真实链路并记录审计结果。

## Deployment boundary

- 实验室入口：`http://192.168.15.133:8080`
- 回滚包：`/data/ghl/migration-backup/web-pre-workbench-20260820T133012Z.tar.gz`、`/data/ghl/migration-backup/web-pre-server-label-20260820T134215Z.tar.gz`
- 本轮未启动 GPU、未启动 Windows 中继、未重建 backend/detector/VLM、未修改 SQLite/病例图片/报告。

# GPU 服务器同步部署（2026-08-20）

## Goal

- 将当前工作区已完成的后端、前端和知识库代码同步到 GPU 服务器。
- 保留 GPU 服务器原有模型服务、SQLite、病例图片和报告；不执行格式化、重置或删除。
- 部署完成后通过 GPU 本机健康检查，并从实验室入口验证切换与独立存储归属。

## Plan

- [in_progress] 使用现有密钥只读确认 SSH、GPU 服务端口、应用目录和数据目录。
- [ ] 备份 GPU 应用、环境配置、SQLite、病例图片和报告，记录容量与校验值。
- [ ] 打包并上传当前后端及其知识库；同步前端仅在 GPU 服务器确有独立 web 服务时执行。
- [ ] 按现有 GPU 启停脚本更新依赖并重启 backend；不重建 detector/VLM。
- [ ] 验证 GPU `/health`、实验室 Admin 状态、手动切换、病例归属和回切行为。
- [ ] 运行必要回归检查并记录部署结果，不提交 Git。

## Constraints

- GPU SSH 入口：`connect.bjb2.seetacloud.com:10373`，使用已有本地密钥，不保存密码。
- 默认 GPU 根目录：`/root/autodl-tmp/ghl`，以远端实际检查结果为准。
- 不修改实验室服务器、GPU 模型权重、detector、Qwen3-VL、SQLite 既有记录和报告。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| 修复后 worktree 目标目录不存在 | 首次复制 `sites-vite-plugin.ts` | 清理临时 worktree，先创建 `web/build` 目录，再执行同一套独立验证 |

### Live verification errors

- 第一版病例脚本从 `backend` 工作目录拼接样本路径，导致上传前 `FileNotFoundError`；改为从项目根解析后重试，未创建错误病例。
- Qwen 第二阶段固定 900 输出 token 时，输入 7293 token 导致 vLLM 400；已将输出上限调整为 700，并更新测试断言。
- 700 输出仍遇到一例输入 7493 token 超限，另一例出现截断 JSON；已将每个外部来源传给 Qwen 的正文截断从 6000 调整为 4000 字符，待重新启动 backend 后复验。
| Root-level pytest collected `training/test_grasshopper_field_eval.py` and backend venv lacked `numpy` | 1 | Run the existing backend suite from `backend/tests` only; do not install training dependencies into the backend runtime for this sync task |

## History cleanup phase (authorized 2026-08-20)

- [x] Read-only inventory of both servers and SQLite integrity.
- [x] Stop lab/GPU backend write paths and create separate tar.gz backups with SHA-256.
- [x] Delete all rows from `diagnosis_cases` and clear only the associated `uploads`/`reports` directory contents on both servers.
- [x] Restart backends and verify both databases are intact with zero cases and zero uploaded/report files.

### Cleanup backups

- Lab: `/data/ghl/migration-backup/history-delete-lab-20260820.tar.gz`, SHA-256 `29da5db190c47521350668f220818faa2f0221d8e752c2e78a3b93a34441b2e8`.
- GPU: `/root/autodl-tmp/ghl-migration-backup/history-delete-gpu-20260820.tar.gz`, SHA-256 `695072bd01e7cdbe4f77d212980cf2d24c43ae3151da546dc7e233fcddc519cd`.

### Cleanup verification

- Lab `diagnosis_cases=0`, uploads=0, reports=0, `PRAGMA integrity_check=ok`.
- GPU `diagnosis_cases=0`, uploads=0, reports=0, `PRAGMA integrity_check=ok`.
- Lab health remains `lab_cpu` with active route `gpu_full`; GPU health remains `gpu_full`; model services were not changed.
| PowerShell command rejected | First archive/upload attempt included a recursive remote removal command and was blocked before execution | Use a new unique staging directory and non-destructive extraction; no remote state was changed |
| SQLite table not found | E2E cleanup used the lab-era table name `cases` on the GPU database | Inspect the GPU schema and update only the new test row using its actual table name |

## Final status

- **Status:** complete（GPU 后端、知识库、检测器、Qwen3-VL、双向中继和隔离 E2E 均已验证）
- **Active instance:** 未自动切换；实验室入口继续使用 `lab_cpu`
- **GPU health:** `gpu_full / 原 GPU 服务器 / ok`
- **Backup:** `/root/autodl-tmp/ghl-migration-backup/gpu-pre-sync-20260820T140209Z.tar.gz`
- **No changes:** GPU 既有病例、图片、报告未删除；未重建或替换模型权重；未提交 Git

# 实验室 backend health 快速修复（2026-08-20）

## Plan

- [x] 只读确认实验室 compose、控制状态和数据目录。
- [x] 备份当前 backend 源码、SQLite、上传图片、报告和控制日志。
- [x] 仅重建并重启 `lab-backend-1`，不重建其他服务。
- [x] 验证 `/health` 返回 `active_instance=gpu_full`，并确认公共页面读取到“原 GPU”。

## Result

- 实验室 `/health` 现在返回 `active_instance_id=gpu_full`、`active_instance_label=原 GPU 服务器`、`active_instance_mode=gpu`。
- `lab-web-1`、`lab-vlm-1`、`lab-detector-1`、`lab-gateway-1` 未重启；SQLite、病例、图片和报告未修改。
- 修复备份：`/data/ghl/migration-backup/backend-pre-health-fix-20260820T141656Z.tar.gz`，SHA-256：`6af56559710d0112a65ab5dbe513822dfa65e7fadc553f37408721a919a1d64c`。

## Constraint

- 当前控制文件已有 `gpu_full`，不重新执行切换，不修改活动实例。
- 保留 Windows 中继和 GPU 服务现状。

# 公共诊断界面恢复旧版（2026-08-20）

## Goal

- 将首次 Impeccable 改造前的公共诊断视觉与页面结构恢复到 `HEAD` 基线。
- 保留当前侧边工作栏、`ProductMark` Logo、后端接口、双服务器归属、病例/报告数据和当前上传校验。
- 只修改 `/`、`/cases/[id]`、`/reports/[id]`、`/history`、`/trends` 的公共页面；不修改 Admin、训练、审核、backend、模型、数据库或服务器。

## Assumptions locked

- 采用“旧版外观 + 当前可用字段”：旧版表单视觉保留，但只提供当前后端白名单和必填字段。
- 历史/趋势页面恢复旧版布局，但保留准确的“当前识别服务器”语义，避免双服务器切换造成数据丢失误解。
- `DESIGN.md`、`PRODUCT.md` 和既有 Impeccable 审计作为历史记录保留，本轮不覆盖。

## Plan

- [x] 为 `WorkspaceShell`/`PublicHeader` 增加旧版公共内容模式，保持侧边栏和 Logo 实现不变。
- [x] 将首页、病例详情、报告、历史、趋势切换为旧版结构并接入现有数据字段。
- [x] 增加独立旧版公共样式覆盖，隔离 Admin 和工作台样式。
- [x] 运行前后端测试、构建、Lint、diff 检查及桌面/移动端验收。

## Constraints

- 不执行 Git 回滚、重置或部署；不删除用户现有未提交改动。
- 不新增依赖，不扩展后端兼容旧字段。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|

## Completed verification

- Frontend `npm test`: 8 passed; `npm run lint`: passed; production build: passed.
- Backend `python -m pytest`: 41 passed, 1 existing Starlette/httpx deprecation warning.
- Browser checks: 1280px and 390px public routes (`/`, `/history`, `/trends`, `/cases/example-case`, `/reports/example-case`) had no horizontal overflow; the current rail and ProductMark remained present on desktop and the mobile rail collapsed as before.
- Impeccable detector only reported the known HTML-cleaning regex/template false positive in `reports/[id]/page.tsx`; no empty image source is emitted by the report UI.

## Dual-server deployment (authorized 2026-08-20)

- [x] Build and archive the restored public UI locally.
- [x] Back up the lab web source and GPU backend/deploy source before replacement.
- [x] Deploy the restored web container to the lab CPU entry without rebuilding backend, detector, VLM, gateway, SQLite, or storage.
- [x] Sync the same backend/deploy version to the GPU instance and restart only the GPU backend.
- [x] Verify both health endpoints, the active GPU route, zero case counts, empty uploads/reports, and all public routes.

### Deployment backups

- Lab web: `/data/ghl/migration-backup/ui-pre-legacy-20260820-230505.tar.gz`, SHA-256 `0b162afe63b0f503eb7cfbd286d9f660a07bb314693f932298907fbb07ad1430`.
- GPU backend/deploy: `/root/autodl-tmp/ghl-migration-backup/ui-pre-legacy-20260820-230505.tar.gz`, SHA-256 `36435d012dc833a9029e9b2768662108334296b8f86a9fcbd3fd79247e2879bc`.

# 2026-08-21 项目完整同步到 GitHub：in_progress

## Goal

将本地项目中适合 ChatGPT Work 后续分析、最小运行验收和部署检查的源码、配置模板、文档、示例与部署清单，安全同步到 `https://github.com/LingmaFuture/plant-health-ai` 的开发分支；不删除、覆盖或回滚现有文件，不上传密钥、缓存、虚拟环境或大数据集。

## Scope and safety

- 先检查本地 Git 状态、分支、远程和与目标仓库的差异。
- 不使用 `git reset`、`git checkout`、`git clean`、`git add -A` 或 `git add .`。
- 仅将确认属于本次同步范围的文件分批暂存；用户已有未提交改动不擅自覆盖。
- `Image Data base/` 只保留目录说明和获取清单；`best_model.pth` 按实际大小和仓库限制决定普通 Git、Git LFS 或仅记录元数据。
- 推送前检查暂存清单、敏感文件模式、大型文件和数据集内容。

## Phases

- [x] 1. 本地/远程 Git 状态、分支、远程地址和文件基线检查
- [x] 2. 大文件、数据集、敏感配置和 `.gitignore` 审计
- [x] 3. 补充 `DATASET.md`、`PROJECT_ASSETS.md` 或配置模板（仅必要时）
- [x] 4. 创建/确认 `competition-dev` 分支并分批暂存确认文件
- [x] 5. 运行提交前检查并提交
- [ ] 6. Push 到目标仓库并验证远程分支、commit 和可 clone 内容
- [ ] 7. 记录 Work 后续读取入口和最小运行验收结论

### Phase 1 result

- [x] Local branch/status/remote inspected.
- [x] Target `main` fetched read-only as `target/main` for comparison.
- [x] Confirmed target `main` is a separate 13-file legacy Gradio project; current project will be published on a new branch and will not overwrite target `main`.
- [x] Created and switched to `competition-dev`; preserved the existing `origin` remote and added target remote separately.

## Verification targets

- `git status --short --branch`、`git diff --stat`、`git diff --cached --stat`
- 关键入口源码、前后端依赖、部署脚本、知识库清单和真实 UI 源码存在
- 不含 `.env` 密钥、token、密码、虚拟环境、`node_modules`、缓存、临时文件和大数据集
- `best_model.pth` 处理方式有明确记录
- 数据集目录结构、类别、数量、期望路径和获取方式有明确记录
- 远程开发分支可被 Work clone，并能完成结构分析与文档级最小验收

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|

## Publish result — 2026-08-21

- Local commit `4c8fa20` (`chore: publish complete project for Work analysis`) is complete.
- Target branch push is blocked: authenticated account `genghailong8-maker` has `push: false` on `LingmaFuture/plant-health-ai`.

# 2026-08-21 Tavily 来源质量过滤修复：complete

## Scope

- 仅收紧 `EvidenceNormalizer` 的来源质量筛选；不启动 YOLO 8870 或 Qwen3-VL 8890，不修改病例、知识库、前端、Google provider 或 legacy provider。
- 保留 Tavily SearchProvider、EvidenceNormalizer、来源去重、来源评分、source ID 连续化和搜索失败降级。

## Verification

- [x] 知乎、贴吧、百度知道、3456.tv、jin-cang.com 及相关子域名按可解释原因过滤。
- [x] `.gov.cn`、科研机构、高校、农技推广/植保相关来源优先排序。
- [x] `CROP_SEARCH_MAX_SOURCES` 作为上限，不强制凑满；单一主域名最多保留 2 条。
- [x] 全低质量输入返回 `status=unavailable` 和空 sources。
- [x] SearchProvider 专项测试：22 passed。
- [x] 后端全量测试在进程级 `CROP_SEARCH_PROVIDER=disabled` 的外部搜索隔离下：66 passed；保留 1 条既有 Starlette/httpx 弃用警告。
- [x] 真实 Tavily 蛴螬危害/可能诱因查询：两次 HTTP 200，各过滤 2 条并保留 3 条，source-1..source-3 连续且有效。
- [x] `git diff --check` 通过；分支为 `competition-dev`；未 commit/push。

# 2026-08-21 外部证据增强诊断完整真实验收：complete

## Scope and safety

- 保持 `competition-dev`；不修改 `master/main`；不 commit/push。
- 只使用项目已有 YOLO、Qwen3-VL、SSH 隧道、backend、frontend 脚本和配置；不更换模型、不删除数据、不写入或打印 secret。
- 先核对实际服务器、路径、权重和环境，再按服务健康状态决定是否启动；8870/8890 不健康时才启动。

## Phases

- [x] 1. 读取项目启动脚本、部署文档、当前分支、环境变量状态和规划记录
- [x] 2. 检查本机/远端 YOLO、Qwen 和 SSH 隧道健康状态
- [x] 3. 按实际配置启动缺失服务并验证 8870/8890
- [x] 4. 启动/验证 backend 与 frontend，不覆盖既有运行数据
- [x] 5. 使用三个真实样本完成 YOLO→Tavily→Normalizer→Qwen→knowledge→病例→前端闭环
- [x] 6. 执行搜索失败降级测试并恢复配置
- [x] 7. 运行后端/前端回归、页面检查和最终验收报告

## Initial findings

- 当前分支 `competition-dev`，HEAD `f53ed24`；工作区存在既有未提交外部证据和 UI 改动，不能清理或回滚。
- `inference/open_tunnel.ps1` 默认连接 `connect.bjb2.seetacloud.com:10373`、用户 `root`，默认私钥为 `%USERPROFILE%\.ssh\id_ed25519`；脚本同时转发 8870 与 8890，并先检查本机健康状态。
- YOLO 远端脚本默认项目目录由脚本位置推导，端口 8870；Qwen 远端默认 `/root/autodl-tmp/crop-pest-vlm`、vLLM 0.26.0、端口 8890。
- 当前 Windows 进程环境中 `CROP_SEARCH_PROVIDER=tavily`、`TAVILY_API_KEY=set`；detector/VLM/backend 变量尚未出现在当前进程环境，需继续检查项目实际启动配置，不输出密钥。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Qwen 8192 上下文超限 | 蛴螬病例首次第二阶段请求 | 将发送给 Qwen 的单来源正文摘录从 4000 压缩至 1600 字符，保留完整 SearchSource 在病例快照中；第二阶段输出上限设为 700 |
| Qwen 500 token 输出截断 | 压缩输入后第一次重试 | 将第二阶段输出上限恢复为 700；三例重新分析均完成 |
| 8001 已被其他本地进程占用 | 启动隔离降级服务 | 改用 8101；使用独立 `runtime-fallback` 目录，测试完成后停止服务；目录因删除命令被安全策略拒绝而保留为未跟踪测试产物 |

## Final verification

- 远端 YOLO/Qwen、SSH 隧道、backend `8000` 和 frontend `http://localhost:3103` 均真实可用；未打印任何 API key。
- 三个真实病例均完成分析：class 14 蛴螬、class 7 马铃薯晚疫病、class 3 马铃薯早疫病；每例 Tavily 来源 5 条、危害 1 条、可能诱因 1 条、`source_ids` 全部存在且连续、`treatment.source=local_knowledge_base`。
- 三例总分析耗时约 8.4–9.4 秒；YOLO 真实远端推理成功，Tavily 真实 HTTP 200，Qwen3-VL 真实返回结构化 JSON。
- 真实病例详情和报告页面均渲染危害、可能诱因、防治措施、参考来源、检索时间；外部来源链接使用新标签与 `noopener noreferrer`；报告保留完整知识库表格、图片和百度百科来源。
- 隔离搜索失败测试中，YOLO 仍识别蛴螬，分析接口返回 HTTP 200，外部证据 `unavailable`、危害/可能诱因为空，防治仍来自本地知识库。
- 后端全量 pytest：66 passed，1 条既有 Starlette/httpx 弃用警告；前端测试：8 passed；production build、ESLint、`git diff --check` 均通过。
- 本阶段已创建本地 commit `5bad8b0`，尚未推送；分支仍为 `competition-dev`，未修改 `master/main`。真实验收结论：PASS。

# 2026-08-21 P0-1 GitHub 可复现前端构建修复：in_progress

## Scope and assumptions

- 只处理 GitHub `competition-dev` 干净环境无法构建前端的问题；不修改 master/main，不处理其他 P0。
- 优先确认 `web/build/sites-vite-plugin` 是源码、生成物、依赖或历史遗留，再选择最小 A/B/C 修复。
- 不提交 `node_modules`、`.env`、模型、数据集、缓存、runtime 或临时构建目录。

## Phases

- [x] 1. 确认分支、基准 commit、当前状态并读取工作区规划记录
- [x] 2. 定位 `sites-vite-plugin` 真实来源、忽略规则和构建引用
- [x] 3. 采用最小方案修复干净 clone 构建缺失
- [x] 4. 运行本地前端测试、Lint、build、render tests
- [x] 5. 使用不带 ignored 文件的独立 worktree 完成 install/build/render 验证
- [x] 6. 完成安全审计、记录结果并准备 P0-1 原子提交

## Success criteria

- 仅从 Git 仓库源码和锁定依赖安装后，前端 production build 与 render tests 均通过。
- `sites-vite-plugin` 必要源码已纳入 Git，或引用已被证明安全移除；不通过静默跳过功能绕过构建。
- 工作区没有本轮新增 secret、模型、数据集、缓存、node_modules、.venv 或 runtime。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|

## Phase 2 finding

- `web/build/sites-vite-plugin.ts` 是约 1.3 KB 的项目源码 Vite plugin，使用 Node `fs/promises` 和 Vite `Plugin` 类型，在 `closeBundle` 阶段复制 `.openai/hosting.json` 与 `drizzle/` 到 `dist/.openai`。
- 根 `.gitignore` 的 `web/build/` 忽略了整个目录；`git check-ignore -v` 命中该规则，`git ls-files web/build` 为空；`web/vite.config.ts` 又直接静态 import 它。
- 采用方案 A：保留 `web/build/` 的默认忽略，仅通过两个最小例外规则放行 `web/build/` 目录和 `sites-vite-plugin.ts` 这个源码文件。

## Verification results

- 修复前 HEAD worktree：`npm ci` 通过，build 失败于 `UNRESOLVED_IMPORT ./build/sites-vite-plugin`。
- 修复后独立 worktree：只补入候选 `.gitignore` 和 `web/build/sites-vite-plugin.ts`，未复制当前 `node_modules` 或 ignored 文件；`npm ci`、production build、8 项 render tests 全部通过。
- 当前工作区：frontend tests 8 passed、ESLint、production build、render tests 和 `git diff --check` 通过。

## Final audit

- 当前分支 `competition-dev`，基准 HEAD `eb7ba9480b5df65a84f1e6f182d0ee62dec27a4d`；未修改 master/main，未 commit/push。
- `git diff --check` 通过；`git status --ignored` 仅显示既有 ignored 数据/模型/缓存，未将其加入待提交范围。
- 待提交源码为 `web/build/sites-vite-plugin.ts`；没有 `.env`、API key、密码、token、SSH 私钥、node_modules、.venv、模型、数据集或 runtime 临时数据。
- 独立 worktree：修复前 build 失败；修复后 `npm ci`、production build、render tests 8/8 通过。
- 最终判断：PASS；本轮仅允许提交 `.gitignore`、`web/build/sites-vite-plugin.ts`、`task_plan.md`、`findings.md`、`progress.md` 五个文件。

# 2026-08-21 P0-2 外部证据正文持久化：in_progress

## Scope and constraints

- 只处理最终 EvidenceNormalizer 来源正文的病例/报告持久化与重启恢复。
- 保持 `competition-dev`；不修改 master/main，不 commit/push。
- 不修改 SearchProvider、Tavily 策略、Normalizer 排序、YOLO、Qwen 第一阶段、knowledge 或公共 UI。
- 不新增 SQLite 表或列；优先复用现有 `analysis_json` 与报告 JSON 快照。

## Phases

- [x] 1. 审计 SearchSource、病例保存、SQLite、报告和历史读取链路
- [x] 2. 设计并实现可选 evidence snapshot 兼容结构
- [x] 3. 增加持久化、source_id、重启、旧病例、报告和安全测试
- [x] 4. 运行 backend/frontend 回归、diff 与安全扫描
- [x] 5. 如服务可用，执行一个真实最小病例；否则明确无法进行真实 E2E
- [x] 6. 输出 P0-2 报告，保持未提交状态

## Success criteria

- `source_id -> sources metadata -> evidence_snapshots.content` 一一对应。
- 列表接口不携带完整正文；病例详情和报告可恢复最终有效正文。
- 进程重启后正文、URL、标题、站点、检索时间和 source_id 仍存在。
- 历史病例不重新调用 Tavily；旧病例无快照时不报错。
- treatment 继续标记 `local_knowledge_base`。

## Verification checkpoint

- Backend pytest：70 passed（临时 `CROP_SEARCH_PROVIDER=disabled`，避免既有 mock 测试误调用本机 Tavily）。
- Frontend tests/render：8 passed；ESLint、production build、`git diff --check` 通过。
- 真实隔离病例：`lab_cpu-da980cfd48b54d4c9f775897ee560d73`；YOLO 主类别蛴螬、置信度约 0.918622；Tavily/Qwen/病例/报告闭环成功。
- 真实重启恢复：5 个 source_id 与 5 份正文快照恢复；重复读取报告未修改快照文件，未重新检索。
- 当前保持未提交、未推送。

# 2026-08-21 P0-3 比赛启动链与健康检查：in_progress

## Scope and constraints

- 只新增比赛现场统一启动、状态、最小 smoke 和安全停止能力；不修改外部证据业务、YOLO、Qwen、Tavily provider、knowledge、数据库或公共 UI。
- 保持 `competition-dev`，不修改 master/main；本轮不 commit、不 push。
- 复用 `inference/open_tunnel.ps1` 建立 GPU 隧道；脚本只管理自己创建的本地进程和 PID 文件，不停止远端推理服务。

## Phases

- [x] 1. 审计现有启动脚本、服务端点、运行环境、端口和状态接口
- [x] 2. 实现 competition start/status/smoke/stop、预检、健康分类和 PID 安全边界
- [x] 3. 更新 `.env.example`、README 和比赛演示 runbook
- [x] 4. 运行脚本单元测试、预检、真实本地链路和故障降级模拟
- [x] 5. 运行 backend/frontend 全量回归、构建、Lint、diff-check 和安全扫描
- [x] 6. 输出 P0-3 报告，保持未提交、未推送

## Success criteria

- 新电脑按文档执行统一入口即可预检并启动 backend、frontend 和必要隧道。
- status 能区分 READY、DEGRADED、FAILED、NOT RUNNING；核心服务失败阻止完整演示，Tavily 失败只降级。
- `tmp/competition` 只保存脚本自有 PID/log 状态；stop 不批量杀 Python/Node，不停止远端服务。
- 本地真实链路和至少一个真实病例可验证；搜索失败、模型离线和端口占用都有可解释提示。

# 2026-08-21 P0-4 Qwen 证据上下文预算：in_progress

## Scope and constraints

- 只处理第二阶段 Qwen 证据上下文的预算、来源选择和 excerpt 截断；不改变 Tavily 最多 5 个来源、Normalizer 排序/过滤、完整 evidence_snapshots、source ID、knowledge treatment、P0-1/P0-3 或前端。
- 保持 `competition-dev`，不修改 master/main；本轮不 commit、不 push。
- 完整正文继续保存和展示；Qwen 只接收独立的有预算 excerpt。

## Phases

- [x] 1. 恢复工作区上下文并审计当前 prompt、图像、字段、证据和输出预算
- [x] 2. 设计并实现可配置的上下文预算、可靠来源选择和保守 token 估算
- [x] 3. 增加来源优先级、source ID、长正文、预算边界和无来源测试
- [x] 4. 使用默认 5 来源完成三病例真实 E2E 与重复稳定性验证
- [x] 5. 运行 backend/frontend 回归、重启恢复、降级和安全检查
- [x] 6. 输出 P0-4 报告，保持未提交、未推送

## Success criteria

- 默认 `CROP_SEARCH_MAX_SOURCES=5` 仍保留、持久化和展示全部最终来源。
- 第二阶段只发送预算允许的 1～2 个高可信来源 excerpt，并保留原始 source ID，不重新编号。
- 真实请求不再触发 Qwen 8192 context overflow；证据不足时安全返回 unavailable，不伪造危害或可能诱因。
- 三个真实病例均有 harms、possible_causes、有效 source_ids 和 `local_knowledge_base` treatment。

## Final verification

- Backend tests from `backend/`: 77 passed, 1 pre-existing Starlette/httpx deprecation warning; frontend tests/render: 8 passed; ESLint and production build passed.
- Default `CROP_SEARCH_MAX_SOURCES=5` real cases completed for grub (class 14), potato late blight (class 7), and potato early blight (class 3). Each retained 5 normalized sources and 5 persisted正文快照; Qwen received 2 selected excerpts with original source IDs and estimated evidence tokens at or below 1600.
- Repeated grub analysis completed twice without context overflow. After backend restart, detail/report reads returned HTTP 200 with 5 sources and 5正文快照 without triggering detect/analyze; treatment remained `local_knowledge_base`.
- Search-disabled, no-source, budget exhaustion, invalid source ID, long正文 and multimodal degradation cases are covered by automated tests. Security/path scan found no real secret, private key, runtime, model, dataset or dependency artifact in the nine changed files.
- P0-4 is complete on `competition-dev`; worktree remains uncommitted and unpushed.

# 2026-08-21 P1 比赛配置与启动路径收口：in_progress

## Scope and constraints

- 只处理比赛文档中 Tavily/Google provider 定位，以及 `competition.ps1` 对 `CROP_STORAGE_DIR`、`CROP_KNOWLEDGE_DIR` 相对路径的解析；不修改核心诊断、搜索算法、YOLO、Qwen、UI 或远程服务。
- Backend 的真实路径语义以 `backend/app/config.py` 为准：相对 `CROP_STORAGE_DIR` 和 `CROP_KNOWLEDGE_DIR` 均相对于 `backend/`；绝对路径保持原样并规范化。
- 保持 `competition-dev`，不修改 master/main；本轮不 commit、不 push。

## Phases

- [x] 1. 审计 provider 文案、脚本根目录定位和 Backend 相对路径语义
- [x] 2. 统一 Tavily 主 provider、Google Grounding optional、Custom Search legacy 文案
- [x] 3. 实现脚本路径解析并增加 root/外部 cwd/绝对路径/中文空格/不存在目录测试
- [x] 4. 运行 PowerShell、root/外部 cwd status/smoke 和完整回归
- [x] 5. 更新 findings/progress，输出 P1 报告，保持未提交、未推送

## Success criteria

- `CROP_SEARCH_PROVIDER=tavily` 在 `.env.example`、README 和演示 runbook 中一致作为比赛默认 provider。
- Google Grounding 仅标记为 optional/compatible，Google Custom Search 仅标记为 legacy。
- 无论调用者当前 cwd 如何，脚本均按 Backend 的相对路径语义检查 knowledge/storage；绝对路径和不存在目录行为正确。
- P0-1～P0-4 回归通过，且没有秘密或运行时文件进入差异。

## P1 Final verification

- Provider 文案已统一：Tavily 为比赛默认，Google Grounding 为 optional/compatible，Google Custom Search 为 legacy；三个比赛入口均保留空 API Key 示例。
- `Resolve-BackendPath` 基于脚本所在目录和 `backend/` 解析相对路径，绝对路径经 `GetFullPath` 规范化，不修改调用者 cwd。
- PowerShell tests、项目根目录 status/smoke、项目外 cwd status/smoke 均通过；两种 cwd 下 Knowledge/Storage 均 READY 且路径一致。
- Backend pytest 77 passed（1 条既有 Starlette/httpx 弃用警告）；frontend/render 8 passed；ESLint、production build、`git diff --check` 通过。
- P1 已完成，当前工作区保持未提交、未推送。

# 跨对话工作交接记录（2026-08-23）

## 当前仓库状态

- 项目目录：`C:\Users\genghailong\Documents\编程大赛`
- 分支：`competition-dev`
- 当前 HEAD：`8807b90aa135d97549d463c37807f81de7300daa`
- 远端：`origin/competition-dev` 已同步
- 记录交接前代码工作区：clean；本次交接新增的未提交改动仅限 `findings.md`、`progress.md`、`task_plan.md` 三份规划文件。
- 最近提交：`fix: align competition config and runtime paths`
- 不修改 `master/main`；后续新对话默认继续在 `competition-dev` 工作。

## 已完成并固化的阶段

- P0-1 `5de74a7`：GitHub clean clone 可复现前端 build；纳入 `web/build/sites-vite-plugin.ts`，未提交依赖或构建缓存。
- P0-2 `0ae9571`：外部证据正文随病例持久化，历史读取不重新调用 Tavily，旧病例兼容。
- P0-3 `057f6c5`：比赛启动链与健康检查，提供 `scripts/competition.ps1 start/status/smoke/stop`；核心服务失败为 FAILED，Tavily/knowledge/storage 异常为 DEGRADED；stop 不停止远程 Detector/Qwen。
- P0-4 `a37ac67`：Qwen 8192 上下文预算控制；搜索/快照仍最多保留 5 个来源，Qwen 默认最多选 2 个来源，证据预算默认 1600，source ID 不重编号，预算不足安全 unavailable。
- P1 `8807b90`：比赛 provider 文案统一、competition.ps1 相对路径解析修复及 PowerShell 路径回归测试。

## 当前业务/配置基线

- 比赛默认外部证据 provider：`CROP_SEARCH_PROVIDER=tavily`
- Google Grounding：`google_grounding`，optional/compatible provider
- Google Custom Search：`google_legacy`，legacy，仅兼容已有资格用户
- `backend/app/config.py` 的相对 `CROP_STORAGE_DIR`、`CROP_KNOWLEDGE_DIR` 均相对于 `backend/`；`scripts/competition.ps1` 已保持一致。
- 当前 Qwen 预算配置默认：context 8192、output 700、reserved input 5892、evidence 1600、max evidence sources 2、excerpt 900 字符。
- 完整来源正文继续保存在 `sources`/`evidence_snapshots`，防治措施继续只来自 `knowledge/` 的 `local_knowledge_base`。
- 所有真实 API Key 只允许存在于本机运行环境；仓库模板为空，不提交密钥。

## 当前服务状态（交接时刻）

- Backend `127.0.0.1:8000`：READY
- Frontend `localhost:3000`：READY
- Knowledge：READY
- Storage：READY，路径为 `backend/runtime`
- Detector `8870`：NOT RUNNING
- Qwen3-VL `8890`：NOT RUNNING
- Tavily：配置存在，状态 READY；当前总状态因 Detector/Qwen 未运行而为 FAILED
- 新对话如需真实识别，先执行 `scripts/competition.ps1 start` 或按 runbook 启动，不要把当前 NOT RUNNING 误判为代码回归。

## 最近完整验证基线

- P1 PowerShell tests：PASS
- 项目根目录 `status/smoke`：READY
- 项目外 cwd `C:\Windows\Temp` 调用 `status/smoke`：READY
- Backend pytest：77 passed，1 条既有 Starlette/httpx 弃用警告
- Frontend/render：8 passed
- ESLint：PASS
- Production build：PASS
- `git diff --check`：PASS
- security/path scan：PASS

## 已知限制与下一步入口

- 根目录 pytest 会额外收集训练评测脚本 `training/test_grasshopper_field_eval.py`，当前环境缺少 NumPy；正式后端验收以 `backend` 目录测试为准，未修改 training。
- P0-4 使用保守字符上界估算器，不等同 Qwen 精确 tokenizer；目标是避免超上下文并在不足时安全降级。
- `findings.md`、`progress.md`、`task_plan.md` 保留历史阶段记录；其中旧阶段的 provider 描述是审计历史，当前有效配置以 P1 章节、README、runbook 和 `.env.example` 为准。
- 当前没有用户指定的下一项 P1/P2 改动。新对话开始时先读取本交接记录、`findings.md`、`progress.md`，检查 `git status`，再等待/确认新的工作范围。

## Verification results

- `scripts/competition.tests.ps1`：PASS；健康分类覆盖 Tavily DEGRADED、Backend/Detector/Qwen FAILED 和 PID 误匹配保护。
- 统一入口实际启动 Backend 8000；使用临时 3110 端口完成 production build/start/status/stop，回收后 8000/3110 无监听，远端 Detector/Qwen 未停止。
- `status -CheckTavilyNetwork` 与 `smoke` 在核心服务 READY 时通过；Backend 停止时正确报告 FAILED。
- Backend pytest：70 passed；Frontend tests/render：8 passed；ESLint、production build、`git diff --check` 和候选文件 secret/path 扫描通过。
- 真实图片 API 链路完成上传、YOLO、Qwen、病例详情和报告；默认 5 来源复现既有 Qwen 8192 上下文超限并安全降级，临时单来源配置下分析 API 完成且 treatment 仍来自 `local_knowledge_base`。该既有上下文问题未在本轮修改。

# UI / 比赛展示优化第一阶段：视觉方案探索（2026-08-23）

## Scope and constraints

- 只做当前 UI 只读审计、公开参考研究、4 套视觉方案与展示版结构草图。
- 不修改 `web` 前端、backend、配置、模型或部署文件；不 commit、不 push、不创建 PR。
- 方案必须覆盖诊断首页、诊断结果页、病例详情/报告页，并保持真实业务边界与证据来源语义。

## Phases

- [x] 1. 阅读前端页面结构并捕获当前首页、病例详情、报告真实状态
- [x] 2. 研究 Apple / Google / AI SaaS / 极简报告型参考风格
- [x] 3. 形成 4 套明显不同的视觉方向与页面草图
- [x] 4. 给出比赛展示、低风险实现、结构保留和综合推荐排序

## Current evidence

- 首页：双栏上传与空结果工作区，Hero 和字段说明偏长。
- 病例详情：图片与状态清晰，但综合分析、外部来源、本地防治和知识库长文重复拉长页面。
- 报告：报告头与指标网格成立，后半段偏“资料归档”，现场讲解需要更强的摘要层级。

## Reference research result

- Apple：层级来自字号/字重/颜色，保持可读性与少量字体角色。
- Google / Gemini：入口轻、结果模块化、复杂输出可探索。
- Material：卡片只承载有明确主体的内容，均质来源更适合列表；长内容按需展开。
- Linear：降低导航和边界的视觉噪声，让核心工作获得注意力。
- Ada：摘要、下一步、可分享报告优先，安全边界仍保留但不抢主结论。

## Errors recorded

| Error | Attempt | Resolution |
|---|---|---|
| Browser runtime path not found | Initial browser setup | Switched from skill subdirectory path to browser plugin root `scripts/browser-client.mjs`; browser connection succeeded. |
| PowerShell wildcard path rejected for `[id]` route files | Read-only source inspection | Existing DOM capture and earlier source scan were sufficient; no retry or source change made. |

# UI 最终视觉方案前端落地（2026-08-24）

## Scope and constraints

- 以用户提供的首页、诊断结果、病例详情/报告三张定稿为最高视觉依据，重构现有 `web` 公共诊断页面。
- 保持既有 API、检测/分析、病例/报告、来源、知识库、打印和降级状态；不修改 backend、模型、检索、训练、部署脚本。
- 保持 `competition-dev`，不 commit、不 push、不创建 PR；仅修改直接相关的前端源文件与交接/QA 文档。

## Phases

- [x] 1. 审计现有页面、复用组件与 CSS 入口，确定最小 Design Tokens 和变更范围。
- [x] 2. 落地统一 tokens、公共导航和首页双栏上传/表单视觉。
- [x] 3. 落地诊断成功结果的图片、摘要行、来源展开和异常状态层级。
- [x] 4. 落地病例详情/报告简报结构、知识库/技术详情降级及打印样式。
- [x] 5. 用已有病例在本地桌面端检查首页、可参考蛴螬结果、病例、报告和来源不可用状态；执行前端回归、lint、build、diff-check。移动端由 820px / 560px 响应式规则覆盖；未调用 GPU。
- [x] 6. 截图对照三张定稿，完成 `design-qa.md` 与验收报告，不提交。

## 582046f Work P0 解阻（2026-08-24）

- [x] 1. 锁定 `competition-dev` / `582046f...` clean 基线并复核 Extractor 与 deploy 运行时依赖。
- [x] 2. 以最小确定性规则修复多实体标题归属和弱 harm 误抽取，并补齐回归测试。
- [x] 3. 移除 `deploy/lab` 与 `deploy/gpu` 的 Qwen/VLM/8890 部署运行时依赖，并添加静态防回归测试。
- [x] 4. 评估 P1 化学防治安全提示；确认不构成同一区域重复，保持现状。
- [x] 5. 完成手工四例、后端全量、前端 render/lint/build 回归。
- [x] 6. 完成 competition PowerShell、全仓关键词分类、diff/安全检查并输出验收报告。

## 人工测试第一轮修复（2026-08-25）

- [x] 1. 确认 `competition-dev` / `0075f633...` 干净基线与严格范围。
- [x] 2. 审计证据检索、抽取、知识 Markdown、首页及病例/报告渲染路径，并补充目标回归测试。
- [x] 3. 实施 T-01/T-04 后端证据清洗、查询与状态语义修复。
- [x] 4. 实施 T-02 单一“防治方法”Markdown 数据源，以及 T-03/T-06 指定前端精简与默认知识展示。
- [x] 5. 执行后端、前端、打印/响应式、人工/历史病例与安全 Git 验收；不 commit、不 push。

## 服务器 Normalizer 修复与候选部署验收（2026-08-25）

- [x] 1. 仅核对既有本地工作树、`/data/ghl/app-next`、测试容器与旧正式容器，确认不触碰正式环境。
- [ ] 2. 为 Normalizer 加入 query-type-aware 选源配额，并为 Extractor 加窄范围科研方法 Guard；补齐回归测试。
- [ ] 3. 完整后端测试后，用离线网络重建 `lab-backend:next-test` 并仅重部署 `lab-backend-next-test`。
- [ ] 4. 在候选入口完成连续 Tavily 真实回归（马铃薯早疫病、蛴螬），给出正式部署建议；当前被英文科研方法变体误抽取、harms 为空阻断，不 commit、不 push、不替换正式容器。

## 候选早疫病 Extractor 阻断复核（2026-08-25）

- [x] 1. 从失败病例 `lab_cpu_test-49a9da7041114a10ae5d41bec4bfca5d` 的持久化快照逐层定位：有效英文危害/流行条件仍在 Normalizer 后的 `source-2`，问题只在 Extractor。
- [x] 2. 补齐括号引用后的英文断句，以及 `existing methods / sample size / develop a method` 窄方法论 guard；回归保护英文危害和真实气象诱因。
- [x] 3. 后端全量 84 passed 后，以 `--network=none` 构建新候选镜像 `sha256:65632ff1f5e885c098be864bc0d6e8a9aec28379077c86331a7f0b99243da26d`，仅轮换候选容器并保留回滚容器。
- [ ] 4. 第 1 次早疫病真实 E2E 虽已恢复 harms/cause 且消除方法污染，但 selected evidence 仍含“晚疫病”来源；按门禁立即停止，未执行第 2/3 次、蛴螬或正式部署。

## 候选环境正确 Entity Guard 验收（2026-08-26）

- [x] 1. 按历史定义复核 `lab_cpu_test-c8035900867845e1a693158d32a6f843`：最终来源并集为 `{source-2}`，不引用混合教学目录 `source-1`；重新判定 Early blight #1 PASS。
- [x] 2. 不修改 production code 或候选镜像，以正确门禁发起 Early blight #2。
- [ ] 3. #2 在 Tavily retrieval 层因 `ConnectError` 返回 zero sources / zero snapshots，未进入 Normalizer/Extractor；按门禁停止，未运行 #3 或蛴螬回归。

## 候选环境管理建议 Guard 与网络恢复收尾（2026-08-26）

- [x] 1. 确认 `c803...` 的 `避免与茄科作物连作，实行轮作倒茬，减少病原菌积累。` 是管理建议误入 possible_causes 的真实 Extractor guard 缺口；保留声明式连作/病原菌/湿度/降雨诱因。
- [x] 2. 恢复既有 Tavily reverse SSH：Lab relay `172.17.0.1:443` 原在监听，但 `127.0.0.1:18443` 无 reverse tunnel；恢复后 Lab tunnel TLS 与候选容器 TLS 均通过，未输出密钥。
- [x] 3. 仅在 Extractor 增加命令式管理句及真实英文研究表格/标题窄 guard；定向 52 passed，完整 backend 86 passed；以 `--network=none` 重建候选。
- [ ] 4. 最终候选 `sha256:54d362475742b723e29209c7bfa50e492d680a1e2ec92246b5589a1a61146015` 的新早疫病 #1 (`ac5232fcc7c64e169b0dde5557c15e8f`) 未产生 possible_causes；Tavily available 但本次快照无合格非管理/非研究诱因。按门禁停止，未执行 #2/#3/蛴螬。

## Possible-causes retrieval-only 定位（2026-08-26）

- [x] 1. 使用当前生产 query `马铃薯早疫病 Alternaria solani 发生条件 流行规律 农业`，连续 3 次独立 Tavily retrieval-only；不创建病例、不写快照、不输出密钥。
- [x] 2. 三次 raw 均为 5 条、Normalizer 均保留 4 条：PMC raw `tavily-2` 的 snippet 含高湿/适温/降雨增加 EB outbreak 的合格诱因，Normalizer 后稳定为 `source-1`；明确晚疫病 PDF 被既有 Entity Guard 丢弃，未丢失合格 cause。
- [x] 3. 同一内存态 normalized evidence 调用当前 Extractor 仍为 `possible_causes=[]`；剩余阻断位于 Extractor 的 snippet/省略号断句与 <=220 字候选形成层，不属于 retrieval 或 Normalizer。按本轮暂停生产代码要求停止，不修 Extractor、不重建镜像、不继续 E2E。

## T-04 省略片段 P0 修复与候选收尾（2026-08-26）

- [x] 1. 仅在 `EvidenceExtractor` 的 extraction-only `_sentences()` / candidate formation 增加 `[...]`、`…` 省略标记边界；不改 raw snapshot、SearchSource 持久化、Tavily query、Normalizer、Entity Guard 或 220 字符上限。
- [x] 2. 增加真实 PMC 模式回归：省略标记夹住的英文 epidemiology cause 可形成独立短句并保留正确 source ID；既有中文管理建议、英文研究方法、英文 harm/cause、噪声和重复守卫保持通过。
- [x] 3. 定向测试 53 passed，完整 backend 测试 87 passed（1 条既有 Starlette/httpx 弃用警告），`git diff --check` PASS。
- [x] 4. 在实验室 CPU 候选环境以 `--network=none` 构建并轮换仅 `lab-backend-next-test`；新镜像为 `sha256:21fee502609a7c9183bebd15de9c7f2933ca8bdf6b2dafaac6c803aa960722a5`，旧候选回滚容器保留，正式服务未动。
- [x] 5. 早疫病真实 E2E 连续 3 次 PASS；三次均为 Detector=`马铃薯早疫病`、harms=2、possible_causes=1、引用 ID 有效、无错误实体/管理/研究/旧噪声污染，treatment=`local_knowledge_base`。
- [ ] 6. 蛴螬真实回归：候选存储与 API 无蛴螬病例/图片，仓库无可确认的真实蛴螬输入；未以数据集图片或 UI 截图冒充真实 E2E，待补充可复用样本后复验。

## T-04 固定蛴螬图片回归（2026-08-26）

- [x] 1. 使用 `E:\病图片\蛴螬\1.jpg` 的副本创建全新病例，未复用旧 analysis、mock 或 dataset fixture。
- [x] 2. Upload、YOLO、Confidence Gate、Tavily、Normalizer、deterministic Extractor、case persistence 与 local Knowledge 均完成；Detector=`蛴螬`、class id=14、confidence=0.918733、detection count=1、analysis/external search=`available`、normalized sources=5、snapshots=5。
- [ ] 3. 最终门禁失败：同一真实 source-1 句子同时进入 harms 与 possible_causes，触发 harm/cause duplicate；按规则停止，不修改 production code、不重建镜像、不重跑。

## T-04 干预归类 P0 修复与交叉回归（2026-08-26）

- [x] 1. 仅扩展 EvidenceExtractor 的窄 management/intervention guard，使灌溉、施用/处理及其降低危害效果的完整句子同时从 harms 与 possible_causes 排除；独立生态/危害事实保留。
- [x] 2. 增加标准化后的跨 section duplicate safety net，重复结论不同时输出到 harms 与 possible_causes，保留 source attribution。
- [x] 3. 定向测试 56 passed，完整 backend 测试 90 passed，`git diff --check` PASS。
- [x] 4. 实验室 CPU 以 `--network=none` 构建新候选并仅轮换 `lab-backend-next-test`；新镜像 `sha256:36be209ca5ec77f609459d634695ee99b7e91fd92835ff00201dc01a92677547`，旧候选与回滚容器保留。
- [x] 5. 固定蛴螬图片新病例 `lab_cpu_test-83adeec6e81f4739b12e60d3068647ec` 通过完整真实 E2E；早疫病交叉回归新病例 `lab_cpu_test-e2a0ddfbcf5d4dc4af89c1391dface48` 通过。

## T-07B Failed Evidence Forensic & Query Refinement（2026-08-27）

- [x] 使用既有三轮 audit 完成 17 个失败 query pair 的逐来源 forensic；三轮 raw 均为 5、available，失败结果稳定。
- [x] 纯 Q 仅 class 0 两条与 class 1 harms；其余失败项分为 E、S 或 mixed。仅修改上述 3 个 Query v2 override 与 exact matrix test；早疫病/蛴螬 Query、Normalizer、Extractor、Guards、Confidence Gate、retry 机制未改。
- [x] v2 retrieval-only 各执行首轮+两次 retry：class 1 harms 为 QUERY FIXED；class 0 harms 为 EXTRACTOR GAP，class 0 causes 为 SOURCE SCARCITY。
- [x] 定向 63 passed；完整 backend 97 passed（1 条既有 warning）；`git diff --check` PASS。未部署、未构建正式镜像、未 commit、未 push。

## T-08 EvidenceExtractor Narrow Coverage Improvement（2026-08-27）

- [x] 使用 T-07B 已保存 normalized evidence 建立正/负 fixture，并单独审计 class 0 南方玉米叶枯病研究来源。
- [x] 仅实施 sentence-level、type-specific 的 Extractor 窄规则；Management/Research/Entity/fragment negatives 在本地回归未退化。
- [x] Preserved Evidence Replay 与稳定 PASS 类回归：12/12 已证实 coverage gap 按预期通过，SOURCE SCARCITY 未被强制补结果。
- [x] 仅对修改影响类别执行 retrieval-only 检查；不创建病例。首轮 12 pair，4 个污染 pair 一次重试后仍重复，未扩大修复。
- [x] 定向 `90 passed`、完整 backend `124 passed, 1 warning`、`git diff --check`；正式环境冻结，commit/push/deployment=NO。
- [ ] T-08 整体验收 PASS：live retrieval-only 仍有未纳入本轮范围的 Research/Management/反向实体污染，状态为 `NEEDS FOLLOW-UP`。

## T-08 follow-up：污染归类窄范围复核（2026-08-27）

### 假设与边界

- 目标是消除已观察到的四类错误用户证据：研究摘要/喷施上下文、实验研究句、叶蝉管理建议、病原体反向伤害蝗虫；不扩大为通用网页质量评分器。
- 保留明确的自然危害与发生条件句；仅在句子本身出现强研究、命令式管理或反向生物学信号时拒绝。
- 直接相关文件仅为 `backend/app/search/evidence_extractor.py` 与 `backend/tests/test_evidence_extractor_t08.py`；不改 Retrieval、Normalizer、Query Builder、Tavily、部署和正式环境。

### 阶段

- [x] 1. 为四类污染建立最小离线回归并确认当前失败行为
- [x] 2. 增加 sentence-level 窄 guard，保持已有正向 fixture 不退化
- [x] 3. 运行定向/完整 backend 回归、diff-check，并更新 findings/progress
- [ ] 4. 在未获候选入口与网络确认前不 build/deploy；live gate 继续保持 NEEDS FOLLOW-UP

## T-08B EvidenceExtractor Safety Closure（2026-08-27）

### Hard constraints

- 正式环境冻结；不 build candidate image、不 deploy、不 commit、不 push。
- 不改 Tavily Query Builder/result count/retry、EvidenceNormalizer、Confidence Gate、persistence、source attribution。
- 只处理 Research、Management imperative、reverse-biological-relation 三类 negative safety；南瓜白粉病 causes 只读核查，安全证据不存在时接受 `SAFE UNAVAILABLE`。

### Gates

- [x] 1. 找齐四条真实失败句，落盘 exact sentence/title/domain/output/root-cause decision path
- [x] 2. 固化四条 negative tests 与相邻 positive controls
- [x] 3. 完成 12-pair preserved replay 与 Early-blight/Grub/既有稳定类回归
- [x] 4. 完成 backend/Search/diff-check 全部 PASS
- [x] 5. 对 5 个受影响 pair 做真实 retrieval-only safety audit（每个最多 3 次）
- [x] 6. 输出 16 类最终矩阵和 T-08B closure report；未满足全部前门禁保持 NO

### Error log

- 2026-08-27：直接调用 `pytest` 失败，当前 PowerShell PATH 未包含 pytest；已确认项目自带 `backend/.venv`，后续统一使用 `.venv\Scripts\python.exe -m pytest`。
- 2026-08-27：PowerShell `Get-Content -Skip` 参数不存在；已改用管道配合 `Select-Object -Skip`，不影响项目文件。
- 2026-08-27：首轮 retrieval-only 脚本导入语句写错导致 Python `SyntaxError`；未发起网络请求，已修正后重跑。
- 2026-08-27：一次组合式 Extractor patch 因上下文位置不匹配被 `apply_patch` 拒绝；未修改文件，已拆分为小 patch 重试。
- 2026-08-27：从仓库根目录运行检查脚本时误用了 `\.venv` 相对路径；未执行脚本，已改用 `backend\\.venv\\Scripts\\python.exe`。
- 2026-08-27：新增 T-08B 回归首次运行发现盲蝽句“不同的酶活性表现不同”未命中研究 guard；已确认这是要求覆盖的研究结果词形，补充窄匹配后复验。
- 2026-08-27：T-08B 新测试前两轮分别发现研究标题上下文与 decision-path 预期不完整；已收紧 `酶活性` 研究词形并校正测试中的实际 marker 布尔值，最终 34/34 PASS。

### Final

- T-08B safety closure = PASS；Ready for Work review = YES。
- formal environment frozen；build candidate image / deployment / commit / push = NO。

## T-07/T-08/T-08B Final Work Review Bundle（2026-08-27）

### Hard constraints

- 不修改任何 production code；不 build image、不 deploy、不 commit、不 push。
- Bundle 取自当前 Windows `competition-dev` 未提交 working tree；不把 GitHub 干净 baseline 当作候选。
- Bundle 禁止包含 `.git`、venv/node_modules、数据库、上传图片、`.env`、密钥、Authorization/Bearer 值或任何 secret value。

### Gates

- [x] 1. 盘点并复制 candidate source、T-07/T-07B/T-08/T-08B evidence 与既有报告。
- [x] 2. 重新保存 Search/Extractor/T-08/T-08B/backend/diff-check 原始日志。
- [x] 3. 自动生成 final query matrix、safety summary、final 16-class status、environment、README。
- [x] 4. 生成 manifest，执行 whole-bundle secret scan 并确认 PASS。
- [x] 5. 生成 ZIP，记录 ZIP size/SHA256，并完成 bundle 自检。

### Error log

- 暂无。
- 2026-08-27：PowerShell 对 `Select-Object -Index (300..335),(500..545)` 的数组参数转换失败；仅阅读命令失败，未修改项目，改用分段范围读取。
- 2026-08-27：PowerShell `Copy-Item -LiteralPath` 不展开 `*.py` 通配符，首次 bundle 复制在 candidate source 阶段停止；仅创建了目标目录，未复制文件，改用 `Get-ChildItem | Copy-Item`。
- 2026-08-27：首次生成 T-08B live evidence JSON 时把 Pydantic conclusion 对象直接交给 `json.dumps`，导致 `TypeError`；请求已完成但文件未写入，改用 `model_dump(mode="json")` 后重跑。
- 2026-08-27：bundle 整理命令因包含删除 bundle 内误放的重复 `pyproject.toml` 被执行策略拒绝；未改变项目或 bundle 内容，后续只复制正确位置并保留重复文件以避免破坏性操作。
- 2026-08-27：生成 bundle 文档 patch 时误写入 repo 内临时 `evidence/t08b/placeholder.txt`；已立即删除该误写文件，未影响原有项目材料。

### Final Work Review Bundle result

- Bundle directory and ZIP generated; candidate source, original T-07/T-07B evidence, T-08/T-08B fixtures/results, raw test logs, auto query matrix, safety/status matrices, manifest and secret scan are present.
- Whole-bundle secret scan = PASS; manifest self-entry is explicitly excluded because it is self-referential.
- No production code changed during bundle creation; build/deployment/commit/push = NO.

## T-08C Research Analysis Language Closure（2026-08-27）

### Hard constraints

- 正式环境冻结；不 build、不 deploy、不 commit、不 push。
- 不改 Tavily Query、SEARCH_QUERY_OVERRIDES、Tavily provider、result count、retry、Normalizer、Entity Guard、Management Guard、Reverse Biological Guard、Confidence Gate、persistence、attribution 或 220-char safety limit。
- 只修复 Research Guard 对 HYSPLIT 叶蝉研究结果句的窄范围漏检；不扩大正向 marker，不把所有“分析”句一概拒绝。
- 保留自然迁飞、气温/适温、越冬恢复、温湿度发生条件和自然扩散等正向证据。

### 阶段与 gates

- [x] 1. 读取既有 live evidence，复现 exact P1 的当前 helper 与最终 extractor 行为。
- [x] 2. 增加窄 Research Analysis/Model/Parameter Result guard，并固化 T-08C negative、adjacent-negative 与自然 positive regression；新增测试 11/11 PASS。
- [x] 3. Replay T-08 12/12、T-08B 全部 fixture，运行 selected/full backend pytest 与 diff-check：selected 139、full 173（1 条既有 warning）、diff-check PASS。
- [x] 4. 对五个指定 pair 各执行一次 retrieval-only live audit；叶蝉按既定上限完成第 2/3 次重试；五个 requested pollution 均为 0。
- [x] 5. 根据实际 live safe sentence reconcile 南瓜白粉病报告/status 文档，不修改其 extractor 行为。
- [x] 6. 生成 `T08C_RESEARCH_ANALYSIS_LANGUAGE_CLOSURE_REPORT.md`，给出 T-08C/T-08/T-08B final gate 与 Ready for Work re-review 结论。

### Error log

- 2026-08-27：PowerShell 对 `Select-Object -Index (300..335),(500..545)` 的数组参数转换失败；仅阅读命令失败，未修改项目，改用分段范围读取。
- 2026-08-27：T-08C 新增自然叶蝉回归首次出现 1 个失败：单独越冬事实本身没有当前 possible_causes 的 cause marker，旧 extractor 即不输出；该失败不是新 Research Guard 回归，已调整测试为验证 helper 不拒绝，另以含发生条件上下文的句子验证最终保留。
- 2026-08-27：最后 artifact validation 从 `backend` 目录使用了错误的相对路径 `artifacts/t08c/...`，读取失败，未修改文件；改用仓库根目录绝对路径复核。

### Final

- T-08C Research Analysis Language Closure = PASS；T-08 = PASS；T-08B = PASS；Ready for Work re-review = YES。正式环境冻结，build/deployment/commit/push = NO。

## T-08C Incremental Work Re-Review Bundle（2026-08-27）

### Hard constraints

- 不修改代码；不 build、不 deploy、不 commit、不 push。
- Bundle 必须取当前 Windows `competition-dev` working tree 与 HEAD=`0075f63325ec2a5f8515586039458ebdbd135a9c`，不能替换为干净 baseline。
- Bundle 不得包含 `.git`、venv/node_modules、数据库、上传图片、`.env`、`backend.env`、密钥、Authorization/Bearer 值或 secret value。
- T-07 不重新审核；只复核 T-08C P1 closure、T-08/T-08B regression、五 pair pollution 与 Pumpkin reconciliation。

### Gates

- [x] 1. 复制最新 candidate source、直接依赖 tests、T-08C report/evidence 与 P1 closure summary。
- [x] 2. 重新保存 T-08C/selected/backend/diff-check 原始日志及 Git 状态/差异文件。
- [x] 3. 生成 README、environment、五 pair live summary、MANIFEST 与全 bundle secret scan：PASS。
- [x] 4. 生成 ZIP，完成 ZIP size/SHA256 与 bundle self-check：PASS。
- [x] 5. 返回 `T-08C Incremental Work Re-Review Bundle Report`，并记录 build/deployment/commit/push 全部 NO。

### Error log

- 暂无。
- 2026-08-27：生成 bundle live summary 时从仓库根目录误调用 `\.venv\Scripts\python.exe`，解释器路径不存在，未写入文件；改在 `backend` 目录使用项目 venv 重跑。

### Final

- Bundle gates 全部 PASS；T-08C/T-08/T-08B = PASS；Remaining P0/P1 = NONE；ALLOW NEW BACKEND CANDIDATE BUILD。只生成复审材料，不改变 production code 或正式环境。

## New Backend Candidate Build + Candidate-only Validation（2026-08-27）

### Hard constraints

- 只构建/验证新的 Backend candidate；不修改 production source、Query、Extractor、Normalizer、Guards、Confidence Gate、Detector/VLM、正式 aliases、Gateway 或正式容器。
- 不 commit、push、PR、正式 deployment；`lab-backend-1`、`lab-web-1`、`lab-detector-1`、`lab-gateway-1`、`lab-vlm-1` 必须保持不变。
- candidate 必须从当前 Windows `competition-dev` 未提交 working tree 构建，不能使用 GitHub clean baseline。

### Gates

- [x] 1. 构建前 branch/HEAD/status/diff-check/relevant source hashes 与 Work bundle 一致。
- [x] 2. `/data/ghl/app-next-t08c-20260827` staging 完整同步，Windows/Lab manifest 0 mismatch（132/132 files）。
- [ ] 3. Backend-only Docker build 成功，new image ID 与旧批准 image 不同（FAIL：基础镜像 metadata 获取网络超时）。
- [ ] 4. 非正式 candidate runtime health/config/persistence/Knowledge/Tavily 基础门禁 PASS（未执行，因 build FAIL）。
- [ ] 5. Candidate runtime Query matrix、T-08C P1 replay、五 pair safety audit PASS（未执行，因 build FAIL）。
- [ ] 6. Early-blight canonical E2E、Grub E2E、low-confidence gate、source scarcity regression PASS（未执行，因 build FAIL）。
- [ ] 7. 生成 candidate validation report；仅保留 candidate image，不做 formal switch（无新 image）。

### Error log

- 2026-08-27：构建前探查误读取不存在的 `backend/Dockerfile`，PowerShell 报路径不存在；未执行 build，已确认实际候选 Dockerfile 为 `deploy/lab/Dockerfile.backend`。
- 2026-08-27：首次生成 canonical manifest + source archive 的组合 PowerShell 命令因多层 here-string/引号组合被执行策略拒绝；未写入 manifest、未创建 archive，改拆为独立 Python 与 tar 步骤。
- 2026-08-27：拆分后的 tar 命令仍因包含组合删除/条件与多路径参数被执行策略拒绝；未创建 archive，改用 `tar.exe` 直接创建到已确认不存在的明确目标。
- 2026-08-27：首次生成 canonical manifest + source archive 的组合命令未执行；已拆分后分别成功生成 manifest/archive，未影响 staging。
- 2026-08-27：Backend-only Docker build 在 `/data/ghl/app-next-t08c-20260827` 因 DNS/网络超时无法获取 `python:3.12-slim` metadata，build 返回 FAIL；按要求停止，未现场修代码、未启动 candidate runtime、未执行 E2E/live audit。
- 2026-08-27：新 image 内容验证的远端 shell loop 在 `set -u` 下因 `$p` 嵌套展开错误中止；image inspect 已成功保存，未修改 image，改用 `docker run --entrypoint sha256sum` 逐文件直接读取。
- 2026-08-27：复制 image hash 后的本地比较命令从仓库根目录误用 `\.venv\Scripts\python.exe`，解释器路径不存在；scp 已成功，改在 `backend` 目录用项目 venv 比较。

### Final

- Candidate-only build gate FAIL；原因记录于 `artifacts/candidate-build-20260827/docker-build.log`。按要求停止；未进行 runtime/E2E/formal switch。

## Backend Candidate Offline Build Recovery（2026-08-27）

### Hard constraints

- 不修改 production source、Query、EvidenceExtractor、Normalizer、Guards、requirements/dependencies、正式 containers、Gateway、Detector/VLM；不 commit、不 push、不 formal deployment。
- 优先只读检查本地 Python base image；如不存在，才允许使用已批准旧 Backend image 做 immutable overlay，且临时 Dockerfile 只能放 deployment audit/staging 区域。
- 任何 build FAIL 立即停止，不现场修业务代码。

### Gates

- [x] 1. 本地 base image 与 dependency parity 检查：本地无 Docker CLI/base image；approved old image immutable overlay 可用，dependency-affecting diff=0。
- [x] 2. 旧 image runtime source manifest 与当前 staging diff，记录 7 个历史备份 missing、19 个 shared runtime SHA mismatch，overlay 文件清单自动生成。
- [x] 3. approved-image overlay build 完成且 `--pull=false --network=none`；new image=`sha256:18430c930af555c6849ecec82c28967c4061dac1ce81e0470f16f622ff87cebc`。
- [x] 4. 新 image content/inheritance hash 验证：19/19 overlay SHA match；CMD/ENTRYPOINT/WorkingDir/User/Env 全部 unchanged。
- [ ] 5. Candidate runtime、Query/P1/five-pair、Early-blight/Grub/low-confidence 验证（基础 runtime、Query、P1 PASS；五 pair Tavily live FAIL，按规则停止后续 E2E）。
- [x] 6. 生成 recovery report；正式环境保持 unchanged；最终 `CANDIDATE FAIL`，不进入 formal Backend update review。

### Error log

- 2026-08-27：无本地 Docker CLI，仅远端 Lab Docker 可用；按要求在远端执行只读 image 检查。
- 2026-08-27：生成 dependency parity/overlay list 命令在已位于 `backend` 的工作目录再次执行 `Set-Location backend`，产生 harmless path warning；脚本仍用绝对仓库路径成功写入 parity、overlay Dockerfile 与 file list，未改代码。
- 2026-08-27：从旧 image 临时容器复制 `/opt/ghl/backend/pyproject.toml` 时发现该路径不存在，远端命令在清理前中止；已确认 app 复制阶段完成，后续先清理该已知临时容器并检查旧 image 实际文件路径，不读取 secret。
- 2026-08-27：old image `/opt/ghl/backend/app` manifest 与当前 staging 存在 7 个历史备份文件 missing、19 个 runtime files SHA mismatch；这是本次要求的 baseline diff，非执行错误，已落盘 `runtime-source-diff.json`，后续按完整 changed list 生成 overlay。
- 2026-08-27：批量 scp 复制旧 image inspect 时发现首次失败的远端临时命令未生成 `old-image-inspect.json`；前两个依赖证据已复制，改为单独远端生成 image inspect 后再取回。
- 2026-08-27：approved-image immutable overlay build 成功；使用 `--pull=false --network=none`，未触发 registry/DNS；19 个 reviewed runtime files 逐项 COPY，无 pip install、无 CMD/ENTRYPOINT 变更。
- 2026-08-27：new image content/inheritance verification PASS；19/19 overlay file SHA match，image ID changed，runtime inheritance fields/environment SHA unchanged。
- 2026-08-27：首次候选 persistence/config 检查的 PowerShell 内嵌引号转义错误导致 ParserError，未执行远端检查；改用 `docker exec -i ... python -` 通过 stdin 重跑，未触碰候选或正式容器。
- 2026-08-27：候选首次启动读取 `backend.env` 后 `search_provider=disabled`，不满足 Tavily 可用门禁；仅删除本次创建的候选容器并以显式 `CROP_SEARCH_PROVIDER=tavily` 重启，正式容器未动，密钥未读取/输出。
- 2026-08-27：并行候选状态检查中的 PowerShell/SSH `docker inspect --format` 引号传递失败并返回空输出；改用 `docker ps`/直接 inspect 重跑，健康与配置检查本身已成功。
- 2026-08-27：首次候选 Query matrix introspection 将 `QueryType`（`typing.Literal`）误当作 Enum 访问，容器内返回 `AttributeError`；未改动容器，改用其实际字符串值 `harms`/`possible_causes` 重跑。
- 2026-08-27：候选五 pair 真实 Tavily retrieval 审计全部返回 `status=error`、raw=0，Normalizer=unavailable；失败证据写入远端 `candidate-live-safety.json`。按门禁立即停止，未执行 Early-blight/Grub/low-confidence/source-scarcity E2E。

### Final

- Offline recovery build/image gates PASS；candidate health/config/persistence、16-class Query matrix、T-08C P1 replay PASS。
- 五 pair live Tavily retrieval 全部 error，按“任一 FAIL 即停止”未运行后续 E2E；最终 `CANDIDATE FAIL`。
- Report：`BACKEND_CANDIDATE_OFFLINE_BUILD_RECOVERY_REPORT.md`。新 image 保留；formal containers/aliases unchanged；build/deployment switch、commit、push 均未执行。

## Candidate Tavily Runtime Error Forensic（2026-08-27）

### Objective / hard constraints

- 只调查 candidate image `sha256:18430c930af555c6849ecec82c28967c4061dac1ce81e0470f16f622ff87cebc` 的 Tavily runtime `status=error`。
- 不修改 production code、Query、Extractor、Normalizer、requirements/dependencies；不 rebuild、不 deploy、不 commit、不 push。
- 只允许复用既有 candidate runtime contract；正式 containers、formal alias `backend`、Gateway、Detector/VLM 保持冻结。
- 先做单个稳定 Query 和分层 DNS/TCP/TLS/HTTP forensic；只有单个 Query available 才恢复并重跑五 pair；只有五 pair PASS 才继续原 E2E。

### Gates

- [x] 1. 同 image candidate restart；secret presence/non-empty 与 `CROP_SEARCH_PROVIDER=tavily` 容器内确认。
- [x] 2. 单个最小 Tavily retrieval 捕获 provider status、exception class/message、HTTP status/body 摘要与 timeout/DNS/TLS 分类：初始 `ConnectTimeout`/10s；mapping recovery 后 available/5。
- [x] 3. DNS/TCP/TLS/HTTP 分层检查；18443 tunnel/relay 只读确认，无需恢复 tunnel。
- [x] 4. successful runtime 与当前 candidate 的非 secret contract diff；overlay/base 网络相关内容 unchanged 证明。
- [x] 5. mapping recovery 后原五 pair、Early-blight/Grub/low-confidence 均 PASS。
- [x] 6. 生成 `CANDIDATE TAVILY RUNTIME ERROR FORENSIC REPORT`，记录 root cause、recovery 与 formal/git 状态。

### Error log

- 2026-08-27：本轮尚未执行 forensic action；所有错误将按发生顺序追加。
- 2026-08-27：首次候选 `docker inspect --format` 使用 PowerShell/Go template 嵌套引号失败，返回 template parsing error；未读取 Env，改用只输出 JSON 安全字段的 template 重跑。
- 2026-08-27：首次分层网络检查的 orchestration 变量名写错（`ps` 未定义），工具脚本在本地立即失败，未执行远端网络检查；改正变量名后重跑。
- 2026-08-27：远端 `ss`/`/dev/tcp` 组合检查在打印 127.0.0.1:18443 listener 后无返回并被中断；listener 证据已取得，relay TCP/TLS 采用独立短检查，不重复该挂起命令。
- 2026-08-27：首次对成功 runtime 与当前 candidate 的容器内环境对比使用的 SSH/Python 引号转义失败，两次均为本地 shell 传参导致 `SyntaxError`；未输出 secret，改用 stdin 传递只输出非敏感字段的 Python 检查。
- 2026-08-27：candidate 最小请求捕获 `ConnectTimeout`（10s，HTTP status/body 均无）；分层结果为 candidate 内 `api.tavily.com` DNS `gaierror: Temporary failure in name resolution`，而 `host.docker.internal`/`172.17.0.1:443` TCP PASS。
- 2026-08-27：成功 runtime `lab-backend-next-test` 对同一 Early-blight Query 返回 `available`/5 sources；其唯一相关 runtime 差异为 `extra_hosts api.tavily.com:172.17.0.1`。新旧 image 的 Python、CA、httpx/httpcore 与 package set 完全一致，overlay 未改变网络依赖。
- 2026-08-27：既有 `127.0.0.1:18443` listener 存在，`openssl s_client` 对该端口 SNI=`api.tavily.com` 为 TLSv1.3/verification OK；candidate 到 relay `172.17.0.1:443` TCP/TLS/SNI 也 PASS，因此未恢复或重设计 tunnel。
- 2026-08-27：补回既有 `--add-host api.tavily.com:172.17.0.1` 后单个 Early-blight Query 恢复 `available`/5 sources；root cause 归类为 candidate runtime startup mapping mismatch，recovery 仅改候选启动参数。
- 2026-08-27：恢复后五 pair retrieval→Normalizer→Extractor 全部 PASS（raw/normalized=5/5，requested pollution=0）；允许继续 candidate-only E2E。
- 2026-08-27：首次 Early-blight candidate upload 使用 `curl --fail` 返回 HTTP 422 且隐藏了 response body；未创建病例，改用不带 `--fail` 的同范围请求获取非敏感 validation detail。
- 2026-08-27：改用 SSH stdin 传递 upload 脚本时，curl form/URL quoting 仍导致 `curl (3) URL using bad/illegal format`，未创建病例；改用远端变量与双引号 form 参数重跑。
- 2026-08-27：定位上述 curl (3) 根因是 PowerShell stdin 传递 CRLF，远端 bash 将 URL 末尾 `\\r` 视为非法字符；后续 SSH stdin 脚本统一先移除 CR。
- 2026-08-27：首次尝试移除 CR 的 PowerShell `.Replace` 参数类型与 JS 字符串中的 SSH key 路径反斜杠均处理错误；本地未建立有效 SSH 会话，改用显式 `[string][char]13` 和双反斜杠路径。
- 2026-08-27：即使移除已有 CR，PowerShell 管道到 SSH 仍将 upload 脚本按 CRLF 传输，curl (3) 再现且未创建病例；改用 base64 单行传输远端脚本，避免 stdin 换行转换。
- 2026-08-27：编排层首次尝试用 JavaScript `btoa` 编码远端 upload 脚本，但当前 exec isolate 不提供 `btoa`，未执行远端操作；改用 PowerShell UTF-8/Base64 编码。
- 2026-08-27：Grub detect API 已完成并写入远端临时 JSON，但后续 SSH/Python 引号转义使摘要解析 `SyntaxError`；未影响病例或检测结果，改用 Base64 编码的远端摘要脚本读取既有 JSON。
- 2026-08-27：low-confidence、Early-blight、Grub candidate-only E2E 全部完成；三病例摘要与 hash/来源/门控证据已落盘 `candidate-e2e-summary.json`。

### Final

- Root cause=`Candidate image/runtime mismatch`：candidate startup 缺少既有 `api.tavily.com:172.17.0.1` host mapping；不是 secret、tunnel、TLS、HTTP API 或 overlay image dependency 问题。
- 仅通过 candidate runtime startup 参数恢复后，single Query、five-pair safety、Early-blight、Grub、low-confidence 全部 PASS；最终 `CANDIDATE PASS / READY FOR FORMAL BACKEND UPDATE REVIEW`。
- Report：`CANDIDATE_TAVILY_RUNTIME_ERROR_FORENSIC_REPORT.md`；formal containers/aliases unchanged；本轮 build/deployment/commit/push=NO。
- 2026-08-27：首次定位 server-side E2E fixtures 的 SSH command 在远端 shell 中错误转义 `for` 循环路径，返回 bash syntax error；未修改文件，改用无循环的独立只读命令。

### Final

- 待 forensic gates 完成；不因上一轮 `CANDIDATE FAIL` 自动改判。

### Final

- 待 offline recovery gates 完成；若旧 image overlay 可行则继续，否则报告具体阻塞并停止。

## Formal Backend-Only Update Review Bundle（2026-08-27）

### Objective / hard constraints

- 仅生成增量、只读、可独立审计的 Backend-only formal update review bundle。
- 不修改 production code，不修改 candidate image，不 rebuild，不 deploy，不 stop formal containers，不 commit，不 push。
- Candidate image 必须保持 `sha256:18430c930af555c6849ecec82c28967c4061dac1ce81e0470f16f622ff87cebc`；formal 五容器保持冻结。

### Gates

- [x] 1. 创建 bundle 目录并复制两份核心报告及直接相关 build evidence。
- [x] 2. 生成脱敏 image、candidate runtime、host mapping、root-cause 与 validation evidence。
- [x] 3. 只读保存 formal current runtime inspect、planned contract、diff、rollback 与 update scope。
- [x] 4. 生成 Git evidence、README、environment、secret scan、MANIFEST；禁止 secret value/数据库/上传图片进入 bundle。
- [x] 5. 生成 ZIP，执行 ZIP self-test，记录 size/SHA256；生成 `FORMAL_BACKEND_ONLY_UPDATE_REVIEW_BUNDLE_REPORT.md`。

### Error log

- 2026-08-27：bundle 生成开始；初始阶段尚无本轮新增执行错误。
- 2026-08-27：首次创建 bundle 目录的本地编排字符串因 JS/PowerShell 反斜杠转义触发 `SyntaxError: Unexpected number`，未执行文件操作；改用正斜线路径后目录和核心 evidence 创建成功。
- 2026-08-27：首次 formal inspect 编排字符串因嵌套 JSON/PowerShell 大括号触发 `SyntaxError: Unexpected token '{'`，未连接远端；改用 raw template 后只读 inspect/status 成功，未修改正式容器。
- 2026-08-27：首次 image evidence 文本生成编排字符串因 PowerShell 换行反引号与 JS 模板字面量冲突触发 `SyntaxError: Unexpected identifier 'n'`，未写入目标文件；改用 `[Environment]::NewLine` 后生成成功。
- 2026-08-27：首次 five-pair Markdown 生成编排字符串因 Markdown 反引号与 JS 模板字面量冲突触发 `SyntaxError: Unexpected identifier 'PASS'`，未写入目标文件；改用不含反引号的等价文本后生成成功。
- 2026-08-27：首个 ZIP self-test/manifest 重算组合命令被本地 PowerShell 执行策略拒绝，未创建临时解压目录、未改 bundle、未改 ZIP；改拆为小步骤执行。
- 2026-08-27：最终 ZIP self-test 首次解析解压后的 manifest 总数时，PowerShell 正则未匹配 `total file count`，校验命令退出 FAIL；未修改 bundle/ZIP，改用直接文本行解析重跑。

### Final

- Bundle=`C:\Users\genghailong\Documents\competition-backend-only-update-review-20260827`，ZIP=`C:\Users\genghailong\Documents\competition-backend-only-update-review-20260827.zip`。
- Bundle 69 files/186707 bytes（不计 MANIFEST 自身）；secret scan=PASS；ZIP self-test=PASS；ZIP=93008 bytes，SHA256=`7E456ADD3AC27435F66141BA9B7DA8089588EDE13055CC9FBBB27BCAE3A90B86`。
- Candidate image 保持 `sha256:18430c930af555c6849ecec82c28967c4061dac1ce81e0470f16f622ff87cebc`；formal 五容器保持冻结；production source modified during bundle creation=NO；build/deployment/commit/push=NO。
- Final report：`FORMAL_BACKEND_ONLY_UPDATE_REVIEW_BUNDLE_REPORT.md`。

## Formal Backend-Only Update（2026-08-27）

### Authorization / hard constraints

- Work approval confirmed: `Overall=PASS`, `Remaining P0/P1=NONE`, `ALLOW FORMAL BACKEND-ONLY UPDATE`。
- Only `lab-backend-1` may be replaced with candidate image `sha256:18430c930af555c6849ecec82c28967c4061dac1ce81e0470f16f622ff87cebc`。
- `lab-web-1`、`lab-gateway-1`、`lab-detector-1`、`lab-vlm-1` must remain unchanged。
- No production source edit、rebuild、dependency change、commit、push；no secret values may be output。

### Gates

- [x] 1. Preflight all formal services, current Backend/API/Gateway, candidate image, relay/tunnel, disk, Docker, SQLite。
- [x] 2. Create and verify fresh backup, including integrity check and rollback material。
- [x] 3. Capture complete pre-switch rollback manifest and current Backend inspect。
- [ ] 4. Replace only `lab-backend-1` with exact runtime contract and both host mappings。
- [x] 4. Replace only `lab-backend-1` with exact runtime contract and both host mappings。
- [x] 5. Runtime parity and Backend foundational gates PASS。
- [x] 6. Tavily DNS/TCP/TLS/provider gate PASS from new formal Backend。
- [ ] 7. Gateway/Web/API regression and Early-blight/Grub/low-confidence/five-pair smoke PASS（FAIL：formal five-pair 叶蝉科 possible_causes 出现管理建议污染）。
- [ ] 8. Generate final deployment report；因 safety trigger 先 rollback，等待回滚验证完成。

### Error log

- 2026-08-27：planning skill 的 `session-catchup.py` 首次调用返回 exit=1；显式路径重跑返回 exit=9009，原因是当前 Windows `python.exe` 仅为 Microsoft Store shim、没有可用 Python 解释器。已改为直接读取 planning files，未影响部署前检查，未执行任何远端变更。
- 2026-08-27：Preflight SQLite 命令的嵌套引号在本地 PowerShell 解析失败，未执行远端 SQLite 检查；改用 base64 编码的容器内只读 Python 脚本。
- 2026-08-27：Preflight HTTP 循环命令中的 `/dev/null` 与 `true` 被本地 PowerShell 误解析，未得到 HTTP 结果；改用逐 URL SSH 调用。
- 2026-08-27：Preflight 存储批量 `ls` 检查发现 `/data/storage/evidence` 不存在并退出 1；未修改存储。继续只读核对正式 storage 布局，确认 evidence 是否位于 reports 或其它已配置目录。
- 2026-08-27：Preflight gateway API 逐项循环在 `/history` 后 SSH 会话未完整返回；已取得 gateway `/health=200`、`/=200`，后续回归改为带超时的逐项调用。
- 2026-08-27：Preflight SQLite 首次命令曾因本地 PowerShell 引号失败，后续 base64 容器脚本已得到 `sqlite_integrity=ok`。
- 2026-08-27：Preflight 首次复杂 HTTP/DNS 编排中本地 PowerShell 解析了远端 shell 语法，未产生有效结果；改用逐项/base64 检查，relay/tunnel listener 与 Backend/Gateway health 已取得。
- 2026-08-27：Preflight 存储布局探查的一次组合编排因 JS 字符串嵌套触发 `SyntaxError`，未执行远端操作；改用逐项 SSH 探查并确认 evidence snapshots 位于 reports JSON。
- 2026-08-27：Fresh backup 首次复制命令的本地编排因嵌套引号触发 `SyntaxError`，未执行；随后 raw template 命令完成目录与复制。
- 2026-08-27：Fresh backup 首次复制 Knowledge 使用宿主机路径 `/data/ghl/knowledge/baidu-baike-20260818`，该路径不存在；SQLite、persistence、uploads、reports、evidence snapshots、runtime control、deploy/runtime 配置已复制，切换未执行。改用当前正式容器内 `/opt/ghl/knowledge/baidu-baike-20260818` 通过 `docker cp` 补齐。
- 2026-08-27：Fresh backup 首次验证/manifest 远端命令包含管道与嵌套引号，SSH 远端 shell 报 `syntax error near unexpected token '|'`；未改变 backup 内容，改用无管道、分步可验证命令。
- 2026-08-27：Backup 严格路径校验发现首次复制链因 Knowledge 错误在其后提前停止，`sqlite/crop-pest.sqlite3` 与 `deploy-runtime/docker-compose.yml` 尚未落盘；此前远端命令末尾 `du` 返回 0 造成误判。已暂停切换，补齐后采用逐项状态码校验。
- 2026-08-27：首次创建新正式 Backend 的 `docker run` 因远端 shell 将含空格的 `CROP_INSTANCE_LABEL=实验室 CPU` 拆参，Docker 报 `invalid reference format`；未创建新容器。旧容器仍保留为 stopped/renamed rollback anchor，改用显式引号重试。
- 2026-08-27：切换后基础门禁聚合脚本在 Python 单行代码中于分号后定义 `def`，返回 `SyntaxError`；未改变新容器，改为无函数、逐请求的只读脚本。
- 2026-08-27：正式 smoke 脚本第一个 Early-blight upload 返回 HTTP 422，`set -e` 立即停止，未创建后续病例；新 Backend 仍运行且未触发 rollback。先读取 upload detail，定位表单编码后重跑。
- 2026-08-27：正式 five-pair 独立脚本首次 `docker exec` 未指定 `/opt/ghl/backend` WorkingDir，容器返回 `ModuleNotFoundError: No module named 'app'`；未改变正式数据/容器，改用 `docker exec -w /opt/ghl/backend` 重跑。
- 2026-08-27：首次标记为 WorkingDir 重跑的命令实际仍遗漏 `-w`，相同 `ModuleNotFoundError` 再现；未改变正式数据/容器，改用显式 `PYTHONPATH=/opt/ghl/backend`。
- 2026-08-27：正式 five-pair safety gate FAIL：叶蝉科 `possible_causes` 输出包含“温室附近不种植十字花科蔬菜，以免除危害”管理建议，Management pollution 不为 0；按 rollback trigger 立即回滚，不继续 smoke。
- 2026-08-27：回滚第一步命令的 JS 编排字符串再次因内嵌引号触发 `SyntaxError`，未执行远端 stop；改用 raw template 后旧/新容器回滚步骤全部成功。
- 2026-08-27：回滚后并行验证编排字符串因 Windows 路径/字符串组合触发 `SyntaxError: Unexpected identifier 'C'`，未执行验证命令；改为逐项执行。
- 2026-08-27：回滚后 Gateway API 单项补验的一次本地字符串编排触发 `SyntaxError`，未执行远端请求；改用 raw template 后 `/api/cases=200`。
- 2026-08-27：回滚后 Tavily 单项验证的一次本地字符串编排触发 `SyntaxError`，未执行远端请求；改用 raw template 后 provider `available`/5、DNS `172.17.0.1`。

### Final

- 正式切换已触发 safety rollback；新 Backend 已移除、pre-switch 旧容器已恢复，回滚后健康/Gateway/Detector/Tavily/SQLite/history 验证完成，最终状态=`ROLLED BACK`。

## T-08D — Leafhopper Management-Clause Safety Closure（2026-08-27）

### Objective / assumptions / hard constraints

- 根因假设已由 formal five-pair 复现确认：事实性生态条件与管理/防治建议拼在同一中文复合句中，现有句级 management guard 未拆出管理尾部，导致其进入 `possible_causes`。
- 最小修复：仅修改 `backend/app/search/evidence_extractor.py` 与新增窄范围 T-08D regression test；在 `possible_causes` 候选选择阶段按中文 clause boundary 拆分并逐段复用现有 guards，保留安全自然事实、拒绝管理 clause。
- 禁止修改 Normalizer、Query/Tavily、Confidence Gate、API schema、前端、架构、依赖；formal backend 保持已安全回滚；不 build、不更新 candidate image、不 deploy、不 commit、不 push。

### Gates

- [x] 1. 记录 exact formal leafhopper regression、root cause 与 safe rollback 状态。
- [x] 2. 实施最小 clause-level extractor 修复与 11 项 T-08D tests（参数化执行 14 passed）。
- [x] 3. T-08 replay 原始 baseline 12/12、当前 T-08 suite 31 passed、T-08B 34/34、T-08C 11/11 PASS。
- [x] 4. Selected search/extractor=153 passed；full backend=187 passed，记录 1 个既有 warning。
- [x] 5. 五 pair local deterministic replay 四类 pollution 全为 0。
- [x] 6. retrieval-only live leafhopper 两次 PASS；五 pair live safety 全为 0。
- [x] 7. git status/diff-stat/diff-check PASS；build/deploy/image update/commit/push 均 NO。
- [x] 8. 已生成 `T08D_LEAFHOPPER_MANAGEMENT_CLAUSE_SAFETY_CLOSURE_REPORT.md`，最终 `T-08D PASS / READY FOR WORK INCREMENTAL REVIEW`。

### Error log

- 2026-08-27：T-08D 开始；planning catch-up 的 Windows Python shim 不可用为前轮已记录问题，本轮直接读取三个 planning 文件并继续，未执行部署操作。
- 2026-08-27：T-08D 首轮 targeted pytest 为 13 passed/1 failed；反向混合句的短管理 clause 被提前从 split 列表过滤，导致整句仍被 management guard 拒绝。修正为先识别所有 clause，再过滤短输出 clause。
- 2026-08-27：T-08D 调试命令首次未显式导入私有 `_sentences`，返回 `NameError`；未修改代码，补充显式导入后完成决策路径核对。
- 2026-08-27：保留回归首次发现 T-08 研究/喷施复合句被 split 绕过 research guard；已将 research-context sentence 设为不可拆分，随后 T-08/T-08B/T-08C=76 passed。
- 2026-08-27：selected extractor/search 首次发现既有有机肥 intervention-effect 句被 split 绕过整句拒绝；已将 intervention-effect 与 research/entity guard 一起设为不可拆分，随后 selected suite=153 passed。
- 2026-08-27：full backend 首次因已进入 `backend` 工作目录仍使用 `backend/.venv/...` 路径，未运行 pytest；改用 `.venv/Scripts/python.exe` 后通过。
- 2026-08-27：live 临时容器首次两次 `docker run/create` 因参数格式返回 `invalid reference format`，未创建运行容器；改用逐步 `docker create`、`source/target` mount 与 `--add-host=` 语法后启动成功。
- 2026-08-27：为避免“减少/控制”管理 regex 的机械误杀，收紧为必须同时带管理对象；收紧后 targeted=153 passed、full backend=187 passed/1 warning，并重新完成 live leafhopper 与五 pair safety。

### Final

- T-08D targeted=14 passed；T-08 current suite=31 passed（原始 T-08 replay baseline=12/12）、T-08B=34 passed、T-08C=11 passed；selected extractor/search=153 passed；full backend=187 passed，1 个既有 Starlette/httpx deprecation warning。
- 五 pair local deterministic replay 与五 pair live safety 均为 research=0、management=0、reverse=0、wrong_entity=0；叶蝉 live 两次均 provider available/raw=5/normalized=5，无管理污染。
- formal Backend 仍安全回滚到 approved image；candidate image 保留；本轮只读 live 临时容器已清理；build=NO、candidate image update=NO、formal deploy=NO、commit=NO、push=NO。
- Report=`T08D_LEAFHOPPER_MANAGEMENT_CLAUSE_SAFETY_CLOSURE_REPORT.md`；T-08D 状态=PASS / READY FOR WORK INCREMENTAL REVIEW。

## T-08D Incremental Work Review Bundle（2026-08-27）

### Objective / hard constraints

- 为 ChatGPT Work 创建独立、增量、可审计 bundle：`C:\Users\genghailong\Documents\competition-t08d-work-review-20260827` 及同名 ZIP。
- 仅复制 T-08D 核心报告、实际 source/test/planning、证据、验证输出、原始测试日志和 Git/secret/manifest 证据；不重新打包 T-07/T-08/T-08B/T-08C 全部历史材料。
- 本阶段只读审查：禁止 production source/Query/Normalizer/Tavily/Confidence Gate/API/frontend/dependencies 修改；禁止 build、deploy、candidate image update、formal restart、commit、push。

### Gates

- [x] 1. 创建 bundle 目录结构并复制最新 T-08D source/tests/planning/context。
- [x] 2. 保存 exact blocker、clause、management guard、positive、T-08C research evidence。
- [x] 3. 保存真实 T-08/T-08B/T-08C/T-08D/selected/full backend/Git 原始日志。
- [x] 4. 生成并核验 local five-pair replay、live leafhopper、five-pair live validation。
- [x] 5. 完成 scope audit、secret scan、README、MANIFEST 与 independent manifest verification。
- [x] 6. 生成 ZIP、ZIP self-test、size/SHA256 和根目录 bundle report。
- [x] 7. 确认 no P0/P1、ALLOW NEW BACKEND CANDIDATE REBUILD FOR T-08D；不允许直接 formal deployment。

### Error log

- 2026-08-27：Bundle 阶段开始；目标目录不存在，按增量目录创建；当前 branch/HEAD 已记录，正式 Backend 保持此前安全回滚状态。
- 2026-08-27：首次生成 pytest 原始日志时错误切片参数，将 `pytest` 当作 Python 脚本路径，返回 `can't open file ... pytest`；未运行测试，改用完整 `python -m pytest` 参数重写日志。
- 2026-08-27：两次只读验证查询在 backend 工作目录误用了 `backend/.venv` 相对路径；返回解释器不存在，未改变文件或运行环境，随后改用 `.venv/Scripts/python.exe`。
- 2026-08-27：首次 ZIP round-trip 一体化命令因执行器拒绝过长 PowerShell/递归表达式而未执行；拆分为压缩、解压、逐文件哈希校验后通过。
- 2026-08-27：最终收尾摘要命令把 PowerShell `-match` 当作 `Get-Content` 参数，secret/manifest 摘要字段为空；未影响已写入的 PASS 证据，随后用 `.Contains()` 重跑并确认两者均 PASS。

### Final

- Completed：bundle evidence、manifest/ZIP self-test、根报告均已生成；Overall=`PASS`，T-08D/T-08/T-08B/T-08C regression/five-pair safety=`PASS`，Remaining P0/P1=`NONE`，仅允许新 candidate rebuild，不允许 direct formal deployment。

## T-08D New Backend Candidate Rebuild + Candidate-only Validation 开始（2026-08-27）

### Objective / hard constraints

- 使用当前 `competition-dev` working tree（包含 T-07/T-08/T-08B/T-08C/T-08D）构建新的 Backend candidate，并只在 candidate 中验证；不从 GitHub clean baseline 构建。
- 只使用 approved old Backend image `sha256:cf471320e05bef619c0e746f1c05c3c658f39c7e029f5b35b3f8f531f460c420` 作为 immutable offline base，加当前 Work-reviewed runtime source overlay；不访问 registry、不 pip install。
- 禁止修改 Query/Extractor/Normalizer/Confidence Gate/API/frontend/dependencies、架构重构、formal deployment、替换 `lab-backend-1`、commit、push、PR；发现新代码问题或任何安全 gate FAIL 立即停止。
- 新 staging 使用 `/data/ghl/app-next-t08d-20260827`，不覆盖 `/data/ghl/app-next-t08c-20260827`；candidate tag 目标为 `lab-backend:t07-t08d-candidate-20260827`。

### Assumptions / success criteria

- 假设 approved image 已在远端本地可用，且 T-08D 无 dependency-affecting diff；若任一假设不成立，停止并报告。
- Source/staging manifest missing=0、extra=0、SHA mismatch=0；dependency diff=0；overlay runtime diff 自动确定并逐文件记录 old/new SHA256。
- New image 必须不同于旧 candidate `sha256:18430c930af555c6849ecec82c28967c4061dac1ce81e0470f16f622ff87cebc`，image content parity=0 mismatch，inheritance/CMD/ENTRYPOINT/WorkingDir/User/env unchanged。
- Candidate runtime 必须保留 `ghl-internal`、安全 mounts、`host.docker.internal:host-gateway` 和 `api.tavily.com:172.17.0.1`；formal containers/aliases unchanged。
- Candidate PASS 仅在 health/Tavily/exact T-08D/T-08C/live leafhopper/five-pair/Early-blight/Grub/low-confidence 全部 PASS 后成立；否则 CANDIDATE FAIL 并停止。

### Gates

- [x] 1. Source gate：branch/HEAD/status/diff-stat/diff-check/实际 production changed files。
- [x] 2. Dependency parity：requirements/pyproject/lock/Pipfile/setup 文件检查，dependency-affecting diff=0。
- [x] 3. New staging sync and canonical-vs-staging manifest parity。
- [x] 4. Approved base availability and offline build preflight。
- [x] 5. Automatic overlay runtime diff and temporary Dockerfile。
- [x] 6. New candidate image build and image content/inheritance verification。
- [x] 7. Candidate runtime contract, health, detector, SQLite, Knowledge/storage, Tavily DNS/TCP/TLS/provider。
- [x] 8. Exact T-08D runtime replay and T-08C research regression。
- [x] 9. Live leafhopper (2 attempts, max 3) and five-pair live safety。
- [x] 10. Canonical Early-blight, Grub, low-confidence candidate-only E2E。
- [x] 11. Formal environment freeze, Git no commit/push, final report。

### Error log

- 2026-08-27：首次 `ssh ghl` 非 TTY 调用在认证阶段无可用输出；改用 `BatchMode` 禁止密码回退并分配 TTY 后连接成功，未改变远端状态。
- 2026-08-27：初始 canonical context 复制包含 `__pycache__`；删除命令被执行策略拒绝，未删除任何用户文件；改为创建 v2 context 并在复制阶段排除 `__pycache__`。
- 2026-08-27：首次远端 staging manifest 的 `awk`/PowerShell 嵌套命令触发本地解析错误，未改变 staging；改用 `find -exec sha256sum` 分步生成并通过 108/108、missing=0、extra=0、SHA mismatch=0。
- 2026-08-27：首次 overlay 比对脚本错误重复拼接 `backend/` 前缀，误报 21 个 missing/mismatch；未重建镜像，修正路径映射后 21 个 source files、0 missing、0 SHA mismatch。
- 2026-08-27：首次 candidate `docker create` 未引用含空格的 `CROP_INSTANCE_LABEL`，Docker 将 `candidate` 解析为镜像名并报 `candidate:latest` 不存在；未创建容器，改用显式引用后启动成功。
- 2026-08-27：首次候选 SQLite 检查把 `-shm/-wal` 文件纳入 glob，报告 `file is not a database`；第二次误假设存在 `cases` 表；均为只读脚本错误，改查主库并按实际 `diagnosis_cases` 表验证 `integrity_check=ok`。
- 2026-08-27：首次 candidate harness 从 `/tmp` 执行导致 `ModuleNotFoundError: app`；一次仅加 `-w` 的重试仍未生效，未改变候选状态；最终显式设置 `PYTHONPATH=/opt/ghl/backend` 后 replay 成功。
- 2026-08-27：读取 formal failure replay 的诊断打印使用 `ensure_ascii=False`，PowerShell code page 触发 `UnicodeEncodeError`；改用 UTF-8 JSON/`ensure_ascii=True`，未改变证据内容。

### Final

- Candidate-only gates 全部 PASS：source/dependency/staging/offline build/overlay/image/runtime/T-08D/T-08C/live safety/E2E/formal freeze/Git 均通过；禁止 direct formal deployment。
- Candidate tag=`lab-backend:t07-t08d-candidate-20260827`，image=`sha256:3ff9c374d9d14d7d005536b15ba9f76cab4849532f53322c872b9dd0d0adf7d8`；approved base 与旧 candidate image 均保留，新候选临时容器已清理。
- Formal 五容器与 aliases 未改变；未 formal deploy、未 commit、未 push。最终报告=`T08D_NEW_BACKEND_CANDIDATE_VALIDATION_REPORT.md`，决策=`CANDIDATE PASS / READY FOR FORMAL BACKEND UPDATE RE-REVIEW`。
## T-08D Formal Backend Update Re-Review Bundle（2026-08-27）

### Objective / hard constraints

- 为 Work 制作小型增量复核包，只证明 candidate `sha256:3ff9c374d9d14d7d005536b15ba9f76cab4849532f53322c872b9dd0d0adf7d8` 可进入第二次 formal Backend-only update review。
- 仅收集既有 candidate validation evidence，并生成 README、MANIFEST、secret scan、ZIP self-test；禁止修改 production code、build、deploy、commit、push。
- 目标 ZIP：`C:\Users\genghailong\Documents\competition-t08d-formal-update-rereview-20260827.zip`；不重新审核 T-07/T-08/T-08B/T-08C 全部历史逻辑。

### Gates

- [x] 1. 选取并复制最小、脱敏、可审计 evidence；排除源码、数据库、图片、context/tar、密钥值。
- [x] 2. 生成 README、T-08D blocker closure、T-08C、live safety、E2E、runtime/formal/Git evidence。
- [x] 3. Secret scan PASS；MANIFEST 记录 path/size/SHA256。
- [x] 4. ZIP self-test 通过，记录 ZIP size/SHA256。
- [x] 5. 确认 production code/build/deploy/commit/push 均 NO，并完成最终报告。

### Error log

- 2026-08-27：开始制作 T-08D formal update re-review bundle；candidate validation 已 PASS，formal 环境保持冻结。
- 2026-08-27：首个 ZIP self-test 复合命令因执行器拒绝过长嵌套 PowerShell 表达式，未解压、未改变 bundle/ZIP；改用固定临时目录和分步验证。
- 2026-08-27：临时解压目录的 `Remove-Item -Recurse` 及逐项删除命令均被安全策略拒绝；已核对目标为本轮明确创建的临时目录后，使用 .NET `Directory.Delete` 删除，最终目录不存在。

### Final

- Completed：bundle 32 个 manifest entries、secret scan PASS、manifest independent verification PASS、ZIP self-test PASS；ZIP size=42567 bytes，SHA256=`f88a77609537247f34a1add6ea71f35da273206128f1a76995bffd4117d95c54`。production code/build/deploy/commit/push 均 NO；完成后停止，禁止 deploy。

## T-08D Formal Backend Update Re-Review — P1 Closure Evidence Collection（2026-08-27）

### Objective / hard constraints

- 仅关闭 Work 提出的 P1-1 SQLite 主库完整性证据矛盾与 P1-2 正式 `lab-backend-1` runtime inspect 缺失。
- 只读检查；禁止修改代码、测试、配置、compose、database、WAL/SHM、容器、网络、环境变量；禁止 build、deploy、restart、stop、recreate、rollback、commit、push。
- 不重新运行完整 T-08D，不重新审核 T-07/T-08/T-08B/T-08C 历史逻辑；正式切换继续禁止，等待 Work 返回 P1 closure review。

### Gates

- [x] 1. 对正式 Backend 实际 `/data/storage/crop-pest.sqlite3` 主文件执行只读 `PRAGMA integrity_check`，返回 `ok`。
- [x] 2. 调查旧 `file is not a database` 日志；缺少命令级 target 证据，明确标记 historical root cause=`NOT PROVEN`，不猜测。
- [x] 3. 完整脱敏 inspect `lab-backend-1` identity/runtime/network/storage/environment，未泄露 secret values。
- [x] 4. 验证 formal image、`ghl-internal`、`backend` alias、`unless-stopped`、WorkingDir、`/data/storage` mount、两条 required host mappings。
- [x] 5. 生成 evidence package、README、P1 summary、MANIFEST、secret scan、ZIP self-test。

### Error log

- 2026-08-27：planning catch-up 无新增未同步上下文；沿用现有 planning files，未执行远端变更。
- 2026-08-27：首个 P1 task-plan patch 使用不存在的 gate 文本，apply_patch 未修改文件；随后用实际末尾上下文追加本轮 section，未影响代码或证据。
- 2026-08-27：曾误创建 `task_plan.md.tmp_marker` 作为追加探针，立即用 apply_patch 删除；该文件未进入 Git/证据包。
- 2026-08-27：首个 ZIP self-test 复合命令因执行器拒绝复杂嵌套 PowerShell 表达式未执行；改为分步解压/校验，最终通过。
- 2026-08-27：临时目录递归删除命令被安全策略拒绝；确认目标是本轮明确创建的临时目录后使用 .NET `Directory.Delete` 清理成功。
- 2026-08-27：P1 bundle Manifest 首次发现 `SECRET_SCAN.txt` 末尾换行导致一个 size/hash mismatch；刷新该条后 14/14 通过。

### Final

- P1-1 main DB integrity=`PASS`；exact path=`/data/storage/crop-pest.sqlite3`；`PRAGMA integrity_check`=`[('ok',)]`；历史旧错误 root cause=`NOT PROVEN`，因为保留日志没有失败命令或选中文件级证据。
- P1-2 formal runtime contract=`PASS`；image=`sha256:cf471320e05bef619c0e746f1c05c3c658f39c7e029f5b35b3f8f531f460c420`；两条 required mapping、mount、alias、restart policy、WorkingDir、secure env presence 均有脱敏证据。
- Evidence package=`C:\Users\genghailong\Documents\competition-t08d-p1-closure-20260827`；Manifest=14/14 PASS；secret scan=PASS；ZIP=`C:\Users\genghailong\Documents\competition-t08d-p1-closure-20260827.zip`，size=9761 bytes，SHA256=`8bbbb07e50cd952e7ca2237356163aaa75761a6d87034e40cbf1a0f800e9cba6`；self-test=PASS。
- Remaining P0=0；Remaining P1=1（历史旧 SQLite 错误 target attribution 未被保留命令证据证明）；Recommendation=`READY FOR WORK P1-CLOSURE RE-REVIEW`；未 deploy/build/commit/push。
## T-08D Formal Backend-only Deployment Retry（2026-08-27）

### Objective / authorization / hard constraints

- Work authorization：`Overall=PASS`、`Remaining P0=0`、`Remaining P1=0`、`ALLOW FORMAL BACKEND-ONLY UPDATE RETRY`。
- 仅将正式 `lab-backend-1` 从 approved image `sha256:cf471320e05bef619c0e746f1c05c3c658f39c7e029f5b35b3f8f531f460c420` 切换到 approved candidate `sha256:3ff9c374d9d14d7d005536b15ba9f76cab4849532f53322c872b9dd0d0adf7d8`。
- Web/Gateway/Detector/VLM、SQLite 数据、production source、working tree 不改；禁止新 build、rebuild、commit、push；禁止顺手修复其它问题。
- Required formal contract：`ghl-internal` + alias `backend`、WorkingDir `/opt/ghl/backend`、restart `unless-stopped`、正式 storage/control mounts、secure env parity、`host.docker.internal:host-gateway`、`api.tavily.com:172.17.0.1`。
- 任一 runtime/smoke/safety/SQLite gate 失败，立即只回滚 Backend 到 old image，并记录原因；不修改其它服务。

### Gates

- [x] 1. Preflight current formal inspect、old image rollback availability、主 SQLite 可访问。
- [x] 2. Fresh rollback/SQLite safety evidence and exact replacement command prepared。
- [x] 3. Replace only `lab-backend-1` with candidate and capture post-deploy inspect。
- [x] 4. Runtime parity、Backend health、Tavily、Gateway/Web integration PASS。
- [x] 5. Exact T-08D/T-08C/five-pair/Early-blight/Grub/low-confidence formal smoke PASS。
- [x] 6. Post-deploy SQLite integrity and data-preservation PASS。
- [x] 7. Generate deployment evidence/report; no code/build/commit/push; hand off to Work review。

### Error log

- 2026-08-27：正式 retry 开始；仅在授权的 Backend-only scope 内执行，尚未替换容器。
- 2026-08-27：首次读取 secure env-file 的 `awk -F= ...` 命令因 PowerShell 转义导致远端 awk 语法错误，未读出任何值、未改变环境；改用只读 `cut -d= -f1 ...` 仅取得变量名。
- 2026-08-27：首次 post-deploy 采集脚本把 Docker inspect JSON 当作数组，并让 PowerShell 展开远端 `$path`；仅影响采集输出，未改变容器/服务，随后用单引号远端脚本重跑 PASS。
- 2026-08-27：首次 exact safety harness 复制到 Docker host `/tmp` 后未复制进候选容器，临时脚本报文件不存在；通过 `docker cp` 重试 PASS，未改挂载数据。
- 2026-08-27：首次只读 E2E harness 使用 host-only `/data/ghl/storage-next-test` 路径，候选容器内不存在；改用临时容器层 fixture、GET-only 既有 case 核验，未创建病例、未调用 detect/analyze、SQLite case_count 保持 9。
- 2026-08-27：首次 ZIP 使用 `Compress-Archive -LiteralPath` 搭配通配符失败，未生成 ZIP；改用精确 bundle 路径的 `-Path` 后生成成功。首次 self-test 将预期的 MANIFEST 条目误计为 extra，修正为 25 个 manifest payload + 1 个 MANIFEST 后 round-trip PASS。
- 2026-08-27：一次最终运行态检查误用了不带时间后缀的 rollback anchor 名称，且远端误调用 Windows `Select-String`；均为只读检查命令错误，正确 anchor 名称与正式服务状态随后核验 PASS。

### Final

- Final：formal replacement、全部硬门禁、MANIFEST、secret scan、ZIP self-test 已完成；bundle 已准备交 Work 独立复核，完成后停止，不再 deploy。

## A — 3-Class Curated Evidence Override（2026-08-28）

### Gates

- [x] Exact class-id mapping for 0/8/15 and curated `危害`/`可能诱因` parser.
- [x] Curated analysis override, source metadata/source_ids, Tavily independence and non-special control.
- [x] Treatment path unchanged; A targeted=9/9, 8-case=8/8, T-08=31/31, T-08B=34/34, T-08C=11/11, T-08D=14/14, backend=210/210.
- [x] Secret scan, MANIFEST=44/44, ZIP self-test=44/44, diff-check PASS.

### Final

- Review Bundle=`C:\Users\genghailong\Documents\编程大赛\competition-3class-curated-evidence-review-20260828.zip`；size=71343 bytes；SHA256=`48aa25ebc46cf145f3713c24de7810249aa8a08717a7b63cd9db27a3d31bb660`。
- 未 build/deploy/restart/修改 SQLite/commit/push；Ready for Work Code Review=YES。

## B0 — Final Knowledge Sync + Relative Image Migration（2026-08-28）

### Preflight result

- 分支确认：`competition-dev`；仅记录既有 dirty working tree，未 checkout/reset/clean。
- v2_5 source ZIP 存在，实际 SHA256=`06D2F6D7955FA983DFDDE44F20DA1582AC439ACFDDA257FA585B7C252546D76A`。
- 已解压并核对 source ZIP：仅 14 个带有效一级类别标题的 Markdown；缺少 manifest 要求的 `class_id=3 马铃薯早疫病` 与 `class_id=9 蚜虫`。
- 按 B0 hard gate 停止；未覆盖知识文档、未复制图片、未修改 manifest、未运行回归、未生成 Review Bundle。
- 预检证据目录：`artifacts/b0-final-knowledge-freeze-20260828/`；缺失两类前不得继续。

### Execution result after corrected folder source

- 新 v2_5 文件夹通过 16/16 类别、34/34 treatment refs、61/61 image sources 和 A frozen semantic gate；已同步 staged data。
- 静态校验通过，但 knowledge/A-stage loader 测试为 3 passed、12 failed：现有 `_rewrite_images()` 固定要求 `assets/`，无法消费 B0 要求的 `../images/`。
- 按 hard stop 停止，不修改 production code/tests，不继续完整 regression，不生成 Review Bundle；等待 loader/data-contract follow-up。

## B0-R1 — Existing Assets Contract Alignment（2026-08-29）

### Execution result

- 已完成 61/61 图片从此前 B0 创建的 `knowledge/baidu-baike-20260818/images/` 到现有 `assets/` contract 的迁移；文档相对引用同步为 `../assets/...`。
- source/destination SHA parity、16/16 文档、0 broken refs、0 knowledge-document obsolete refs、0 absolute residue、34/34 treatment refs、manifest/path/mapping/static A-frozen checks 均通过。
- 强制 loader gate=`8 passed, 7 failed, 1 warning`；失败涉及 HTML `<img>` renderer contract、旧非补零 endpoint 断言，以及 v2_5 `### 内容：` 与既有 curated parser contract 不一致。
- 按 B0-R1 stop condition 停止；未修改 loader/tests/production code，未运行全量回归、diff-check、secret scan，未 build/deploy/restart/commit/push，未生成 Review Bundle。
- 详细阻塞报告：`artifacts/b0-r1-assets-contract-20260829/b0-r1-loader-gate-blocker.md`；loader 输出：`artifacts/b0-r1-assets-contract-20260829/loader-gate.txt`。

### Operational notes

- 初始附件路径含转录差异，改用实际 attachment directory 定位；一次 PowerShell `-LiteralPath` 通配符复制失败；一次资产复制误落到 knowledge 数字根目录；首次搬迁脚本相对路径计算错误；首次非递归删除旧 `images/` 失败。均已通过只读检查/纠正操作完成，未触碰生产代码或 SQLite。

## B0-R2 — Markdown / Asset Path Contract Normalization（2026-08-29）

### Preflight result

- 分支确认：`competition-dev`。
- 已从 `backend/app/knowledge_documents.py`、`backend/tests/test_knowledge_documents.py` 和 `backend/tests/test_curated_evidence_override.py` 确认现有契约：仅支持 Markdown `![alt](relative)` 图片；资产目录/endpoint 使用非补位目录及文件名；curated 内容 heading 为 exact `### 内容`。
- 在任何数据修改前比较 61 个零补位 B0-R1 文件与非补位目标路径，发现 7 个不同 SHA 冲突，另有 1 个目标路径不存在；按 B0-R2 hard stop 停止。
- 未修改 knowledge Markdown/assets/manifest、loader、tests、production code、SQLite；未运行 targeted/full regression、diff-check、secret scan；未 build/deploy/restart/commit/push；未生成 Review Bundle。
- 详细契约与冲突证据：`artifacts/b0-r2-markdown-asset-contract-20260829/existing-contract-evidence.md`。

## B0-R3 — Collision-Safe Asset Merge + Final Contract Normalization（2026-08-29）

### Execution result

- branch=`competition-dev`；确认 renderer、asset root、Markdown syntax、非补位命名与 exact `### 内容` contract。
- 61/61 premerge map 完成；37 个 `COPIED_CANONICAL`、24 个 `REUSED_BY_SHA`、0 个覆盖历史资产；历史 tracked assets 61 个 SHA 未变。
- 09/12 及其他发现的 HTML 图片共 11 个均转换为 Markdown，最终 Markdown image refs=61、HTML residue=0、absolute residue=0、padded refs=0、broken refs=0；08 `### 内容：`→`### 内容`。
- manifest、16-class mapping、A frozen semantic payload、treatment content、34/34 treatment refs 均通过；61/61 incoming/final SHA parity PASS；已删除 61 个已确认的 B0 padded 临时副本。
- targeted loader gate=`9 passed, 6 failed, 1 warning`；按 stop condition 停止，未运行 full regression、diff-check、secret scan、build/deploy/commit/push，未生成 Review Bundle。
- 失败详见 `artifacts/b0-r3-markdown-asset-contract-20260829/targeted-loader-gate.md`；完整数据校验为 `asset-contract-validation.json`。

### Operational errors

- 首版 pre-delete validator 将相对路径误判为 absolute residue，修正为仅检查 Windows drive-absolute pattern 后重新验证 PASS。
- 首次 targeted pytest 在已位于 backend 目录时仍使用 `backend\\.venv` 路径，未启动测试；改用 `.\\.venv\\Scripts\\python.exe` 后得到正式 gate 结果。一次从仓库根目录调用 backend tests 的只读 `rg` 路径错误，随后在 backend 目录重试。

## B0-R4 — Curated Source Sanitization + Stale Knowledge Test Baseline Update（2026-08-29）

### Gates

- [x] `08.md` parser-critical hidden-character audit and source-block-only sanitization；08 curated semantic payload unchanged。
- [x] Confirmed class 0 `features_html` expectation is stale data baseline；updated only the approved assertion in `backend/tests/test_knowledge_documents.py`。
- [x] Targeted loader gate：knowledge 6/6、curated 9/9；hidden-character parser-critical=0；R3 asset/A/treatment/manifest validation PASS。
- [x] Backend full regression：210 passed、1 warning。
- [ ] `git diff --check`：FAIL，135 existing B0/v2_5 whitespace findings across knowledge additions；超出 R4 scope，按门禁停止。

### Final

- 未修改 production Python、loader、curated parser、其他 tests、Web/Gateway/Detector/VLM、SQLite；未 build/deploy/restart/commit/push。
- 未运行 secret scan，未生成 B0 final Review Bundle；详细证据在 `artifacts/b0-r4-curated-source-sanitization-20260829/`。

### Operational errors

- 初次 hidden scan 将 class 0 URL 行尾 TAB 误标为 parser-critical，已收窄判定为字段前缀隐藏字符；初次 A frozen compare 未忽略允许的 whitespace/path normalization，已修正验证器后 PASS。

## B0-R5 — Knowledge Whitespace Normalization + Final Freeze（2026-08-29）

- Preflight branch=`competition-dev`；初始 `git diff --check`=135，全部在 16 个知识库 Markdown（134 行尾空白、1 个 EOF 空白行），无 production/test/web 越界。
- 仅规范已报告知识库空白并同步 16 个文档 hash；16/16 非空语义 payload、A 冻结区、treatment、34/34 refs、61/61 资产引用与资产 SHA 保持不变。
- `git diff --check`=PASS 0 issues；knowledge 6/6、curated 9/9、8-case 8/8、T-08 31/31、T-08B 34/34、T-08C 11/11、T-08D 14/14、five-pair 4/4、backend 210/210；pollution=0/0。
- 已完成：secret scan、最终 scope 复核与 final Review Bundle 自测；不 build/deploy/restart/commit/push。

## B — Severity Engine + Tiered Treatment Matching（2026-08-29）

- Preflight：branch=`competition-dev`；冻结 knowledge 16/16、assets 98、manifest 已快照。
- 已新增独立 `backend/app/severity.py`，实现 Decimal 严重度、严格 tier parser、精确 treatment source resolution；最小集成修改 `analysis.py`/`main.py`，保留 legacy `field_severity` 与无输入行为。
- 已新增 `test_severity.py`、`test_severity_integration.py`；B targeted=83/83，完整 backend=281/281，冻结 knowledge/assets/manifest 前后 hash 不变，diff-check PASS。
- 已完成 final secret scan、Review Bundle、MANIFEST 与实际 ZIP self-test：44/44 payload entries，外部独立复核 PASS；ZIP secret scan 0 match。
- Bundle=`C:\Users\genghailong\Documents\编程大赛\competition-b-severity-tiered-treatment-review-20260829.zip`；最终 size=354993 bytes；SHA256=`eb1d37bc57e6b4ae6cd05c0a73d02290963bde970e8ede6ad0e65ab78102f147`。
- 本阶段 complete；未 build/deploy/restart/commit/push。

## B-R1 — Partial Severity Input Validation Closure（2026-08-29）

### Objective / hard constraints

- 仅关闭唯一 P1：`affected_ratio_percent` 已提供且 `spread_speed="unknown"` 时必须返回 422，不得静默成为 `not_provided`。
- 允许 production 修改最多 `backend/app/main.py`、`backend/app/severity.py`，测试仅限两个 severity 测试文件；不改算法、tier parser、source resolution、Tavily、Extractor、Curated、知识库/assets/manifest、SQLite、前端或其他服务。
- 禁止处理 `moderate` alias、cross-tier sentinel、missing-tier integration 等 non-blocking findings；禁止 build/deploy/restart/commit/push。

### Gates

- [x] branch 与 B frozen baseline 预检。
- [x] 最小 missing/unknown 一致判定与 API 422 regression（targeted 72/72）。
- [ ] B contract、历史 safety、full backend、diff-check、pollution 全通过。
- [ ] 生成脱敏 Review Bundle、MANIFEST、secret scan、ZIP self-test。

### Errors encountered

- 首次 targeted pytest 在 `backend` 工作目录仍使用根目录相对解释器 `./backend/.venv`，命令未启动 pytest；改用 backend 内 `./.venv/Scripts/python.exe` 重跑。
- B-R1 full backend regression 在既有 `backend/tests/test_phase9_public_api.py::test_unknown_spread_forces_unknown_severity` 失败：该历史测试要求 `affected_ratio=10 + spread_speed="unknown"` 上传成功，再在 analyze 阶段转为 unknown；新 P1 contract 要求同一输入在 upload 阶段 422。按本轮禁止修改该历史测试文件/历史 expectation 的 scope，停止，不生成 Review Bundle。

### Status

- 当前阶段：in_progress。

## E1-A-R1 — Official ModelScope Alternate Staging（2026-08-29）

- [x] 读取 E1-A-R1 全文约束并确认只允许官方 `OpenGVLab/InternVL3-1B`，不运行 E1 benchmark。
- [x] 使用独立临时 ModelScope 环境完成官方 `master` 快照下载；本地 21/21 文件物化、metadata/custom-code 离线检查通过。
- [x] `model.safetensors` 大小 `1876463472` bytes，SHA256 与 HF canonical anchor `a8b67c54568417f3631723e6b3e120720eaa638e03e62dc25666c70e3ae3e484` 精确一致。
- [x] 传输到 repo 外独立 lab cache `/data/ghl/models/internvl3-1b-modelscope-20260829`；服务器 21/21 全量 hash parity 与离线读取通过。
- [x] 生成 E1-A-R1 staging evidence 与脱敏 Review Bundle；不改 production/tests/deps/SQLite，不 build/deploy/restart/commit/push。

## E1 — InternVL3-1B Native CPU Benchmark（2026-08-30）

### Objective / hard constraints

- 使用 E1-A-R1 已冻结的官方 `OpenGVLab/InternVL3-1B` ModelScope snapshot，在真实 LAB CPU 服务器上做离线 native CPU benchmark。
- 仅允许独立 benchmark harness、临时 benchmark venv 与 evidence artifacts；不得修改 production/test/dependency/Web/Backend/inference/Qwen/SQLite/Docker，不 build/deploy/restart/commit/push，不进入 E2。

### Gates

- [x] 读取 E1 规格全文、确认 16-class canonical coverage 与 benchmark gates。
- [x] 完成真实 LAB hardware/runtime/model preflight；冻结模型与 16/16 真实输入 manifest。
- [x] 完成 repo 外独立 CPU-only benchmark venv 离线安装；pilot model load PASS，model 21/21 parity 与主权重 SHA 已复核。
- [ ] 冻结 prompt 并完成单图 inference pilot。
- [ ] 完成 16-class primary、8×3 stability、raw/parsed/schema/timing/memory/device evidence。
- [ ] 生成脱敏 E1 Work Review Bundle、MANIFEST、secret scan、ZIP self-test。

### Errors / recovery notes

- `pip download` 使用 PyTorch CPU index 无法解析指定 `2.2.2`/`2.2.2+cpu`，改用官方 exact wheel URL；未改项目依赖。
- 首次远端 preflight 的 PowerShell 双引号展开了远端 `$p`，导致语法错误；改用单引号重跑，未产生远端项目变更。
- 首次 primary copy 假定不存在的 `source_filename` 字段，复制 0 个文件；改用 `source_path` 扩展名解析后 16/16 成功，未改源图片。

### Status

- 当前阶段：in_progress；下一步创建 canonical crop mapping、冻结 prompt、做单图 chat API pilot，然后再执行正式 benchmark。

### Stop condition reached（2026-08-30）

- 两次允许的非计分 pilot 均已执行；模型/CPU/offline/input parity PASS。
- Pilot 1：JSON 围栏 + 截断，strict schema FAIL。
- Pilot 2：JSON syntax PASS，但 summary 泄漏上游类别 `玉米叶枯病`，违反 forbidden diagnosis/disease/class output gate。
- 按 E1 stop condition 停止；16-class main benchmark、8×3 stability、E1 performance metrics 和 passing Review Bundle 均未执行/未生成；不进入 E2。
- 阻塞证据：`artifacts/e1-internvl3-1b-cpu-benchmark-20260830/E1-BLOCKER-REPORT.md`。
- 当前阶段：blocked pending explicit later E1 prompt/harness authorization。
- STOP evidence package：`competition-e1-internvl3-1b-native-cpu-benchmark-review-20260830.zip`，18/18 manifest payload checks，19/19 ZIP entry checks，size 27054 bytes，SHA256=`49c9835469d206d2f104f523e7425b6baaaf6d4d33afb81111e63ffc4cc6ad14`；该包明确为 STOP/NOT READY，不是 E1 PASS bundle。

## E1-R1 — InternVL3-1B Prompt / Decoding Contract Stabilization（2026-08-30）

### Objective / hard constraints

- Work 已授权一次统一 prompt/decoding contract stabilization；仅允许独立 benchmark artifacts/harness，原两个 pilot 输入必须 exact parity；不得 main/stability/E2、生产集成、模型替换/量化/优化。
- Prompt、decoding、schema、parser、validation rules 必须在两个 pilot 前冻结，pilot 间不得修改；任一失败即 STOP。

### Gates

- [x] 保存原 E1 prompt/decoding、真实 truncation evidence 与 missing finish metadata；结论保持 INCONCLUSIVE。
- [x] 一次性冻结 R1 prompt/decoding；保留 YOLO internal context，加入 16/16 canonical-class scanner；记录 prompt/decoding SHA。
- [x] 原 Pilot 1、Pilot 2 输入 exact parity；同一 contract 依次运行，两次 process/model/CPU/offline/input gates PASS。
- [x] 按 stop condition 停止：两次 exact nested schema 均 FAIL；未进行第三次 pilot、main benchmark、stability 或 E2。
- [x] 生成 STOP/NOT READY Review Bundle、MANIFEST、secret scan、ZIP self-test。

### Findings / errors

- 两次 R1 model output 均为扁平 `affected_part`/`visual_symptoms`/`multimodal_summary` 字符串，不符合冻结 nested `status/value/items/text` schema。
- 冻结 decoding record 使用 `not_passed` 文档哨兵，harness 误将其传入 `generate()`，产生 Transformers warnings；Pilot 1 后禁止修复，Pilot 2 原样运行以保持 contract 一致。
- Pilot 2 首次远端命令误写 venv 路径，未启动模型；随后用已验证 venv 原样重跑，未产生 contract/生产变更。

### Status

- `E1-R1 CONTRACT STABILIZATION FAILED`；Recommendation=`MASTER DECISION REQUIRED`。
- Bundle=`competition-e1-r1-internvl3-1b-contract-stabilization-review-20260830.zip`；该包是 STOP evidence，不是 PASS candidate。

## E1-R1H — InternVL3-1B Benchmark Harness-Only Correction（2026-08-30）

### Objective / hard constraints

- 仅修复独立 benchmark/evidence harness 对 R1 `not_passed` decoding metadata 的错误传递；不修改 production、模型、prompt、schema、parser、依赖、SQLite、部署或服务。
- 保持 R1 prompt 字节、有效 generation 参数、两张 pilot 输入、官方模型 snapshot、CPU/offline contract 完全一致；只做两个 pilot，不运行 Main/Stability/E2。

### Gates

- [x] 1. 建立 allowlist harness，证明 `not_passed` 与未知 generation kwarg 均未传给 `model.chat`。
- [x] 2. 使用同一 R1 输入执行 Pilot 1 → Pilot 2，捕获 raw/parsed/schema/stdout/stderr/warnings。
- [x] 3. 根据 harness cleanliness 与 exact schema 结果决定 STOP/MASTER DECISION，并生成脱敏 Review Bundle。

### Status

- 当前阶段：complete（harness clean；model contract failure confirmed；STOP）。
- R1H bundle：`competition-e1-r1h-internvl3-1b-harness-correction-review-20260830.zip`；size=89517 bytes，SHA256=`19ae4ca67d89edf1c732d741dfeb7421ae2b4a2991d728b26ac896df08f564ff`，MANIFEST=100/100，ZIP self-test=101/101，secret scan PASS。

## E1-S1 — InternVL3-1B Simplified Model-Facing Contract Evaluation（2026-08-30）

### Objective / hard constraints

- 这是主控授权的新实验，不是 E1-R1/R1H 的旧 nested contract retry；只评估独立 model-facing `affected_part / visual_symptoms / multimodal_summary` flat string/null contract。
- 复用 Work 已确认 VALID 的 R1H clean harness allowlist；只新增独立 prompt/schema/benchmark harness 与 evidence artifacts，不改 production、tests、dependencies、模型、SQLite、服务或旧 R1/R1H evidence。
- 四个固定 pilot：原 class00-1 + 正式 pool 的 class08-1 generic pest + class14-1 underground pest；启动前冻结输入、prompt template、simple schema、effective decoding，Pilot 1→4 间不调参、不换图。

### Gates

- [x] 1. 固定四张真实输入并记录 SHA、class/crop/growth/environment context。
- [x] 2. 冻结 E1-S1 prompt template、flat schema、R1H effective decoding 与 harness。
- [x] 3. Pilot 1 按硬门禁 STOP：standalone harness 在模型调用前因 `lab_path`/`image_path` 字段映射崩溃；Pilot 2–4 未运行，Main/Stability/E2 未进入。
- [x] 4. 保存 STOP 证据并生成脱敏 Review Bundle、MANIFEST、secret scan、ZIP self-test。

### Status

- 当前阶段：complete（STOP；harness defect remains；未形成模型 simple-contract 结论）。
- STOP bundle：`competition-e1-s1-internvl3-1b-simple-contract-review-20260830.zip`；size=51453 bytes，SHA256=`5421d2bd1c42cfc953eca5dee9c47c522d4ddbe4b8ff251ef747a24f75afcf31`，MANIFEST=55/55，ZIP self-test=56/56，secret scan PASS。

## E1-S1H — Harness Field-Mapping Correction（2026-08-30）

### Objective / hard constraints

- 仅修复 standalone S1 harness 的 stale `entry["lab_path"]` 读取，使其使用冻结 manifest 的 authoritative `entry["image_path"]`；可加入最小 4-entry image-path/SHA preflight。
- Prompt、decoding、schema、四 pilot manifest、模型/CPU/offline/generation semantics 均冻结；不得改 production/test/backend/web/inference/dependencies/SQLite/knowledge/Qwen，不实现 adapter。
- 通过 preflight 后，按 1→2→3→4 各运行一次；任一 model hard gate 失败立即停止。即使 4/4 PASS，也仅出 bundle，Main/Stability/E2 不运行。

### Gates

- [x] 1. 恢复 E1-S1 STOP evidence，确认根因为 pre-inference `KeyError: lab_path`，prompt/decoding/schema/manifest SHA 全部冻结。
- [x] 2. 仅修正 S1 image accessor，并加入最小 manifest image-path/SHA preflight；记录 exact diff 与 stale lookup=0 证据。
- [x] 3. 4-entry preflight=PASS；Pilot 1 真实推理完成后因 canonical diagnosis/treatment leakage 触发 hard stop，Pilot 2–4 未运行。
- [x] 4. 生成脱敏 STOP Work review bundle、MANIFEST、ZIP self-test、secret scan。

### Errors encountered

- 2026-08-30 E1-S1：`e1-s1-pilot.py` 从旧 R1 contract 保留 `entry["lab_path"]`，而冻结 S1 TSV 的唯一路径字段为 `image_path`；Pilot 1 在 model.chat 前崩溃，未执行推理。E1-S1H 获得 Work 授权后才允许修正该 standalone harness 映射。
- 2026-08-30：本机 `python` launcher 不可用，未执行本地 compile；改用既有 LAB benchmark venv，静态 compile PASS。
- 2026-08-30：首次远端静态检查的 PowerShell 变量转义错误，命令在路径展开阶段失败，未触发模型；改用单引号远端 shell 后 PASS。
- 2026-08-30：首次 ZIP 命令误将 wildcard 用于 `Compress-Archive -LiteralPath`，ZIP 未生成；改用 `-Path` 后同一证据目录成功打包并自检。未删除或覆盖用户文件。
- 2026-08-30：初始 secret pattern 将文档标题 `Authorization:` 误报为 secret；收窄为携带 Bearer/token/basic 值的 header 模式后 0 matches。

### Status

- 当前阶段：complete（harness correction PASS；Pilot 1 model contract hard-gate FAIL；STOP）。
- Bundle：`competition-e1-s1h-internvl3-1b-field-mapping-correction-review-20260830.zip`；MANIFEST=52/52，ZIP self-test=53/53，secret scan PASS。

## E1-S1D — Pilot-Data Correction + Clean Simple-Contract Evaluation（2026-08-30）

### Objective / hard constraints

- 仅替换被 Work 确认污染的 S1 Pilot 1；replacement 必须维持 class 0 `玉米叶枯病`，从真实、无业务说明文字的项目原始照片中按 inference 前冻结的确定规则选择。
- 对 replacement 与未自动替换的 Pilot 2/3/4 全部完成 sample-policy visual preflight；任何一张不合格均在模型调用前 STOP。
- Prompt/decoding/schema/S1H clean harness/model/CPU-offline contract 均冻结；不得改 production/test/harness/model/prompt/decoding/schema/SQLite/knowledge/Web/inference service/Qwen，亦不得裁剪或修图。

### Gates

- [x] 1. 保留旧 Pilot 1 污染证据，枚举 163 个同 class training-data candidates，按稳定规则选择并冻结 replacement。
- [x] 2. 新 Pilot 1 visual preflight PASS；Pilot 2 与污染原图同 SHA 并 FAIL，触发立即 pre-inference stop；Pilot 3/4 未在 S1D 复核。
- [x] 3. 冻结 prompt/decoding/schema/S1H harness 均未变；因 4/4 data preflight FAIL，Pilots 1–4 均未执行模型。
- [x] 4. 保存 STOP evidence 并生成 Work bundle、MANIFEST、ZIP self-test、secret scan。

### Status

- 当前阶段：complete（data preflight STOP；benchmark input defect remains；simple contract NOT EVALUATED）。
- Bundle：`competition-e1-s1d-internvl3-1b-pilot-data-correction-review-20260830.zip`；MANIFEST=32/32，ZIP self-test=33/33，secret scan PASS。

### Errors encountered

- 2026-08-30：本地 .NET image metadata reader 无法打开旧 composite source；旧图尺寸已在冻结 manifest 中为 1290×383，且本轮 contamination decision 直接由原图 visual review 与 exact SHA identity 证明，不依赖该 metadata read。未重试或修改图片。
## E1-S1D-R1 — Full 4-Pilot Data Sanitization（2026-08-30）

### Objective / hard constraints

- 仅做四 Pilot 的数据清洗与确定性同类替换；任何模型加载、推理、主 benchmark、stability、E2 均禁止。
- 保持 Prompt/Decoding/Schema/S1H harness/model snapshot/canonical mapping 冻结；不修改 production、tests、dependencies、SQLite、knowledge、Web 或 inference 服务。

### Gates

- [x] 1. 四 Pilot 全部完成 sample-policy、SHA、视觉和 production-representative 审核。
- [x] 2. 所有 invalid Pilot 按 class/canonical 同类确定性排序替换；最终 4 SHA 唯一且排除污染 SHA。
- [x] 3. 冻结 clean 4-Pilot manifest，保存 exclusion ledger、candidate enumeration、same-class proof 与视觉审核。
- [x] 4. 确认 frozen prompt/decoding/schema/harness parity，model loaded/chat/generation/new output 均为 0。
- [x] 5. 生成脱敏 Work Review Bundle、MANIFEST、secret scan、ZIP self-test 后停止，等待独立审核。

### Status

- 当前阶段：complete（dataset sanitized；等待 Work independent review；未进入模型推理）。

## E1-S1P — InternVL3-1B Clean 4-Pilot Simple-Contract Inference（2026-08-30）

### Objective / hard constraints

- Work 已批准使用 E1-S1D-R1 的 clean 4-Pilot manifest，对 InternVL3-1B 执行一次性 simple-contract inference。
- 仅允许 LAB native CPU/offline、冻结 Prompt/Decoding/Schema/S1H harness；Pilot 1→4 固定顺序，每张最多一次；首个功能失败立即停止。
- 不进入 Main 16-class benchmark、Stability 或 E2；不修改 production/test/data/model/harness/prompt/decoding/schema/SQLite，不 build/deploy/restart/commit/push。

### Gates

- [x] 1. 4/4 input SHA、dimensions、canonical mapping、historical contaminated SHA、frozen contract 和 harness preflight PASS。
- [x] 2. LAB CPU/offline/model identity PASS；Pilot 1 执行一次。
- [x] 3. Pilot 1 JSON/schema PASS，但 canonical/diagnosis leakage=1/1，按 hard-stop 不运行 Pilot 2–4。
- [x] 4. 保存 raw/parsed/scanner/grounding/latency/runtime/stop evidence，生成脱敏 Review Bundle。

### Status

- 当前阶段：complete（clean model functional failure；STOP；等待 Master Decision；未进入 Pilot 2–4/Main/Stability/E2）。

## E1-2A — InternVL3-2B Official Model Staging（2026-08-30）

### Objective / hard constraints

- 仅准备并核验官方 `OpenGVLab/InternVL3-2B` 模型制品；不加载模型、不调用 `model.chat`、不生成、不执行 Pilot/Main/Stability/E2。
- ModelScope 官方 `OpenGVLab/InternVL3-2B` 为主来源，官方 Hugging Face `OpenGVLab/InternVL3-2B` 仅作 identity/metadata cross-check；不得使用 Pretrained、Instruct、hf、量化、社区或第三方变体。
- 2B 必须使用独立 Windows/LAB staging，保留 1B frozen artifact；不修改 production/test/backend/Web/SQLite/knowledge/Qwen/dependencies，不 build/deploy/restart/commit/push。

### Gates

- [ ] 1. Official repository/provider/revision identity and HF cross-check。
- [ ] 2. Complete Windows materialized file inventory and SHA256。
- [ ] 3. Windows staging completeness / unexpected payload / links / temp-file scans。
- [ ] 4. LAB transfer and 100% full-file SHA parity。
- [ ] 5. Static offline readability without model instantiation/inference。
- [ ] 6. Frozen E1-S1 assets, no-change boundaries, secret scan, MANIFEST, ZIP self-test。

### Status

- 当前阶段：complete（official 2B staging、Windows/LAB full parity、static readability PASS；未推理；等待 Work 独立审核）。
