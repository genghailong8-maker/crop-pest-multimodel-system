export type Detection = {
  class_id: number;
  class_name: string;
  class_name_en?: string;
  category_type?: string;
  confidence: number;
  bbox: [number, number, number, number];
};

export type GroundedEvidence = {
  source: "image" | "yolo" | "field_input";
  reference: string;
  observation: string;
};

export type GroundedConclusion = {
  conclusion: string;
  evidence: GroundedEvidence[];
};

export type GroundedAssessment = {
  harms: GroundedConclusion[];
  causes: GroundedConclusion[];
};

export type EvidenceSource = {
  id: string;
  title: string;
  site_name: string;
  url: string;
  snippet?: string | null;
  retrieved_at: string;
  reliability_level?: string | null;
};

export type EvidenceConclusion = {
  conclusion: string;
  source_ids: string[];
};

export type EvidenceAnalysis = {
  status: "available" | "unavailable";
  harms: EvidenceConclusion[];
  possible_causes: EvidenceConclusion[];
};

export type SeverityLevel = "mild" | "moderate" | "severe" | "uncertain";

export type R31HostStatus = "FULL" | "PARTIAL" | "REJECTED";
export type R31TreatmentLevel = "host_severity" | "host_general" | "insect_general" | "none";
export type R31CapabilitySet = {
  host_relation: boolean;
  host_damage: boolean;
  severity: boolean;
  host_general_treatment: boolean;
  host_severity_treatment: boolean;
  vector_disease: boolean;
};
export type R31Source = {
  id: string;
  title: string;
  organization?: string | null;
  url?: string | null;
  doi?: string | null;
  tier?: string | null;
  support_scope?: string | null;
};
export type R31HostOption = {
  crop: string;
  status: R31HostStatus;
  capabilities: R31CapabilitySet;
  severity_available: boolean;
};
export type R31SeverityLevel = {
  level: Exclude<SeverityLevel, "uncertain">;
  label: string;
  rubric: string;
  rubric_text?: string;
  observable_features: string[];
  source_ids: string[];
  sources: R31Source[];
  evidence_type?: string | null;
  synthesis_note?: string | null;
};
export type R31SeverityPayload = {
  available: boolean;
  levels: Partial<Record<Exclude<SeverityLevel, "uncertain">, R31SeverityLevel>>;
  source_ids: string[];
  sources: R31Source[];
  provenance?: Record<string, unknown>;
};
export type R31HostEvidence = {
  available: boolean;
  text?: string | null;
  source_ids?: string[];
  sources?: R31Source[];
};
export type R31VectorDisease = {
  disease: string;
  relationship: string;
  symptoms: string;
  general_disease_treatment: string;
  source_ids: string[];
  sources: R31Source[];
  disease_severity_available: boolean;
  severity: R31SeverityPayload;
};
export type R31HostDetails = {
  host_relation: R31HostEvidence;
  damage: R31HostEvidence;
  severity_available: boolean;
  severity: R31SeverityPayload;
  vector_diseases: R31VectorDisease[];
  provenance: Record<string, unknown>;
};
export type R31Treatment = {
  treatment_level: R31TreatmentLevel;
  body: {
    mode?: string;
    sections?: Record<string, string>;
    measures?: Record<string, string>;
    pesticide_policy?: string | null;
    severity_note?: string | null;
  } | null;
  source_ids: string[];
  provenance: Record<string, unknown>;
  fallback_message: string;
};
export type R31HostKnowledge = {
  schema_version: string;
  available: boolean;
  class_id: number;
  insect: string;
  recommended_host: string | null;
  recommended_label: string | null;
  supported_hosts: string[];
  host_options: R31HostOption[];
  other: { value: "OTHER"; label: string };
  confirmed_host: string | null;
  selection_required: boolean;
  host_authority: {
    recommended_host_is_confirmed_host: boolean;
    confirmation: string;
    rejected_hosts_returned: boolean;
  };
  generic_evidence: {
    status: string;
    harms: EvidenceConclusion[];
    possible_causes: EvidenceConclusion[];
    source_ids: string[];
    sources: EvidenceSource[];
    authority: string;
  };
  host: (R31HostOption & { value?: string }) | null;
  host_knowledge: R31HostDetails | null;
  treatment: R31Treatment | null;
  host_selection_error?: string;
};

