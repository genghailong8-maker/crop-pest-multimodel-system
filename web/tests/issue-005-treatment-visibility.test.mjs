import assert from "node:assert/strict";
import test from "node:test";
import { shouldRenderTreatmentSection } from "../app/lib/treatment-visibility.ts";

test("no-target and unavailable Treatment states render no Treatment section", () => {
  assert.equal(shouldRenderTreatmentSection(true, undefined, false), false);
  assert.equal(shouldRenderTreatmentSection(true, "unavailable", false), false);
  assert.equal(shouldRenderTreatmentSection(true, "unavailable", true), false);
});

test("valid local Treatment content stays visible for mild, moderate, and severe", () => {
  for (const tier of ["mild", "moderate", "severe"]) {
    assert.equal(shouldRenderTreatmentSection(true, "available", true), true, tier);
  }
});

test("empty available payload and explicit hide flag do not render an empty section", () => {
  assert.equal(shouldRenderTreatmentSection(true, "available", false), false);
  assert.equal(shouldRenderTreatmentSection(false, "available", true), false);
});
