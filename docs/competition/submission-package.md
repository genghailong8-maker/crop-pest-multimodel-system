# 比赛提交包与公开仓库审核

## 1. 建议提交内容

- `README.md`、`PUBLICATION_POLICY.md` 和本目录五份比赛材料（含答辩幻灯片提纲）；
- `backend/`、`web/`、`inference/`、`training/` 的源码与运行说明；
- `scripts/collect_phase5_evidence.py` 和 `scripts/final_repro_check.py`；
- 后端测试、网页测试配置和不含原始图像的官方划分/审计元数据；
- 派生标量指标、校准结论、模型角色说明和来源/许可证登记；
- 提交时记录的 Git commit、分支、复现命令和已知限制。

推荐答辩包结构：

```text
competition-package/
├─ README.md
├─ PUBLICATION_POLICY.md
├─ docs/competition/              # 含 presentation-outline.md
├─ backend/  web/  inference/  training/  scripts/
├─ data/official/splits/        # 仅划分元数据，不含图片/标签
└─ artifacts/experiments/       # 仅小型派生报告，按策略筛选
```

## 2. 明确排除内容

不得从公开仓库或比赛压缩包直接携带：官方图片/标签、第三方图片/标注、`.pt`/`.onnx` 权重、数据库、运行日志、上传图片、`.env`、SSH 私钥、含密钥的服务清单、未经许可的大归档。需要现场演示的模型和数据使用受控服务器备份，不改变公开仓库边界。

## 3. 发布前审核命令

```powershell
$py = "C:\Users\genghailong\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py scripts\final_repro_check.py --output artifacts\release\final-repro-check-20260810.json
git status --short --branch
git diff --check
git ls-files | Select-String -Pattern '\\.(pt|onnx|jpg|jpeg|png|webp|zip|tar|gz|db|sqlite|pem|key)$'
```

最后一条命令必须无输出。`CLAUDE.md` 是工作区内的用户文件，不属于提交包，也不应被加入 Git。

## 4. 交付口径

- 当前分支：`codex/publish-audits-and-calibration-plan`。
- 公开仓库：`genghailong8-maker/crop-pest-multimodel-system`。
- 当前主模型是官方冻结验证集上表现最好的保留主模型；不是“所有 16 类都已同等提升”的宣称。
- `active` 路由保持关闭；独立 frozen 门未通过时，任何提交包都不得把 shadow 结果描述成生产替换。
- 知识来源是原则级 IPM/绿色防控来源，不是具体产品标签；答辩时应主动说明这一点。
