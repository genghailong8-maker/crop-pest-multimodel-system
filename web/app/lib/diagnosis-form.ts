export const GROWTH_STAGE_OPTIONS = [
  ["seedling", "苗期"],
  ["vegetative", "营养生长期"],
  ["flowering", "开花期"],
  ["fruiting_or_seed_setting", "结果或结实期"],
  ["maturity", "成熟期"],
  ["uncertain", "不确定"],
] as const;

export type DiagnosisFormValues = {
  image: File;
  crop: string;
  part?: string;
  growthStage?: string;
  publicConsent: boolean;
};

export function buildDiagnosisFormData(values: DiagnosisFormValues): FormData {
  const form = new FormData();
  form.append("image", values.image);
  form.append("crop", values.crop);
  if (values.part) form.append("part", values.part);
  if (values.growthStage) form.append("growth_stage", values.growthStage);
  form.append("public_consent", String(values.publicConsent));
  return form;
}
