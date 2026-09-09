"""Finalize deterministic documentation status text after generators run."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "knowledge" / "insect-host-r3.1" / "README.md"


def main() -> None:
    text = README.read_text(encoding="utf-8")
    stale = "当前 36 个 Prompt 为 `TRACEABLE`、78 个保持 `NEEDS_EVIDENCE`"
    current = "最终受控扩充后当前 39 个 Prompt 为 `TRACEABLE`、75 个保持 `NEEDS_EVIDENCE`"
    text = text.replace(stale, current)
    if stale in text:
        raise RuntimeError("README stale Prompt count remains")
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
