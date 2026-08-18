export type Detection = {
  class_id: number;
  class_name: string;
  class_name_en?: string;
  category_type?: string;
  confidence: number;
  bbox: [number, number, number, number];
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

export function instanceHeaders(record: Pick<CaseRecord, "instance_id">): HeadersInit {
  return record.instance_id ? { "X-Crop-Instance": record.instance_id } : {};
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

export function userDiagnosisTitle(record?: CaseRecord | null) {
  if (!record) return "待分析";
  if (record.resolution_status === "no_supported_target") return "无法可靠判断";
  if (record.resolution_status === "retake_required") return "需要补拍后再判断";
  if (record.resolution_status === "service_unavailable") return "暂时无法完成判断";
  return record.analysis?.primary_diagnosis || record.detector_summary?.primary_candidate?.class_name || "待补充证据";
}

export function spreadSpeedLabel(value?: string | null) {
  return ({ unknown: "不清楚", none: "暂未扩散", slow: "缓慢", moderate: "中等", rapid: "快速" } as Record<string, string>)[value ?? "unknown"] ?? "不清楚";
}

export function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