export type R3Candidate = { value: string; score: number; rank: number };
export type R3PredictionField = { top1: string | null; candidates: R3Candidate[]; margin: number | null };
export type R3ContextPrediction = {
  status: "available" | "unavailable";
  reason?: string;
  model?: string;
  revision?: string;
  subject_type?: R3PredictionField | null;
  crop_species?: R3PredictionField | null;
  affected_part?: R3PredictionField | null;
  insect_species?: R3PredictionField | null;
};
export type R3Context = {
  schema_version?: string;
  authority: "user_confirmed" | string;
  source: "user_confirmed" | string;
  subject_type: "plant" | "insect";
  crop_species: string | null;
  affected_part: string | null;
  insect_species: string | null;
  model_prediction?: R3ContextPrediction | null;
};
export type R3TaxonomyOption = { value: string; label: string; prompts?: string[] };
export type R3Taxonomy = {
  schema_version: string;
  subject_types: R3TaxonomyOption[];
  crops: R3TaxonomyOption[];
  affected_parts: R3TaxonomyOption[];
  insects: R3TaxonomyOption[];
};
export type DraftRecord = {
  id: string;
  status: "uploaded" | "analyzed" | "low_confidence" | "model_unavailable" | "finalized";
  image_url: string;
  image_filename?: string;
  image_width?: number;
  image_height?: number;
  quality?: CaseRecord["quality"];
  detections?: Detection[] | null;
  detector_summary?: CaseRecord["detector_summary"];
  context_prediction?: R3ContextPrediction | null;
  confidence_gate?: {
    status: "allowed" | "blocked";
    threshold: number;
    confidence: number | null;
    message?: string;
  };
  draft_edit_token?: string;
  final_case_id?: string | null;
};

export type SeverityReference = {
  class_id: number;
  canonical_class: string;
  severity: "mild" | "moderate" | "severe";
  rubric_reference: string;
  image_asset: string | null;
  image_type: "REAL_REFERENCE" | "REAL_DAMAGE_IMAGE" | "AI_ILLUSTRATION" | "AI_GENERATION_REQUIRED" | "MISSING";
  source: { title: string; url: string; domain?: string; author?: string } | null;
  license: string;
  fallback_label: string;
};

export type SeverityResult = {
  status: "available" | "not_provided";
  level: SeverityLevel | null;
  label: string | null;
  affected_ratio?: number | null;
  spread_speed?: "none" | "slow" | "ongoing" | "rapid" | null;
  score?: number | null;
  scope?: "current_sample";
  source?: "user_guided_rubric";
  algorithm_version?: string;
  decision_rule?: string;
};

export type CaseContext = {
  crop: {
    status: "available" | "unavailable" | "not_applicable";
    value: string | null;
    source: "yolo_class_mapping" | "user_reported" | null;
  };
  growth_stage: {
    status: "available" | "not_provided";
    value: string | null;
    label: string | null;
    source: "user";
  };
  affected_ratio_percent: number | null;
  spread_speed: "unknown" | "none" | "slow" | "ongoing" | "moderate" | "rapid" | null;
  severity: SeverityResult;
  environment: {
    source: "system_default";
    cultivation_scene: string;
    temperature_c: number;
    relative_humidity_percent: number;
    soil_moisture: string;
    light_condition: string;
    ventilation: string;
    recent_extreme_weather: string;
  };
};

export type Treatment = {
  source: "local_knowledge_base";
  status?: "available" | "unavailable" | "pending_alignment_update";
  reason?: string;
  severity_level?: SeverityResult["level"];
  severity_label?: string | null;
  content: {
    prevention?: string[];
    first_actions?: string[];
    management?: Record<string, string[]>;
    prevention_html?: string | null;
    tier?: string;
    markdown?: string;
    markdown_html?: string;
  };
  source_ids: string[];
  requires_pesticide_warning?: boolean;
  pesticide_warning?: string | null;
};

