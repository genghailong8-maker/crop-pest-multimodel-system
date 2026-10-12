export function shouldRenderTreatmentSection(
  showTreatment: boolean,
  status: string | undefined,
  hasTreatmentContent: boolean,
): boolean {
  return showTreatment && status === "available" && hasTreatmentContent;
}
