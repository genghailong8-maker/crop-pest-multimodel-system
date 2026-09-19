from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "knowledge" / "insect-host-r3.1"
DOC = ROOT / "docs" / "competition" / "r3.1" / "《AI示意图提示词与来源依据》.md"
OUTPUT = KNOWLEDGE / "ai-illustration-manifest.json"
TASKS = ROOT / "docs" / "competition" / "r3.1" / "《AI示意图生成任务清单》.md"
ASSETS = ROOT / "docs" / "competition" / "r3.1" / "《AI示意图正式资产清单》.md"

HOST_SLUGS = {
    "大豆": "soybean", "玉米": "corn", "小麦": "wheat", "棉花": "cotton",
    "桃": "peach", "葡萄": "grape", "马铃薯": "potato", "茶": "tea",
}
SEVERITY_ZH = {"轻度": "mild", "中度": "moderate", "重度": "severe"}


def parse_prompt_sections(text: str) -> dict[tuple[str, str, str], dict[str, str]]:
    pattern = re.compile(
        r"^### (?P<insect>.+?) × (?P<host>.+?) × (?P<label>轻度|中度|重度)\n(?P<body>.*?)(?=^### |\Z)",
        re.M | re.S,
    )
    parsed = {}
    for match in pattern.finditer(text):
        body = match.group("body")
        status = re.search(r"`PROMPT_EVIDENCE_STATUS`: `([^`]+)`", body)
        prompt = re.search(r"#### Final image-generation prompt\s*\n\s*> (.+?)(?=\n\n#### )", body, re.S)
        if not status or not prompt:
            continue
        final_prompt = "\n".join(line.removeprefix("> ") for line in prompt.group(1).strip().splitlines())
        parsed[(match.group("insect"), match.group("host"), SEVERITY_ZH[match.group("label")])] = {
            "prompt_evidence_status": status.group(1),
            "final_prompt": final_prompt,
        }
    return parsed


def main() -> None:
    evidence = json.loads((KNOWLEDGE / "severity-evidence.json").read_text(encoding="utf-8"))
    capability = json.loads((KNOWLEDGE / "capability-fallback.json").read_text(encoding="utf-8"))
    prompts = parse_prompt_sections(DOC.read_text(encoding="utf-8"))
    full = {
        (r["class_id"], r["insect"], r["crop"])
        for r in capability["records"]
        if r["status"] == "FULL" and r["capabilities"]["severity"]
    }
    records = []
    for row in evidence["records"]:
        if row.get("object_type") != "insect_host" or row.get("status") != "COMPLETE":
            continue
        key = (row["insect"], row["crop"], row["severity"])
        prompt = prompts.get(key)
        if not prompt or prompt["prompt_evidence_status"] != "TRACEABLE":
            continue
        full_key = (row["class_id"], row["insect"], row["crop"])
        if full_key not in full:
            raise SystemExit(f"TRACEABLE prompt is not a FULL host: {key}")
        host_slug = HOST_SLUGS[row["crop"]]
        asset_id = f"r31-class{row['class_id']}-{host_slug}-{row['severity']}"
        filename = f"class{row['class_id']}-{host_slug}-{row['severity']}.webp"
        records.append({
            "class_id": row["class_id"],
            "insect": row["insect"],
            "host": row["crop"],
            "severity": row["severity"],
            "prompt_evidence_status": "TRACEABLE",
            "final_prompt": prompt["final_prompt"],
            "source_ids": row["source_ids"],
            "observable_features": row["observable_features"],
            "evidence_taxon": row["evidence_taxon"],
            "asset_id": asset_id,
            "target_filename": filename,
            "target_relative_path": f"web/public/r31/severity/{filename}",
            "generation_status": "PENDING_IMAGE_GENERATION",
            "review_status": "NOT_RUN",
            "image_sha256": None,
        })
    records.sort(key=lambda r: (r["class_id"], r["host"], ["mild", "moderate", "severe"].index(r["severity"])))
    hosts = {(r["class_id"], r["host"]) for r in records}
    if len(records) != 39 or len(hosts) != 13:
        raise SystemExit(f"frozen gate mismatch: records={len(records)} hosts={len(hosts)}")
    if len({r["asset_id"] for r in records}) != 39 or len({r["target_relative_path"] for r in records}) != 39:
        raise SystemExit("asset ids or target paths are not unique")
    payload = {
        "schema_version": "1.0",
        "batch": "R3.1 Batch 4B",
        "source_of_truth": [
            "docs/competition/r3.1/《AI示意图提示词与来源依据》.md",
            "knowledge/insect-host-r3.1/severity-evidence.json",
        ],
        "asset_root": "web/public/r31/severity",
        "expected_records": 39,
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    task_lines = ["# 《AI示意图生成任务清单》", "", "农业知识与 Prompt 已冻结；仅以下 TRACEABLE 项可生成。", ""]
    asset_lines = ["# 《AI示意图正式资产清单》", "", "统一声明：AI示意图 · 非真实照片 · 仅供辅助判断。示意图依据经过审核的农业资料生成，不作为病虫害诊断或现场检测依据。", "", "| Asset ID | 昆虫 | 寄主 | Severity | Source IDs | 目标路径 | Generation | Review |", "|---|---|---|---|---|---|---|---|"]
    for r in records:
        task_lines += [
            f"## {r['asset_id']}", "",
            f"- insect：{r['insect']}", f"- host：{r['host']}", f"- severity：{r['severity']}",
            f"- target filename：`{r['target_filename']}`", f"- source IDs：{', '.join(r['source_ids'])}",
            f"- generation_status：`{r['generation_status']}`", "", "### Exact final prompt", "", f"> {r['final_prompt']}", "",
        ]
        asset_lines.append(f"| `{r['asset_id']}` | {r['insect']} | {r['host']} | {r['severity']} | {', '.join(r['source_ids'])} | `{r['target_relative_path']}` | {r['generation_status']} | {r['review_status']} |")
    TASKS.write_text("\n".join(task_lines), encoding="utf-8")
    ASSETS.write_text("\n".join(asset_lines) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "hosts": len(hosts), "output": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
