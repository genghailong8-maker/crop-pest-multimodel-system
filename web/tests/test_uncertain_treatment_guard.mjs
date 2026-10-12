import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const sourcePath = new URL("../app/components/R31HostKnowledgePanel.tsx", import.meta.url);

test("R3.1 host treatment is not rendered for a persisted uncertain severity", async () => {
  const source = await readFile(sourcePath, "utf8");
  assert.match(source, /record\.severity\?\.status === "available" && record\.severity\.level === "uncertain"/);
  assert.match(source, /hasUncertainSeverity \? null : <TreatmentPanel treatment=\{visibleKnowledge\.treatment\} \/>/);
  assert.match(source, /isOther && !hasUncertainSeverity/);
});
