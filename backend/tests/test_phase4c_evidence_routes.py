from app.search.evidence_extractor import EvidenceExtractor
from app.search.models import SearchEvidence, SearchSource
from app.search.tavily import _query


def test_phase4c_disease_cause_queries_target_extension_condition_evidence() -> None:
    rice_query = _query("水稻稻瘟病", "possible_causes")
    nclb_query = _query("玉米大斑病", "possible_causes")

    assert "叶面湿润" in rice_query
    assert "病原菌" in rice_query
    assert "病残体" in nclb_query
    assert "越冬" in nclb_query
    assert "农业技术" in nclb_query


def test_phase4c_extension_condition_fragments_are_extracted_as_causes() -> None:
    evidence = SearchEvidence(
        class_name="玉米大斑病",
        query_type="possible_causes",
        status="available",
        sources=[
            SearchSource(
                id="sdsu-nclb",
                title="Northern Corn Leaf Blight Developing in Corn",
                site_name="extension.sdstate.edu",
                url="https://extension.sdstate.edu/northern-corn-leaf-blight-developing-corn",
                snippet="Northern corn leaf blight develops under extended leaf wetness conditions and warm temperatures.",
                content=(
                    "The pathogen overwinters in corn residue and is dispersed onto corn leaves by wind and rain. "
                    "Northern corn leaf blight develops under extended leaf wetness conditions and warm temperatures."
                ),
            )
        ],
    )

    result = EvidenceExtractor().extract(evidence)

    assert result.status == "available"
    assert result.possible_causes
    assert result.possible_causes[0].source_ids == ["sdsu-nclb"]
