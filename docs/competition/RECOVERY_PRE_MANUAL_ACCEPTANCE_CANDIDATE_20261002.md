# Recovering the pre-manual-acceptance candidate

## 1. Restore the repository source

```powershell
git clone --branch backup/pre-manual-acceptance-20261002 --single-branch git@github.com:genghailong8-maker/crop-pest-multimodel-system.git crop-pest-candidate
Set-Location crop-pest-candidate
git status --short --branch
git rev-parse HEAD
```

The branch is a candidate backup based on the certified `competition-dev` parent, not a Formal release. It deliberately does not include database records, secrets, validation datasets, model weights, temporary-server logs, or the full runtime archive. There is no Git LFS dependency for this candidate.

## 2. Restore the model assets separately

Obtain the separately backed-up `final-delivery-20261002` asset directory from the local acceptance artifact copy. Do not fetch floating/latest model revisions. Verify each file against:

- [`PRE_MANUAL_ACCEPTANCE_EXTERNAL_ASSETS_20261002.json`](assets/PRE_MANUAL_ACCEPTANCE_EXTERNAL_ASSETS_20261002.json)
- [`R3_TEMP_CLIP_MODEL_MANIFEST.json`](assets/R3_TEMP_CLIP_MODEL_MANIFEST.json)
- [`R3_TEMP_CONTEXT_BUNDLE_MANIFEST.json`](assets/R3_TEMP_CONTEXT_BUNDLE_MANIFEST.json)

The detector must be `Frozen YOLO26N`, SHA256 `e233fc1971f88288fabed8d37af32047f6d1cb643213d9de0ee61385666479ba`. The local Context asset is `openai/clip-vit-base-patch32` at immutable revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`; its weight file and all tokenizer/processor files must match the nine-entry model manifest. Context historical byte parity remains unverified; this is a controlled reconstructed baseline, not a historical image clone.

Do not place weights, runtime SQLite, or secrets in source control. Keep the approved Tavily credential in a protected runtime secret store and configure it only during an independently authorized deployment.

## 3. Focused checks and runtime recovery

Use the versions and lockfiles committed in this branch. The focused candidate regressions can be run with:

```powershell
python -m pytest backend/tests/test_insect_evidence_candidate.py backend/tests/test_host_knowledge_uncertain.py
Push-Location web
node --test tests/issue-005-treatment-visibility.test.mjs tests/test_uncertain_treatment_guard.mjs
Pop-Location
```

Follow the repository deployment documentation for a new isolated runtime; initialize a new local SQLite database unless a separately approved migration is designed. The GitHub clone alone is not a complete runnable model package until the external assets are restored and verified.

Before any deployment, run the focused Evidence/ISSUE-005 tests documented with this candidate, then service health and smoke checks. Do not deploy this candidate to Lab Formal without separate authorization and a fresh drift check. Preserve the Context quality warning in [`PRE_MANUAL_ACCEPTANCE_CANDIDATE_20261002.md`](PRE_MANUAL_ACCEPTANCE_CANDIDATE_20261002.md).
