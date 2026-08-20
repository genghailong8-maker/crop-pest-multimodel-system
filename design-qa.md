# 参考图驱动诊断工作台 Design QA

Reference: `C:\Users\genghailong\.codex\generated_images\019ffe65-7d07-7030-b103-a5114a65922e\exec-578ab5e0-48e4-4e64-aede-c6260acf2ecb.png`

## Result

**Final result: passed**

## Checked

- Desktop workbench: deep-green left rail, current server indicator, diagnosis path, and three-column evidence workspace are present.
- Mobile workbench: top navigation and vertical reading order at 390px; no horizontal overflow.
- Real product truth: reference-only date/name/plot/sample content was not copied; image, detection, evidence, report and server data remain API-backed.
- Public flow: `/`, `/history`, `/trends`, `/cases/[id]` and `/reports/[id]` share the same workbench shell.
- Accessibility: navigation uses `aria-current`, server and status surfaces use polite live regions, form semantics and image alt text are preserved.
- Laboratory deployment: `lab_cpu` web UI returns HTTP 200; GPU and model services were not modified.
