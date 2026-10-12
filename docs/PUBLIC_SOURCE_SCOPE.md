# 可公开源码版范围与差异

- 来源基线：`COMPETITION_FINAL_20261009`，冻结 manifest SHA256 `419d09056725840f8d2636ad508961f6254af38ab5cf3738066368231b15bab1`。冻结原件未修改。
- 保留冻结版活动源码；候选各文件与冻结源的路径、大小及 SHA 对照见 `PUBLIC_CANDIDATE_FILE_MANIFEST.csv`。
- 保留正式植物 5 类知识、昆虫 official5/24-host 对照及对应证据状态、Severity/Treatment 映射、Severity 图片和现有校验代码。新增来源与资产索引见 `docs/knowledge-reproduction/`。
- 排除百度百科目录/98 张图片、模型权重、P1 中许可未核实的 116 张、SQLite/病例/图片/报告/备份、个人配置/凭证、原始 Git 历史及构建缓存。
- 保留的旧 Phase 9 文档已添加历史范围提示，避免其旧系统数据被误读为最终 E2/Frozen 指标。
- 没有将其他工作区训练脚本归为 E2 最终权重训练来源，因为现有冻结材料未证实其身份。
- 公开源码差异说明不修改运行 Resolver、默认配置、业务 fallback 或模型代码；若缺少外部资产导致运行限制，见 `docs/MISSING_RUNTIME_DEPENDENCIES.md`。
- 再分发审查为 PARTIAL：包含来源链接并不等于获得来源内容/图片的再分发授权；每项第三方材料应遵守各自许可。
