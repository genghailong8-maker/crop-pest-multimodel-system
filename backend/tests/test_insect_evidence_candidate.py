from __future__ import annotations

import unittest

from app.search.evidence_extractor import (
    EvidenceExtractor,
    _associate_candidate_with_target,
    _has_foreign_leading_insect_subject,
    _is_human_medical_only_fragment,
)
from app.search.models import SearchEvidence, SearchSource


class InsectEvidenceCandidateTests(unittest.TestCase):
    def extract(self, section: str, clause: str, title: str = "芫菁", context: str = "") -> list[str]:
        source = SearchSource(
            id="replay-1",
            title=title,
            site_name="saved Tavily replay",
            url="https://example.test/saved-source",
            snippet=clause,
            content=context + clause,
            reliability_level="权威农业数据库",
        )
        evidence = SearchEvidence(
            class_name="芫菁",
            query_type=section,
            status="available",
            sources=[source],
        )
        result = EvidenceExtractor().extract(evidence)
        values = result.harms if section == "harms" else result.possible_causes
        return [item.conclusion for item in values]

    def test_reject_human_cantharidin_medical_only(self) -> None:
        clause = "斑蝥素对人体的胃肠、尿殖道、心脏和血管具有实质性损伤，中毒严重时，会出现血尿、肾脏衰竭、全身出血等症状，甚至导致死亡。"
        self.assertNotIn(clause, self.extract("harms", clause))

    def test_reject_cabbage_butterfly_clause(self) -> None:
        clause = "菜粉蝶幼虫取食叶片，咬成孔洞和缺口，严重时可将叶片吃光，只剩叶脉和叶柄，幼苗受害轻则影响包心，重则整株死亡。"
        self.assertNotIn(clause, self.extract("harms", clause))

    def test_reject_rove_beetle_clause(self) -> None:
        clause = "隐翅虫繁殖一年1-2代，以卵或幼虫在隐蔽处越冬，每年春夏繁殖较快，1天产卵2-6粒，最多可达23粒，寿命可长达6个月左右。"
        self.assertNotIn(clause, self.extract("possible_causes", clause))

    def test_reject_longhorn_beetle_lifecycle_clause(self) -> None:
        clause = "成虫的寿命不长，一般为10天至2个月，但在蛹室内越冬的成虫可能达到7-8个月，雄天牛寿命一般比雌天牛短。"
        self.assertNotIn(clause, self.extract("possible_causes", clause))

    def test_accept_saved_agricultural_harm_clause(self) -> None:
        clause = "成虫为植食性，大多在田间活动，迁飞力弱，取食大豆、花生、棉花、马铃薯等植物叶片和花瓣，对农业有一定的危害。"
        self.assertIn(
            clause,
            self.extract(
                "harms",
                clause,
                "saved source",
                context="芫菁属成虫为植食性昆虫。",
            ),
        )

    def test_reject_habitat_only_clause_as_harm(self) -> None:
        clause = "芫菁常栖息于中海拔以下山区林缘的植物叶面。"
        self.assertNotIn(clause, self.extract("harms", clause))

    def test_reject_crop_damage_clause_as_possible_cause(self) -> None:
        clause = "成虫为植食性，大多在田间活动，迁飞力弱，取食大豆、花生、棉花、马铃薯等植物叶片和花瓣，对农业有一定的危害。"
        self.assertNotIn(clause, self.extract("possible_causes", clause, "芫菁科昆虫之毒_搜狐网"))

    def test_accept_saved_agricultural_occurrence_clause(self) -> None:
        clause = "成虫为植食性，大多在田间活动，迁飞力弱，取食大豆、花生、棉花、马铃薯等植物叶片和花瓣，对农业有一定的危害。"
        source = SearchSource(
            id="replay-agriculture",
            title="芫菁科昆虫之毒_搜狐网",
            site_name="www.sohu.com",
            url="https://www.sohu.com/a/807953463_121119271",
            snippet=clause,
            content="芫菁科成虫为植食性昆虫。" + clause,
            reliability_level="其他可信农业专业站点",
        )
        associated, explicit = _associate_candidate_with_target("芫菁", source, clause, "harms")
        self.assertTrue(associated)
        self.assertFalse(explicit)  # accepted only via the source's same-line target context
        self.assertFalse(_has_foreign_leading_insect_subject("芫菁", clause))
        self.assertFalse(_is_human_medical_only_fragment(clause))

    def test_reject_insect_title_only_context(self) -> None:
        clause = "成虫出现于5~9月，主食多种豆科植物。"
        self.assertNotIn(clause, self.extract("possible_causes", clause, "芫菁"))

    def test_reject_subtype_season_clause_without_local_scope(self) -> None:
        source = SearchSource(
            id="source-4",
            title="如何防治豆宛青蟲 - 農業知識入口網",
            site_name="saved agriculture portal snapshot",
            url="https://kmweb.moa.gov.tw/knowledge_view.php?id=3686",
            retrieved_at="2026-10-01",
            reliability_level="普通网页",
            snippet="成虫出现于5~9月，主食多种豆科植物。",
            content="豆芫菁属中小型甲虫，是有毒性昆虫,体长1.3~2.5公分，体色黑色。成虫出现于5~9月，主食多种豆科植物。幼虫生活于土壤地下，以蝗虫卵为食，成虫会群聚一起，分布在平地至低山地区。",
        )
        result = EvidenceExtractor().extract(
            SearchEvidence(class_name="芫菁", status="available", sources=[source])
        )
        self.assertNotIn(
            "成虫出现于5~9月，主食多种豆科植物。",
            [item.conclusion for item in result.possible_causes],
        )

    def test_reject_local_context_with_competing_insect(self) -> None:
        source = SearchSource(
            id="mixed-line",
            title="芫菁",
            site_name="saved replay",
            url="https://example.test/mixed",
            snippet="菜粉蝶成虫于夏季出现并群聚取食。",
            content="芫菁是另一类甲虫。菜粉蝶成虫于夏季出现并群聚取食。",
            reliability_level="其他可信农业专业站点",
        )
        result = EvidenceExtractor().extract(
            SearchEvidence(class_name="芫菁", status="available", sources=[source])
        )
        self.assertNotIn(
            "菜粉蝶成虫于夏季出现并群聚取食。",
            [item.conclusion for item in result.possible_causes],
        )

    def test_reject_journal_issue_bibliography_as_aphid_cause(self) -> None:
        clause = "本期《中国农业科学》以“专题”的形式集中发表8 篇迁飞性害虫相关论文，这8 篇论文各有侧重，其中2 篇是关于玉米螟和蚜虫的种群动态，2 篇是关于环境条件对迁飞害虫的影响，2 篇是关于迁飞害虫的习性研究，另外2 篇是关于重要迁飞害虫稻飞虱的基因研究分析。"
        source = SearchSource(
            id="observed-aphid-research-source",
            title="迁飞性害虫发生与防控",
            site_name="sciopen.com",
            url="https://www.sciopen.com/local/article_pdf/10.3864/j.issn.0578-1752.2024.20.004.pdf",
            snippet=clause,
            content=clause,
            reliability_level="农业科研院所",
        )
        evidence = SearchEvidence(
            class_name="蚜虫",
            query_type="possible_causes",
            status="available",
            sources=[source],
        )
        result = EvidenceExtractor().extract(evidence)
        self.assertEqual(result.possible_causes, [])

    def test_reject_aphid_pesticide_mode_of_action_as_harm(self) -> None:
        clause = "蚜虫等刺吸式口器害虫取食吸入带有氟啶虫酰胺的植物汁液后，会被迅速阻止吸汁，1小时之内完全没有排泄物出现，最终因饥饿而死亡。"
        self.assertNotIn(
            clause,
            self.extract("harms", clause, "春季蚜虫很容易大爆发，学会这5个方法，清除彻底又省心 -农资与市场官网"),
        )

    def test_reject_aphid_control_difficulty_as_occurrence_cause(self) -> None:
        clause = "今年部分地区长时间的干旱是造成蚜虫难治的重要原因。"
        self.assertNotIn(
            clause,
            self.extract("possible_causes", clause, "春季蚜虫很容易大爆发，学会这5个方法，清除彻底又省心 -农资与市场官网"),
        )

    def test_reject_aphid_lifecycle_narrative_as_cause(self) -> None:
        clause = "2. 多数种类在生长季以无翅孤雌生殖,种群数量增长得异常快,到了营养条件变差的时候,无翅个体产下后代变为有翅个体,可以转移到营养条件好的环境继续为害。"
        self.assertNotIn(
            clause,
            self.extract("possible_causes", clause, "春季蚜虫很容易大爆发，学会这5个方法，清除彻底又省心 -农资与市场官网"),
        )

if __name__ == "__main__":
    unittest.main()
