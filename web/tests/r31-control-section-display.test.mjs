import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const sourcePath = new URL("../app/components/R31HostKnowledgePanel.tsx", import.meta.url);

test("R3.1 control sections use Chinese labels and suppress empty/duplicate content", async () => {
  const source = await readFile(sourcePath, "utf8");
  assert.match(source, /agricultural_control:\s*"农业防治"/);
  assert.match(source, /physical_control:\s*"物理防治"/);
  assert.match(source, /biological_control:\s*"生物防治"/);
  assert.match(source, /monitoring:\s*"监测建议"/);
  assert.match(source, /typeof value === "string" && value\.trim\(\)\.length > 0/);
  assert.match(source, /key !== "management" \|\| !specificControlTexts\.has\(value\.trim\(\)\)/);
});

test("ordinary R3.1 UI keeps confirmed host but hides internal capability and provenance identifiers", async () => {
  const source = await readFile(sourcePath, "utf8");
  assert.match(source, /已确认寄主：\$\{selected\}/);
  assert.match(source, /confirmed_host/);
  assert.doesNotMatch(source, /当前寄主能力|USER_CONFIRMED_HOST|Backend 证据约束|来源 ID|R3\.1 作物知识/);
  assert.doesNotMatch(source, /FULL|COMPLETE|SEVERITY_ONLY|host capability|treatment capability status/);
  assert.match(source, /source\.title/);
});
