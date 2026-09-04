# Severity V2 impact map — design only

| Real file/interface or field | Current role | B2-Implementation action | Compatibility / migration design |
| --- | --- | --- | --- |
| backend/app/severity.py: SPREAD_SPEED_VALUES, calculate_severity, SeverityResult.score | V1 ratio/speed weighted score and automatic tier level | REMOVE from new V2 decision path; REPLACE with versioned user-guided rubric resolver | PRESERVE callable V1 behavior for historical records; never reinterpret prior scores. |
| backend/app/analysis.py: _severity_values and severity_basis | Builds V1 basis with ratio, speed and score | REPLACE for V2 payload construction | Store V2 level/source/scope/unit/visible-feature basis alongside legacy basis. |
| backend/app/main.py: POST /api/cases form fields affected_ratio_percent, spread_speed | Diagnosis request accepts V1 inputs | REPLACE in future versioned request schema | Keep old optional fields readable for legacy endpoint/records until migration is retired. |
| backend/app/main.py: response severity, treatment, report/case payloads | Publishes V1 low/medium/high and selected tier | REPLACE response contract; COMPATIBILITY adapter required | Return version marker; uncertain must not default-select treatment tier. |
| backend/app/database.py: cases.affected_ratio_percent, spread_speed, field_severity | SQLite V1 persistence | MIGRATION_REQUIRED: add V2 columns/version, do not drop columns | Existing rows remain V1. New V2 values are absent unless user explicitly reassesses. |
| backend/app/case_context.py: severity_for_record and context fields | Mirrors ratio/speed and V1 severity | REPLACE for V2 context; PRESERVE legacy display | Include severity_scope=current_sample and source=user_guided_rubric only for V2 records. |
| backend/app/knowledge.py and backend/app/knowledge_documents.py: tier treatment lookup | Local Knowledge serves selected tier | PRESERVE treatment text; ADJUST lookup policy | Only use validated V2 mapping after user confirmation; uncertain returns no tier-specific treatment. |
| backend/app/search/curated.py, tavily.py, normalizer.py, evidence_extractor.py | Curated harms/causes/sources responsibility | NO_CHANGE | Do not route severity into these pathways. |
| backend/tests/test_severity.py, test_severity_integration.py, test_api.py, test_analysis.py, test_case_context.py | Locks V1 scoring, API, analysis and compatibility behavior | PRESERVE V1 tests; ADD V2 unit/enum/uncertain/migration tests | Test no automatic V1-to-V2 conversion and no uncertain tier selection. |
| web/app/lib/diagnosis-form.ts | Sends V1 ratio/speed | REPLACE in future form | Offer user-guided unit/state choice; no VLM or hidden score selection. |
| web/app/lib/api.ts | Types request/response V1 fields | MIGRATION_REQUIRED | Version types; retain V1 fields as legacy read-only compatibility. |
| web/app/components/FieldFacts.tsx, EvidenceRail.tsx, DiagnosisSummary.tsx, CaseContextCard.tsx | Displays ratio/speed/field severity | REPLACE UI rendering | V1 records stay visibly legacy; V2 shows level/source/scope/unit and uncertainty. |
| web/app/cases/[id]/page.tsx, reports/[id]/page.tsx, history/page.tsx, trends/page.tsx | Detail/report/history/trend use V1 field severity | COMPATIBILITY | Do not aggregate V1 and V2 categories without version labels. |
| web/tests/rendered-html.test.mjs, web/tests/d-context-display.test.mjs | Rendering behavior checks | ADD future V2 cases; PRESERVE existing | Verify no V1 fields are requested in new flow and uncertain is non-escalating. |
| knowledge/baidu-baike-20260818/documents/00.md through 15.md | Frozen treatment prose | NO_CHANGE | Alignment TSV is design evidence; no B2 body change. |
| data/official/dataset.yaml and YOLO inference pathways | Canonical diagnosis | PRESERVE | YOLO remains diagnosis authority. |

## Historical case policy

A historical case retaining affected_ratio_percent, spread_speed, field_severity, severity_basis, a score, or a V1-selected treatment remains a V1 record. Future reads display those values with a legacy version label. There is no automatic backfill, conversion, or treatment remapping. A V2 value exists only after an authorized user reassessment explicitly records the new contract fields.

## Scope result

This is a read-only implementation design. No B2 production file, SQLite schema, API, knowledge treatment body, YOLO, VLM, Tavily, or Curated pathway is changed.
