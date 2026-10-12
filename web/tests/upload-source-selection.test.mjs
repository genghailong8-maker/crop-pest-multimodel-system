import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
const styles = await readFile(new URL("../app/product-legacy.css", import.meta.url), "utf8");

test("gallery and camera upload use distinct native inputs and the same image flow", () => {
  assert.match(page, /ref=\{libraryInputRef\}[^>]*type="file"[^>]*accept="image\/jpeg,image\/png,image\/webp"[^>]*aria-hidden="true"[^>]*tabIndex=\{-1\}[^>]*onChange=\{chooseFile\}/);
  assert.match(page, /ref=\{cameraInputRef\}[^>]*type="file"[^>]*accept="image\/jpeg,image\/png,image\/webp"[^>]*capture="environment"[^>]*aria-hidden="true"[^>]*tabIndex=\{-1\}[^>]*onChange=\{chooseFile\}/);
  assert.match(page, /本地图库上传/);
  assert.match(page, /拍照上传/);
  assert.match(page, /openImagePicker\(libraryInputRef\.current\)/);
  assert.match(page, /openImagePicker\(cameraInputRef\.current\)/);
  assert.match(page, /input\.value = "";\s*input\.click\(\)/);
});

test("upload source choices remain keyboard-operable and adapt to narrow screens", () => {
  assert.match(page, /className="final-upload-choice"/);
  assert.match(page, /className="final-upload-choice final-upload-choice-camera"/);
  assert.match(styles, /\.final-upload-choice:focus-visible/);
  assert.match(styles, /\.final-upload-actions\s*\{[^}]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(styles, /@media \(max-width: 560px\)/);
});
