import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_archive import validate_archive


ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "docs" / "competition" / "r3.1" / "《R3.1完整知识库归档版》.md"


class ArchiveParityTests(unittest.TestCase):
    def test_historical_archive_is_self_consistent(self) -> None:
        text = ARCHIVE.read_text(encoding="utf-8")
        self.assertIn("ARCHIVE_KNOWLEDGE_PARITY = PASS", text)
        self.assertEqual(text.count("<!-- ARCHIVE_INSECT:"), 8)
        self.assertEqual(text.count("<!-- ARCHIVE_HOST:"), 38)
        for term in (
            "FULL", "PARTIAL", "REJECTED", "host_relation", "host_damage", "severity",
            "host_general_treatment", "host_severity_treatment", "recommended_host",
            "confirmed_host", "HOST_SEVERITY_TREATMENT", "HOST_GENERAL_TREATMENT",
            "GENERAL_INSECT_TREATMENT", "NO_TREATMENT",
        ):
            self.assertIn(term, text)

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
