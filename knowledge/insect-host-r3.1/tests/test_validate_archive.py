import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_archive import validate_archive


ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "docs" / "competition" / "r3.1" / "《R3.1完整知识库归档版》.md"


class ArchiveParityTests(unittest.TestCase):
    def test_current_archive_matches_ssot(self) -> None:
        result = validate_archive(archive_path=ARCHIVE)
        self.assertEqual(result["status"], "PASS", result)

    def test_missing_rubric_fails_closed(self) -> None:
        text = ARCHIVE.read_text(encoding="utf-8")
        needle = "<!-- ARCHIVE_SEVERITY:"
        start = text.index(needle)
        end = text.index("\n", start)
        marker = text[start:end]
        mutated = text.replace(marker, "")
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / ARCHIVE.name
            candidate.write_text(mutated, encoding="utf-8")
            result = validate_archive(archive_path=candidate)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(next(item for item in result["checks"] if item["name"] == "severity_provenance_markers")["passed"])


if __name__ == "__main__":
    unittest.main()
