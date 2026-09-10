---
target: competition showcase page
total_score: 21
max_score: 28
na_heuristics: 5,7,10
p0_count: 1
p1_count: 2
timestamp: 2026-08-20T08-05-50Z
slug: web-app-showcase-page-tsx
---
# Competition Showcase Critique

Method: dual-agent (A: 01a01e29-2e7e-7c20-a694-8f2dc972c4c7 · B: 01a01e29-2f0c-75c3-8263-16a29f4c40bd)

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 2/4 | Anchor state is basic and failed assets have no fallback. |
| 2 | Match System / Real World | 4/4 | Field sampling, evidence, cases and reports use domain language. |
| 3 | User Control and Freedom | 3/4 | Clear CTAs; mobile loses section navigation after the hero. |
| 4 | Consistency and Standards | 4/4 | Color, type, CTA and diagram semantics are coherent. |
| 5 | Error Prevention | n/a | No consequential form interaction on this surface. |
| 6 | Recognition Rather Than Recall | 4/4 | Workflow, evidence sources and server ownership stay labelled. |
| 7 | Flexibility and Efficiency | n/a | Not materially applicable to this persuasive surface. |
| 8 | Aesthetic and Minimalist Design | 3/4 | Strong hierarchy, but repeated evidence language lengthens the story. |
| 9 | Error Recovery | 1/4 | Vinext image optimization failed in the inspected local runtime. |
| 10 | Help and Documentation | n/a | Technical detail is progressively disclosed. |
| **Total** | | **21/28** | **Good, with one runtime blocker** |

## Design Specificity Verdict

The showcase is strongly product-specific and not interchangeable with a generic SaaS landing page. The evidence network, six-stage diagnosis path, refusal semantics, independent CPU/GPU instances and frozen evaluation ledger are all grounded in this system. The deterministic detector returned zero findings for `web/app/showcase/page.tsx`.

Browser evidence confirmed zero horizontal overflow at 1280px and 390px, correct heading hierarchy, useful image alt text and reduced-motion source handling. Live overlay injection was unavailable because the browser evaluation surface is read-only, so no user-visible overlays are claimed.

## Overall Impression

The first screen communicates the evidence-driven diagnosis proposition quickly and with a distinctive agricultural technology voice. The strongest opportunity is to make the three innovations and proof meaning explicit earlier while ensuring real imagery cannot fail through the framework optimizer.

## What Is Working

- The two-line promise, evidence network and agricultural image establish a memorable product identity.
- The dual-instance diagram explains case ownership and switching in user terms instead of operational topology.
- Trust language is disciplined: evidence can be traced, knowledge stays independent and insufficient evidence can be refused.

## Priority Issues

### P0 — Optimized showcase imagery fails in the inspected runtime

Both `next/image` optimizer routes returned HTTP 500 although direct static PNG URLs returned 200. This can remove the hero and real-product proof. Use stable direct static delivery with explicit dimensions, loading intent and responsive CSS, then verify production output.

### P1 — Three innovations are not explicit enough in the first 30 seconds

The concepts exist in the hero facts but read as capability metadata. Rename them as a compact innovation summary so a judge can repeat the three differentiators before reaching the detailed sections.

### P1 — Technical metrics need plain-language meaning

`mAP50-95`, `Top-1` and conflict recognition are credible but not self-explanatory. Pair each with one concise statement of what it demonstrates and retain the evaluation boundary.

### P2 — Mobile long-form navigation is weak

The mobile header hides both section navigation and its CTA. Add a restrained mobile dock for project highlights, results and diagnosis without hijacking scrolling.

### P2 — Supporting evidence labels are too small

Several meaningful labels and notes use 9–12px or low-opacity text. Raise meaningful support text and dark-surface contrast; reserve the smallest size for dates or secondary metadata.

### P2 — Brand link touch height is below 44px

The measured brand link is 42.5px desktop and 36px mobile. Give the link a 44px minimum height.

## Persona Red Flags

- Jordan: model metrics are unexplained and the innovation summary is not yet explicit.
- Riley: image optimizer failure conflicts with the page's engineering-confidence message.
- Casey: the long mobile narrative lacks a persistent section or diagnosis entry.
- Competition judge: the proposition is clear in 10 seconds, but the three innovations are not equally repeatable within 30 seconds.

## Minor Observations

- Focus-visible treatment, semantic landmarks and reduced-motion handling are good.
- The dated real-system screenshot caption is strong trust material.
- No detector false positives were reported.

## Questions to Consider

- If a judge only sees the hero, can they name all three innovations correctly?
- What should `0.5482` make a non-technical advisor believe, and what should it not imply?
- Which artifact best proves this is more than a polished classifier demo?