export type SeverityRubric = {
  canonical_class: string;
  assessment_template: string;
  assessment_unit: string;
  observable_features: string;
  mild: string;
  moderate: string;
  severe: string;
  uncertain: string;
};

export type SeverityRubricPayload = {
  status: "available";
  canonical_class: string;
  rubric: SeverityRubric;
  references: Partial<Record<"mild" | "moderate" | "severe", SeverityReference>>;
};

export type CaseRecord = {
  id: string;
  instance_id: string;
  created_at: string;
  updated_at: string;
  crop: string;
  part: string;
  growth_stage: string;
  environment: Record<string, string>;
  notes: string;
  image_filename: string;
  image_url: string;
  status: string;
  is_test: boolean;
  resolution_status: "conclusive" | "retake_required" | "no_supported_target" | "service_unavailable";
  user_summary: string;
  next_action: string;
  resolution_reasons: string[];
  affected_ratio_percent: number | null;
  spread_speed: "unknown" | "none" | "slow" | "moderate" | "rapid";
  public_consent: boolean;
  expires_at: string | null;
  diagnostic_risk: "low" | "medium" | "high" | "unknown";
  field_severity: "low" | "medium" | "high" | "unknown";
  severity?: SeverityResult;
  severity_rubric?: SeverityRubricPayload | { status: "unavailable"; reason: string };
  case_context?: CaseContext;
  context?: R3Context | null;
  host_knowledge?: R31HostKnowledge;
  quality: { acceptable?: boolean; flags?: string[]; width?: number; height?: number } | null;
  detections: Detection[] | null;
  detector_summary: {
    needs_review?: boolean;
    review_reasons?: string[];
    primary_candidate?: { class_id: number; class_name: string; max_confidence: number } | null;
    candidate_classes?: Array<{ class_id: number; class_name: string; max_confidence: number }>;
    explainability?: {
      knowledge_card?: {
        observation_focus: string;
        first_actions: string[];
        source_ids: string[];
        chemical_safety?: string;
      } | null;
      model_evidence?: Record<string, unknown>;
      human_review?: { required: boolean; reasons: string[] };
    };
    inference?: Record<string, unknown>;
  } | null;
  evidence_analysis?: EvidenceAnalysis;
  sources?: EvidenceSource[];
  treatment?: Treatment;
  analysis: {
    status?: string;
    message?: string;
    schema_version?: string;
    primary_diagnosis?: string | null;
    candidate_diagnoses?: string[];
    symptoms?: string[];
    harm?: string[];
    harm_level?: string;
    possible_causes?: string[];
    evidence?: string[];
    grounded_assessment?: GroundedAssessment;
    evidence_analysis?: EvidenceAnalysis;
    sources?: EvidenceSource[];
    uncertainty?: string[];
    required_additional_photos?: string[];
    detector_alignment?: "agree" | "uncertain" | "conflict";
    diagnostic_risk?: string;
    field_severity?: string;
    severity_basis?: string;
    needs_human_review?: boolean;
    review_reasons?: string[];
    provenance?: Record<string, unknown>;
    independent_judgment?: Record<string, unknown>;
  } | null;
  review: Record<string, unknown> | null;
  case_edit_token?: string;
};

export type HealthStatus = {
  status: string;
  instance_id: string;
  instance_label: string;
  active_instance_id: string;
  active_instance_label: string;
  active_instance_mode: "cpu" | "gpu";
  model_configured?: boolean;
  evidence_extractor?: "deterministic_cpu";
  public_mode?: boolean;
};

export type KnowledgeDocument = {
  schema_version: "baidu-knowledge-v1";
  version: string;
  class_id: number;
  class_name: string;
  title: string;
  source: { title: string; url: string; attribution: string };
  markdown: string;
  requires_pesticide_warning: boolean;
  pesticide_warning?: string | null;
  chemical_detection?: "prevention_hierarchy" | "keyword_fallback" | "none";
  symptoms_html: string;
  features_html: string;
  prevention_html: string;
  full_html: string;
  sections?: KnowledgeSection[];
};

export type KnowledgeSection = {
  title: string;
  html: string;
  full_width: boolean;
};

