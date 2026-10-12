from app.main import (
    _format_public_evidence_conclusion,
    _format_public_evidence_analysis,
    public_analysis_payload,
)


def test_gray_leaf_spot_weather_translation_tracks_source_claim():
    source_claim = (
        "The disease develops rapidly during prolonged periods of hot, humid weather."
    )
    assert _format_public_evidence_conclusion(
        source_claim, primary_diagnosis="玉米灰斑病", section="possible_causes"
    ) == (
        "持续高温高湿天气会加快玉米灰斑病的发展。"
    )


def test_gray_leaf_spot_generic_environment_claim_is_not_expanded():
    source_claim = (
        "GLS is commonly seen where favorable environmental conditions, "
        "high heat and humidity, occur annually."
    )
    assert _format_public_evidence_conclusion(
        source_claim, primary_diagnosis="玉米灰斑病", section="possible_causes"
    ) is None


def test_gray_leaf_spot_cause_formatter_preserves_provenance_and_suppresses_unsupported_claim():
    formatted = _format_public_evidence_analysis(
        {
            "status": "available",
            "harms": [],
            "possible_causes": [
                {
                    "conclusion": "GLS is commonly seen where favorable environmental conditions, high heat and humidity, occur annually.",
                    "source_ids": ["source-3"],
                },
                {
                    "conclusion": "The disease develops rapidly during prolonged periods of hot, humid weather.",
                    "source_ids": ["source-5"],
                },
            ],
        },
        primary_diagnosis="玉米灰斑病",
    )
    assert formatted["possible_causes"] == [
        {
            "conclusion": "持续高温高湿天气会加快玉米灰斑病的发展。",
            "source_ids": ["source-5"],
        }
    ]


def test_gray_leaf_spot_persisted_tavily_claims_render_with_sources():
    formatted = public_analysis_payload(
        {
            "primary_diagnosis": "玉米灰斑病",
            "evidence_analysis": {
                "status": "available",
                "harms": [
                    {
                        "conclusion": "Initial symptoms are small (one-sixteenth inch in diameter), water-soaked, circular lesions",
                        "source_ids": ["source-1"],
                    },
                    {
                        "conclusion": "As the disease develops and lesions expand, huge areas of the leaf are damaged",
                        "source_ids": ["source-4"],
                    },
                ],
                "possible_causes": [
                    {
                        "conclusion": "Conditions for development: Warm temperatures and high humidity create an optimum environment for gray leaf spot.",
                        "source_ids": ["source-5"],
                    },
                    {
                        "conclusion": "The light brown color of the lesions is retained until environmental conditions are favorable for the production of conidia, at which time they take on a silvery-gray cast, hence the name of the disease",
                        "source_ids": ["source-5"],
                    },
                ],
            },
            "sources": [
                {"id": "source-1", "title": "Initial symptoms"},
                {"id": "source-4", "title": "Leaf damage"},
                {"id": "source-5", "title": "Disease conditions"},
            ],
        }
    )

    evidence = formatted["evidence_analysis"]
    assert [item["conclusion"] for item in evidence["harms"]] == [
        "初期病斑较小，呈水浸状、近圆形。",
        "随着病害发展，病斑扩大或汇合会造成叶片受损。",
    ]
    assert [item["conclusion"] for item in evidence["possible_causes"]] == [
        "温暖且湿度较高的环境有利于玉米灰斑病发生和发展。"
    ]
    assert {source["id"] for source in formatted["sources"]} == {
        "source-1",
        "source-4",
        "source-5",
    }


def test_gray_leaf_spot_suppresses_legacy_bad_conclusion_and_orphan_source():
    formatted = public_analysis_payload(
        {
            "primary_diagnosis": "玉米灰斑病",
            "evidence_analysis": {
                "status": "available",
                "harms": [{"conclusion": "受害事实", "source_ids": ["source-5"]}],
                "possible_causes": [
                    {
                        "conclusion": "温度、湿度和水分等环境条件有利于玉米灰斑病病斑扩展。",
                        "source_ids": ["source-3"],
                    }
                ],
            },
            "sources": [
                {"id": "source-3", "title": "generic source"},
                {"id": "source-5", "title": "disease harm source"},
            ],
        }
    )
    assert formatted["evidence_analysis"]["possible_causes"] == []
    assert [source["id"] for source in formatted["sources"]] == ["source-5"]


def test_aphid_suppresses_persisted_control_difficulty_and_orphan_source():
    formatted = public_analysis_payload(
        {
            "primary_diagnosis": "蚜虫",
            "evidence_analysis": {
                "status": "available",
                "harms": [],
                "possible_causes": [
                    {
                        "conclusion": "这就是蚜虫很难彻底根除的原因。",
                        "source_ids": ["source-2"],
                    },
                    {
                        "conclusion": "这就是蚜虫难根除的又一个原因。",
                        "source_ids": ["source-2"],
                    },
                ],
            },
            "sources": [{"id": "source-2", "title": "防治难度材料"}],
        }
    )
    assert formatted["evidence_analysis"]["possible_causes"] == []
    assert formatted["sources"] == []
