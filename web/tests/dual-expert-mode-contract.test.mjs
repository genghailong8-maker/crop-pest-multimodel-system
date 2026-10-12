import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
const contextConfirmation = await readFile(new URL("../app/components/R3ContextConfirmation.tsx", import.meta.url), "utf8");

test("the user must choose a direct recognition mode before upload", () => {
  assert.match(page, /type TargetMode = "plant_disease" \| "insect_pest"/);
  assert.match(page, /if \(!targetMode\) items\.push\("识别模式"\)/);
  assert.match(page, /form\.append\("target_mode", targetMode\)/);
  assert.match(page, /植物病害/);
  assert.match(page, /昆虫虫害/);
});

test("CLIP context does not switch the selected expert mode", () => {
  assert.match(page, /targetMode === "insect_pest" \? "insect" : "plant"/);
  assert.doesNotMatch(contextConfirmation, /onSubjectType/);
  assert.match(contextConfirmation, /CLIP仅提供视觉上下文建议/);
  assert.match(contextConfirmation, /onCropSpecies/);
  assert.match(contextConfirmation, /onAffectedPart/);
  assert.match(contextConfirmation, /onInsectSpecies/);
});