export type TrendPayload = {
  scope: string;
  days: 7 | 30;
  total: number;
  by_date: Record<string, number>;
  crops: Record<string, number>;
  candidate_classes: Record<string, number>;
  field_severity: Record<string, number>;
  review_status: Record<string, number>;
  trace_cases: Array<{
    id: string;
    created_at: string;
    crop: string;
    candidate: string;
    field_severity: string;
    review_status: string;
  }>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

export function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

export async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? "请求失败，请稍后重试");
  }
  return payload as T;
}

export function saveEditToken(caseId: string, token?: string) {
  if (typeof window !== "undefined" && token) {
    window.localStorage.setItem(`crop-case-token:${caseId}`, token);
  }
}

export function editHeaders(caseId: string, json = false): HeadersInit {
  const token = typeof window === "undefined"
    ? null
    : window.localStorage.getItem(`crop-case-token:${caseId}`);
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(token ? { "X-Case-Edit-Token": token } : {}),
  };
}

export function saveDraftToken(draftId: string, token?: string) {
  if (typeof window !== "undefined" && token) {
    window.localStorage.setItem(`crop-draft-token:${draftId}`, token);
  }
}

export function draftHeaders(draftId: string, json = false): HeadersInit {
  const token = typeof window === "undefined"
    ? null
    : window.localStorage.getItem(`crop-draft-token:${draftId}`);
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(token ? { "X-Draft-Edit-Token": token } : {}),
  };
}

export function instanceHeaders(record: Pick<CaseRecord, "instance_id">): HeadersInit {
  return record.instance_id ? { "X-Crop-Instance": record.instance_id } : {};
}

export async function analyzeCase(record: Pick<CaseRecord, "id" | "instance_id">): Promise<CaseRecord> {
  return readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${record.id}/analyze`), {
    method: "POST",
    headers: { ...editHeaders(record.id), ...instanceHeaders(record) },
  }));
}

export function instanceLabel(instanceId?: string | null) {
  return ({ lab_cpu: "实验室 CPU", gpu_full: "原 GPU" } as Record<string, string>)[instanceId ?? ""] ?? "病例创建服务器";
}

export function publicResolutionReasons(reasons?: string[]) {
  return (reasons ?? []).filter((reason) => !/https?:\/\/|server error|traceback|bad gateway/i.test(reason));
}

export function severityLabel(value?: string | null) {
  return ({ low: "较低", medium: "中等", high: "较高", unknown: "无法判断" } as Record<string, string>)[value ?? "unknown"] ?? "无法判断";
}

export function riskLabel(value?: string | null) {
  return ({ low: "结果较可靠", medium: "结果有些不确定", high: "结果不够可靠", unknown: "尚未判断" } as Record<string, string>)[value ?? "unknown"] ?? "尚未判断";
}

export function resolutionLabel(value?: CaseRecord["resolution_status"]) {
  return ({
    conclusive: "已有可参考结果",
    retake_required: "需要补拍后再判断",
    no_supported_target: "未发现支持的目标",
    service_unavailable: "识别服务暂不可用",
  } as Record<string, string>)[value ?? ""] ?? "正在整理结果";
}

export function isConclusive(record?: Pick<CaseRecord, "resolution_status"> | null) {
  return record?.resolution_status === "conclusive";
}

export function isInsectCase(record?: Pick<CaseRecord, "host_knowledge" | "context"> | null) {
  return record?.host_knowledge?.available === true || record?.context?.subject_type === "insect";
}

export function userDiagnosisTitle(record?: CaseRecord | null) {
  if (!record) return "待分析";
  if (record.resolution_status === "no_supported_target") return "无法可靠判断";
  if (record.resolution_status === "retake_required") return "需要补拍后再判断";
  if (record.resolution_status === "service_unavailable") return "暂时无法完成判断";
  return record.analysis?.primary_diagnosis || record.detector_summary?.primary_candidate?.class_name || "待补充证据";
}

export function spreadSpeedLabel(value?: string | null) {
  return ({ unknown: "未提供", none: "暂未扩散", slow: "缓慢扩散", ongoing: "持续扩散", moderate: "中等扩散", rapid: "快速扩散" } as Record<string, string>)[value ?? "unknown"] ?? "未提供";
}

export function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
