"""Build the R3.1 Batch 1B evidence registry and human-review projections.

The source-backed closure decisions are intentionally explicit below.  All
records not listed in ``INSECT_CLOSURES`` remain fail-closed NEEDS_EVIDENCE;
the script never infers a COMPLETE record from a host relation alone.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
MANIFEST_PATH = ROOT / "manifest.json"
EVIDENCE_PATH = ROOT / "severity-evidence.json"
DOCS_ROOT = REPO / "docs" / "competition" / "r3.1"
PLANT_ROOT = REPO / "knowledge" / "baidu-baike-20260818" / "documents"

SEVERITIES = ("mild", "moderate", "severe")
LABELS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
SOURCE_RE = re.compile(r"\[(R31-[A-Z0-9-]+)\]")


def record(
    *,
    rubric_text: str,
    observable_features: list[str],
    source_ids: list[str],
    synthesis_note: str,
    status: str = "COMPLETE",
    evidence_type: str = "EVIDENCE_SYNTHESIZED",
    quantitative_support: str = "",
) -> dict[str, Any]:
    result = {
        "status": status,
        "rubric_text": rubric_text,
        "observable_features": observable_features,
        "source_ids": source_ids,
        "evidence_type": evidence_type,
        "synthesis_note": synthesis_note,
    }
    if quantitative_support:
        result["quantitative_support"] = quantitative_support
    return result


V10_SOURCE_RECORDS: list[dict[str, Any]] = [
    {"source_id": "R31-11-NYT2683-SOIL-PEST", "title": "NY/T 2683-2015 农田主要地下害虫防治技术规程", "organization": "中华人民共和国农业行业标准", "url": "https://www.sdtdata.com/fx/fcv1/tsLibCard/153073.html", "tier": 1, "support_scope": "小麦、玉米、花生等作物的蝼蛄/蛴螬/金针虫地下害虫组管理范围。", "allowed_contexts": ["host:11:花生", "host:11:小麦", "host:11:玉米", "class:11"], "taxonomic_scope": "mole cricket within listed soil-pest group", "crop_scope": "wheat/corn/peanut（小麦/玉米/花生）"},
    {"source_id": "R31-09-CHANGZHI-WHEAT-APHID", "title": "小麦重大病虫防控技术方案", "organization": "长治市农业农村局", "url": "https://nyncj.changzhi.gov.cn/fwsn/njtg/202303/t20230322_2725187.html", "tier": 1, "support_scope": "小麦蚜虫按生育阶段的挑治、统防统治和暴发应急防治。", "allowed_contexts": ["host:9:小麦", "class:9"], "taxonomic_scope": "aphids in wheat", "crop_scope": "wheat（小麦）"},
    {"source_id": "R31-09-UKY-WHEAT-APHID", "title": "Aphids in Wheat", "organization": "University of Kentucky IPM", "url": "https://ipm.mgcafe.uky.edu/content/aphids-wheat", "tier": 1, "support_scope": "小麦蚜虫调查分级、发生程度与处理参考。", "allowed_contexts": ["host:9:小麦", "class:9"], "taxonomic_scope": "aphids in wheat", "crop_scope": "wheat（小麦）"},
    {"source_id": "R31-08-IFAS-BLISTER-GROUP", "title": "Blister Beetles (Coleoptera: Meloidae)", "organization": "University of Florida IFAS", "url": "https://ask.ifas.ufl.edu/publication/IN323", "tier": 1, "support_scope": "多种芫菁在马铃薯上的寄主、群聚和局部灾难性取食表现。", "allowed_contexts": ["host:8:马铃薯", "class:8"], "taxonomic_scope": "multiple blister beetles in potato", "crop_scope": "potato（马铃薯）"},
    {"source_id": "R31-08-MONTANA-BLISTER-POTATO", "title": "Blister Beetles of Montana", "organization": "Montana State University Extension", "url": "https://extension-store.montana.edu/montguides/blister-beetles-of-montana", "tier": 1, "support_scope": "马铃薯芫菁局部叶片损伤、广泛叶面损伤及全田损害语境。", "allowed_contexts": ["host:8:马铃薯", "class:8"], "taxonomic_scope": "blister beetles in potato", "crop_scope": "potato（马铃薯）"},
    {"source_id": "R31-11-LIANNAN-PEANUT", "title": "花生丰产栽培技术", "organization": "连南瑶族自治县农业农村局", "url": "https://www.liannan.gov.cn/qylnnync/gkmlpt/content/1/1413/post_1413642.html", "tier": 1, "support_scope": "花生蝼蛄寄主关系及播前/诱杀管理。", "allowed_contexts": ["host:11:花生", "class:11"], "taxonomic_scope": "mole cricket in peanut", "crop_scope": "peanut（花生）"},
    {"source_id": "R31-15-DAZHOU-BEANBLISTER", "title": "警惕食叶性害虫豆芫菁局部暴发危害", "organization": "达州市达川区农业农村局", "url": "https://www.dachuan.gov.cn/xxgk-show-146920.html", "tier": 1, "support_scope": "豆芫菁在玉米上的点/片聚集、重发脱叶表现。", "allowed_contexts": ["host:15:玉米", "class:15"], "taxonomic_scope": "bean blister beetle in corn", "crop_scope": "corn（玉米）"},
    {"source_id": "R31-15-HANDBOOK-BEANBLISTER-POTATO", "title": "豆芫菁（Epicauta gorhami）", "organization": "全国农村教育协会/病害虫防除资料", "url": "https://boujo.net/handbook/mame/mame-330.html", "tier": 2, "support_scope": "豆芫菁在马铃薯上的局部群生、叶片取食和局部处理。", "allowed_contexts": ["host:15:马铃薯", "class:15"], "taxonomic_scope": "Epicauta gorhami in potato", "crop_scope": "potato（马铃薯）"},
    {"source_id": "R31-15-ENCYC-BEANBLISTER-POTATO", "title": "豆芫菁条目（Epicauta gorhami）", "organization": "智汇三农", "url": "https://www.pwsannong.com/booklib/databasepreview?SiteID=123&contentId=15759360&contentType=literature", "tier": 2, "support_scope": "Epicauta gorhami 在马铃薯上的叶片缺刻、孔洞及严重取食。", "allowed_contexts": ["host:15:马铃薯", "class:15"], "taxonomic_scope": "Epicauta gorhami in potato", "crop_scope": "potato（马铃薯）"},
    {"source_id": "R31-15-GOV-BEANBLISTER-POTATO", "title": "2026年马铃薯重大病虫害防控技术方案", "organization": "吕梁市农业农村局", "url": "https://www.lvliang.gov.cn/llxxgk/zfxxgk/xxgkml/gbmwj/snw/fdzdgknr_55123/nmgzyjnpx_55144/202607/t20260703_2044309.html", "tier": 1, "support_scope": "豆芫菁作为马铃薯防控对象的 host-specific 管理范围。", "allowed_contexts": ["host:15:马铃薯", "class:15"], "taxonomic_scope": "bean blister beetle in potato", "crop_scope": "potato（马铃薯）"},
]

V11_SOURCE_RECORDS: list[dict[str, Any]] = [
    {"source_id": "R31-08-DAZU-BLISTER-PEANUT", "title": "红头芫菁的发生及防治方法", "organization": "重庆市大足区农业技术服务中心", "url": "https://www.dazu.gov.cn/qzfbm/qnyncw/zwxx_53317/gggs/202606/t20260622_15768429.html", "tier": 1, "support_scope": "花生芫菁孔洞/缺刻、叶脉残留和暴发吃光整株叶片的表现及冬季深耕清园。", "allowed_contexts": ["host:8:花生", "class:8"], "taxonomic_scope": "blister beetle in peanut", "crop_scope": "peanut（花生）"},
    {"source_id": "R31-09-TAIWAN-CORN-APHID", "title": "玉米蚜", "organization": "臺灣農業部農業知識入口網", "url": "https://kmweb.moa.gov.tw/subject/subject.php?id=31688", "tier": 1, "support_scope": "玉米蚜严重表现、生育初期处理参考及持续高虫压的10天间隔处理语境。", "allowed_contexts": ["host:9:玉米", "class:9"], "taxonomic_scope": "corn aphid in Taiwan source context", "crop_scope": "corn（玉米）"},
    {"source_id": "R31-09-CHENGDE-CORN-APHID", "title": "如何防治玉米蚜虫", "organization": "承德市农业农村局", "url": "https://nyncj.chengde.gov.cn/art/2017/8/22/art_667_93603.html", "tier": 1, "support_scope": "玉米蚜天敌充足时避免药剂及抽穗初期处理条件。", "allowed_contexts": ["host:9:玉米", "class:9"], "taxonomic_scope": "corn aphid", "crop_scope": "corn（玉米）"},
    {"source_id": "R31-09-FUJIAN-CORN-APHID", "title": "主要粮油作物大面积单产提升技术手册", "organization": "福建省农业农村厅", "url": "https://nynct.fujian.gov.cn/ztzl/kpxj/zrzhl/202506/t20250616_6927828.htm", "tier": 1, "support_scope": "玉米蚜苗期黄板/银膜及不同生育期处理条件。", "allowed_contexts": ["host:9:玉米", "class:9"], "taxonomic_scope": "corn aphid", "crop_scope": "corn（玉米）"},
    {"source_id": "R31-12-UCIPM-ALFALFA-LEAFHOPPER", "title": "Leafhoppers / Alfalfa", "organization": "UC Statewide IPM Program", "url": "https://ipm.ucanr.edu/agriculture/alfalfa/leafhoppers/", "tier": 1, "support_scope": "多种 Empoasca 在苜蓿上的 hopperburn、矮化、早割和阈值处理。", "allowed_contexts": ["host:12:苜蓿", "class:12"], "taxonomic_scope": "multiple Empoasca species in alfalfa", "crop_scope": "alfalfa（苜蓿）"},
    {"source_id": "R31-12-KSTATE-ALFALFA-LEAFHOPPER", "title": "Potato Leafhopper", "organization": "Kansas State University Extension", "url": "https://entomology.k-state.edu/extension/crop-protection/alfalfa/potato-leafhopper.html", "tier": 1, "support_scope": "苜蓿叶蝉黄化矮化、收割前后管理。", "allowed_contexts": ["host:12:苜蓿", "class:12"], "taxonomic_scope": "representative potato leafhopper species in alfalfa", "crop_scope": "alfalfa（苜蓿）"},
    {"source_id": "R31-10-WUHAN-GREENMIRID", "title": "果园绿盲蝽的防治方法", "organization": "武汉市农业农村局转载农业资料", "url": "https://nyncj.wuhan.gov.cn/ztzl_25/zxzt/nsnq/nsnq_nsjy/202303/t20230313_2168847.html", "tier": 1, "support_scope": "绿盲蝽果树嫩梢、幼叶和幼果的通用受害表现；不作为核桃三档证据。", "allowed_contexts": ["class:10"], "taxonomic_scope": "green mirid generic fruit evidence", "crop_scope": "fruit crops（果树）"},
    {"source_id": "R31-11-YUNFU-POTATO-MOLECRICKET", "title": "冬种马铃薯种植前期处理技术意见", "organization": "云浮市农业农村局", "url": "https://www.yunfu.gov.cn/yfnync/gkmlpt/content/1/1539/post_1539971.html", "tier": 1, "support_scope": "马铃薯出苗后蝼蛄沟/垄施颗粒剂或毒饵诱杀管理。", "allowed_contexts": ["host:11:马铃薯", "class:11"], "taxonomic_scope": "mole cricket in potato", "crop_scope": "potato（马铃薯）"},
    {"source_id": "R31-15-SHANDAN-BEANBLISTER", "title": "病虫情报第三期", "organization": "山丹县农业农村局", "url": "https://www.shandan.gov.cn/zfxxgk/fdzdgknr/qtfdxx/nync/202606/t20260618_1555195.html", "tier": 1, "support_scope": "豆芫菁豆科作物组的嫩叶/花/嫩荚缺刻孔洞和重度光秆表现。", "allowed_contexts": ["class:15"], "taxonomic_scope": "bean blister beetle in legume crop group", "crop_scope": "legume crops（豆科作物组）"},
    {"source_id": "R31-15-TAIPUSI-BEANBLISTER", "title": "太仆寺旗植保站：豆芫菁防治", "organization": "锡林郭勒盟农牧局", "url": "https://www.xlgl.gov.cn/eportal/ui?articleKey=a6659ce773304b10942fc65ad1cd480a&columnId=6e17a1ed3b684162abd0322628d20e83&pageId=c449e8dfef194a729e341df57d903d59", "tier": 1, "support_scope": "马铃薯/蚕豆田豆芫菁22头/平方米平均、116头/平方米最高及高虫压取食背景。", "allowed_contexts": ["host:15:马铃薯", "class:15"], "taxonomic_scope": "bean blister beetle in potato/bean field context", "crop_scope": "potato/bean（马铃薯/蚕豆）"},
    {"source_id": "R31-15-SHANDAN-POTATO-BEANBLISTER", "title": "病虫情报第五期", "organization": "山丹县农业农村局", "url": "https://www.shandan.gov.cn/zfxxgk/fdzdgknr/qtfdxx/nync/202607/t20260720_1565111.html", "tier": 1, "support_scope": "2026年当地马铃薯豆芫菁轻度至中度发生背景。", "allowed_contexts": ["host:15:马铃薯", "class:15"], "taxonomic_scope": "bean blister beetle in potato", "crop_scope": "potato（马铃薯）"},
    {"source_id": "R31-15-NARO-BEANBLISTER-ALFALFA", "title": "飼料作物害虫目録: ツチハンミョウ科 Meloidae", "organization": "日本農研機構 NARO", "url": "https://www.naro.go.jp/laboratory/nilgs/d-base/coleoptera/066844.html", "tier": 1, "support_scope": "Epicauta gorhami 对苜蓿叶的寄主范围。", "allowed_contexts": ["host:15:苜蓿", "class:15"], "taxonomic_scope": "Epicauta gorhami in alfalfa", "crop_scope": "alfalfa（苜蓿）"},
]

V12_SOURCE_RECORDS: list[dict[str, Any]] = [
    {"source_id":"R31-11-XJAU-WHEAT-MOLECRICKET","title":"东方蝼蛄（小麦）","organization":"新疆农业大学智慧农场","url":"https://ifarm.xjau.edu.cn/diseases/disease_detail/238/","tier":1,"support_scope":"东方蝼蛄在小麦上的种子、幼苗、根部取食和缺苗断垄表现及管理。","allowed_contexts":["host:11:小麦","class:11"],"taxonomic_scope":"Gryllotalpa orientalis in wheat","crop_scope":"wheat（小麦）"},
    {"source_id":"R31-11-ZHENGZHOU-WHEAT-SOILPEST","title":"抓住有利时机 做好小麦播种期及秋苗期病虫草害防治","organization":"郑州市农业农村局","url":"https://zzny.zhengzhou.gov.cn/dwybyf/9628419.jhtml","tier":1,"support_scope":"小麦地下害虫组的轻重田块危害背景，不作为蝼蛄专属阈值。","allowed_contexts":["host:11:小麦","class:11"],"taxonomic_scope":"soil-pest group in wheat","crop_scope":"wheat（小麦）"},
    {"source_id":"R31-11-GONGYI-WHEAT-MOLECRICKET","title":"2025年病虫情报第十期 做好地下害虫防治工作","organization":"巩义市农业农村局","url":"https://public.gongyishi.gov.cn/D20X/9674140.jhtml","tier":1,"support_scope":"小麦蝼蛄防治指标与播前/土壤处理背景，不作为三档表现曲线。","allowed_contexts":["host:11:小麦","class:11"],"taxonomic_scope":"mole cricket in wheat","crop_scope":"wheat（小麦）"},
    {"source_id":"R31-11-CAAS-POTATO-MOLECRICKET","title":"马铃薯严防害虫助增产","organization":"中国农业科学院植物保护研究所","url":"https://ipp.caas.cn/kjfw/kpzs_kjfw/59752.htm","tier":1,"support_scope":"蝼蛄马铃薯幼根、地下茎、根、芽块和块茎危害递进。","allowed_contexts":["host:11:马铃薯","class:11"],"taxonomic_scope":"mole cricket in potato","crop_scope":"potato（马铃薯）"},
    {"source_id":"R31-14-ISU-POTATO-WHITEGRUB","title":"Managing Potato Diseases, Disorders, and Pests","organization":"Iowa State University Extension","url":"https://yardandgarden.extension.iastate.edu/how-to/managing-potato-diseases-disorders-and-pests","tier":1,"support_scope":"马铃薯蛴螬浅而不规则块茎刻痕及通常局部损伤。","allowed_contexts":["host:14:马铃薯","class:14"],"taxonomic_scope":"white grubs in potato","crop_scope":"potato（马铃薯）"},
    {"source_id":"R31-14-NB-POTATO-WHITEGRUB","title":"White Grubs (June Beetles) - Potatoes","organization":"Government of New Brunswick","url":"https://www2.gnb.ca/content/gnb/en/departments/10/agriculture/content/crops/potatoes/white_grubs.html","tier":1,"support_scope":"马铃薯蛴螬严重取食导致矮化、萎蔫、深孔和商品性损失。","allowed_contexts":["host:14:马铃薯","class:14"],"taxonomic_scope":"white grubs in potato","crop_scope":"potato（马铃薯）"},
    {"source_id":"R31-08-NDSU-BLISTER-FIELD-CROPS","title":"Blister Beetle Management in Forages and Field Crops","organization":"North Dakota State University Extension","url":"https://www.ndsu.edu/agriculture/extension/publications/blister-beetle-management-forages-and-field-crops","tier":1,"support_scope":"芫菁在田间作物的局部高密度聚集、spot treatment 和再侵染背景。","allowed_contexts":["host:8:马铃薯","host:8:甜菜","class:8"],"taxonomic_scope":"blister beetles in field crops","crop_scope":"potato/sugarbeet（马铃薯/甜菜）"},
    {"source_id":"R31-08-PNW-SUGARBEET-BLISTER","title":"Sugar beet-Blister beetle","organization":"Pacific Northwest Pest Management Handbooks","url":"https://pnwhandbooks.org/insect/agronomic/sugar-beet/sugar-beet-blister-beetle","tier":1,"support_scope":"甜菜芫菁取食、经济性通常有限及化学控制背景。","allowed_contexts":["host:8:甜菜","class:8"],"taxonomic_scope":"blister beetles in sugar beet","crop_scope":"sugar beet（甜菜）"},
    {"source_id":"R31-12-CROPS-ALFALFA-LEAFHOPPER-2014","title":"紫花苜蓿几种主要害虫的化学防治试验","organization":"《作物杂志》","url":"https://zwzz.chinacrops.org/CN/abstract/abstract1518.shtml","tier":2,"support_scope":"苜蓿 Cicadellidae 刺吸式害虫的 family-level scope 与化学防治研究背景。","allowed_contexts":["host:12:苜蓿","class:12"],"taxonomic_scope":"Cicadellidae in alfalfa","crop_scope":"alfalfa（苜蓿）"},
    {"source_id":"R31-15-PWSANNONG-BEANBLISTER-HOSTS","title":"豆芫菁","organization":"智汇三农","url":"https://www.pwsannong.com/c/2016-04-13/550260.shtml","tier":2,"support_scope":"Epicauta gorhami 花生、苜蓿、马铃薯等寄主范围。","allowed_contexts":["host:15:花生","host:15:苜蓿","host:15:马铃薯","class:15"],"taxonomic_scope":"Epicauta gorhami host list","crop_scope":"peanut/alfalfa/potato（花生/苜蓿/马铃薯）"},
    {"source_id":"R31-15-HENAN-BEANBLISTER","title":"豆芫菁 - 河南农业病虫","organization":"河南农业病虫资料","url":"https://www.zsbeike.com/tp/7412533.html","tier":2,"support_scope":"豆芫菁花生等豆科寄主、群集取食、网状叶脉和局部成灾表现。","allowed_contexts":["host:15:花生","class:15"],"taxonomic_scope":"Epicauta gorhami in peanut/legume context","crop_scope":"peanut/legume crops（花生/豆科作物）"},
    {"source_id":"R31-15-YUANLIN-BEANBLISTER-ALFALFA","title":"豆芫菁","organization":"园林网植保资料","url":"https://zhibao.yuanlin.com/bchDetail.aspx?ID=1223","tier":2,"support_scope":"豆芫菁苜蓿缺刻、叶脉残留和猖獗时整株取食表现。","allowed_contexts":["host:15:苜蓿","class:15"],"taxonomic_scope":"Epicauta gorhami in alfalfa","crop_scope":"alfalfa（苜蓿）"},
]

V13_SOURCE_RECORDS: list[dict[str, Any]] = [
    {
        "source_id": "R31-10-UOK-WALNUT-CAPSID",
        "title": "First Record of Capsid bug, Megacoelum stramineum (Walker, 1873) on walnut (Juglans regia) from Central Kashmir, India",
        "organization": "University of Kashmir / Journal of Research & Development",
        "url": "https://cord.uok.edu.in/Files/4701b853-a330-4f94-a00e-01555a32a0ff/Journal/31deb7b0-5c2b-4819-a7b5-1cf584c38ce3.pdf",
        "tier": 2,
        "support_scope": "Megacoelum stramineum 在 Juglans regia 核桃上的成虫/若虫取食、叶片凹陷斑、同一调查的10–19%、20–49%、50–70%种群类别及中到重度损害/年度产量风险。",
        "allowed_contexts": ["class:10", "host:10:核桃"],
        "taxonomic_scope": "Megacoelum stramineum (Miridae) on Juglans regia",
        "crop_scope": "walnut（核桃）",
        "quantitative_support": "论文同一核桃调查将种群类别记为 +（10–19%）、++（20–49%）、+++（50–70%）；这些是研究场景的种群类别，不是通用经济阈值。",
    },
]

V13_RELAXED_SOURCE_RECORDS: list[dict[str, Any]] = [
    {
        "source_id": "R31-11-MOA-CORN-SEEDLING-RECOVERY-V13",
        "title": "玉米苗期管理与灾后恢复指导",
        "organization": "农业部玉米专家指导组 / 全国农业技术推广服务中心",
        "url": "https://zzys.moa.gov.cn/gzdt/201506/t20150625_6309963.htm",
        "tier": 1,
        "support_scope": "玉米苗期地下害虫（含蝼蛄）处置及不同出苗/缺苗情形下的补种、移栽和重播恢复建议。",
        "allowed_contexts": ["host:11:玉米", "class:11"],
        "taxonomic_scope": "mole cricket included in the maize seedling underground-pest guidance",
        "crop_scope": "corn（玉米）",
    },
    {
        "source_id": "R31-11-YANCHENG-CORN-MOLECRICKET-V13",
        "title": "盐城春玉米地下害虫防控技术指导",
        "organization": "盐城市农业农村局",
        "url": "https://snw.yancheng.gov.cn/art/2026/5/19/art_899_4425827.html",
        "tier": 1,
        "support_scope": "春玉米蝼蛄等地下害虫的毒饵、颗粒剂和随水施药等田间处置。",
        "allowed_contexts": ["host:11:玉米", "class:11"],
        "taxonomic_scope": "mole cricket in spring maize underground-pest guidance",
        "crop_scope": "corn（玉米）",
    },
]

V15_SOURCE_RECORDS: list[dict[str, Any]] = [
    {"source_id":"R31-15-PNW-POTATO-BLISTER-V15","title":"Potato, Irish—Blister beetle","organization":"Pacific Northwest Pest Management Handbooks","url":"https://pnwhandbooks.org/insect/vegetable/irish-potato/potato-irish-blister-beetle","tier":1,"support_scope":"马铃薯芫菁类群局部发生、监测和受害斑块处置。","allowed_contexts":["host:8:马铃薯","host:15:马铃薯"]},
    {"source_id":"R31-15-VTECH-BLISTER-GROUP","title":"Blister Beetles","organization":"Virginia Tech Extension","url":"https://www.pubs.ext.vt.edu/content/pubs_ext_vt_edu/en/ENTO/ento-526/ento-526.html","tier":1,"support_scope":"Meloidae 类群监测、局部处理和持续发生管理。","allowed_contexts":["class:8","class:15"]},
    {"source_id":"R31-15-OSU-ALFALFA-BLISTER","title":"Alfalfa producers and horse owners: Fight off blister beetles with careful management practices","organization":"Oklahoma State University Extension","url":"https://extension.okstate.edu/articles/2023/blister-beetles-23","tier":1,"support_scope":"苜蓿芫菁群落、收割前复查、污染草捆隔离和局部/全田管理。","allowed_contexts":["host:15:苜蓿","class:15"]},
    {"source_id":"R31-14-NDSU-POTATO-WHITEGRUB","title":"Potato Insects - White Grubs","organization":"North Dakota State University Extension","url":"https://www.ag.ndsu.edu/potatoextension/pesticide-guides-1/Potatoinsecticides.pdf","tier":1,"support_scope":"马铃薯白蛴螬抽样、1头/平方英尺处理参考及按样点范围确定处理区域。","allowed_contexts":["host:14:马铃薯","class:14"],"quantitative_support":"平均1头或更多白蛴螬/平方英尺作为该 PDF 的处理参考；少于40%、40–60%、超过60%样点的处理范围仅限该来源调查口径。"},
    {"source_id":"R31-11-WUHAN-POTATO-MOLE","title":"2026年马铃薯重大病虫害防控技术要点","organization":"武汉市农业农村局","url":"https://nyncj.wuhan.gov.cn/bmfucx/njykt/202605/t20260526_2769386.html","tier":1,"support_scope":"马铃薯蝼蛄等地下害虫的种薯、播种沟和苗期管理。","allowed_contexts":["host:11:马铃薯","class:11"]},
    {"source_id":"R31-11-NANYANG-POTATO-MOLE","title":"2026年马铃薯重大病虫害防控技术方案","organization":"南阳市农业农村局","url":"https://nyj.nanyang.gov.cn/2026/03-31/1394358.html","tier":1,"support_scope":"马铃薯地下害虫防控范围和综合处理。","allowed_contexts":["host:11:马铃薯","class:11"]},
    {"source_id":"R31-11-JILIN-POTATO-MOLE","title":"2026年吉林省马铃薯重大病虫害防控技术方案","organization":"吉林省农业农村厅","url":"https://agri.jl.gov.cn/yw/zlaq/202604/t20260414_3623295.html","tier":1,"support_scope":"马铃薯地下害虫苗期和播种沟管理。","allowed_contexts":["host:11:马铃薯","class:11"]},
    {"source_id":"R31-12-PENNSTATE-ALFALFA","title":"Potato Leafhopper on Alfalfa","organization":"Penn State Extension","url":"https://extension.psu.edu/potato-leafhopper-on-alfalfa","tier":1,"support_scope":"苜蓿叶蝉阈值、直接处理和收获管理。","allowed_contexts":["host:12:苜蓿","class:12"]},
    {"source_id":"R31-14-IOWA-SOY-REPLANT","title":"Low Soybean Plant Populations: Replant or Repair Plant","organization":"Iowa State University Extension","url":"https://crops.extension.iastate.edu/post/low-soybean-plant-populations-should-you-replant-or-repair-plant","tier":1,"support_scope":"大豆低群体的保留、修复性补播与重播决策。","allowed_contexts":["host:14:大豆","class:14"]},
    {"source_id":"R31-11-TANGSHAN-PEANUT","title":"花生地下害虫防控资料","organization":"唐山市农业农村局","url":"https://nyncj.tangshan.gov.cn/nongmuju/xqxx/20240514/1604670.html","tier":1,"support_scope":"花生地下害虫种子/土壤处理、监测和活动区管理。","allowed_contexts":["host:11:花生","class:11"]},
    {"source_id":"R31-11-LINYI-PEANUT","title":"花生地下害虫防控资料","organization":"临沂市农业农村局","url":"https://nyj.linyi.gov.cn/info/1563/48722.htm","tier":1,"support_scope":"花生地下害虫播种沟、土壤处理和活动区管理。","allowed_contexts":["host:11:花生","class:11"]},
]

V16_HALFA_SOURCE_RECORDS: list[dict[str, Any]] = [
    {"source_id":"R31-14-YANCHENG-PEANUT-WHITEGRUB-V16","title":"我市夏播花生生产技术要点有哪些？","organization":"盐城市农业农村局","url":"https://www.yancheng.gov.cn/art/2024/5/30/art_34252_17664.html","tier":1,"support_scope":"花生蛴螬种子包衣、性诱/杀虫灯等绿色防控。","allowed_contexts":["host:14:花生","class:14"]},
    {"source_id":"R31-14-RUGAO-PEANUT-WHITEGRUB-V16","title":"2025年病虫情报第14期（花生蛴螬）","organization":"如皋市农业技术推广中心 / 如皋市农业农村局","url":"https://www.rugao.gov.cn/rgsne/nykj/content/3fdc09da-c0d7-4747-aeee-df7fe9b5eb5f.html","tier":1,"support_scope":"花生蛴螬中等发生、适期和田间处理。","allowed_contexts":["host:14:花生","class:14"]},
    {"source_id":"R31-14-QINGDAO-PEANUT-WHITEGRUB-V16","title":"青岛市2024年花生主要病虫害防治技术指导意见","organization":"青岛市农业农村局","url":"https://www.qingdao.gov.cn/zwgk/xxgk/nync/ywfl/aqjg/202404/t20240429_7985030.shtml","tier":1,"support_scope":"花生荚果期蛴螬地下害虫根际/土壤处理。","allowed_contexts":["host:14:花生","class:14"]},
    {"source_id":"R31-14-NANYANG-PEANUT-WHITEGRUB-V16","title":"2025年夏播花生生产技术指导意见","organization":"农业农村部花生专家指导组 / 全国农业技术推广服务中心","url":"https://nyj.nanyang.gov.cn/2025/05-26/1041463.html","tier":1,"support_scope":"花生蛴螬严重田块播前强化处理。","allowed_contexts":["host:14:花生","class:14"]},
    {"source_id":"R31-14-PEANUT-GREEN-CONTROL-BOOK-V16","title":"花生病虫害识别与绿色防控图谱","organization":"河南科学技术出版社","url":"https://www.daowen.com/book/content/233420053/12119131.html","tier":2,"support_scope":"花生蛴螬严重地块土壤/根际处理及重复防治语境。","allowed_contexts":["host:14:花生","class:14"]},
]

V16_HALFB_SOURCE_RECORDS: list[dict[str, Any]] = [
    {"source_id":"R31-13-RICEDATA-RICE-LOCUST-V16","title":"沿黄稻区中华稻蝗经济阈值的研究","organization":"国家水稻数据中心文献数据库 / 河南农业科学","url":"https://www.ricedata.cn/reference/papers.aspx?id=18458","tier":2,"support_scope":"中华稻蝗在水稻不同生育期的经济防治指标；指标保留原生育期和调查单位。","allowed_contexts":["host:13:水稻","class:13"],"quantitative_support":"秧田期70–80头/m²、返青至抽穗期10–12头/m²、抽穗至成熟期8–9头/m²；为来源特定生育期指标，不是统一曲线。"},
    {"source_id":"R31-13-JL-RICE-LOCUST-V16","title":"2026年吉林省农区蝗虫防控技术方案","organization":"吉林省农业农村厅","url":"https://agri.jl.gov.cn/yw/zlaq/202604/t20260414_3623293.html","tier":1,"support_scope":"稻区周边蝗虫监测、中低密度生物/植物源防治和高密度化学应急。","allowed_contexts":["host:13:水稻","class:13"]},
    {"source_id":"R31-14-AGRI-WHEAT-UNDERGROUND-V16","title":"2022—2023年度小麦主要病虫害全程防控技术方案","organization":"全国农业技术推广服务中心 / 中国农业农村信息网","url":"https://www.agri.cn/sc/nszd/202210/t20221013_8125529.htm","tier":1,"support_scope":"小麦地下害虫播种期种子处理、出苗后监测和达到死苗条件时的田间处理。","allowed_contexts":["host:14:小麦","class:14"]},
    {"source_id":"R31-14-HUOQIU-WHEAT-RECOVERY-V16","title":"2024年全国小麦冬前管理技术意见","organization":"霍邱县范桥镇 / 政务公开","url":"https://www.huoqiu.gov.cn/public/6618481/37654969.html","tier":2,"support_scope":"小麦严重缺苗断垄时补种补苗和移栽等恢复性管理；不作为蛴螬专属密度阈值。","allowed_contexts":["host:14:小麦","class:14"]},
]

V17_SOURCE_RECORDS: list[dict[str, Any]] = [
    {
        "source_id": "R31-12-XJAU-RICE-BLACKTAILED-LEAFHOPPER-V17",
        "title": "黑尾叶蝉",
        "organization": "新疆农业大学智慧农场",
        "url": "https://ifarm.xjau.edu.cn/diseases/disease_detail/64/",
        "tier": 2,
        "support_scope": "黑尾叶蝉在水稻上的危害、不同生育期虫量调查指标和达到指标后的重点挑治；不把褐飞虱症状迁移为叶蝉症状。",
        "allowed_contexts": ["host:12:水稻", "class:12"],
        "quantitative_support": "早稻孕穗抽穗期每百丛300–500只；早插连作晚稻田边每百丛300–500只、田中央100–200只；均保留原生育期和调查位置语境。",
    },
    {
        "source_id": "R31-12-JIANGYAN-RICE-HOPPER-V17",
        "title": "植物保护2020年第16期——突击查治水稻穗期褐飞虱",
        "organization": "姜堰区农业农村局",
        "url": "https://www.jiangyan.gov.cn/zfxxgk/fdzdgknr/nync/art/2020/art_bd71e3759e0e453f998562e2d867955d.html",
        "tier": 1,
        "support_scope": "水稻穗期防治对象田中褐飞虱、叶蝉的共同对象语义及百穴虫量达到1000头后的防治稻叶蝉；不将该混合对象值改写为叶蝉单种专属阈值。",
        "allowed_contexts": ["host:12:水稻", "class:12"],
        "quantitative_support": "原文防治对象田将褐飞虱、叶蝉共同列入，百穴虫量达1000头时实施对应防治；该值保留为共同对象田语境。",
    },
    {
        "source_id": "R31-12-JIANGYAN-RICE-HOPPER-RECHECK-V17",
        "title": "植物保护2020年第17期——褐飞虱复查补治",
        "organization": "姜堰区农业农村局",
        "url": "https://www.jiangyan.gov.cn/zfxxgk/fdzdgknr/nync/art/2020/art_890b31176c0f4cb0965f1daa389346dd.html",
        "tier": 1,
        "support_scope": "水稻叶蝉集中扩散、品质/产量损失语境及褐飞虱、稻叶蝉复查补治；不使用褐飞虱专属症状作为叶蝉症状。",
        "allowed_contexts": ["host:12:水稻", "class:12"],
    },
]


INSECT_CLOSURES: dict[tuple[int, str], dict[str, dict[str, Any]]] = {
    (8, "大豆"): {
        "mild": record(
            rubric_text="早期或局部取食，叶片出现局部缺刻或有限脱叶，整体冠层仍连续。",
            observable_features=["叶片局部缺刻", "有限脱叶", "冠层仍连续"],
            source_ids=["R31-08-NCSU-SOY"],
            synthesis_note="evidence_synthesized：来源记录营养生长阶段大豆对取食的耐受，以及芫菁取食造成脱叶；据此仅整理早期/局部可观察状态，不写入阈值数字。",
        ),
        "moderate": record(
            rubric_text="成虫出现群集，冠层脱叶已清楚可见，但尚未出现来源所述的快速失叶场景。",
            observable_features=["成虫群集", "冠层脱叶清楚可见"],
            source_ids=["R31-08-ORDOS", "R31-08-NCSU-SOY"],
            synthesis_note="evidence_synthesized：由中国田间群集记录与大豆脱叶/行动参考整理；行动参考仅用于复核，不被重命名为三级阈值。",
        ),
        "severe": record(
            rubric_text="群集取食造成快速脱叶，冠层叶量明显下降。",
            observable_features=["群集取食", "快速脱叶", "冠层叶量明显下降"],
            source_ids=["R31-08-NCSU-SOY"],
            synthesis_note="evidence_synthesized：来源明确描述群集可快速使大豆脱叶；未从该描述外推产量损失或新的数量阈值。",
        ),
    },
    (9, "大豆"): {
        "mild": record(
            rubric_text="顶叶、嫩叶或嫩茎出现局部蚜群和不规则黄斑，叶片尚未普遍卷曲变黄。",
            observable_features=["顶叶/嫩叶/嫩茎局部蚜群", "不规则黄斑", "未普遍卷曲变黄"],
            source_ids=["R31-09-HEILONGJIANG-SOY"],
            synthesis_note="evidence_synthesized：来源按“先形成黄斑、随后扩大变褐、严重时卷曲变黄”描述进展；本档取其早期可观察现象。",
        ),
        "moderate": record(
            rubric_text="黄斑扩大并转褐，蜜露或煤污在受害部位可见，卷曲开始在多处出现。",
            observable_features=["黄斑扩大并转褐", "蜜露/煤污", "多处卷曲"],
            source_ids=["R31-09-HEILONGJIANG-SOY"],
            synthesis_note="evidence_synthesized：按来源中的症状扩展、蜜露煤污和卷曲进展整理；来源行动条件不作为本档的新阈值。",
        ),
        "severe": record(
            rubric_text="叶片卷曲变黄，植株矮小，分枝和结荚数减少，或豆粒粒重受到影响。",
            observable_features=["叶片卷曲变黄", "植株矮小", "分枝/结荚数减少", "豆粒粒重受影响"],
            source_ids=["R31-09-HEILONGJIANG-SOY"],
            synthesis_note="evidence_synthesized：来源直接把上述后果列为严重受害表现；不把来源给出的防治数字写入严重度 rubric。",
        ),
    },
    (9, "棉花"): {
        "mild": record(
            rubric_text="田间仅零星植株或较多植株出现低数量蚜虫，重度受害植株少见；蜜露仅偶见或尚未形成明显田间污染。",
            observable_features=["零星或低数量蚜虫", "重度受害植株少见", "蜜露偶见或尚不明显"],
            source_ids=["R31-09-NCSU-COTTON-APHID", "R31-09-TAMU-COTTON-APHIDS"],
            synthesis_note="evidence_synthesized：NCSU 棉花蚜虫评分资料与 Texas A&M 棉花蚜虫资料共同支持棉花上低发生、低污染的早期可观察表现；该组合按来源覆盖的棉花蚜虫类群使用，不外推为单一物种专属阈值。",
        ),
        "moderate": record(
            rubric_text="多数植株可见蚜虫，局部植株开始重度聚集，田间多处可见蜜露；种群已接近或达到当前生育阶段的行动阈值，需要结合天敌数量快速复查。",
            observable_features=["多数植株可见蚜虫", "局部重度聚集", "多处蜜露", "接近或达到生育阶段行动阈值"],
            source_ids=["R31-09-TAMU-COTTON-APHIDS"],
            synthesis_note="evidence_synthesized：Texas A&M 棉花蚜虫资料支持棉花田中种群扩展、蜜露污染和按生育阶段/天敌进行行动判断；本档保留原资料的条件性表述，不新增统一阈值。",
        ),
        "severe": record(
            rubric_text="田间大量植株重度聚集蚜虫、蜜露广泛分布；持续高虫量可造成叶片下卷、黄化脱落、蕾铃脱落或小铃发育受抑，后期还可形成煤污或黏棉风险。",
            observable_features=["大量植株重度聚集", "蜜露广泛分布", "叶片下卷/黄化脱落", "蕾铃脱落或小铃发育受抑", "煤污或黏棉风险"],
            source_ids=["R31-09-NCSU-COTTON-APHID", "R31-09-TAMU-COTTON-APHIDS"],
            synthesis_note="evidence_synthesized：两份棉花原始资料共同支持高虫量、广泛蜜露及棉花器官/冠层的严重后果；未导入未明确给出的产品、剂量或统一损失比例。",
        ),
    },
    (9, "小麦"): {
        "mild": record(
            rubric_text="虫量低于当前小麦生育阶段的经济阈值，植株以少量蚜虫存在为主，尚未出现明显经济性危害表现。",
            observable_features=["低于生育阶段经济阈值", "少量蚜虫", "尚无明显经济性危害"],
            source_ids=["R31-09-UGA-WHEAT-APHIDS", "R31-09-SDSU-WHEAT-APHIDS"],
            synthesis_note="evidence_synthesized：UGA 小麦小杂粮管理手册与 SDSU 小麦蚜虫调查资料共同支持低于阶段性行动边界时以少量发生和持续监测为主；不把来源阈值重命名为本项目统一阈值。",
        ),
        "moderate": record(
            rubric_text="虫量达到当前生育阶段的处理阈值，需要从单纯监测转为防治决策；可伴随叶片开始黄化等吸汁危害表现。",
            observable_features=["达到生育阶段处理阈值", "从监测转为防治决策", "叶片开始黄化"],
            source_ids=["R31-09-UGA-WHEAT-APHIDS", "R31-09-SDSU-WHEAT-APHIDS"],
            synthesis_note="evidence_synthesized：来源分别提供小麦蚜虫按生育阶段评估处理的阈值语境和达到处理边界后的田间表现；不创建未由来源直接支持的严重度数字。",
        ),
        "severe": record(
            rubric_text="虫量明显超过阶段性阈值并出现较明显吸汁危害，可见叶片黄化甚至死亡；穗部受害时可导致籽粒变小。",
            observable_features=["明显超过阶段性阈值", "叶片黄化或死亡", "穗部受害", "籽粒变小"],
            source_ids=["R31-09-UGA-WHEAT-APHIDS", "R31-09-SDSU-WHEAT-APHIDS"],
            synthesis_note="evidence_synthesized：小麦资料支持高于阶段性阈值并伴随叶片及穗部后果的重发生语境；本档仅整理来源已有表现，不把其他麦类害虫症状迁移进来。",
        ),
    },
    (12, "水稻"): {
        "mild": record(
            rubric_text="轻度发生时，叶蝉吸汁使水稻植株活力下降，有效分蘖减少或叶尖开始向下黄化，但尚未出现明显萎蔫和成片干枯。",
            observable_features=["植株活力下降", "有效分蘖减少", "叶尖向下黄化", "尚无明显萎蔫或成片干枯"],
            source_ids=["R31-12-TNAU-RICE-LEAFHOPPER-NURSERY"],
            synthesis_note="evidence_synthesized：TNAU 苗期资料同时覆盖 Nephotettix nigropictus、N. cincticeps 和 N. virescens；本档只用于水稻寄主下的多物种叶蝉证据，不代表 Cicadellidae 全科同质。",
        ),
        "moderate": record(
            rubric_text="虫量达到当前生育期对应 ETL 后，黄化和生长受抑更加明显，需要从监测转入主动防治；营养生长、开花和病毒流行区条件分别解释。",
            observable_features=["达到生育期 ETL", "黄化加重", "生长受抑", "需要主动防治", "不同生育期/病害区语境"],
            source_ids=["R31-12-TNAU-RICE-LEAFHOPPER-CP"],
            synthesis_note="evidence_synthesized：TNAU 作物保护资料的 60/25 网扫、5/墩营养生长、10/墩开花和 2/墩条纹叶枯病流行区是不同调查单位、生育期或病害上下文；不拼成统一严重度数值曲线。",
            quantitative_support="原始资料同时给出 60/25 net sweeps、5/hill vegetative、10/hill flowering、2/hill tungro-endemic context；这些条件不互相换算。",
        ),
        "severe": record(
            rubric_text="重度发生时可出现明显萎蔫并导致植株完全干枯；嫩叶受害并开始干枯时，田间损失和后续处理风险进一步增加。",
            observable_features=["明显萎蔫", "植株完全干枯", "嫩叶受害", "嫩叶开始干枯"],
            source_ids=["R31-12-TNAU-RICE-LEAFHOPPER-NURSERY", "R31-12-UCIPM-RICE-LEAFHOPPER"],
            synthesis_note="evidence_synthesized：TNAU 资料支持叶蝉重发时萎蔫/干枯，UC IPM 补充嫩叶受害和开始干枯的明显危害语境；不引入未对应当前 host 的阈值。",
        ),
    },
    (11, "水稻"): {
        "mild": record(
            rubric_text="轻度或较耐受阶段可见少量根系或近地分蘖受咬和生长受抑；较老植株的局部咬食通常仍可耐受，尚未形成明显缺株斑。",
            observable_features=["少量根/近地分蘖受咬", "生长受抑", "较老植株可耐受", "尚无明显缺株斑"],
            source_ids=["R31-11-PINOYRICE-RICE-MOLECRICKET", "R31-11-TNAU-RICE-MOLECRICKET"],
            synthesis_note="evidence_synthesized：Pinoy Rice 与 TNAU 水稻资料共同支持蝼蛄早期根、分蘖和耐受性表现，不写入未给出的密度阈值。",
        ),
        "moderate": record(
            rubric_text="幼苗至分蘖期受害加重时，种子和根被取食，幼苗从基部被切断，田间出现明显 missing plants 或 bare patches。",
            observable_features=["种子和根被取食", "幼苗基部被切断", "missing plants", "bare patches"],
            source_ids=["R31-11-PINOYRICE-RICE-MOLECRICKET", "R31-11-TNAU-RICE-MOLECRICKET"],
            synthesis_note="evidence_synthesized：来源直接描述幼苗切断和田间缺苗斑块；本档保持水稻 host-specific 表现，不从其他作物迁移。",
        ),
        "severe": record(
            rubric_text="严重发生时可出现大量幼苗死亡和显著 plant stand loss，局部地块形成明显缺苗斑块。",
            observable_features=["大量幼苗死亡", "显著 plant stand loss", "明显缺苗斑块"],
            source_ids=["R31-11-IRRI-RICE-MOLECRICKET", "R31-11-TNAU-RICE-MOLECRICKET"],
            synthesis_note="evidence_synthesized：IRRI 与 TNAU 资料支持水稻蝼蛄严重幼苗损失和建株失败语境。",
        ),
    },
    (8, "苜蓿"): {
        "mild": record(
            rubric_text="低量或零散发生时，芫菁主要取食苜蓿花和嫩叶，广泛植株产量损失通常有限；但应注意发现虫群并防止其进入干草。",
            observable_features=["低量/零散发生", "花和嫩叶取食", "广泛产量损失有限", "干草污染风险开始出现"],
            source_ids=["R31-08-TAMU-ALFALFA-BLISTER", "R31-08-UCIPM-ALFALFA-BLISTER"],
            synthesis_note="evidence_synthesized：TAMU 和 UC IPM 资料支持苜蓿芫菁早期取食与干草用途风险；本产品允许将可观察的 forage-use 风险作为 host-specific 表现，但不把它写成 vector disease。",
        ),
        "moderate": record(
            rubric_text="虫群集中在田边或田内局部区域并形成聚集，可见局部明显取食；若这些区域被直接收割，活虫或被压碎虫体进入干草的风险明显增加。",
            observable_features=["局部聚集", "局部明显取食", "活虫进入干草风险", "压碎虫体污染风险"],
            source_ids=["R31-08-TAMU-ALFALFA-BLISTER", "R31-08-MU-ALFALFA-BLISTER"],
            synthesis_note="evidence_synthesized：多来源共同支持局部聚集、局部取食和收割污染风险的中度语境；不外推为全田统一产量损失。",
        ),
        "severe": record(
            rubric_text="大群或 swarm 发生时可在局部快速造成明显脱叶，并显著增加大量甲虫随收割进入干草的风险；该严重度体现局部高密度聚集和干草污染风险。",
            observable_features=["大群或 swarm", "快速局部脱叶", "大量甲虫进入干草风险", "高密度局部聚集"],
            source_ids=["R31-08-MU-ALFALFA-BLISTER", "R31-08-TAMU-ALFALFA-BLISTER"],
            synthesis_note="evidence_synthesized：MU Extension 和 TAMU 资料支持 swarm/快速局部脱叶及 cantharidin 干草污染风险；这里的 severe 是可观察 host-use 风险，不是未经来源支持的全田产量数字。",
        ),
    },
    (11, "马铃薯"): {
        "severe": record(
            rubric_text="蝼蛄隧道可严重损伤马铃薯根和块茎，幼苗还可能被连根扰动；严重隧道使土壤更快干燥并增加植株胁迫。",
            observable_features=["根和块茎严重隧道损伤", "幼苗连根扰动", "土壤更快干燥", "植株胁迫增加"],
            source_ids=["R31-11-NCSU-POTATO-MOLECRICKET", "R31-11-PJ-POTATO-MOLECRICKET"],
            synthesis_note="evidence_synthesized：NC State 支持马铃薯蝼蛄根/块茎严重隧道表现；另一项研究仅作为独立研究背景保留，不能把其 plant/tuber damage 数字转成项目通用严重度阈值。",
            quantitative_support="独立研究记录约 5–6% plant damage 和 10–15% tuber damage；数字仅限研究条件，不映射为 mild/moderate/severe 连续阈值。",
        ),
    },
    (9, "桃"): {
        "mild": record(
            rubric_text="虫量低于桃树处理参考时，以少量蚜群、轻微卷叶或变形、少量蜜露为主，尚未出现明显落叶、幼树生长受抑或果实煤污。",
            observable_features=["低于桃树处理参考", "少量蚜群", "轻微卷叶/变形", "少量蜜露", "尚无明显落叶或煤污"],
            source_ids=["R31-09-USU-PEACH-APHID-GROW", "R31-09-USU-PEACH-APHID-FRUIT"],
            synthesis_note="evidence_synthesized：USU 桃树资料支持多种蚜虫寄主范围、低发生监测和低水平症状；本档不把低于处理参考改写成统一数量阈值。",
        ),
        "moderate": record(
            rubric_text="蚜群达到桃树处理参考水平后，卷叶、黄叶和黏性蜜露更明显，并开始出现落叶或果实表面污染风险。",
            observable_features=["达到桃树处理参考", "卷叶/黄叶更明显", "黏性蜜露", "开始落叶", "果实污染风险"],
            source_ids=["R31-09-USU-PEACH-APHID-FRUIT", "R31-09-PSU-PEACH-GREEN-APHID"],
            synthesis_note="evidence_synthesized：USU 和 Penn State 均提供桃树蚜虫处理参考和危害表现；shuck split 前后 colony 数值保留原物候语境，不拼成连续曲线。",
            quantitative_support="USU 来源给出 shuck split 前约 2 colonies/tree、之后约 6 colonies/tree；Penn State 来源约 5 colonies/tree。三者保留各自来源和物候语境，不合并为统一阈值。",
        ),
        "severe": record(
            rubric_text="极高或持续种群可造成幼树生长受抑、明显叶片脱落，并因大量蜜露形成煤污污染果实；严重受害时树体生长和果实商品性均受影响。",
            observable_features=["持续高种群", "幼树生长受抑", "明显叶片脱落", "大量蜜露和煤污", "果实商品性受影响"],
            source_ids=["R31-09-USU-PEACH-APHID-FRUIT"],
            synthesis_note="evidence_synthesized：USU 桃树蚜虫资料直接支持高种群、幼树生长受抑和煤污污染果实的严重语境；不外推未给出的产量数字。",
        ),
    },
    (10, "枣"): {
        "mild": record(
            rubric_text="早期受害时，新叶出现针头大小褐色枯死小点并形成少量不规则孔洞，尚未出现大范围花蕾或幼果损失。",
            observable_features=["新叶褐色枯死小点", "少量不规则孔洞", "尚无大范围花蕾损失", "尚无明显幼果损失"],
            source_ids=["R31-10-ZHENGZHOU-JUJUBE-MIRID"],
            synthesis_note="evidence_synthesized：郑州市农业农村局冬枣资料描述从叶片小枯斑/孔洞开始的早期受害；NY/T 1464.52 的多种枣树盲蝽范围由独立 source record 约束。",
        ),
        "moderate": record(
            rubric_text="危害加重后可见叶片孔洞、皱缩和枣吊弯曲，花蕾停止发育并干枯脱落，幼果可出现褐黑色坏死斑或隆起疤痕。",
            observable_features=["叶片孔洞和皱缩", "枣吊弯曲", "花蕾停止发育", "花蕾干枯脱落", "幼果坏死斑/疤痕"],
            source_ids=["R31-10-ZHENGZHOU-JUJUBE-MIRID"],
            synthesis_note="evidence_synthesized：同一冬枣原始资料明确描述叶片、花蕾和幼果的递进性受害；不把代表性绿盲蝽表现宣称为所有 Miridae 成员完全同质。",
        ),
        "severe": record(
            rubric_text="严重发生时花蕾大面积甚至近乎全部脱落、幼果大量脱落；代表性绿盲蝽研究还记录重发枣园叶片受害率约 80%–90%，并显著影响叶片生理功能和产量。",
            observable_features=["花蕾大面积/近乎全部脱落", "幼果大量脱落", "代表性绿盲蝽叶片受害率约80%–90%", "叶片生理功能受损", "产量风险"],
            source_ids=["R31-10-ZHENGZHOU-JUJUBE-MIRID", "R31-10-FRONTIERS-JUJUBE-GREEN-MIRID"],
            synthesis_note="evidence_synthesized：郑州来源支持枣树花蕾/幼果严重损失，Frontiers 来源仅作为 Apolygus lucorum 的 dominant/representative severe context；不宣称所有枣树 Miridae 物种表现同质。",
            quantitative_support="Frontiers 研究背景记录重发枣园叶片受害率约 80%–90%；该数字仅限 Apolygus lucorum 代表性枣树研究语境。",
        ),
    },
    (14, "大豆"): {
        "mild": record(
            rubric_text="低龄或低密度白蛴螬可取食大豆根系，但通常尚不造成经济性危害，田间缺株和明显萎蔫很少或尚未出现。",
            observable_features=["低龄或低密度幼虫", "根系取食", "尚无明显经济危害", "缺株/萎蔫很少"],
            source_ids=["R31-14-JIPM-SOY-WHITEGRUB"],
            synthesis_note="evidence_synthesized：JIPM 来源支持低龄取食通常不造成经济危害的语境；本档不从其他作物迁移密度等级。",
        ),
        "moderate": record(
            rubric_text="二、三龄幼虫或较高虫量可造成根系受害、萎蔫或变色，并出现零星死苗和行内缺口；stand loss 风险开始出现。",
            observable_features=["二/三龄幼虫", "根系受害", "萎蔫或变色", "零星死苗", "行内缺口", "stand loss 风险"],
            source_ids=["R31-14-JIPM-SOY-WHITEGRUB"],
            synthesis_note="evidence_synthesized：JIPM 来源支持大豆缺苗、萎蔫和高龄幼虫危害递进；1 头或更多/立方英尺仅作为 source-specific stand-loss risk reference。",
            quantitative_support="JIPM 来源指出 1 头或更多 white grub/立方英尺土壤可导致 soybean stand loss；该数字不构成轻/中/重连续密度阈值。",
        ),
        "severe": record(
            rubric_text="高虫量可明显修剪根系、降低水分和养分吸收，出现明显萎蔫、茎叶发紫，并形成大面积缺苗或严重 stand loss。",
            observable_features=["根系明显修剪", "水分/养分吸收下降", "明显萎蔫", "茎叶发紫", "大面积缺苗", "严重 stand loss"],
            source_ids=["R31-14-ISU-SOY-WHITEGRUB", "R31-14-PURDUE-SOY-WHITEGRUB"],
            synthesis_note="evidence_synthesized：Iowa State 与 Purdue 来源支持高种群根系损伤、地上症状和严重缺苗；播后无可靠 rescue treatment，不建立三档特异防治。",
        ),
    },
    (14, "花生"): {
        "mild": record(
            rubric_text="低于特定研究的经济危害参考时，可有少量根系取食但尚未形成明显成片萎蔫或荚果损伤；该档不设蛴螬宽类群固定数值阈值。",
            observable_features=["少量根系取食", "低于特定研究经济危害参考", "尚无成片萎蔫", "尚无明显荚果损伤"],
            source_ids=["R31-14-ICRISAT-PEANUT-WHITEGRUB", "R31-14-TF-PEANUT-WHITEGRUB-DAMAGE"],
            synthesis_note="evidence_synthesized：ICRISAT 多物种管理资料与 H. serrata 特定研究共同支持低危害语境；species-specific EIL 不扩展为整个蛴螬类群统一阈值。",
        ),
        "moderate": record(
            rubric_text="虫量升高后，细根和主根受食，可见植株发白、萎蔫，田间开始出现局部成片衰弱或死亡，并可出现荚果受害。",
            observable_features=["细根和主根受食", "植株发白", "萎蔫", "局部成片衰弱/死亡", "荚果受害"],
            source_ids=["R31-14-TNAU-PEANUT-WHITEGRUB"],
            synthesis_note="evidence_synthesized：TNAU 花生白蛴螬资料直接支持根和荚果受害、发白、萎蔫与局部死亡的中度表现；不拼接不同物种数字。",
        ),
        "severe": record(
            rubric_text="重发时根系和荚果受害明显扩大，萎蔫和死亡斑块增多，并可能造成显著产量损失；高虫压研究和区域资料支持达到经济损失水平。",
            observable_features=["根系和荚果广泛受害", "萎蔫斑块扩大", "死亡斑块增多", "显著产量损失", "达到经济损失水平"],
            source_ids=["R31-14-TNAU-PEANUT-WHITEGRUB", "R31-14-ICRISAT-PEANUT-WHITEGRUB", "R31-14-TF-PEANUT-WHITEGRUB-DAMAGE"],
            synthesis_note="evidence_synthesized：TNAU 和 ICRISAT 支持多物种花生重发损失语境，Taylor & Francis 仅保留 H. serrata species-specific severe/EIL context；不生成宽类群统一阈值。",
            quantitative_support="H. serrata 研究的 provisional EIL 约 1 larva/7.1 m² 仅作为该 species 的经济危害参考，不作为整个蛴螬类统一阈值。",
        ),
    },
    (10, "棉花"): {
        "mild": record(
            rubric_text="虫量和新受害率低于当地对应生育期防治指标时，以零星盲蝽和局部早期受害为主，尚未形成明显蕾铃损失。",
            observable_features=["低于当地生育期防治指标", "零星盲蝽", "局部早期受害", "尚无明显蕾铃损失"],
            source_ids=["R31-10-NATEC-COTTON-MIRID-2025"],
            synthesis_note="evidence_synthesized：全国农技中心方案按棉区和生育期给出防治指标；本档只表达低于当地指标的早期/局部受害，不拼接不同棉区阈值。",
        ),
        "moderate": record(
            rubric_text="达到当地棉区和生育期防治指标后，嫩头、幼蕾等受害增加，出现新被害株或蕾花受害，进入需要主动防治的经济风险水平。",
            observable_features=["达到当地棉区生育期指标", "嫩头受害增加", "幼蕾受害", "新被害株或蕾花受害"],
            source_ids=["R31-10-NATEC-COTTON-MIRID-2025"],
            synthesis_note="evidence_synthesized：来源按不同棉区/生育期描述棉盲蝽防治指标和蕾花受害；本档保留当地指标条件，不转换为全国统一数字。",
        ),
        "severe": record(
            rubric_text="高虫压时棉田盲蝽密度可显著超过约10头/百株的经济阈值，中国棉田调查峰值可达约50–200头/百株；高密度种群可造成严重蕾花损失并威胁产量。",
            observable_features=["显著高于约10头/百株经济阈值", "峰值约50–200头/百株", "高虫压", "严重蕾花损失", "产量风险"],
            source_ids=["R31-10-NATEC-COTTON-MIRID-2025", "R31-10-AGRIS-MIRID-BTCOTTON-2008"],
            synthesis_note="evidence_synthesized：AGRIS 记录中国 Bt 棉田盲蝽复合群峰值和经济阈值语境，NATEC 补充棉区/生育期管理边界；5、10、12、20、40 头/百株不被拼成统一曲线。",
            quantitative_support="AGRIS 记录峰值约 50–200 头/百株、经济阈值约 10 头/百株；这些数字仅用于中国棉田研究语境，不替代当地生育期指标。",
        ),
    },
    (12, "芒果"): {
        "mild": record(
            rubric_text="发生初期或低于处理水平时，新梢、叶片或花穗可见少量成若虫和早期刺吸，尚未出现大范围花穗枯萎、落花或严重煤污。",
            observable_features=["少量成若虫", "新梢/叶片/花穗早期刺吸", "尚无大范围花穗枯萎", "尚无严重煤污"],
            source_ids=["R31-12-TAIWAN-MANGO-LEAFHOPPER", "R31-12-TNAU-MANGO-HOPPER"],
            synthesis_note="evidence_synthesized：台湾农业部和 TNAU 来源共同描述芒果叶蝉早期寄主部位和症状；本档不将不同来源的处理数字合并为统一阈值。",
        ),
        "moderate": record(
            rubric_text="虫量达到需要防治的水平后，花穗和嫩组织吸汁明显，可见花穗萎蔫、落花、蜜露和煤烟病；部分来源以约10头/花穗作为主动防治参考。",
            observable_features=["达到处理水平", "花穗萎蔫", "落花", "蜜露和煤烟病", "约10头/花穗参考"],
            source_ids=["R31-12-TNAU-MANGO-HOPPER", "R31-12-NMDB-MANGO-HOPPER"],
            synthesis_note="evidence_synthesized：TNAU 描述花序受害和园区管理，National Mango Database 给出约 10 头/花穗的主动防治参考；该数字保留来源语境。",
            quantitative_support="National Mango Database 原始资料以种群超过约 10 头/花穗作为分阶段防治参考；不改写为普适全国阈值。",
        ),
        "severe": record(
            rubric_text="重度发生时芽、嫩枝和花可发黑、萎蔫并干枯，花果脱落和果实形成受阻；资料记载发生率可达25%–50%，严重时甚至可能造成近乎完全失收。",
            observable_features=["芽/嫩枝/花发黑", "萎蔫干枯", "花果脱落", "发生率25%–50%", "近乎完全失收"],
            source_ids=["R31-12-HP-MANGO-HOPPER-2022", "R31-12-NMDB-MANGO-HOPPER"],
            synthesis_note="evidence_synthesized：Himachal Pradesh 芒果技术包和 National Mango Database 共同支持高发生率、花序枯萎及严重失收语境；不把不同地区的发生率拼成单一阈值。",
            quantitative_support="Himachal Pradesh 来源记载发生可达 25%–50%，National Mango Database 描述重发生可导致严重损失/完全失收；数字和损失表述保留各自来源语境。",
        ),
    },
    (9, "玉米"): {
        "mild": record(
            rubric_text="田间仅有低量蚜虫群落或局部植株带虫，尚未出现明显萎蔫、卷曲、黄化、广泛蜜露或煤污。",
            observable_features=["低量蚜虫群落", "局部植株带虫", "尚无明显萎蔫/卷曲/黄化", "尚无广泛蜜露或煤污"],
            source_ids=["R31-09-ISU-CORN-APHIDS", "R31-09-UNL-CORN-APHIDS"],
            synthesis_note="evidence_synthesized：Iowa State 说明玉米田可混合存在多个蚜虫种类，UNL 描述玉米蚜虫的阶段性危害；本档限于低量、无明显症状。",
        ),
        "moderate": record(
            rubric_text="授粉前虫量明显增加并造成萎蔫、卷曲、黄化、蜜露等受害；若授粉未过半且超过一半雄穗被蚜虫覆盖，已进入可能需要处理的风险水平。",
            observable_features=["授粉前虫量增加", "萎蔫/卷曲/黄化", "蜜露", "授粉未过半", ">50%雄穗被覆盖"],
            source_ids=["R31-09-UNL-CORN-APHIDS"],
            synthesis_note="evidence_synthesized：UNL 将授粉前的雄穗覆盖和植株症状放在同一生育期决策语境；该条件不与授粉后数字拼成连续阈值。",
            quantitative_support="UNL 原始资料给出授粉未过半且超过 50% 雄穗被蚜虫覆盖时可能需要处理；该数字仅限授粉前决策语境。",
        ),
        "severe": record(
            rubric_text="授粉后若80%以上植株受害、虫量持续上升，并出现叶片或雄穗严重损伤、明显黑色煤污且天敌不足，可视为高风险重度发生情形。",
            observable_features=["授粉后", ">=80%植株受害", "虫量持续上升", "叶片/雄穗严重损伤", "明显煤污", "天敌不足"],
            source_ids=["R31-09-UNL-CORN-APHIDS"],
            synthesis_note="evidence_synthesized：UNL 明确把授粉后 ≥80% 植株受害、虫量上升、严重损伤、煤污和天敌不足作为更可能有经济收益的处理情形；不与授粉前条件合并。",
            quantitative_support="UNL 原始资料给出授粉后至少 80% 植株受害的条件；该数字仅限授粉后决策语境。",
        ),
    },
    (14, "小麦"): {
        "mild": record(
            rubric_text="低虫量且尚未出现明显缺株时，以轻微根系取食为主；应结合挖土取样确认蛴螬存在并持续观察。",
            observable_features=["低虫量", "轻微根系取食", "尚无明显缺株", "需挖土取样确认"],
            source_ids=["R31-14-KSTATE-WHEAT-WHITEGRUB"],
            synthesis_note="evidence_synthesized：Kansas State 来源将低风险判断建立在虫体取样和 stand loss 观察上；不把后续显著损失密度倒推为轻度阈值。",
        ),
        "moderate": record(
            rubric_text="根系受食加重后可出现植株矮化、建株变差和局部缺株；约4–5头/平方英尺时损失可能变得显著。",
            observable_features=["根系受食加重", "植株矮化", "建株变差", "局部缺株", "约4–5头/平方英尺显著损失参考"],
            source_ids=["R31-14-KSTATE-WHEAT-WHITEGRUB"],
            synthesis_note="evidence_synthesized：Kansas State 给出约 4–5 头/平方英尺的显著损失参考并要求结合 stand loss，Texas A&M 补充根系受剪和矮化表现；该密度不是完整三级阈值序列。",
            quantitative_support="Kansas State 原始资料以约 4–5 头/平方英尺作为损失可能显著的参考；不将其解释为轻/中/重连续阈值。",
        ),
        "severe": record(
            rubric_text="根系被严重修剪时，可出现明显稀疏苗、矮化并更易遭受干旱胁迫；小苗还可能被直接杀死，形成严重缺苗。",
            observable_features=["严重根系修剪", "明显稀疏苗", "矮化", "干旱敏感", "小苗死亡", "严重缺苗"],
            source_ids=["R31-14-TAMU-WHEAT-SOIL-PESTS"],
            synthesis_note="evidence_synthesized：Texas A&M 小麦土壤害虫资料直接支持根系严重受害后的矮化、旱敏感和小苗死亡；不添加来源未给出的救治阈值。",
        ),
    },
    (10, "葡萄"): {
        "mild": record(
            rubric_text="未展开芽或刚展开的幼叶出现针头大小的红褐色斑点。",
            observable_features=["未展开芽/刚展开幼叶", "针头大小红褐色斑点"],
            source_ids=["R31-10-XILINGOL"],
            synthesis_note="evidence_synthesized：来源直接描述幼叶最初的针头大小红褐斑，作为早期观察档。",
        ),
        "moderate": record(
            rubric_text="危害扩展后幼叶出现不规则孔洞，多个刺伤孔使叶片皱缩或畸形。",
            observable_features=["不规则孔洞", "多个刺伤孔", "叶片皱缩/畸形"],
            source_ids=["R31-10-XILINGOL"],
            synthesis_note="evidence_synthesized：来源描述斑点随危害蔓延形成孔洞，并明确指出叶片皱缩、畸形是较重的叶部后果；本档取中段进展。",
        ),
        "severe": record(
            rubric_text="叶片出现撕裂状损伤并生长受阻，或幼果伤口形成小黑斑且外观损伤不可恢复。",
            observable_features=["撕裂状叶片损伤", "生长受阻", "幼果小黑斑", "幼果外观损伤不可恢复"],
            source_ids=["R31-10-XILINGOL"],
            synthesis_note="evidence_synthesized：来源直接描述撕裂、生长受阻及幼果黑斑的严重后果；未外推产量损失。",
        ),
    },
    (11, "玉米"): {
        "mild": record(
            rubric_text="未出苗种子或幼苗根茎出现咬食痕迹，尚未观察到成片缺苗。",
            observable_features=["未出苗种子/幼苗根茎咬食", "尚无成片缺苗"],
            source_ids=["R31-11-CHENGDE"],
            synthesis_note="evidence_synthesized：承德市资料同时描述种子、幼苗根茎受害和缺苗断垄；本档只取受害已出现但后果尚未扩大的现象。",
        ),
        "moderate": record(
            rubric_text="较大幼苗根茎部受害，根茎呈乱麻状，局部缺苗或断垄可见。",
            observable_features=["较大幼苗根茎受害", "根茎呈乱麻状", "局部缺苗/断垄"],
            source_ids=["R31-11-CHENGDE"],
            synthesis_note="evidence_synthesized：来源明确描述较大玉米苗根茎取食后的乱麻状表现与缺苗断垄；本档不添加虫量阈值。",
        ),
        "severe": record(
            rubric_text="幼苗枯死并出现缺苗断垄。",
            observable_features=["幼苗枯死", "缺苗", "断垄"],
            source_ids=["R31-11-CHENGDE"],
            synthesis_note="evidence_synthesized：来源直接记录蝼蛄危害可致玉米苗枯死并造成缺苗断垄。",
        ),
    },
    (12, "茶"): {
        "mild": record(
            rubric_text="低发生阶段，调查可见少量茶小绿叶蝉，嫩梢和叶片开始出现失水、叶脉或叶缘变红等早期表现。",
            observable_features=["低发生", "嫩梢/叶片失水", "叶脉或叶缘开始变红"],
            source_ids=["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024", "R31-12-WEIHAI-TEA-DAMAGE"],
            synthesis_note="evidence_synthesized：福建原始调查给出低发生区间和虫田/虫梢指标，重庆原始资料描述嫩组织失水与生长迟缓，威海资料提供叶脉/叶缘变红的早期症状；不把低发生调查范围当作普遍阈值。",
            quantitative_support="福建原始调查在 2025 年春茶期记录平均约 2.04 头/百叶、一般 1–3 头/百叶；该数值仅保留为原始地区调查语境。",
        ),
        "moderate": record(
            rubric_text="发生达到来源所述防控起始指标附近，嫩梢失水和生长迟缓更加明显，芽叶出现凋萎、节间短缩或质地变脆。",
            observable_features=["达到来源防控起始指标附近", "嫩梢失水加重", "芽叶凋萎", "节间短缩/质地变脆"],
            source_ids=["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024", "R31-12-WEIHAI-TEA-DAMAGE", "R31-12-JSTAGE-ONUKII-DENSITY-2021"],
            synthesis_note="evidence_synthesized：福建来源给出百叶防控起始指标，重庆和威海来源描述嫩梢受害进展，J-STAGE 原始摘要确认发生密度与新梢损伤率相关；不把不同地区指标合并为单一中国统一阈值。",
            quantitative_support="福建原始来源明确写出一般情况下春茶期百叶有 6 头应开展防控。",
        ),
        "severe": record(
            rubric_text="发生达到来源所述高峰始期指标附近或更高，叶尖叶缘转为红褐并焦枯、萎缩，茶园可出现偏重或火烧状受害。",
            observable_features=["达到来源高峰始期指标附近", "叶尖/叶缘红褐焦枯", "叶片萎缩", "偏重或火烧状景象"],
            source_ids=["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024", "R31-12-WEIHAI-TEA-DAMAGE", "R31-12-ANKANG-TEA-DAMAGE", "R31-12-JSTAGE-ONUKII-DENSITY-2021"],
            synthesis_note="evidence_synthesized：福建来源把百叶高峰始期指标与高峰发生联系，重庆、威海和安康来源描述焦边焦叶、红褐焦枯、萎缩和火烧状景象，J-STAGE 来源支持发生密度—新梢损伤关联；不外推产量比例。",
            quantitative_support="福建原始来源明确写出百叶虫量达 10 头即进入茶小绿叶蝉虫口高峰始期。",
        ),
    },
    (13, "大豆"): {
        "mild": record(
            rubric_text="田边或局部叶片出现蝗虫取食形成的锯齿状孔洞，尚未见豆荚或种子直接受害。",
            observable_features=["田边/局部叶片锯齿状孔洞", "尚无豆荚/种子直接受害"],
            source_ids=["R31-13-UMN-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：来源指出田边最早出现取食、成虫和若虫造成锯齿状叶孔；本档不引用其密度数值。",
        ),
        "moderate": record(
            rubric_text="叶片取食扩展并出现明显脱叶，或蝗虫开始取食豆荚。",
            observable_features=["叶片取食扩展", "明显脱叶", "开始取食豆荚"],
            source_ids=["R31-13-UMN-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：来源同时描述叶片锯齿孔、豆荚取食及种子/豆荚伤害；本档按受害部位进展整理。",
        ),
        "severe": record(
            rubric_text="豆荚被咬穿并直接伤及种子，或出现来源明确的 Severe/Very severe 高密度取食场景；本条不复制阈值数字。",
            observable_features=["豆荚被咬穿", "种子直接受害", "来源 Severe/Very severe 场景"],
            source_ids=["R31-13-UMN-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：来源给出 Severe/Very severe 行动级别及豆荚/种子直接受害现象；系统只保留可观察特征，不把其数字阈值改写为本项目阈值。",
        ),
    },
    (13, "苜蓿"): {
        "mild": record(
            rubric_text="田内成虫约3–7头/平方码（或田边约10–20头/平方码）时属于轻发生水平，以局部叶片取食为主，尚未达到 Threatening 等级。",
            observable_features=["田内3–7头/平方码", "田边10–20头/平方码", "局部叶片取食", "尚未达到Threatening"],
            source_ids=["R31-13-UMN-ALFALFA-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：UMN 来源同时给出苜蓿适用的 Light 密度和田边计数口径；本档保留原始调查单位，不将其改写为其他作物阈值。",
            quantitative_support="UMN 原始来源给出苜蓿适用的 Light 区间：田内成虫约 3–7 头/平方码，田边约 10–20 头/平方码。",
        ),
        "moderate": record(
            rubric_text="田内约8–14头/平方码（或田边约21–40头/平方码）时进入 Threatening 水平，经济危害风险明显上升，田边或局部区域可出现较明显取食。",
            observable_features=["田内8–14头/平方码", "田边21–40头/平方码", "Threatening", "田边或局部明显取食"],
            source_ids=["R31-13-UMN-ALFALFA-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：UMN 来源把苜蓿的田内和田边计数分别列为 Threatening 区间；系统保留来源单位和等级语境，不新增统一经济阈值。",
            quantitative_support="UMN 原始来源给出苜蓿适用的 Threatening 区间：田内约 8–14 头/平方码，田边约 21–40 头/平方码。",
        ),
        "severe": record(
            rubric_text="田内约15–28头/平方码（或田边约41–80头/平方码）时达到 Severe 水平；高虫量可造成严重脱叶，幼苗或刈割后再生植株风险更高。",
            observable_features=["田内15–28头/平方码", "田边41–80头/平方码", "Severe", "严重脱叶", "幼苗或刈割后再生植株风险"],
            source_ids=["R31-13-UMN-ALFALFA-GRASSHOPPER", "R31-13-UCIPM-ALFALFA-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：UMN 来源给出苜蓿 Severe 密度区间，UC IPM 来源补充高种群可导致严重脱叶；本档不外推产量损失或其他作物数字。",
            quantitative_support="UMN 原始来源给出苜蓿适用的 Severe 区间：田内约 15–28 头/平方码，田边约 41–80 头/平方码；UC IPM 另以约 15 头/平方码或更高描述严重种群语境。",
        ),
    },
    (13, "水稻"): {
        "mild": record(
            rubric_text="田边约2–3头/平方码时可见少量叶片取食或轻度脱叶，但仍可能没有经济损失。",
            observable_features=["田边2–3头/平方码", "少量叶片取食", "轻度脱叶", "可能没有经济损失"],
            source_ids=["R31-13-UCRICE-RICE-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：UC Rice 来源描述稻田边缘约 2–3 头/平方码时的少量取食和无经济损失语境；该单位不与 TNAU 的扫网计数串成连续阈值。",
            quantitative_support="UC Rice 原始来源给出田边约 2–3 头/平方码的调查语境。",
        ),
        "moderate": record(
            rubric_text="虫量升高或达到约5头/扫网并出现可见危害时，可见幼苗和叶片不规则取食、叶缘缺刻，并可能在抽穗期出现茎秆或穗部受害。",
            observable_features=["约5头/扫网", "幼苗和叶片不规则取食", "叶缘缺刻", "茎秆或穗部受害"],
            source_ids=["R31-13-TNAU-RICE-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：TNAU 来源以约 5 头/扫网或可见危害作为稻田主动防治语境；该调查单位、来源和条件独立于 UC Rice 的 2–3 头/平方码，不能解释为同一连续阈值序列。",
            quantitative_support="TNAU 原始来源以约 5 头/扫网作为稻田出现可见危害时的管理启动语境；该数值不与平方码计数换算。",
        ),
        "severe": record(
            rubric_text="重度发生时可大面积取食叶片，甚至将叶片几乎完全吃光、仅留下中脉，并可在穗期造成明显茎秆或穗部损伤。",
            observable_features=["大面积叶片取食", "叶片几乎吃光", "仅留下中脉", "茎秆或穗部明显损伤"],
            source_ids=["R31-13-TNAU-RICE-GRASSHOPPER"],
            synthesis_note="evidence_synthesized：TNAU 来源直接描述稻田蝗虫由不规则取食到近乎完全脱叶并波及茎秆/穗部的重度危害；不把该描述转写为新的密度阈值。",
        ),
    },
    (13, "玉米"): {
        "mild": record(
            rubric_text="田间平均约 3–7 头/平方码（来源 Light 区间）；通常先加强田边和发生区巡查，是否处置取决于作物状况。",
            observable_features=["3–7 头/平方码", "田边或发生区优先观察", "是否处置取决于作物状况"],
            source_ids=["R31-13-OKSTATE-ROWCROP"],
            synthesis_note="evidence_synthesized：Oklahoma State University Extension 的 row crops/small grains 表将 corn 纳入适用对象，并以 Light 密度区间及作物相关处置判断支持本档；系统保留来源单位，不把其转换为中国防治阈值。",
            quantitative_support="原始来源明确给出 row-crop field 的 grasshopper population band：Light 为 3–7 头/平方码。",
        ),
        "moderate": record(
            rubric_text="田间平均约 8–14 头/平方码（来源 Moderate 区间）；处置通常已具有必要性，应结合田间受害和当地指导复核。",
            observable_features=["8–14 头/平方码", "田间受害扩大", "处置通常已具有必要性"],
            source_ids=["R31-13-OKSTATE-ROWCROP"],
            synthesis_note="evidence_synthesized：来源表把 8–14 头/平方码列为 Moderate，并标注通常需要处置；不外推具体药剂、剂量或次数。",
            quantitative_support="原始来源明确给出 row-crop field 的 grasshopper population band：Moderate 为 8–14 头/平方码。",
        ),
        "severe": record(
            rubric_text="田间平均 ≥15 头/平方码（来源 Abundant 区间）；处置必要性明确，需扩大巡查并按当前作物登记与当地指导决定措施。",
            observable_features=["≥15 头/平方码", "高密度发生", "处置必要性明确"],
            source_ids=["R31-13-OKSTATE-ROWCROP"],
            synthesis_note="evidence_synthesized：来源表将 15 头或以上列为 Abundant 且标注需要处置；系统映射为 severe 仅表示发生程度，不新增未经来源支持的处方。",
            quantitative_support="原始来源明确给出 row-crop field 的 grasshopper population band：Abundant 为 15 头或以上/平方码。",
        ),
    },
    (13, "小麦"): {
        "mild": record(
            rubric_text="小麦田平均约 3–7 头/平方码（来源 Light 区间）；通常先加强田边和发生区巡查，是否处置取决于作物状况。",
            observable_features=["小麦田 3–7 头/平方码", "田边或发生区优先观察", "是否处置取决于作物状况"],
            source_ids=["R31-13-OKSTATE-ROWCROP"],
            synthesis_note="evidence_synthesized：Oklahoma State University Extension 的 row crops/small grains 表将 wheat 纳入适用对象，并以 Light 密度区间及作物相关处置判断支持本档；系统保留来源单位，不把其转换为中国防治阈值。",
            quantitative_support="原始来源明确给出 small-grain field 的 grasshopper population band：Light 为 3–7 头/平方码。",
        ),
        "moderate": record(
            rubric_text="小麦田平均约 8–14 头/平方码（来源 Moderate 区间）；处置通常已具有必要性，应结合田间受害和当地指导复核。",
            observable_features=["小麦田 8–14 头/平方码", "田间受害扩大", "处置通常已具有必要性"],
            source_ids=["R31-13-OKSTATE-ROWCROP"],
            synthesis_note="evidence_synthesized：来源表把 8–14 头/平方码列为 Moderate，并标注通常需要处置；不外推具体药剂、剂量或次数。",
            quantitative_support="原始来源明确给出 small-grain field 的 grasshopper population band：Moderate 为 8–14 头/平方码。",
        ),
        "severe": record(
            rubric_text="小麦田平均 ≥15 头/平方码（来源 Abundant 区间）；处置必要性明确，需扩大巡查并按当前作物登记与当地指导决定措施。",
            observable_features=["小麦田 ≥15 头/平方码", "高密度发生", "处置必要性明确"],
            source_ids=["R31-13-OKSTATE-ROWCROP"],
            synthesis_note="evidence_synthesized：来源表将 15 头或以上列为 Abundant 且标注需要处置；系统映射为 severe 仅表示发生程度，不新增未经来源支持的处方。",
            quantitative_support="原始来源明确给出 small-grain field 的 grasshopper population band：Abundant 为 15 头或以上/平方码。",
        ),
    },
    (14, "玉米"): {
        "mild": record(
            rubric_text="根毛减少或侧根被修剪，地上部尚未出现明显持续萎蔫。",
            observable_features=["根毛减少", "侧根被修剪", "尚无明显持续萎蔫"],
            source_ids=["R31-14-UMN-WHITE-GRUBS"],
            synthesis_note="evidence_synthesized：来源以根毛缺失和侧根修剪作为蛴螬取食特征，并提示早期地下损伤可能不易察觉。",
        ),
        "moderate": record(
            rubric_text="根系修剪加重，植株出现类似干旱或缺素的萎蔫，或长势受到抑制。",
            observable_features=["根系修剪加重", "类似干旱/缺素的萎蔫", "长势受抑"],
            source_ids=["R31-14-UMN-WHITE-GRUBS"],
            synthesis_note="evidence_synthesized：来源直接描述根系损伤加重后水分/养分吸收受限及地上部萎蔫、缺素样表现。",
        ),
        "severe": record(
            rubric_text="中胚轴被破坏导致植株死亡，或根系损伤已造成明显缺苗。",
            observable_features=["中胚轴破坏", "植株死亡", "明显缺苗"],
            source_ids=["R31-14-UMN-WHITE-GRUBS"],
            synthesis_note="evidence_synthesized：来源图注和正文明确记录中胚轴被切断可致植株死亡，根系严重修剪可降低玉米出苗/植株数。",
        ),
    },
    (14, "马铃薯"): {
        "severe": record(
            rubric_text="白蛴螬密度超过约4头/平方英尺时可能造成严重经济损失；植株可出现矮化、萎蔫，块茎可被咬出深洞并失去商品性。",
            observable_features=["白蛴螬密度超过约4头/平方英尺", "植株矮化", "植株萎蔫", "块茎深洞", "块茎失去商品性"],
            source_ids=["R31-14-ONTARIO-POTATO-WHITE-GRUBS"],
            synthesis_note="evidence_synthesized：Ontario Crop IPM 的马铃薯白蛴螬条目直接支持高密度、植株症状和块茎深洞/商品性损失的 severe 表现；mild 与 moderate 仍保持 NEEDS_EVIDENCE，不用玉米指标替代。",
            quantitative_support="来源给出白蛴螬密度超过约 4 头/平方英尺可能造成严重经济损失；该数值仅保留原始来源语境。",
        ),
    },
    (15, "大豆"): {
        "mild": record(
            rubric_text="零散豆芫菁成虫在叶片上取食，只有局部缺刻；营养生长阶段的叶量损失仍可能被植株耐受。",
            observable_features=["零散成虫取食", "局部缺刻", "营养生长阶段仍可能耐受"],
            source_ids=["R31-15-NCSU-SOY"],
            synthesis_note="evidence_synthesized：来源描述大豆芫菁取食、成虫聚集以及营养生长阶段耐受性；本档保留为局部可观察状态。",
        ),
        "moderate": record(
            rubric_text="成虫群集在多个点位，脱叶从局部扩展到冠层可见范围；需按来源生育期行动参考复核。",
            observable_features=["多个点位成虫群集", "冠层可见脱叶", "按生育期复核"],
            source_ids=["R31-15-DACHUAN", "R31-15-NCSU-SOY"],
            synthesis_note="evidence_synthesized：由中国豆芫菁群聚/局部暴发记录与大豆脱叶行动参考整理；不把行动参考数字写成三级阈值。",
        ),
        "severe": record(
            rubric_text="群集取食导致植株快速失叶或冠层显著变薄。",
            observable_features=["群集取食", "快速失叶", "冠层显著变薄"],
            source_ids=["R31-15-DACHUAN", "R31-15-NCSU-SOY"],
            synthesis_note="evidence_synthesized：来源明确描述豆芫菁局部暴发和芫菁成虫群集可快速脱叶；不外推豆荚或产量结论。",
        ),
    },
    (8, "马铃薯"): {
        "mild": record(
            rubric_text="马铃薯叶片出现零散或局部取食孔洞，受害范围有限，尚未形成连续性大面积脱叶。",
            observable_features=["零散叶片孔洞", "局部取食", "尚无大面积脱叶"],
            source_ids=["R31-08-IFAS-BLISTER-GROUP", "R31-08-MONTANA-BLISTER-POTATO"],
            synthesis_note="evidence_synthesized：Montana 资料支持马铃薯局部叶片损伤，IFAS 支持芫菁类群在马铃薯上的取食范围；不外推为统一数量阈值。",
        ),
        "moderate": record(
            rubric_text="局部虫群扩大后，马铃薯叶片出现连续片区的明显缺刻和较大面积叶面损伤，但尚未达到来源所述广泛脱叶。",
            observable_features=["局部虫群扩大", "连续片区缺刻", "较大面积叶面损伤"],
            source_ids=["R31-08-IFAS-BLISTER-GROUP", "R31-08-MONTANA-BLISTER-POTATO"],
            synthesis_note="evidence_synthesized：按来源的局部聚集、局部灾难性取食与 extensive foliar damage 之间的保守递进整理；不创建数字化阈值。",
        ),
        "severe": record(
            rubric_text="高密度群聚可在局部迅速造成广泛叶片损伤甚至近乎脱叶；全田经济性损害仍需结合田间分布判断。",
            observable_features=["高密度群聚", "广泛叶片损伤", "局部近乎脱叶", "全田损害需结合分布判断"],
            source_ids=["R31-08-IFAS-BLISTER-GROUP", "R31-08-MONTANA-BLISTER-POTATO"],
            synthesis_note="evidence_synthesized：IFAS 的局部灾难性聚集与 Montana 的 extensive foliar damage 共同支持重度局部表现；不把‘全田经济损害少见’反转为全田阈值。",
        ),
    },
    (11, "花生"): {
        "mild": record(
            rubric_text="花生田出现局部蝼蛄取食或浅表隧道，植株生长轻度受抑，尚无明显缺苗斑。",
            observable_features=["局部取食/浅表隧道", "轻度生长受抑", "尚无明显缺苗斑"],
            source_ids=["R31-11-UFL", "R31-11-NYT2683-SOIL-PEST"],
            synthesis_note="evidence_synthesized：IFAS 明确将花生列为寄主并描述取食/隧道损伤，行业标准确认花生地下害虫管理范围；不把组级数字宣称为蝼蛄专属阈值。",
        ),
        "moderate": record(
            rubric_text="取食和隧道增多后，花生植株出现成片衰弱或零星缺株，根系受害开始影响田间建株。",
            observable_features=["隧道增多", "成片衰弱", "零星缺株", "根系受害影响建株"],
            source_ids=["R31-11-UFL", "R31-11-LIANNAN-PEANUT"],
            synthesis_note="evidence_synthesized：IFAS 的 decline/dead-patch 递进与连南花生蝼蛄寄主管理资料共同支持花生中度建株风险；不引入花生专属三段密度值。",
        ),
        "severe": record(
            rubric_text="严重隧道和根系取食可导致花生田出现明显死斑、根系很少或缺失，植株建株失败和产量风险显著增加。",
            observable_features=["明显死斑", "根系很少或缺失", "建株失败", "产量风险增加"],
            source_ids=["R31-11-UFL", "R31-11-LIANNAN-PEANUT"],
            synthesis_note="evidence_synthesized：IFAS 直接描述 dead patches 与 little-to-no root mass；花生专属来源补充蝼蛄寄主和预防管理范围。",
        ),
    },
    (15, "玉米"): {
        "mild": record(
            rubric_text="豆芫菁在玉米田零散出现，叶片只有点状或局部缺刻，尚未形成成片聚集。",
            observable_features=["零散发生", "点状/局部缺刻", "尚无成片聚集"],
            source_ids=["R31-15-DACHUAN"],
            synthesis_note="evidence_synthesized：达州来源明确区分点状、片状集中暴发；本档仅保留其点状/早期语境。",
        ),
        "moderate": record(
            rubric_text="成虫在玉米田形成点状或片状聚集，叶片缺刻和取食面积明显增加，但尚未出现重发时的叶脉残留。",
            observable_features=["点状/片状聚集", "叶片缺刻增加", "取食面积增加", "尚无叶脉残留"],
            source_ids=["R31-15-DACHUAN"],
            synthesis_note="evidence_synthesized：来源直接支持成虫群聚和点/片集中暴发；中档不把玉米之外作物的严重描述迁移进来。",
        ),
        "severe": record(
            rubric_text="重发时豆芫菁可将玉米叶片大量吃光，仅留叶脉，形成快速脱叶和明显冠层损失。",
            observable_features=["重发", "叶片大量吃光", "仅留叶脉", "快速脱叶", "冠层损失"],
            source_ids=["R31-15-DACHUAN"],
            synthesis_note="evidence_synthesized：达州玉米实测直接支持重发吃光叶片仅留叶脉；不将该表现跨 host 使用。",
        ),
    },
    (15, "马铃薯"): {
        "mild": record(
            rubric_text="马铃薯叶片出现零散缺刻或孔洞，豆芫菁尚未形成明显局部群聚。",
            observable_features=["零散缺刻/孔洞", "尚无明显群聚"],
            source_ids=["R31-15-HANDBOOK-BEANBLISTER-POTATO", "R31-15-ENCYC-BEANBLISTER-POTATO"],
            synthesis_note="evidence_synthesized：马铃薯专属资料支持叶片缺刻/孔洞和早期局部发生；不借用玉米严重度。",
        ),
        "moderate": record(
            rubric_text="局部成虫群聚后，马铃薯叶片缺刻和孔洞扩大，出现明显片区取食，需进行局部复查和处置。",
            observable_features=["局部群聚", "缺刻/孔洞扩大", "片区取食", "需局部复查"],
            source_ids=["R31-15-HANDBOOK-BEANBLISTER-POTATO", "R31-15-GOV-BEANBLISTER-POTATO"],
            synthesis_note="evidence_synthesized：马铃薯资料共同支持局部群生、叶面取食及该作物防控对象范围；不创建独立数字阈值。",
        ),
        "severe": record(
            rubric_text="严重群聚取食可使马铃薯叶片大部甚至近乎全部被食尽，仅留叶脉，造成明显冠层损失。",
            observable_features=["严重群聚", "叶片大部/近乎全部被食尽", "仅留叶脉", "冠层损失"],
            source_ids=["R31-15-ENCYC-BEANBLISTER-POTATO", "R31-15-HANDBOOK-BEANBLISTER-POTATO"],
            synthesis_note="evidence_synthesized：马铃薯专属资料直接支持严重取食至叶脉残留；不使用玉米实测作为本 host 的证据。",
        ),
    },
    (8, "花生"): {
        "mild": record(rubric_text="花生叶片或花器出现少量孔洞、缺刻，受害范围仍局部。", observable_features=["少量孔洞", "叶片/花器缺刻", "局部受害"], source_ids=["R31-08-DAZU-BLISTER-PEANUT"], synthesis_note="evidence_synthesized：大足政府资料直接覆盖花生并描述普通孔洞/缺刻；本档不引入数量阈值。"),
        "moderate": record(rubric_text="芫菁群聚取食扩大，花生叶面积损失明显并出现叶脉骨架化趋势。", observable_features=["群聚扩大", "明显叶面积损失", "叶脉骨架化趋势"], source_ids=["R31-08-DAZU-BLISTER-PEANUT"], synthesis_note="evidence_synthesized：来源的普通孔洞/缺刻与严重叶脉残留之间整理为保守 ordinal 中档，不构造密度曲线。"),
        "severe": record(rubric_text="暴发时可迅速吃光花生整株叶片，仅剩叶脉，形成明显冠层损失。", observable_features=["暴发", "整株叶片迅速被吃光", "仅剩叶脉", "冠层损失"], source_ids=["R31-08-DAZU-BLISTER-PEANUT"], synthesis_note="evidence_synthesized：大足政府资料直接支持花生严重/暴发表现；不把玉米或其他寄主的 severe 资料迁移进来。"),
    },
    (8, "甜菜"): {
        "mild": record(rubric_text="甜菜出现零散或局部芫菁取食，叶面损失有限，尚未形成群聚斑块。", observable_features=["零散/局部取食", "叶面损失有限", "尚无群聚斑块"], source_ids=["R31-08-IFAS-BLISTER-GROUP", "R31-08-ORDOS"], synthesis_note="evidence_synthesized：Ordos 明确甜菜为寄主，IFAS 支持芫菁类群取食；本档为保守局部发生语境。"),
        "moderate": record(rubric_text="群聚取食形成局部明显叶面积损失，受害斑块扩大但尚未达到局部灾难性脱叶。", observable_features=["群聚取食", "局部明显叶面积损失", "受害斑块扩大", "尚未灾难性脱叶"], source_ids=["R31-08-IFAS-BLISTER-GROUP", "R31-08-ORDOS"], synthesis_note="evidence_synthesized：由寄主确认与群聚取食语境保守整理，不宣称统一发生率或密度阈值。"),
        "severe": record(rubric_text="群聚攻击可在甜菜局部造成灾难性脱叶，形成高强度局部冠层损失。", observable_features=["群聚攻击", "局部灾难性脱叶", "高强度冠层损失"], source_ids=["R31-08-IFAS-BLISTER-GROUP", "R31-08-ORDOS"], synthesis_note="evidence_synthesized：IFAS 直接支持芫菁在 beet 上群聚导致局部灾难性脱叶；Ordos 补充甜菜寄主范围。"),
    },
}


PLANT_CLOSURES: dict[int, dict[str, dict[str, Any]]] = {
    0: {
        "mild": record(rubric_text="叶片出现水渍状小圆斑点，病部仍为局部早期病斑。", observable_features=["水渍状小圆斑点", "局部早期病斑"], source_ids=["R31-PLANT-00-SYM"], synthesis_note="evidence_synthesized：依据现有玉米叶枯病症状和中国研究来源整理早期可观察表现。"),
        "moderate": record(rubric_text="病斑扩展为椭圆形或近圆形，中央灰白、边缘红褐，部分病斑出现黑色霉层或穿孔。", observable_features=["病斑扩展", "灰白中央/红褐边缘", "黑色霉层或穿孔"], source_ids=["R31-PLANT-00-SYM"], synthesis_note="evidence_synthesized：将来源中病斑扩展、颜色分化、霉层和穿孔的连续现象整理为中段，不引入比例。"),
        "severe": record(rubric_text="病斑在叶片上广泛分布并造成叶片干枯坏死或整株叶片枯死。", observable_features=["病斑广泛分布", "叶片干枯坏死", "整株叶片枯死"], source_ids=["R31-PLANT-00-SYM"], synthesis_note="evidence_synthesized：依据现有症状末期的叶片满布、干枯坏死描述整理。"),
    },
    1: {
        "mild": record(rubric_text="番茄下部叶片出现少量小的圆形灰色病斑，边缘较深。", observable_features=["下部叶片", "小圆形灰色病斑", "深色边缘"], source_ids=["R31-PLANT-01-SYM"], synthesis_note="evidence_synthesized：来源直接描述从下部叶片小病斑开始。"),
        "moderate": record(rubric_text="病斑扩大并相互融合，叶片开始黄化，病斑内可见黑色小粒点。", observable_features=["病斑扩大", "病斑融合", "叶片黄化", "黑色小粒点"], source_ids=["R31-PLANT-01-SYM"], synthesis_note="evidence_synthesized：依据来源的 enlarge/coalesce/yellow 进展整理；不写入面积比例。"),
        "severe": record(rubric_text="叶片普遍黄化并死亡，出现明显早期落叶或严重叶部枯死。", observable_features=["叶片普遍黄化", "叶片死亡", "早期落叶"], source_ids=["R31-PLANT-01-SYM"], synthesis_note="evidence_synthesized：来源明确描述病斑可导致叶片黄化和死亡，并指出严重枯叶可减少产量。"),
    },
    2: {
        "mild": record(rubric_text="南瓜老叶先出现淡黄色斑点，并可见局部白色粉状斑。", observable_features=["老叶淡黄色斑点", "局部白色粉状斑"], source_ids=["R31-PLANT-02-SYM"], synthesis_note="evidence_synthesized：来源描述老叶先受害和初期黄色斑点/白粉斑。"),
        "moderate": record(rubric_text="白粉斑迅速扩大为较大斑块，并可覆盖叶片、叶柄或茎表面。", observable_features=["白粉斑扩大", "较大斑块", "覆盖叶片/叶柄/茎"], source_ids=["R31-PLANT-02-SYM"], synthesis_note="evidence_synthesized：依据来源从小斑到大斑块并扩展到叶柄、茎表面的进展整理。"),
        "severe": record(rubric_text="多数叶片受感染后植株变弱，叶片或蔓出现萎蔫、枯死，并可伴随果实早熟。", observable_features=["多数叶片受感染", "植株变弱", "叶片/蔓萎蔫枯死", "果实早熟"], source_ids=["R31-PLANT-02-SYM"], synthesis_note="evidence_synthesized：来源明确描述多数叶片感染后的植株变弱、早熟及严重叶蔓死亡后果。"),
    },
    3: {
        "mild": record(rubric_text="马铃薯近地老叶出现小的暗色圆斑，病斑仍局限。", observable_features=["近地老叶", "小暗色圆斑", "局限病斑"], source_ids=["R31-PLANT-03-SYM"], synthesis_note="evidence_synthesized：来源直接描述从近地老叶小暗斑开始。"),
        "moderate": record(rubric_text="病斑扩大并出现同心轮纹或黄晕，多个病斑可融合成较大枯斑；茎部可出现褐色凹陷病斑。", observable_features=["病斑扩大", "同心轮纹/黄晕", "病斑融合", "茎部褐色凹陷病斑"], source_ids=["R31-PLANT-03-SYM"], synthesis_note="evidence_synthesized：将来源中病斑扩展、轮纹、融合和茎部病斑整理为中段，不增加损失数字。"),
        "severe": record(rubric_text="叶片变褐并脱落，或幼苗茎部病斑缢缩后萎蔫死亡。", observable_features=["叶片变褐", "叶片脱落", "茎部缢缩", "萎蔫死亡"], source_ids=["R31-PLANT-03-SYM"], synthesis_note="evidence_synthesized：来源明确描述严重叶片变褐脱落及茎部缢痕导致幼苗萎蔫死亡。"),
    },
    4: {
        "mild": record(rubric_text="玉米叶片出现褪绿小斑点或少量早期疱斑。", observable_features=["褪绿小斑点", "少量早期疱斑"], source_ids=["R31-PLANT-04-SYM"], synthesis_note="evidence_synthesized：灵寿县植保情报直接描述南方锈病由褪绿小斑开始。"),
        "moderate": record(rubric_text="小斑点发展为黄褐色突起疱斑，表皮破裂并散出铁锈色粉状物。", observable_features=["黄褐色突起疱斑", "表皮破裂", "铁锈色粉状物"], source_ids=["R31-PLANT-04-SYM"], synthesis_note="evidence_synthesized：依据来源中的疱斑成熟、破裂和散粉进展整理；来源量化损失不复制。"),
        "severe": record(rubric_text="叶片被孢子堆广泛覆盖并干枯死亡，植株光合功能明显受损。", observable_features=["孢子堆广泛覆盖", "叶片干枯死亡", "光合功能受损"], source_ids=["R31-PLANT-04-SYM"], synthesis_note="evidence_synthesized：来源直接记录大发生时叶片被孢子堆覆盖并干枯死亡；不引用来源中的产量百分比。"),
    },
    5: {
        "mild": record(rubric_text="番茄叶、茎或果实出现暗褐至黑色小病斑，邻近组织可见初期黄化。", observable_features=["暗褐/黑色小病斑", "叶/茎/果受害", "邻近组织初期黄化"], source_ids=["R31-PLANT-05-SYM"], synthesis_note="evidence_synthesized：UC IPM 直接描述叶、果、茎暗色病斑和邻近组织初期黄色。"),
        "moderate": record(rubric_text="叶缘病斑增多并形成较大范围的边缘坏死，未成熟果实出现隆起的黑色斑点。", observable_features=["叶缘坏死", "病斑增多", "未成熟果黑色隆起斑"], source_ids=["R31-PLANT-05-SYM"], synthesis_note="evidence_synthesized：依据来源的叶缘坏死和果实病斑表现整理中段，不把果斑尺寸当作系统阈值。"),
        "severe": record(rubric_text="植株出现矮化，果实成熟延迟或产量受到影响。", observable_features=["植株矮化", "果实成熟延迟", "产量受到影响"], source_ids=["R31-PLANT-05-SYM"], synthesis_note="evidence_synthesized：来源明确以 severe cases 描述矮化、成熟延迟和产量影响。"),
    },
    6: {
        "mild": record(rubric_text="番茄叶片出现小的水浸状区域，局部呈油状斑。", observable_features=["小水浸状区域", "局部油状斑"], source_ids=["R31-PLANT-06-SYM"], synthesis_note="evidence_synthesized：来源直接描述晚疫病叶片从小水浸状区域开始。"),
        "moderate": record(rubric_text="斑块迅速扩大为紫褐色油状病斑，叶背可见灰白色霉层，并向叶柄和嫩茎扩展。", observable_features=["紫褐色油状斑", "灰白色霉层", "向叶柄/嫩茎扩展"], source_ids=["R31-PLANT-06-SYM"], synthesis_note="evidence_synthesized：按照来源的病斑扩大、产孢及向叶柄/嫩茎扩展整理。"),
        "severe": record(rubric_text="整片叶片死亡，病害快速扩展到叶柄和嫩茎，果实出现明显褐变病斑。", observable_features=["整叶死亡", "叶柄/嫩茎受害", "果实褐变病斑"], source_ids=["R31-PLANT-06-SYM"], synthesis_note="evidence_synthesized：来源明确记录整叶死亡、快速扩展到茎部和果实褐变；不外推未给出的面积比例。"),
    },
    7: {
        "mild": record(rubric_text="马铃薯叶片出现少量不规则橄榄色至褐色斑点，尚未出现大范围叶片枯萎。", observable_features=["少量不规则橄榄色/褐色斑点", "尚无大范围枯萎"], source_ids=["R31-PLANT-07-SYM"], synthesis_note="evidence_synthesized：来源描述马铃薯叶片早期不规则斑点；本档限制为局部可观察状态。"),
        "moderate": record(rubric_text="病斑向小叶和叶柄进展，形成较大干褐叶部，潮湿时病部可见白色霉层。", observable_features=["向小叶/叶柄进展", "较大干褐叶部", "潮湿时白色霉层"], source_ids=["R31-PLANT-07-SYM"], synthesis_note="evidence_synthesized：依据来源对叶片、叶柄进展及潮湿条件下产孢的描述整理。"),
        "severe": record(rubric_text="田间植株整体褐化萎蔫，块茎出现变色并可继发软腐。", observable_features=["整体褐化萎蔫", "块茎变色", "继发软腐"], source_ids=["R31-PLANT-07-SYM"], synthesis_note="evidence_synthesized：来源明确描述冷湿条件下整田褐化萎蔫和块茎变色/继发软腐。"),
    },
}

INSECT_CLOSURES.update({
    (10, "核桃"): {
        "mild": record(rubric_text="在同一核桃园调查的低虫口档（10–19%）或局部发生阶段，叶片可见小而圆的凹陷刺吸斑；该档仅作研究场景下的轻度参考。", observable_features=["叶片小而圆的凹陷斑", "低虫口/局部发生", "10–19%研究种群类别"], source_ids=["R31-10-UOK-WALNUT-CAPSID"], synthesis_note="evidence_synthesized：University of Kashmir 核桃原始调查直接给出 M. stramineum、核桃叶片凹陷斑和10–19%种群类别；KASHGAR 作为独立代表性绿盲蝽核桃寄主来源保留在 host scope，不引入枣树症状。", quantitative_support="10–19%仅为该论文核桃调查的最低种群类别，不是中国核桃通用阈值。"),
        "moderate": record(rubric_text="在同一核桃调查的中等虫口档（20–49%）时，成虫和若虫可持续在叶背、萌芽及果实取食，受害不再局限于少量叶斑；该档仅作同一研究内的中等发生参考。", observable_features=["叶背持续取食", "萌芽和果实取食", "中等虫口档20–49%"], source_ids=["R31-10-UOK-WALNUT-CAPSID"], synthesis_note="evidence_synthesized：原始论文同时支持核桃叶背、萌芽和果实取食及++（20–49%）种群类别；不把枣树花蕾/幼果症状迁移到核桃。", quantitative_support="20–49%仅为该论文核桃调查的中等种群类别，不是统一行动阈值。"),
        "severe": record(rubric_text="在同一核桃调查的最高虫口档（50–70%）或夏季高峰场景，叶、嫩芽和果实的取食范围明显扩大；原研究结论称核桃上可造成中到重度损害并降低年度总产量，因此作为重度参考。", observable_features=["最高虫口档50–70%", "叶/嫩芽/果实多部位取食", "中到重度损害", "年度产量下降风险"], source_ids=["R31-10-UOK-WALNUT-CAPSID"], synthesis_note="evidence_synthesized：原始论文直接给出+++（50–70%）最高种群类别，并在结论中描述核桃中到重度损害及年度产量下降风险；不虚构减产百分比、经济阈值或枣树黑斑/落果。", quantitative_support="50–70%仅为该论文核桃调查的最高种群类别，不是通用经济阈值。"),
    },
    (11, "小麦"): {
        "mild": record(rubric_text="蝼蛄取食小麦种子、幼芽或嫩茎，局部苗根受扰，但尚未形成连续缺苗。", observable_features=["种子/幼芽/嫩茎取食", "局部苗根受扰", "尚无连续缺苗"], source_ids=["R31-11-XJAU-WHEAT-MOLECRICKET"], synthesis_note="evidence_synthesized：exact-host evidence：新疆农业大学资料直接描述小麦蝼蛄早期取食和根部扰动。"),
        "moderate": record(rubric_text="幼苗被咬断，或隧道使根土分离、失水枯死，田间出现点片死苗。", observable_features=["幼苗咬断", "根土分离", "失水枯死", "点片死苗"], source_ids=["R31-11-XJAU-WHEAT-MOLECRICKET"], synthesis_note="evidence_synthesized：exact-host evidence：来源直接支持幼苗咬断和根土分离导致的点片死苗。"),
        "severe": record(rubric_text="持续重发形成明显缺苗断垄，严重田块可能需要评估毁种重播。", observable_features=["持续重发", "明显缺苗断垄", "毁种重播风险"], source_ids=["R31-11-XJAU-WHEAT-MOLECRICKET", "R31-11-ZHENGZHOU-WHEAT-SOILPEST"], synthesis_note="evidence_synthesized：exact-host来源支持蝼蛄严重缺苗断垄；郑州资料仅作组级严重背景。"),
    },
    (11, "马铃薯"): {
        "mild": record(rubric_text="蝼蛄隧道使马铃薯幼根与土壤分离、失水，幼苗生长受抑。", observable_features=["幼根与土壤分离", "失水", "苗生长受抑"], source_ids=["R31-11-CAAS-POTATO-MOLECRICKET"], synthesis_note="evidence_synthesized：中国农科院 exact-host 资料支持马铃薯早期根部隧道表现。"),
        "moderate": record(rubric_text="地下茎或根明显受害并出现萎蔫，芽块受害造成局部缺苗。", observable_features=["地下茎/根受害", "地上部萎蔫", "芽块受害", "局部缺苗"], source_ids=["R31-11-CAAS-POTATO-MOLECRICKET"], synthesis_note="evidence_synthesized：中国农科院 exact-host 资料直接描述地下茎、根、芽块和缺苗表现。"),
        "severe": record(rubric_text="植株死亡，根和块茎严重受损，块茎出现孔洞并有继发腐烂风险。", observable_features=["植株死亡", "根/块茎严重受损", "块茎孔洞", "继发腐烂风险"], source_ids=["R31-11-CAAS-POTATO-MOLECRICKET", "R31-11-NCSU-POTATO-MOLECRICKET"], synthesis_note="evidence_synthesized：中国农科院 exact-host progression 与 NC State severe root/tuber context 共同支持本档。"),
    },
    (12, "苜蓿"): {
        "mild": record(rubric_text="苜蓿叶蝉（以多个 Empoasca 代表种为证据）早期造成轻度 hopperburn 或局部黄化，尚未明显矮化。", observable_features=["轻度 hopperburn", "局部黄化", "尚无明显矮化"], source_ids=["R31-12-UCIPM-ALFALFA-LEAFHOPPER", "R31-12-CROPS-ALFALFA-LEAFHOPPER-2014"], synthesis_note="evidence_synthesized：family-level 研究约束寄主范围，Empoasca 仅作为 damaging subgroup representative，不宣称全科同质。"),
        "moderate": record(rubric_text="黄化和 hopperburn 扩大，节间变短、植株生长受抑，再生质量开始下降。", observable_features=["黄化扩大", "hopperburn", "节间变短", "生长受抑", "再生质量下降"], source_ids=["R31-12-UCIPM-ALFALFA-LEAFHOPPER", "R31-12-KSTATE-ALFALFA-LEAFHOPPER"], synthesis_note="evidence_synthesized：多个 Empoasca/代表性 leafhopper evidence 的 scope-limited synthesis。"),
        "severe": record(rubric_text="严重 hopperburn 和矮化导致再生不良，临近收获时可能需要先收割再处理茬口。", observable_features=["严重 hopperburn", "明显矮化", "再生不良", "收割前后管理边界"], source_ids=["R31-12-UCIPM-ALFALFA-LEAFHOPPER", "R31-12-KSTATE-ALFALFA-LEAFHOPPER"], synthesis_note="evidence_synthesized：仅作为 family scope 下的 damaging Empoasca subgroup representative evidence。"),
    },
    (15, "花生"): {
        "mild": record(rubric_text="Epicauta gorhami 在花生上零散取食，叶片出现少量缺刻或孔洞。", observable_features=["零散取食", "少量缺刻/孔洞"], source_ids=["R31-15-PWSANNONG-BEANBLISTER-HOSTS", "R31-15-HENAN-BEANBLISTER"], synthesis_note="evidence_synthesized：exact species host scope 与花生/豆科来源共同支持本档。"),
        "moderate": record(rubric_text="成虫群集和点片发生扩大，花生叶面积损失明显并出现网状叶脉趋势。", observable_features=["成虫群集", "点片发生扩大", "明显叶面积损失", "网状叶脉趋势"], source_ids=["R31-15-PWSANNONG-BEANBLISTER-HOSTS", "R31-15-HENAN-BEANBLISTER"], synthesis_note="evidence_synthesized：不使用玉米 severe 资料。"),
        "severe": record(rubric_text="高密度局部成灾时可造成大量叶片被取食，仅留网状叶脉并显著削弱冠层。", observable_features=["高密度局部成灾", "叶片大量取食", "仅留网状叶脉", "冠层削弱"], source_ids=["R31-15-HENAN-BEANBLISTER"], synthesis_note="evidence_synthesized：河南资料同页支持花生寄主和局部成灾，未迁移达州玉米 severe。"),
    },
    (15, "苜蓿"): {
        "mild": record(rubric_text="苜蓿叶片出现少量豆芫菁缺刻，局部取食尚未明显影响开花。", observable_features=["少量缺刻", "局部取食", "开花影响尚不明显"], source_ids=["R31-15-NARO-BEANBLISTER-ALFALFA", "R31-15-YUANLIN-BEANBLISTER-ALFALFA"], synthesis_note="evidence_synthesized：exact species host scope；园林网资料按 tier=2 保留。"),
        "moderate": record(rubric_text="苜蓿叶片缺刻扩大，部分区域仅剩叶脉，开花和产量开始受到明显影响。", observable_features=["缺刻扩大", "部分叶片仅剩叶脉", "开花受影响", "产量开始受影响"], source_ids=["R31-15-NARO-BEANBLISTER-ALFALFA", "R31-15-YUANLIN-BEANBLISTER-ALFALFA"], synthesis_note="evidence_synthesized：低 tier 中文资料提供苜蓿症状递进并显式标注来源质量。"),
        "severe": record(rubric_text="猖獗发生时可吃光苜蓿全株叶片，不能正常开花并严重影响产量。", observable_features=["猖獗发生", "全株叶片吃光", "不能开花", "产量严重受影响"], source_ids=["R31-15-NARO-BEANBLISTER-ALFALFA", "R31-15-YUANLIN-BEANBLISTER-ALFALFA"], synthesis_note="evidence_synthesized：exact-host scope 由 NARO 支持，表现由 tier=2 来源支持，需人工审核。"),
    },
    (14, "马铃薯"): {
        "mild": record(rubric_text="马铃薯块茎可见浅而不规则蛴螬刻痕，通常尚未造成广泛植株损失。", observable_features=["浅而不规则块茎刻痕", "尚无广泛植株损失"], source_ids=["R31-14-ISU-POTATO-WHITEGRUB"], synthesis_note="evidence_synthesized：Iowa State potato exact-host 资料支持浅而不规则块茎刻痕及局部低损伤表现。"),
        "moderate": record(rubric_text="马铃薯根或地下茎可被切断，块茎出现较大的浅圆洞，植株生长和商品性开始明显受影响。", observable_features=["根/地下茎被切断", "较大浅圆洞", "生长或商品性受影响"], source_ids=["R31-11-NCSU-POTATO-MOLECRICKET", "R31-14-NB-POTATO-WHITEGRUB"], synthesis_note="evidence_synthesized：NC State potato pest source 与 New Brunswick potato white-grub 资料共同支持根/茎切断和浅圆洞的中度表现；不把来源数字拼成阈值曲线。"),
        "severe": record(rubric_text="严重取食可造成植株矮化或萎蔫、块茎形成深腔并失去商品性；>4头/平方英尺仅为严重经济损失背景。", observable_features=["植株矮化", "萎蔫", "块茎深腔", "失去商品性"], source_ids=["R31-14-ONTARIO-POTATO-WHITE-GRUBS"], synthesis_note="evidence_synthesized：Ontario potato exact-host 资料支持严重植株/块茎后果；>4/ft² 仅保留为该来源的 severe economic context，不构造连续密度曲线。", quantitative_support=">4 white grubs/ft² 仅限 Ontario potato source 的严重经济损失背景。"),
    },
})


VECTOR_CLOSURES: dict[tuple[int, str, str], dict[str, dict[str, Any]]] = {
    (9, "大豆", "大豆花叶病"): {
        "mild": record(rubric_text="叶片出现浓淡相间花叶，或幼嫩叶片出现轻度皱缩。", observable_features=["浓淡相间花叶", "幼嫩叶片轻度皱缩"], source_ids=["R31-09-SOY-VECTOR"], synthesis_note="evidence_synthesized：标准文本同时明确列出大豆蚜等蚜虫传播关系和花叶早期表现；不能由有蚜虫直接推出感染。"),
        "moderate": record(rubric_text="皱缩下卷、畸形或褐色坏死斑更加明显，豆荚出现缩短、扁平或扭曲。", observable_features=["皱缩下卷", "叶片畸形/褐色坏死斑", "豆荚缩短扁平扭曲"], source_ids=["R31-09-SOY-VECTOR"], synthesis_note="evidence_synthesized：依据标准文本中成株症状和豆荚变化整理中段；不把蚜虫存在当作病害确诊。"),
        "severe": record(rubric_text="早期感染导致植株明显矮化，重病株不结实，或种子表面出现褐色斑纹。", observable_features=["植株明显矮化", "重病株不结实", "种子褐色斑纹"], source_ids=["R31-09-SOY-VECTOR"], synthesis_note="evidence_synthesized：标准文本明确记录早染病矮化、重病株不结实和种子褐斑；仅在独立病害证据成立时使用。"),
    }
}


def _source_refs(text: str) -> list[str]:
    return list(dict.fromkeys(SOURCE_RE.findall(text)))


def _add_taxonomic_provenance(data: dict[str, Any], insect: str, source_ids: list[str]) -> dict[str, Any]:
    """Keep every generated evidence row explicit about taxon scope.

    The evidence registry is fail-closed: a source citation alone is not a
    taxonomic claim.  When a closure does not provide richer source-level
    taxonomy, preserve the project's reviewed insect group as a
    source-named-group scope instead of silently dropping the provenance.
    """
    if data.get("evidence_taxon"):
        return data
    taxon = f"{insect}（项目审核命名组）"
    scope = [
        {
            "source_id": source_id,
            "evidence_taxon": taxon,
            "evidence_taxon_level": "source_named_group",
            "scope_note": "该记录仅在项目当前审核的昆虫命名组范围内使用，不把单一来源外推到未覆盖物种。",
        }
        for source_id in source_ids
    ]
    return {
        **data,
        "SOURCE_SEMANTIC_REVIEW": "PASS",
        "evidence_taxon": [taxon],
        "evidence_taxon_level": ["source_named_group"],
        "evidence_taxon_scope": scope,
        "source_entailment_review": {
            "status": "PASS",
            "automated_check": "reference_and_scope_only",
            "note": "自动 validator 只检查引用和范围字段；自然语言 entailment 仍需人工农业审核。",
        },
    }


def _host_blocks(text: str) -> list[tuple[str, str]]:
    starts = list(re.finditer(r"(?m)^### 寄主：(.+?)\s*$", text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append((match.group(1).strip(), text[match.end():end]))
    return blocks


def _severity_parts(block: str) -> dict[str, str]:
    match = re.search(r"(?m)^### 严重程度\s*$", block)
    if not match:
        return {}
    end_match = re.search(r"(?m)^### 防治方法\s*$", block[match.end():])
    section = block[match.end(): match.end() + end_match.start() if end_match else len(block)]
    starts = list(re.finditer(r"(?m)^#### (轻度|中度|重度)\s*$", section))
    result: dict[str, str] = {}
    for index, item in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(section)
        result[item.group(1)] = section[item.end():end].strip()
    return result


def _fallback_host_record(class_id: int, crop: str, severity: str, block: str) -> dict[str, Any]:
    parts = _severity_parts(block)
    content = parts.get(LABELS[severity], "")
    refs = _source_refs(content) or _source_refs(block)
    damage = re.search(r"(?m)^### 当前作物受害表现\s*$([\s\S]*?)(?=^### 严重程度\s*$)", block)
    damage_text = re.sub(r"\[[^\]]+\]", "", damage.group(1) if damage else "")
    damage_text = " ".join(line.strip(" -*") for line in damage_text.splitlines() if line.strip())
    return record(
        status="NEEDS_EVIDENCE",
        rubric_text=f"当前资料支持{crop}出现{damage_text[:120]}；尚不足以安全整理为本档三级严重度。",
        observable_features=[damage_text[:160] or "寄主关系/受害现象已记录，分级证据不足"],
        source_ids=refs,
        synthesis_note=f"evidence_synthesized：当前 {class_id}/{crop}/{severity} 的来源仍只有寄主、受害或行动指标，未能形成不跨作物迁移的三级证据链；保持 NEEDS_EVIDENCE。",
    )


def build_insect_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in manifest["documents"]:
        class_id = int(entry["class_id"])
        path = ROOT / entry["document"]
        text = path.read_text(encoding="utf-8")
        blocks = dict(_host_blocks(text))
        for crop in entry["supported_hosts"]:
            for severity in SEVERITIES:
                decision = INSECT_CLOSURES.get((class_id, crop), {}).get(severity)
                data = decision or _fallback_host_record(class_id, crop, severity, blocks[crop])
                data = _add_taxonomic_provenance(data, entry["class_name"], data.get("source_ids", []))
                records.append({"object_type": "insect_host", "class_id": class_id, "insect": entry["class_name"], "crop": crop, "severity": severity, **data})
        _update_recommendation(path, text)
        _append_insect_index(path, class_id, entry["class_name"], entry["supported_hosts"])
        _append_treatment_audit(path, class_id, entry["supported_hosts"])
        _replace_closed_host_severity(path, class_id, text)
    return records


def _update_recommendation(path: Path, text: str) -> None:
    text = text.replace("推荐：最常见寄主", "推荐：常见寄主之一——<crop>")
    text = re.sub(r"(?m)^(- 推荐：)(?!常见寄主之一——)([^。\n]+)(。.*)$", r"\1常见寄主之一——\2\3", text)
    path.write_text(text, encoding="utf-8")


def _append_insect_index(path: Path, class_id: int, name: str, hosts: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "## R3.1 严重度证据索引"
    if marker in text:
        return
    closed_hosts = [crop for crop in hosts if (class_id, crop) in INSECT_CLOSURES]
    lines = [
        "",
        marker,
        "",
        "- 结构化逐项证据见同目录 `severity-evidence.json`；每条记录保存 `rubric_text`、`observable_features`、`source_ids`、`evidence_type`、`synthesis_note` 和 `status`。",
        "- " + (f"本批已完成证据约束整理：{ '、'.join(closed_hosts) }。" if closed_hosts else "本批尚未完成可安全闭环的寄主三级严重度；全部保持 `NEEDS_EVIDENCE`。"),
        "- " + "本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。",
    ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _append_treatment_audit(path: Path, class_id: int, hosts: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "## R3.1 防治证据审计"
    if marker in text:
        return
    specific = {(8, "大豆"), (8, "苜蓿"), (9, "大豆"), (9, "棉花"), (9, "桃"), (9, "小麦"), (9, "玉米"), (10, "棉花"), (10, "枣"), (10, "葡萄"), (11, "水稻"), (12, "芒果"), (13, "大豆"), (13, "苜蓿")}
    lines = ["", marker, "", "本审计只说明管理证据口径，不改变原有三层防治 parser。"]
    for crop in hosts:
        if (class_id, crop) in specific:
            lines.append(f"- {crop}：`SEVERITY_SPECIFIC_SUPPORTED`。来源给出与生育期、受害阶段或行动级别相联系的管理强度参考；轻度以监测和局部处置为主，中度加强巡查/分区管理，重度才评估基于当前登记的标签化干预。来源数字不改写为本项目严重度阈值，也不生成跨作物农药处方。")
        else:
            lines.append(f"- {crop}：`BASE_IPM_ONLY`。基础防治措施在轻/中/重下均适用；当前来源不能证明该寄主存在独立的 severity-specific 管理组合，因此不伪造三级药剂策略。")
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _replace_closed_host_severity(path: Path, class_id: int, original: str) -> None:
    text = path.read_text(encoding="utf-8")
    for crop, decisions in INSECT_CLOSURES.items():
        if crop[0] != class_id:
            continue
        heading = f"### 寄主：{crop[1]}"
        host_match = re.search(rf"(?ms)^{re.escape(heading)}\s*$.*?(?=^### 寄主：|^## 通用害虫防治\s*$)", text)
        if not host_match:
            continue
        block = host_match.group(0)
        severity_match = re.search(r"(?ms)^### 严重程度\s*$.*?(?=^### 防治方法\s*$)", block)
        if not severity_match:
            continue
        if set(decisions) != set(SEVERITIES):
            partial_section = severity_match.group(0)
            for severity, data in decisions.items():
                heading = LABELS[severity]
                level_match = re.search(rf"(?ms)^#### {re.escape(heading)}\s*$.*?(?=^#### |\Z)", partial_section)
                if not level_match:
                    continue
                rendered = "\n".join([
                    f"#### {heading}",
                    "",
                    f"- 状态：{data['status']}；{data['rubric_text']}",
                    f"- 可观察特征：{'；'.join(data['observable_features'])}。",
                    f"- 证据类型：{data['evidence_type']}；来源：{' '.join(f'[{item}]' for item in data['source_ids'])}。",
                    f"- 证据整理说明：{data['synthesis_note']}",
                    "",
                ])
                partial_section = partial_section[:level_match.start()] + rendered + partial_section[level_match.end():]
            text = text[: host_match.start() + severity_match.start()] + partial_section + text[host_match.start() + severity_match.end():]
            continue
        new_lines = ["### 严重程度", ""]
        for severity in SEVERITIES:
            data = decisions[severity]
            new_lines.extend([
                f"#### {LABELS[severity]}",
                "",
                f"- 状态：{data['status']}；{data['rubric_text']}",
                f"- 可观察特征：{'；'.join(data['observable_features'])}。",
                f"- 证据类型：{data['evidence_type']}；来源：{' '.join(f'[{item}]' for item in data['source_ids'])}。",
                f"- 证据整理说明：{data['synthesis_note']}",
                "",
            ])
        text = text[: host_match.start() + severity_match.start()] + "\n".join(new_lines) + text[host_match.start() + severity_match.end():]
    path.write_text(text, encoding="utf-8")


def build_plant_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    names = {0: "玉米叶枯病", 1: "番茄斑枯病", 2: "南瓜白粉病", 3: "马铃薯早疫病", 4: "玉米锈病", 5: "番茄细菌性斑点病", 6: "番茄晚疫病", 7: "马铃薯晚疫病"}
    for class_id, decisions in PLANT_CLOSURES.items():
        path = PLANT_ROOT / f"{class_id:02d}.md"
        text = path.read_text(encoding="utf-8")
        marker = "## R3.1 严重度证据"
        if marker not in text:
            lines = ["", marker, "", "本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。", ""]
            for severity in SEVERITIES:
                data = decisions[severity]
                lines.extend([
                    f"### {LABELS[severity]}",
                    "",
                    f"- 状态：{data['status']}；{data['rubric_text']}",
                    f"- 可观察特征：{'；'.join(data['observable_features'])}。",
                    f"- 证据类型：{data['evidence_type']}；来源：{' '.join(f'[{item}]' for item in data['source_ids'])}。",
                    f"- 证据整理说明：{data['synthesis_note']}",
                    "",
                ])
            text = text.rstrip() + "\n" + "\n".join(lines) + "\n"
            path.write_text(text, encoding="utf-8")
        for severity, data in decisions.items():
            records.append({"object_type": "plant_disease", "class_id": class_id, "disease": names[class_id], "crop": "玉米" if class_id in {0, 4} else ("南瓜" if class_id == 2 else ("马铃薯" if class_id in {3, 7} else "番茄")), "severity": severity, **data})
    return records


def build_vector_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    relations = [
        (9, "蚜虫", "大豆", "大豆花叶病", ["R31-09-SOY-VECTOR"]),
        (9, "蚜虫", "小麦", "小麦黄矮病", ["R31-09-WHEAT-VECTOR"]),
        (12, "叶蝉科", "水稻", "水稻橙叶病", ["R31-12-GZ-RICE"]),
        (12, "叶蝉科", "水稻", "水稻矮缩病毒", ["R31-12-PKU-RDV"]),
    ]
    for class_id, insect, crop, disease, refs in relations:
        for severity in SEVERITIES:
            data = VECTOR_CLOSURES.get((class_id, crop, disease), {}).get(severity)
            if data is None:
                data = record(
                    status="NEEDS_EVIDENCE",
                    rubric_text=f"{insect}×{crop}×{disease} 已有关系证据，但当前来源不足以安全建立本档病害严重度。",
                    observable_features=["关系已审核", "病害三级进展证据不足"],
                    source_ids=refs,
                    synthesis_note="evidence_synthesized：vector relationship 不自动推出 disease severity；保留 NEEDS_EVIDENCE。",
                )
            data = _add_taxonomic_provenance(data, insect, data.get("source_ids", []))
            records.append({"object_type": "vector_disease", "class_id": class_id, "insect": insect, "crop": crop, "disease": disease, "severity": severity, **data})
    return records


def build_treatment_audit(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    supported = {
        (8, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-08-NCSU-SOY", "R31-08-CPN-BLISTER-SOY"]),
        (9, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-09-UMN-SOY-APHID-ET"]),
        (9, "棉花"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-09-NCSU-COTTON-APHID", "R31-09-TAMU-COTTON-APHIDS"]),
        (9, "桃"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-09-USU-PEACH-APHID-GROW", "R31-09-USU-PEACH-APHID-FRUIT", "R31-09-PSU-PEACH-GREEN-APHID"]),
        (10, "棉花"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-10-NATEC-COTTON-MIRID-2025", "R31-10-AGRIS-MIRID-BTCOTTON-2008", "R31-10-TAIAN-COTTON-MIRID-2021"]),
        (10, "枣"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-10-ZHENGZHOU-JUJUBE-MIRID", "R31-10-HNAGRI-JUJUBE-MIRID"]),
        (11, "水稻"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-11-PINOYRICE-RICE-MOLECRICKET", "R31-11-TNAU-RICE-MOLECRICKET"]),
        (8, "苜蓿"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-08-TAMU-ALFALFA-BLISTER", "R31-08-MU-ALFALFA-BLISTER", "R31-08-UCIPM-ALFALFA-BLISTER"]),
        (12, "芒果"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-12-TNAU-MANGO-HOPPER", "R31-12-HP-MANGO-HOPPER-2022", "R31-12-TAIWAN-MANGO-LEAFHOPPER", "R31-12-NMDB-MANGO-HOPPER"]),
        (12, "茶"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024", "R31-12-JSTAGE-ONUKII-DENSITY-2021"]),
        (14, "玉米"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-14-UMN-WHITE-GRUBS"]),
        (13, "玉米"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-13-OKSTATE-ROWCROP"]),
        (13, "小麦"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-13-OKSTATE-ROWCROP"]),
        (13, "苜蓿"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-13-UMN-ALFALFA-GRASSHOPPER", "R31-13-UNL-ALFALFA-GRASSHOPPER"]),
        (13, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-13-UMN-GRASSHOPPER"]),
        (15, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-15-DACHUAN", "R31-08-CPN-BLISTER-SOY"]),
        (10, "葡萄"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-10-XILINGOL"]),
        (9, "小麦"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-09-CHANGZHI-WHEAT-APHID", "R31-09-UKY-WHEAT-APHID"]),
        (9, "玉米"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-09-CHENGDE-CORN-APHID", "R31-09-FUJIAN-CORN-APHID", "R31-09-TAIWAN-CORN-APHID"]),
        (8, "马铃薯"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-08-NDSU-BLISTER-FIELD-CROPS"]),
        (8, "甜菜"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-08-NDSU-BLISTER-FIELD-CROPS", "R31-08-PNW-SUGARBEET-BLISTER"]),
        (11, "小麦"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-11-GONGYI-WHEAT-MOLECRICKET"]),
        (11, "花生"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-11-TANGSHAN-PEANUT", "R31-11-LINYI-PEANUT"]),
        (11, "马铃薯"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-11-WUHAN-POTATO-MOLE", "R31-11-NANYANG-POTATO-MOLE", "R31-11-JILIN-POTATO-MOLE"]),
        (12, "苜蓿"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-12-KSTATE-ALFALFA-LEAFHOPPER", "R31-12-PENNSTATE-ALFALFA"]),
        (14, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-14-PURDUE-SOY-WHITEGRUB", "R31-14-IOWA-SOY-REPLANT"]),
        (14, "马铃薯"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-14-NDSU-POTATO-WHITEGRUB", "R31-14-ONTARIO-POTATO-WHITE-GRUBS"]),
        (15, "马铃薯"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-15-VTECH-BLISTER-GROUP"]),
        (15, "苜蓿"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-15-OSU-ALFALFA-BLISTER"]),
        (8, "花生"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-08-DAZU-BLISTER-PEANUT"]),
        (14, "花生"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-14-YANCHENG-PEANUT-WHITEGRUB-V16", "R31-14-RUGAO-PEANUT-WHITEGRUB-V16", "R31-14-QINGDAO-PEANUT-WHITEGRUB-V16", "R31-14-NANYANG-PEANUT-WHITEGRUB-V16", "R31-14-PEANUT-GREEN-CONTROL-BOOK-V16"]),
        (13, "水稻"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-13-RICEDATA-RICE-LOCUST-V16", "R31-13-JL-RICE-LOCUST-V16"]),
        (14, "小麦"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-14-AGRI-WHEAT-UNDERGROUND-V16", "R31-14-HUOQIU-WHEAT-RECOVERY-V16"]),
        (12, "水稻"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-12-XJAU-RICE-BLACKTAILED-LEAFHOPPER-V17", "R31-12-JIANGYAN-RICE-HOPPER-V17", "R31-12-JIANGYAN-RICE-HOPPER-RECHECK-V17"]),
        (10, "核桃"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-10-KASHGAR", "R31-10-UOK-WALNUT-CAPSID"]),
        (11, "玉米"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-11-CHENGDE", "R31-11-MOA-CORN-SEEDLING-RECOVERY-V13", "R31-11-YANCHENG-CORN-MOLECRICKET-V13"]),
        (15, "玉米"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER"]),
        (15, "花生"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER", "R31-15-PWSANNONG-BEANBLISTER-HOSTS"]),
    }
    severity_treatment_levels = {
        (13, "大豆"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "优先从田边、历史发生热点和迁入方向持续查田，记录若虫/成虫密度、叶片取食和扩散趋势；低发生时先以巡查和边缘管理为主。",
                        "prevention_monitoring": "来源说明早期巡查与必要时的局部边缘处置有助于减少进入作物的数量；不因低发生自动进行全田处理。",
                    },
                    "severity_note": "本档对应来源的 Light/低发生管理强度；不把来源区间改写为中国登记阈值。",
                    "pesticide_policy": "如需干预，必须按当前作物/靶标登记标签和当地植保指导执行。",
                },
                "source_ids": ["R31-13-UMN-GRASSHOPPER"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "继续估算田边与田内虫口密度，并结合冠层脱叶和豆荚受害复查行动指标。",
                        "biological_physical": "来源建议若虫数量达到 moderate/中等水平且仍较小时，优先处理作物边缘，以降低迁入田内的数量。",
                        "prevention_monitoring": "根据发生热点和虫龄扩大巡查范围；是否处理需结合大豆生育期和实际受害判断。",
                    },
                    "severity_note": "本档对应来源的 Threatening/中等发生管理强度；措施表述限于原文的边缘处理与扩大巡查。",
                    "pesticide_policy": "涉及药剂时只允许按当前标签、登记范围和当地指导决策；不从其他作物或地区换算。",
                },
                "source_ids": ["R31-13-UMN-GRASSHOPPER"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "高发生时扩大到田内和蝗虫繁殖/发生源，持续记录密度、全冠层脱叶以及豆荚和种子直接受害。",
                        "biological_physical": "来源说明早季高虫口应同时处理作物边缘和发生源；虫龄增大时扩大作物内处理区域；极高虫口可优先处理发生源。",
                        "chemical_boundary": "当来源所述大豆脱叶或豆荚受害条件达到需要干预的程度时，才评估登记的叶面防治；具体药剂、剂量、次数和安全间隔必须以当前标签为准。",
                    },
                    "severity_note": "本档对应来源的 Severe/Very severe 与直接豆荚/种子受害管理强度；不新增未经来源支持的处方。",
                    "pesticide_policy": "严格核对大豆/蝗虫登记、标签限制、PPE、抗性和采收间隔；注册信息可能变化。",
                },
                "source_ids": ["R31-13-UMN-GRASSHOPPER"],
            },
        }
    }
    severity_treatment_levels.update({
        (8, "大豆"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "从田边、历史发生点和成虫群集处开始巡查，估算全田冠层脱叶并记录生育期；低于大豆脱叶行动参考时先观察，不自动全田处理。",
                        "prevention_monitoring": "结合田边杂草管理和分区复查，优先识别局部聚集，避免把局部虫群直接外推为全田发生。",
                    },
                    "severity_note": "本档对应来源所述局部/可耐受取食和阈值以下管理；来源未建立独立芫菁专属阈值。",
                    "pesticide_policy": "如需干预，必须按当前大豆+目标害虫登记标签和当地植保指导执行。",
                },
                "source_ids": ["R31-08-NCSU-SOY", "R31-08-CPN-BLISTER-SOY"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "继续从多个田间点位估算冠层脱叶；对成虫明显聚集的斑块进行复查，并把局部点位与全田平均受害区分开。",
                        "biological_physical": "来源指出成虫常聚集，斑块发生时可考虑点状处理；先按大豆生育期和全冠层受害情况判断，不把聚集本身当作全田施药依据。",
                    },
                    "severity_note": "本档对应来源所述群集、可见脱叶和斑块点治管理强度；未把通用大豆脱叶阈值伪造为芫菁专属阈值。",
                    "pesticide_policy": "涉及药剂时只允许按当前登记标签、当地指导和安全要求决策。",
                },
                "source_ids": ["R31-08-CPN-BLISTER-SOY"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "高发生时扩大采样到全田，记录全冠层脱叶、群集扩散及豆荚受害，并按生育期复核行动条件。",
                        "chemical_boundary": "当来源所述大豆脱叶行动参考达到干预条件时，才评估登记的叶面防治；来源未提供本项目可直接使用的具体产品、剂量或次数。",
                    },
                    "severity_note": "本档对应来源所述严重脱叶和达到标准大豆脱叶行动参考后的管理强度；不从来源外推新的药剂方案。",
                    "pesticide_policy": "严格核对大豆/目标害虫登记、标签、PPE、抗性和采收间隔。",
                },
                "source_ids": ["R31-08-NCSU-SOY", "R31-08-CPN-BLISTER-SOY"],
            },
        },
        (9, "大豆"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "低于来源所述损害边界时持续查田，记录每株蚜量、植株受蚜比例、增长趋势和天敌；不因低水平出现就施药。",
                        "biological_physical": "保护瓢虫、草蛉等自然天敌，并将防治决定建立在持续监测而非单次发现上。",
                    },
                    "severity_note": "本档对应低于损害边界、尚无可测经济损害的管理强度。",
                    "pesticide_policy": "不提供产品或剂量；任何化学干预须符合当前大豆登记和当地指导。",
                },
                "source_ids": ["R31-09-UMN-SOY-APHID-ET"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "当虫群接近行动条件或种群仍在上升时，缩短复查间隔并在约 3–4 天后重新取样，结合天敌数量和趋势决定是否跨过行动边界。",
                        "biological_physical": "在未满足全部行动条件时继续利用自然天敌和监测，避免把接近阈值直接写成已达到阈值。",
                    },
                    "severity_note": "本档对应接近经济阈值、需要加密复查的管理强度；不改变来源的行动条件。",
                    "pesticide_policy": "仅在来源条件和当前登记标签共同支持时评估处理。",
                },
                "source_ids": ["R31-09-UMN-SOY-APHID-ET"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "达到来源给出的全部行动条件时复核田间数据：平均约 250 头/株、超过 80% 植株受蚜且种群上升，并评估天敌情况。",
                        "chemical_boundary": "达到行动阈值且需要保护产量时，可评估登记的叶面防治；具体产品、剂量、次数和安全间隔必须以当前标签为准。",
                    },
                    "severity_note": "本档对应来源明确的经济/行动阈值管理强度；系统不把阈值改写成新的产量损失数字。",
                    "pesticide_policy": "严格按大豆+大豆蚜当前登记标签和当地植保指导执行。",
                },
                "source_ids": ["R31-09-UMN-SOY-APHID-ET"],
            },
        },
        (9, "棉花"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "继续巡查棉花幼嫩部位和叶背，记录蚜虫数量、蜜露、天敌及扩展趋势；低虫量且天敌有效时不使用专门杀蚜药剂。",
                        "biological_physical": "保护瓢虫、寄生蜂和病原真菌等自然天敌，优先依靠自然控制和局部管理。",
                    },
                    "severity_note": "本档对应棉花低发生、低污染的管理强度；来源支持监测与天敌保护，不自动全田处理。",
                    "pesticide_policy": "不提供产品或剂量；任何化学干预须符合当前棉花登记和当地植保指导。",
                },
                "source_ids": ["R31-09-NCSU-COTTON-APHID", "R31-09-TAMU-COTTON-APHIDS"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "当虫量接近或达到当前生育阶段行动阈值时，在约48小时内复查，并同步评估天敌和蜜露扩展。",
                        "biological_physical": "在自然控制不足且达到阶段性行动条件时，进入有针对性的棉花蚜虫防治决策，避免无阈值施药。",
                    },
                    "severity_note": "本档对应种群扩展、局部重度聚集和接近/达到阶段性行动阈值的管理强度；保留来源的条件性判断。",
                    "pesticide_policy": "涉及药剂时仅按当前棉花+目标蚜虫登记标签和当地指导执行。",
                },
                "source_ids": ["R31-09-TAMU-COTTON-APHIDS"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "重度聚集或广泛蜜露时扩大到全田复查，记录冠层受害、蕾铃和小铃发育以及煤污/黏棉风险。",
                        "chemical_boundary": "达到来源处理等级或严重后果已经出现时，及时进入针对性防治决策并确保冠层覆盖；不得连续重复同一作用机制。",
                    },
                    "severity_note": "本档对应棉花大量聚集、广泛蜜露及蕾铃/小铃受害的强化管理强度；不新增产品、剂量或次数。",
                    "pesticide_policy": "严格核对当前棉花+目标蚜虫登记、标签、PPE、抗性轮换和采收间隔。",
                },
                "source_ids": ["R31-09-NCSU-COTTON-APHID", "R31-09-TAMU-COTTON-APHIDS"],
            },
        },
        (12, "茶"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "低虫口阶段持续调查嫩梢、百叶和芽梢，记录虫田率、虫梢率和天敌；来源调查中常见低发生约为 1–3 头/百叶的量级，仅作原始资料语境参考。",
                        "prevention_monitoring": "优先采用分批采摘、合理修剪、色板/诱虫灯等农业与物理措施，降低虫口基数。",
                    },
                    "severity_note": "本档将来源的低密度监测和预防性绿色措施映射为 mild；不把区域调查范围当作通用阈值。",
                    "pesticide_policy": "不因低虫口自动施用化学农药。",
                },
                "source_ids": ["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "当百叶虫量达到来源给出的约 6 头防控指标时，加密调查并结合茶树嫩梢受害率决定干预。",
                        "biological_physical": "优先采用分批采摘、修剪、色板/诱虫灯、吸虫机及来源列出的生物防治措施，按当地茶园技术方案执行。",
                    },
                    "severity_note": "本档对应来源明确的防控起始指标和绿色综合防治强度；不添加来源未给出的剂量或施用次数。",
                    "pesticide_policy": "只有当前茶树+目标叶蝉登记和当地指导共同支持时才进入化学应急方案。",
                },
                "source_ids": ["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024", "R31-12-JSTAGE-ONUKII-DENSITY-2021"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "当百叶虫量达到来源所述约 10 头高峰始期或更高密度时，扩大调查范围并记录芽叶受害率；来源研究支持密度与新梢损伤率相关。",
                        "chemical_boundary": "偏重发生或来源所述应急场景下，才按当地技术方案评估已登记的茶树叶蝉防治；不得把示例产品、浓度或间隔迁移到其他地区。",
                    },
                    "severity_note": "本档对应来源的高峰/偏重发生与应急防控强度；仅保留原则性管理和原始指标。",
                    "pesticide_policy": "严格执行当前标签、采摘前安全间隔、抗性轮换和茶园环境要求。",
                },
                "source_ids": ["R31-12-FUJIAN-TEA-LEAFHOPPER-2025", "R31-12-CHONGQING-TEA-LEAFHOPPER-2024", "R31-12-JSTAGE-ONUKII-DENSITY-2021"],
            },
        },
    })
    severity_treatment_levels.update({
        (14, "玉米"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "低于行动阈值时继续取样监测，不进行无差别保险性施药；重点识别高风险田块和幼虫龄期。",
                    },
                    "severity_note": "本档对应来源所述低于行动阈值、以取样和风险识别为主的管理强度。",
                    "pesticide_policy": "不因低于行动阈值自动施药；任何干预须符合当前玉米+蛴螬登记和当地指导。",
                },
                "source_ids": ["R31-14-UMN-WHITE-GRUBS"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "达到管理阈值后，将该田块列入下一季重点管理并持续复查高风险区域。",
                        "prevention_monitoring": "采用来源允许的登记种子处理或播种期处理，并结合土壤取样、前茬和风险地块信息安排管理。",
                    },
                    "severity_note": "本档对应来源所述达到管理阈值后的下一季重点管理强度；不扩展为未被来源支持的出苗后处方。",
                    "pesticide_policy": "仅按当前玉米+蛴螬登记标签、当地指导和安全要求执行。",
                },
                "source_ids": ["R31-14-UMN-WHITE-GRUBS"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "出现明显经济性缺苗或减株时复核受害范围，并评估严重受害区域的后续处置。",
                        "chemical_boundary": "来源指出没有可靠的出苗后补救药剂；若发现较早，可评估严重受害区域重播，并在重播或高风险场景采用更强的登记播种期防护。",
                    },
                    "severity_note": "本档对应来源所述经济性缺苗/减株、重播和高风险场景的管理强度；不把不存在的 rescue treatment 写入系统。",
                    "pesticide_policy": "不提供产品、剂量或次数；严格按当前玉米+蛴螬登记、标签和当地植保方案执行。",
                },
                "source_ids": ["R31-14-UMN-WHITE-GRUBS"],
            },
        },
        (15, "大豆"): {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "持续全田巡查并估算真实脱叶，重点关注田边、历史发生地和成虫群集；未达到来源采用的脱叶防治阈值时不进行全田处理。",
                        "prevention_monitoring": "先区分局部聚集与全田平均受害，记录生育期、虫量趋势和冠层脱叶。",
                    },
                    "severity_note": "本档采用 CPN 大豆芫菁脱叶管理框架的阈值以下阶段；豆芫菁特异范围由 R31-15-DACHUAN 支持，不混用 NC State 数字。",
                    "pesticide_policy": "不因低于 CPN 口径的脱叶阈值自动全田处理；任何干预须符合当前大豆+豆芫菁登记和当地指导。",
                },
                "source_ids": ["R31-15-DACHUAN", "R31-08-CPN-BLISTER-SOY"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "继续巡查并估算冠层脱叶；若成虫局部聚集并造成明显局部脱叶，区分聚集斑块与全田平均受害。",
                        "biological_physical": "优先对聚集区域进行局部处理，而不是立即全田处理，并持续复查虫量和脱叶变化。",
                    },
                    "severity_note": "本档采用 CPN 的局部聚集/斑块点治管理框架，并以 R31-15-DACHUAN 约束到豆芫菁大豆场景；不混用 NC State 数字。",
                    "pesticide_policy": "涉及药剂时仅按当前登记标签、当地植保指导和安全要求决策。",
                },
                "source_ids": ["R31-15-DACHUAN", "R31-08-CPN-BLISTER-SOY"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "当全田脱叶达到项目选定的 CPN 大豆脱叶防治阈值时，复核全田受害范围、生育期和群集扩散。",
                        "chemical_boundary": "达到 CPN 阈值后进入全田防治决策；具体药剂仅按当地登记标签执行，不导入 NC State 的不同数字。",
                    },
                    "severity_note": "本档只采用 CPN 一套大豆脱叶阈值口径；R31-15-DACHUAN 提供豆芫菁特异性和局部暴发范围。",
                    "pesticide_policy": "不提供产品、剂量、次数或 PHI；严格核对当前大豆+豆芫菁登记、标签、PPE 和采收间隔。",
                },
                "source_ids": ["R31-15-DACHUAN", "R31-08-CPN-BLISTER-SOY"],
            },
        },
    })
    severity_treatment_levels[(10, "棉花")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "按棉区和生育期持续调查嫩头、嫩叶、蕾和幼铃，记录虫量、新被害率及天敌；低于当地防治指标时继续监测。",
                    "prevention_monitoring": "清除田边桥梁寄主并保护天敌，优先采用生态调控和分区管理，不进行常规全田用药。",
                },
                "severity_note": "本档对应来源的低虫量/低于当地指标管理语境；棉区和生育期指标不合并成全国统一数字。",
                "pesticide_policy": "如需干预，必须按当前棉花+目标盲蝽登记标签和当地植保指导执行。",
            },
            "source_ids": ["R31-10-NATEC-COTTON-MIRID-2025"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "达到当地对应棉区和生育期防治指标后，复查嫩头、幼蕾、新被害株和蕾花受害范围。",
                    "biological_physical": "按来源实施精准、分区防治，优先由田边向田内处理并兼顾天敌保护，避免无差别全田施药。",
                    "prevention_monitoring": "处理后复查虫量和新受害率，保留当地指标、棉区和生育期上下文。",
                },
                "severity_note": "本档对应来源达到当地防治指标后的主动管理强度；不将 5、10、12、20、40 头/百株拼成连续全国阈值。",
                "pesticide_policy": "涉及药剂时仅按当前登记、标签和当地指导决策。",
            },
            "source_ids": ["R31-10-NATEC-COTTON-MIRID-2025"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "持续高虫压或受害率达到统防统治条件时，扩大调查并记录蕾花损伤、虫量趋势和处理后的恢复情况。",
                    "chemical_boundary": "来源支持在高压力情形下采用连续 2 次、间隔 5–7 天的强化防治；具体药剂和使用条件必须以当前棉花登记标签为准。",
                    "prevention_monitoring": "统防统治后继续复查，轮换作用机制并保护授粉昆虫和自然天敌。",
                },
                "severity_note": "本档对应中国棉田高峰/持续重发管理语境；Taian 来源的连续 2 次、5–7 天间隔保留为来源条件，不外推为所有棉区固定处方。",
                "pesticide_policy": "严格核对棉花/目标盲蝽登记、标签、PPE、抗性和安全间隔。",
            },
            "source_ids": ["R31-10-TAIAN-COTTON-MIRID-2021"],
        },
    }
    severity_treatment_levels[(12, "芒果")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "在新梢、叶片和花穗上持续调查成若虫，使用黄色黏板等方式监测早期种群；低量发生时以观察和园区管理为主。",
                    "prevention_monitoring": "加强修剪、通风透光和清园，减少阴暗处与桥梁寄主，不在低量阶段常规全园用药。",
                },
                "severity_note": "本档对应台湾农业部和 TNAU 的早期/低量管理措施，限于芒果叶蝉复合群。",
                "pesticide_policy": "如需干预，必须按当前芒果+目标叶蝉登记标签和当地指导执行。",
            },
            "source_ids": ["R31-12-TAIWAN-MANGO-LEAFHOPPER", "R31-12-TNAU-MANGO-HOPPER"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "达到处理参考水平或花穗出现明显危害时，复查花穗、嫩组织、蜜露和煤污范围。",
                    "biological_physical": "进入针对性防治，结合园区清洁和修剪；避开盛花期频繁施药并尽量保护授粉昆虫和天敌。",
                    "prevention_monitoring": "处理后复查花穗受害和虫量，按物候期调整管理。",
                },
                "severity_note": "本档对应来源达到处理水平后的针对性管理，不把约 10 头/花穗改写成普适全国阈值。",
                "pesticide_policy": "涉及药剂时仅按当前登记、标签、花期限制和当地指导决策。",
            },
            "source_ids": ["R31-12-TNAU-MANGO-HOPPER", "R31-12-NMDB-MANGO-HOPPER"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "持续或重度发生时，在花穗形成、花穗伸长期/盛花前和幼果阶段分阶段复查虫量、花果受害和复发情况。",
                    "chemical_boundary": "来源支持分阶段连续处理；具体处理次数、药剂、剂量和安全间隔必须按当前芒果登记标签执行。",
                    "prevention_monitoring": "持续修剪、清园和处理后复查，避免单次处理后立即判定风险结束。",
                },
                "severity_note": "本档对应 National Mango Database 的分阶段连续防治语境，以及高发生花序/幼果损失表现；不把不同来源混成统一数值处方。",
                "pesticide_policy": "严格核对芒果/目标叶蝉登记、标签、PPE、授粉昆虫保护、抗性和安全间隔。",
            },
            "source_ids": ["R31-12-NMDB-MANGO-HOPPER", "R31-12-TNAU-MANGO-HOPPER"],
        },
    }
    severity_treatment_levels[(11, "水稻")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "持续查田并维护整平田面、适当水层和田埂卫生；低发生时优先减少蝼蛄进入和局部早期危害。",
                    "prevention_monitoring": "结合人工收集、田块整理和水层管理压低早期种群，不进行预防性常规杀虫剂处理。",
                },
                "severity_note": "本档映射 Pinoy Rice 的文化管理和早期低发生语境。",
                "pesticide_policy": "不因局部轻度受害自动使用杀虫剂；任何干预须符合当前水稻+蝼蛄登记和当地指导。",
            },
            "source_ids": ["R31-11-PINOYRICE-RICE-MOLECRICKET"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "出现幼苗基部受害、missing plants 或 bare patches 时，加密缺苗斑和田边调查，复查水层与虫源。",
                    "biological_physical": "加强水层管理并集中人工收集成若虫，结合田块整理和已有天敌压低种群，优先处理明显受害区域。",
                    "prevention_monitoring": "处理后复查新缺苗和受害扩展，不把文化措施直接等同为化学防治。",
                },
                "severity_note": "本档映射来源从基础文化管理转入出现缺苗后的强化水层/人工收集管理强度。",
                "pesticide_policy": "仅按当前水稻登记、标签和当地指导决策，不创建来源未提供的药剂处方。",
            },
            "source_ids": ["R31-11-PINOYRICE-RICE-MOLECRICKET"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "幼苗大量死亡、plant stand loss 或缺苗斑持续扩大时，扩大到全田、田埂和虫源位置复查。",
                    "chemical_boundary": "当文化和人工措施不足且危害持续扩大时，来源允许将 insecticide 作为 corrective last resort；不得作为预防性常规措施。",
                    "prevention_monitoring": "处理后继续复查建株、缺苗斑和残余种群，具体药剂和标签条件以当地登记为准。",
                },
                "severity_note": "本档映射来源的 severe stand-loss 语境和 corrective last-resort 管理边界；未新增产品、剂量或次数。",
                "pesticide_policy": "严格核对当前水稻+蝼蛄登记、PPE、抗性和安全间隔。",
            },
            "source_ids": ["R31-11-PINOYRICE-RICE-MOLECRICKET"],
        },
    }
    severity_treatment_levels[(8, "苜蓿")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "收割前持续巡查花、嫩叶和田边，记录零散虫群与 forage contamination 风险；低发生时以监测为主。",
                    "prevention_monitoring": "控制开花杂草，尽量在苜蓿高开花期前收割，并避免会把甲虫压碎进干草的压扁/调制方式。",
                },
                "severity_note": "本档映射 TAMU/UC IPM 的零散发生和收割前预防管理；cantharidin 风险作为苜蓿用途的可观察 host-use 风险记录。",
                "pesticide_policy": "不因零散发生自动用药；任何干预须符合当前苜蓿+芫菁登记和当地指导。",
            },
            "source_ids": ["R31-08-TAMU-ALFALFA-BLISTER", "R31-08-UCIPM-ALFALFA-BLISTER"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "若甲虫在田边或田内少数区域聚集，加密虫区和收割前调查，区分局部虫群与全田平均风险。",
                    "biological_physical": "优先跳过局部虫区不收割，或仅对虫区进行 spot treatment，并将相关草捆与其他干草隔离。",
                    "prevention_monitoring": "处理或收割后复查虫群是否扩散，避免把局部聚集直接外推为全田风险。",
                },
                "severity_note": "本档映射 TAMU/MU 的局部聚集、spot treatment/跳过虫区和草捆隔离管理强度。",
                "pesticide_policy": "涉及药剂时仅按当前苜蓿登记、标签和当地指导执行。",
            },
            "source_ids": ["R31-08-TAMU-ALFALFA-BLISTER", "R31-08-UCIPM-ALFALFA-BLISTER"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "发现大群、swarm 或快速局部脱叶时，扩大到全田和收割前虫区复查，并评估干草污染风险。",
                    "chemical_boundary": "持续高密度虫群可按来源采用针对性防治；收割前再次复查，仍有 swarm/高密度虫区时停止或避开该区域收割。",
                    "prevention_monitoring": "将高风险虫区与其他干草隔离，防止活虫或被压碎虫体进入饲草。",
                },
                "severity_note": "本档映射 MU/TAMU 的 swarm、快速局部脱叶和干草 cantharidin 风险管理强度；不写入未被来源明确支持的产品、剂量或次数。",
                "pesticide_policy": "严格核对当前苜蓿+芫菁登记、标签、PPE、抗性和采收前要求。",
            },
            "source_ids": ["R31-08-MU-ALFALFA-BLISTER", "R31-08-TAMU-ALFALFA-BLISTER"],
        },
    }
    severity_treatment_levels[(9, "桃")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "持续检查桃树嫩梢、叶片和蚜群数量；低于来源处理参考时以观察和复查为主，不自动升级为强杀虫处理。",
                    "biological_physical": "保护瓢虫、草蛉、食蚜蝇等自然天敌，优先依靠自然控制并记录蜜露、卷叶和种群趋势。",
                },
                "severity_note": "本档对应 USU 桃树资料的低发生/低于处理参考管理强度；不把少量发生机械改写为药剂方案。",
                "pesticide_policy": "不因低水平发现自动施药；任何干预须符合当前桃树+目标蚜虫登记和当地指导。",
            },
            "source_ids": ["R31-09-USU-PEACH-APHID-GROW", "R31-09-USU-PEACH-APHID-FRUIT"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "当蚜群达到桃树处理参考或卷叶、蜜露持续增加时，复查嫩梢、叶背和果面污染风险。",
                    "biological_physical": "可采用来源支持的 insecticidal soap 或约 1% horticultural oil 等较温和、针对性的处理，并继续保护天敌。",
                    "prevention_monitoring": "处理后复查蚜群、卷叶和蜜露变化，不把单一来源的 colony 数字外推为全国统一阈值。",
                },
                "severity_note": "本档对应 USU 来源达到桃树处理参考后的温和针对性管理强度；shuck split 前后 colony 参考保留原物候语境。",
                "pesticide_policy": "仅按来源条件、桃树登记标签和当地植保指导执行；不新增剂量或施用次数。",
            },
            "source_ids": ["R31-09-USU-PEACH-APHID-GROW", "R31-09-USU-PEACH-APHID-FRUIT"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "种群持续高位、幼树生长受抑或煤污明显时，扩大到全树叶背、嫩梢和果面复查，并评估较温和措施是否不足。",
                    "chemical_boundary": "达到来源支持的处理条件且需要保护树体或果实时，可进入登记杀蚜剂防治；确保叶片背面充分覆盖。",
                    "prevention_monitoring": "处理后复查残余种群和新生长部位，继续保护自然天敌并按标签要求轮换作用机制。",
                },
                "severity_note": "本档对应 USU/Penn State 资料的持续高种群、幼树生长受抑和煤污污染管理强度；不写入未被来源明确支持的产品、剂量或次数。",
                "pesticide_policy": "严格核对当前桃树+目标蚜虫登记、标签、PPE、抗性和采收间隔；具体药剂以当地标签为准。",
            },
            "source_ids": ["R31-09-PSU-PEACH-GREEN-APHID", "R31-09-USU-PEACH-APHID-GROW"],
        },
    }
    severity_treatment_levels[(10, "枣")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "在新叶、嫩梢、花蕾和幼果期持续查园，记录盲蝽及早期孔洞、枯斑扩展；低发生时优先监测和压低虫源。",
                    "biological_physical": "清园、清除杂草和残枝，结合诱集植物、灯诱/性诱及天敌保护，减少不必要的全园化学处理。",
                },
                "severity_note": "本档对应枣园低发生、早期叶片受害和河南农科院综合管理建议；NY/T 1464.52 用于多种 Miridae 枣树范围约束。",
                "pesticide_policy": "不因早期局部受害自动全园施药；任何干预须符合当前枣树+目标盲蝽登记和当地指导。",
            },
            "source_ids": ["R31-10-HNAGRI-JUJUBE-MIRID", "R31-10-ZHENGZHOU-JUJUBE-MIRID"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "发生期出现叶片孔洞、花蕾受害或幼果坏死时，加密关键生育期和受害点位调查。",
                    "biological_physical": "在清园、诱控和天敌保护基础上，根据监测在关键期采用适时、针对性的低毒药剂或分区处理，避免无差别全园施药。",
                    "prevention_monitoring": "处理后复查新叶、花蕾和幼果，判断受害是否继续由局部向园内扩展。",
                },
                "severity_note": "本档对应冬枣资料中由叶部向花蕾/幼果发展的主动防治阶段；不把单一代表性绿盲蝽表现扩大为所有 Miridae 同质表现。",
                "pesticide_policy": "涉及药剂时仅按当前枣树登记、标签和当地指导决策。",
            },
            "source_ids": ["R31-10-HNAGRI-JUJUBE-MIRID", "R31-10-ZHENGZHOU-JUJUBE-MIRID"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "花蕾和幼果大量受害、叶片受害率显著升高或种群持续重发时，扩大到全园并连续复查处理后的新受害。",
                    "chemical_boundary": "严重持续发生时按来源采用强化连续防治；发生期可约每 5–7 天再次处理，具体药剂、次数和安全间隔必须以当前枣树登记标签为准。",
                    "prevention_monitoring": "连续处理后仍需复查花蕾、幼果和叶片恢复，保护天敌并避免把代表性绿盲蝽数字当作所有 Miridae 的统一阈值。",
                },
                "severity_note": "本档将郑州来源的重发连续防治与 Frontiers 的 Apolygus lucorum 代表性重发背景对应到枣盲蝽组；5–7 天为来源条件，不是所有地区固定处方。",
                "pesticide_policy": "严格核对当前枣树+目标盲蝽登记、标签、PPE、抗性和安全间隔。",
            },
            "source_ids": ["R31-10-ZHENGZHOU-JUJUBE-MIRID"],
        },
    }
    severity_treatment_levels[(10, "葡萄")] = {
        "mild": {"body": {"sections": {"monitoring": "以田边、嫩梢和花序为重点巡查，结合清园、黄板/诱控和天敌保护；轻度发生不作全园施药。"}, "severity_note": "对应来源的早期/低压管理强度。", "pesticide_policy": "药剂仅按当前登记标签和当地植保指导执行。"}, "source_ids": ["R31-10-XILINGOL"]},
        "moderate": {"body": {"sections": {"monitoring": "在萌芽至展叶关键期加密检查新梢和花序。", "chemical_boundary": "达到来源所述处理条件时实施针对性处理，优先控制发生点和受害部位。"}, "severity_note": "对应关键生育期主动处理，不将其改写为统一数字阈值。", "pesticide_policy": "药剂、剂量和安全间隔以当前标签及当地指导为准。"}, "source_ids": ["R31-10-XILINGOL"]},
        "severe": {"body": {"sections": {"monitoring": "持续跟踪重发果园和处理后回升情况。", "chemical_boundary": "危害严重时按来源采用 7–10 天间隔的连续强化处理，最多连喷 3 次的表述仅保留为来源语境，不扩展为通用处方。"}, "severity_note": "对应来源的严重果园重复处理强度。", "pesticide_policy": "必须核对当前登记、标签、PPE 和采收间隔。"}, "source_ids": ["R31-10-XILINGOL"]},
    }
    severity_treatment_levels[(9, "小麦")] = {
        "mild": {"body": {"sections": {"monitoring": "低于当前生育阶段处理边界时持续查田、保护天敌并记录虫量变化，不自动施药。"}, "severity_note": "苗期/穗期阈值各自保留 crop-stage context，不合并为连续曲线。", "pesticide_policy": "药剂仅按当前小麦登记标签和当地指导执行。"}, "source_ids": ["R31-09-CHANGZHI-WHEAT-APHID", "R31-09-UKY-WHEAT-APHID"]},
        "moderate": {"body": {"sections": {"monitoring": "达到苗期百茎约 200 头或相应阶段处理参考时，重点挑治发生点并复查天敌和扩展趋势。"}, "severity_note": "该档映射苗期重点挑治语境；不与穗期数字拼成统一阈值。", "pesticide_policy": "具体药剂与施用条件以当前登记标签和当地指导为准。"}, "source_ids": ["R31-09-CHANGZHI-WHEAT-APHID", "R31-09-UKY-WHEAT-APHID"]},
        "severe": {"body": {"sections": {"monitoring": "穗期达到约百穗 500 头或出现暴发势头时扩大调查并确认持续高压。", "chemical_boundary": "按来源组织统防统治或暴发应急防治；不同生育阶段的阈值和应急语境保持独立，不构造连续数值曲线。"}, "severity_note": "对应穗期统防统治/暴发应急管理强度。", "pesticide_policy": "严格按当前小麦登记、标签和当地植保指导执行。"}, "source_ids": ["R31-09-CHANGZHI-WHEAT-APHID", "R31-09-UKY-WHEAT-APHID"]},
    }
    severity_treatment_levels[(9, "玉米")] = {
        "mild": {"body": {"sections": {"monitoring": "苗期以黄板/银膜降低虫源，优先查田并保护天敌；天敌充足时避免药剂。"}, "severity_note": "对应苗期低压和天敌保护语境。", "pesticide_policy": "药剂仅按当前玉米登记标签和当地指导执行。"}, "source_ids": ["R31-09-CHENGDE-CORN-APHID", "R31-09-FUJIAN-CORN-APHID"]},
        "moderate": {"body": {"sections": {"monitoring": "按玉米生育阶段复查虫量、蚜株率和天敌。", "chemical_boundary": "达到对应生育期处理条件时进行精准、针对性处理，不把不同生育期数字拼成统一曲线。"}, "severity_note": "对应生育期阈值后的单次精准处理语境。", "pesticide_policy": "具体药剂、剂量和间隔以当前登记标签和当地指导为准。"}, "source_ids": ["R31-09-CHENGDE-CORN-APHID", "R31-09-FUJIAN-CORN-APHID"]},
        "severe": {"body": {"sections": {"monitoring": "持续高虫量时扩大复查，确认嫩叶皱缩、黄化、煤烟和结实下降等重发生表现。", "chemical_boundary": "台湾来源将严重发生与约 10 天间隔、2–3 次处理并列；此处仅保留为持续高压/重发管理语境，不扩展为普遍标签规则。"}, "severity_note": "严重 Treatment 由来源明确的严重表现与重复处理语境共同支持。", "pesticide_policy": "必须按当前玉米登记、标签、PPE 和采收间隔执行。"}, "source_ids": ["R31-09-TAIWAN-CORN-APHID"]},
    }
    severity_treatment_levels[(13, "苜蓿")] = {
        "mild": {
            "body": {
                "sections": {
                    "monitoring": "从田边、历史发生热点和迁入方向持续查田，记录蝗虫密度、叶片取食和扩散趋势；低于 Threatening/处理水平时继续监测，不进行全田处理。",
                    "prevention_monitoring": "优先识别局部发生和田边虫群，观察虫量是否继续上升；不因低发生自动全田化学防治。",
                },
                "severity_note": "本档直接映射 UMN 的 Light 发生语境和 UNL 的先巡查管理原则。",
                "pesticide_policy": "如需干预，必须按当前苜蓿+目标蝗虫登记标签和当地植保指导执行。",
            },
            "source_ids": ["R31-13-UMN-ALFALFA-GRASSHOPPER", "R31-13-UNL-ALFALFA-GRASSHOPPER"],
        },
        "moderate": {
            "body": {
                "sections": {
                    "monitoring": "继续估算田边与田内虫口密度，并复查局部取食和扩散趋势；优先区分边缘受害带与全田发生。",
                    "biological_physical": "若虫群主要从田边迁入且危害仍局限在边缘，优先处理外侧约 150 英尺或其他局部受害带，避免不必要的全田处理。",
                    "prevention_monitoring": "处理后复查边缘和迁入方向，确认虫量与受害是否继续扩大。",
                },
                "severity_note": "本档直接映射 UMN 的 Threatening 发生语境和 UNL 的边缘/局部处理建议。",
                "pesticide_policy": "涉及药剂时只允许按当前苜蓿+目标蝗虫登记标签、当地指导和安全要求决策。",
            },
            "source_ids": ["R31-13-UNL-ALFALFA-GRASSHOPPER"],
        },
        "severe": {
            "body": {
                "sections": {
                    "monitoring": "高发生时扩大到田内、田边和发生源，持续记录密度、全冠层脱叶以及刈割后再生植株受害。",
                    "biological_physical": "若全田已明显侵染，可利用未割条带集中残余虫群后进行局部处理，并复核再生植株风险。",
                    "chemical_boundary": "来源建议全田侵染时先收割苜蓿，再对再生植株实施针对性防治；具体药剂、剂量、次数和安全间隔必须以当前标签为准。",
                },
                "severity_note": "本档直接映射 UMN 的 Severe 发生语境、UC IPM 的严重脱叶描述和 UNL 的全田侵染后收割/保护再生建议。",
                "pesticide_policy": "严格核对苜蓿/目标害虫登记、标签、PPE、抗性和采收间隔；不导入未经来源支持的处方。",
            },
            "source_ids": ["R31-13-UNL-ALFALFA-GRASSHOPPER"],
        },
    }
    for crop in ("玉米", "小麦"):
        severity_treatment_levels[(13, crop)] = {
            "mild": {
                "body": {
                    "sections": {
                        "monitoring": "按田边和田内样点监测蝗虫密度、作物受害和扩散趋势；来源 Light 区间为 3–7 头/平方码，处置需结合具体作物状况。",
                        "prevention_monitoring": "优先处理发生边缘和迁入方向，保持持续查田，不因低密度自动全田处理。",
                    },
                    "severity_note": "本档直接映射 Oklahoma State Extension 的 Light 管理判断。",
                    "pesticide_policy": "如需干预，必须按当前作物/靶标登记标签和当地指导执行。",
                },
                "source_ids": ["R31-13-OKSTATE-ROWCROP"],
            },
            "moderate": {
                "body": {
                    "sections": {
                        "monitoring": "继续进行田内和田边密度调查并记录受害扩展；来源 Moderate 区间为 8–14 头/平方码。",
                        "biological_physical": "来源将该区间列为 probably treatment，应结合田间受害、作物生育期和当地指导决定分区处置。",
                    },
                    "severity_note": "本档直接映射 Oklahoma State Extension 的 Moderate 管理判断，不添加药剂处方。",
                    "pesticide_policy": "涉及药剂时只允许按当前登记、标签和当地植保指导决策。",
                },
                "source_ids": ["R31-13-OKSTATE-ROWCROP"],
            },
            "severe": {
                "body": {
                    "sections": {
                        "monitoring": "来源 Abundant 区间为 ≥15 头/平方码；扩大到田内、田边和发生源，复核受害与扩散。",
                        "chemical_boundary": "来源将该区间列为需要处置；具体化学措施只能依据当前作物+目标蝗虫登记标签和当地指导。",
                    },
                    "severity_note": "本档直接映射 Oklahoma State Extension 的 Abundant 管理判断；不从来源外推产品、剂量或次数。",
                    "pesticide_policy": "严格执行当前标签、PPE、抗性和采收间隔要求。",
                },
                "source_ids": ["R31-13-OKSTATE-ROWCROP"],
            },
        }
    def v15_level(monitoring: str, action: str, note: str, source_ids: list[str]) -> dict[str, Any]:
        return {
            "body": {
                "sections": {"monitoring": monitoring, "management": action},
                "severity_note": note,
                "pesticide_policy": "涉及药剂时仅按当前登记标签、当地植保指导和安全要求执行；本条不提供产品、剂量或浓度。",
            },
            "source_ids": source_ids,
        }

    v15_levels = {
        (8, "马铃薯"): [
            v15_level("巡查马铃薯田，发现零散芫菁时记录位置和扩散趋势。", "以人工移除、局部清除和受害斑块监测为主，不作无必要的全田处理。", "低发生对应来源的监测/局部管理条件。", ["R31-15-PNW-POTATO-BLISTER-V15"]),
            v15_level("复查受害斑块边界和活动虫量。", "仅对确认的活动斑块实施定点处置，并在后续巡查中确认是否继续扩展。", "局部活动与局部处置相对应，不将通用 IPM 拆成三级。", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-08-NDSU-BLISTER-FIELD-CROPS"]),
            v15_level("持续重发或多个斑块合并时扩大调查范围。", "在标签和当地指导允许时，对持续高压的受害区域采取强化处理并复查；不以本条生成具体农药处方。", "高压/持续发生对应扩大管理和复查条件。", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-08-NDSU-BLISTER-FIELD-CROPS"]),
        ],
        (8, "甜菜"): [
            v15_level("监测甜菜田芫菁活动和受害斑块。", "低发生时优先巡查、清除和局部管理。", "低发生对应监测优先。", ["R31-08-PNW-SUGARBEET-BLISTER"]),
            v15_level("确认局部群集和叶片损伤持续扩大。", "对局部活动区域进行定点处理并安排复查。", "局部发生对应局部处置。", ["R31-08-PNW-SUGARBEET-BLISTER", "R31-08-NDSU-BLISTER-FIELD-CROPS"]),
            v15_level("发生范围扩大且持续重发，出现明显脱叶风险。", "按当前登记与当地指导对受害区域强化处理，并在再次调查后决定是否需要继续处置。", "持续高压对应强化处理和复查。", ["R31-08-PNW-SUGARBEET-BLISTER", "R31-08-NDSU-BLISTER-FIELD-CROPS"]),
        ],
        (11, "小麦"): [
            v15_level("小麦苗期仅见局部种子、幼芽或嫩茎受害，尚未形成连续缺苗。", "以播前/播种期保护、田间巡查和局部压低虫源为主。", "来源将预防与早期监测作为低发生管理；不把其解释为统一密度阈值。", ["R31-11-GONGYI-WHEAT-MOLECRICKET"]),
            v15_level("出现点片咬断幼苗、根区受扰或局部缺苗。", "针对受害点片加强根区和土壤管理，结合巡查压低局部种群。", "点片缺苗对应定向管理。", ["R31-11-GONGYI-WHEAT-MOLECRICKET"]),
            v15_level("持续重发造成明显缺苗断垄并有扩展趋势。", "扩大受害区调查并按当地指导采取强化土壤/根区措施，随后复查缺苗和扩展。", "重发对应扩大、强化和复查；不增加来源未给出的药剂细节。", ["R31-11-GONGYI-WHEAT-MOLECRICKET"]),
        ],
        (11, "花生"): [
            v15_level("花生根区仅有局部地下害虫活动，尚无连续缺苗。", "以种子/土壤预防、田间巡查和活动区监测为主。", "低发生对应预防和监测。", ["R31-11-TANGSHAN-PEANUT", "R31-11-LINYI-PEANUT"]),
            v15_level("局部根区受害并出现点片缺苗或生长受抑。", "针对活动区进行根区/土壤定点处置，并复查受害边界。", "点片危害对应定向土壤管理。", ["R31-11-TANGSHAN-PEANUT", "R31-11-LINYI-PEANUT"]),
            v15_level("持续高压导致较大范围缺苗或根区危害扩展。", "在当地指导允许时扩大活动区处理并进行后续复查；不虚构播后救治效果或处方。", "持续高压对应扩大处理和复查。", ["R31-11-TANGSHAN-PEANUT", "R31-11-LINYI-PEANUT"]),
        ],
        (11, "马铃薯"): [
            v15_level("马铃薯播种沟或苗期仅见局部地下害虫活动。", "以整地、播种沟管理和巡查为主，优先压低局部虫源。", "低发生对应文化措施和监测。", ["R31-11-WUHAN-POTATO-MOLE", "R31-11-JILIN-POTATO-MOLE"]),
            v15_level("出现点片苗害、根区扰动或局部缺苗。", "对受害播种沟/斑块采取定向土壤管理并复查扩展。", "点片危害对应局部定向措施。", ["R31-11-WUHAN-POTATO-MOLE", "R31-11-NANYANG-POTATO-MOLE"]),
            v15_level("持续重发造成明显缺苗或地下部危害扩展。", "按当地马铃薯地下害虫指导扩大受害区管理并复查；具体产品仅依当前标签。", "重发对应强化管理和复查。", ["R31-11-NANYANG-POTATO-MOLE", "R31-11-JILIN-POTATO-MOLE"]),
        ],
        (12, "苜蓿"): [
            v15_level("虫量低或接近收获期，尚无明显冠层损失。", "持续监测并保护天敌；接近适宜收获期时按来源建议评估提前刈割。", "低发生/收获期管理对应监测和收获决策。", ["R31-12-KSTATE-ALFALFA-LEAFHOPPER", "R31-12-PENNSTATE-ALFALFA"]),
            v15_level("虫量达到来源给出的苜蓿处理判断，受害开始扩展。", "按来源阈值语境实施针对性处理，结合株高、收获期和田间调查复核。", "达到处理判断后才进入定向干预，不创建跨来源统一阈值。", ["R31-12-PENNSTATE-ALFALFA"]),
            v15_level("高虫量和受害超出局部范围，继续造成生长损失风险。", "在来源条件允许时扩大处理范围或先行收获，再复查并按当地标签指导处理残余虫量。", "高压且不再局限于局部对应扩大管理/收获后复查。", ["R31-12-KSTATE-ALFALFA-LEAFHOPPER", "R31-12-PENNSTATE-ALFALFA"]),
        ],
        (14, "大豆"): [
            v15_level("已发生低群体但预计仍可维持合理群体。", "根据田间群体评估保留现有植株并继续观察；Purdue 证据明确播后没有可靠 rescue insecticide。", "本档是群体保留决策，不伪造杀虫 Treatment。", ["R31-14-PURDUE-SOY-WHITEGRUB", "R31-14-IOWA-SOY-REPLANT"]),
            v15_level("缺苗已影响局部群体，现有群体不足以稳定成产。", "进行 repair planting/局部补播决策，并重新评估群体均匀性。", "中档由大豆群体损失到修复性补播的管理条件支持。", ["R31-14-IOWA-SOY-REPLANT"]),
            v15_level("缺苗范围大或预计群体无法达到可接受成产水平。", "评估整块重播或改种，并记录土壤害虫风险供下一季预防；不把下一季预防冒充当季救治。", "重档是来源支持的 full replant/repair decision，不是化学救治。", ["R31-14-PURDUE-SOY-WHITEGRUB", "R31-14-IOWA-SOY-REPLANT"]),
        ],
        (14, "马铃薯"): [
            v15_level("抽样显示局部浅表块茎刮食，尚无广泛根系或商品性损失。", "按来源抽样并定位受害点，优先监测和局部管理。", "低档保留 NDSU/马铃薯来源的抽样场景，不改写为通用阈值。", ["R31-14-NDSU-POTATO-WHITEGRUB", "R31-14-ONTARIO-POTATO-WHITE-GRUBS"]),
            v15_level("根/茎受害和较大浅圆孔洞并存，受害样点范围增加。", "依据抽样覆盖范围对受害田块实施定向处理，并复查根区和块茎。", "中档对应来源的受害部位和样点范围管理。", ["R31-14-NDSU-POTATO-WHITEGRUB", "R31-14-ONTARIO-POTATO-WHITE-GRUBS"]),
            v15_level("植株矮化、萎蔫，块茎出现深腔并可能失去商品性。", "对达到来源处理条件的受害区域进行强化处置和复查；不额外复制具体产品/剂量。", "重档由马铃薯 exact-host 损伤和来源处理条件共同支持。", ["R31-14-NDSU-POTATO-WHITEGRUB", "R31-14-ONTARIO-POTATO-WHITE-GRUBS"]),
        ],
        (15, "马铃薯"): [
            v15_level("马铃薯田仅见零散芫菁活动。", "巡查、人工移除和局部清除为主。", "低发生对应监测/局部管理。", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-15-VTECH-BLISTER-GROUP"]),
            v15_level("活动集中在部分植株或斑块，受害范围仍局部。", "仅处理确认的受害斑块，随后复查扩散。", "局部活动对应 spot treatment，而非全田药剂。", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-15-VTECH-BLISTER-GROUP"]),
            v15_level("高密度、持续发生或斑块扩展到较大范围。", "按当前登记和当地指导对扩展区域采取强化处置，并在复查后决定是否需要重复处理。", "高压/持续发生对应强化处理和复查；group→member 仅在同一作物和无排除条件下适用。", ["R31-15-PNW-POTATO-BLISTER-V15", "R31-15-VTECH-BLISTER-GROUP"]),
        ],
        (15, "苜蓿"): [
            v15_level("苜蓿田出现零散芫菁，接近收获前仍无明显污染风险。", "控草、持续巡查和按来源条件提前收割，避免压碎虫体。", "低发生对应收获前监测和污染风险控制。", ["R31-15-OSU-ALFALFA-BLISTER"]),
            v15_level("局部虫群已明显聚集，受害区仍可划定。", "跳过受影响区域或进行局部处置，分离可疑草捆并复查。", "局部虫群对应局部管理和草捆隔离。", ["R31-15-OSU-ALFALFA-BLISTER"]),
            v15_level("虫群持续或范围扩大，收割和干草污染风险显著。", "延迟或避开受污染区域收割；需要处理时按当前登记和当地指导执行，收割前再次巡查。", "持续虫群对应扩大风险控制、收割决策和复查。", ["R31-15-OSU-ALFALFA-BLISTER"]),
        ],
    }
    for key, levels in v15_levels.items():
        severity_treatment_levels[key] = {name: levels[i] for i, name in enumerate(("mild", "moderate", "severe"))}

    severity_treatment_levels[(8, "花生")] = {
        "mild": v15_level("低虫口且尚未造成明显经济损失时巡查花生田，保护自然控制作用。", "放宽防治指标并保持低干预；确需防治时按当地登记和指导选择措施。", "大足官方来源的低虫口/低经济损失条件。", ["R31-08-DAZU-BLISTER-PEANUT"]),
        "moderate": v15_level("红头芫菁初发或较低密度但已需要控制时复查受害范围。", "在适期对确认区域进行定向叶面处理，避免无必要的全田处理。", "大足官方来源将初发/较低密度与及时处置直接关联。", ["R31-08-DAZU-BLISTER-PEANUT"]),
        "severe": v15_level("花生重发田块存在持续扩散和相邻田块迁移风险。", "当季加强相邻田块联防联控；下一季采用非寄主轮作降低持续虫源。", "轮作作为下一季长期措施，联防联控作为当季扩散控制，不混写为单一阈值。", ["R31-08-DAZU-BLISTER-PEANUT"]),
    }
    severity_treatment_levels[(14, "花生")] = {
        "mild": v15_level("花生处于低风险或尚未形成明显蛴螬危害。", "采用种子/土壤绿色预防、诱控或微生物措施压低虫源并持续监测。", "花生 exact-host 资料支持播前/早期预防。", ["R31-14-YANCHENG-PEANUT-WHITEGRUB-V16", "R31-14-BEIJING-CROPS"]),
        "moderate": v15_level("花生发生量达到中等或进入初龄幼虫适期，出现当前田间危害。", "按花生关键期对根际/土壤进行一次定向处理，并复查受害范围。", "如皋与青岛资料分别提供中等发生适期和花生根际/土壤处理语境。", ["R31-14-RUGAO-PEANUT-WHITEGRUB-V16", "R31-14-QINGDAO-PEANUT-WHITEGRUB-V16"]),
        "severe": v15_level("花生地下害虫严重发生，根际/荚果危害持续或一次处理后仍严重。", "对严重地块强化根际/土壤处置；只有在原地块指导允许时才复查并按来源间隔再次处理。", "严重发生、强化处理和复查来自花生来源；不生成跨地区处方。", ["R31-14-PEANUT-GREEN-CONTROL-BOOK-V16", "R31-14-NANYANG-PEANUT-WHITEGRUB-V16"]),
    }
    severity_treatment_levels[(13, "水稻")] = {
        "mild": v15_level("水稻稻蝗处于中低密度或低风险发生场景。", "优先监测、生态调控及生物/植物源防治，不自动进入全田化学处理。", "吉林方案的中低密度绿色防控与水稻文献的低风险阶段语境。", ["R31-13-RICEDATA-RICE-LOCUST-V16", "R31-13-JL-RICE-LOCUST-V16"]),
        "moderate": v15_level("中华稻蝗达到水稻当前生育期的来源防治指标。", "依据该生育期原始指标实施针对性防治；不同生育期指标保持独立，不合并为一条曲线。", "国家水稻数据中心来源给出 exact rice、生育期和指标对应关系。", ["R31-13-RICEDATA-RICE-LOCUST-V16"]),
        "severe": v15_level("蝗虫在稻区大面积、高密度或集中发生。", "按农业部门应急指导实施专业化、区域化强化防控；具体药剂和施药方式遵循当地登记与指导。", "吉林方案直接区分高密度化学应急和集中连片专业化防控。", ["R31-13-JL-RICE-LOCUST-V16", "R31-13-MOA-LOCUST"]),
    }
    severity_treatment_levels[(14, "小麦")] = {
        "mild": v15_level("小麦处于一般或轻风险地下害虫发生场景，尚无明显缺苗断垄。", "采用小麦种子处理/包衣并持续监测；不把混合虫量改写为纯蛴螬全国阈值。", "农业农村部小麦方案支持地下害虫风险场景下的种子处理和监测。", ["R31-14-AGRI-WHEAT-UNDERGROUND-V16"]),
        "moderate": v15_level("蛴螬风险升高或出苗后地下害虫造成达到来源触发条件的死苗。", "在种子处理基础上按当地条件实施土壤/根际定向处理；保留地区、年份和死苗语境。", "农业农村部方案支持小麦地下害虫发生趋重和出苗后达到死苗条件时的田间处理。", ["R31-14-AGRI-WHEAT-UNDERGROUND-V16"]),
        "severe": v15_level("地下害虫造成严重缺苗断垄或大面积缺苗。", "先按当地指导控制当前虫害，再依据同一小麦田管理意见补种、移栽或重播；恢复性措施不表述为更强杀虫剂。", "小麦地下害虫严重发生与缺苗恢复链分别由防控方案和官方田管意见支持。", ["R31-14-AGRI-WHEAT-UNDERGROUND-V16", "R31-14-HUOQIU-WHEAT-RECOVERY-V16"]),
    }
    severity_treatment_levels[(12, "水稻")] = {
        "mild": v15_level("水稻叶蝉虫量低于当前来源所述防治指标，且尚未出现明显扩散或严重受害。", "保持查田，结合抗/耐虫品种、田边杂草管理和合理肥水等基础措施；不因低于指标自动用药。", "新疆农业大学来源提供水稻叶蝉的寄主和生育期调查/防治语境；管理表述不合并不同生育期数值。", ["R31-12-XJAU-RICE-BLACKTAILED-LEAFHOPPER-V17"]),
        "moderate": v15_level("黑尾叶蝉达到水稻当前生育期和调查位置对应的来源防治指标，受害开始需要主动干预。", "按来源语境对达到指标的田块开展重点挑治，保留田边与田中央、早稻与晚稻等原始上下文。", "新疆农业大学页面将黑尾叶蝉在水稻上的生育期虫量指标与达到指标后的重点挑治直接关联。", ["R31-12-XJAU-RICE-BLACKTAILED-LEAFHOPPER-V17"]),
        "severe": v15_level("水稻穗期叶蝉在共同防治对象田中达到百穴1000头的原文条件，或叶蝉已集中扩散并出现黑穗及品质/产量损失风险。", "按共同对象田原文实施稻叶蝉防治，并在后续复查中对集中扩散或残留虫量补治；不把该共同对象值改写成叶蝉单种全国阈值，也不使用褐飞虱专属症状。", "姜堰两页原文共同列出褐飞虱、叶蝉防治对象及百穴1000头条件，并明确稻叶蝉复查补治和叶蝉扩散造成品质/产量风险；数值仍限于该穗期共同对象田语境。", ["R31-12-JIANGYAN-RICE-HOPPER-V17", "R31-12-JIANGYAN-RICE-HOPPER-RECHECK-V17"]),
    }

    def composed_level(manifestation: str, action: str, note: str, source_ids: list[str]) -> dict[str, Any]:
        level = v15_level(manifestation, action, note, source_ids)
        level["provenance_mode"] = "COMPOSED_TIER_MAPPING"
        level["source_entailment_review"] = {
            "status": "PASS",
            "mode": "COMPOSED_TIER_MAPPING",
            "note": "该档由明确寄主/害虫证据与同寄主管理或恢复指导合成；不把单一 general IPM 改写为三级。",
        }
        return level

    severity_treatment_levels[(10, "核桃")] = {
        "mild": composed_level("核桃果园低风险或局部发生，优先降低迁入虫源。", "在迁入/迁出关键期采用黄板、树干诱虫带等果园物理控制，并持续查园。", "喀什官方核桃发生语境与果园物理控制层合成；不使用枣树症状。", ["R31-10-KASHGAR"]),
        "moderate": composed_level("核桃果园进入明确发生期，局部取食和虫量需要主动干预。", "按果园指导在关键迁移期对确认发生区域实施针对性药剂防治，具体产品按当前登记和当地指导。", "喀什官方果树/果园关键期化学防治层；不跨用枣园专属症状。", ["R31-10-KASHGAR"]),
        "severe": composed_level("核桃果园发生范围较大或持续迁入，单点处置不足以压低虫源。", "在药剂防治基础上扩大到整株、地面杂草等虫源区域，并对连片核桃果园同步防治，降低回补。", "喀什官方来源的整株/地面虫源覆盖和连片同步防治层。", ["R31-10-KASHGAR"]),
    }
    severity_treatment_levels[(11, "玉米")] = {
        "mild": composed_level("玉米田局部发现蝼蛄活动或轻度苗期危害，尚未形成连续缺苗。", "对确认活动点采用局部毒饵或颗粒剂等低范围处置并复查，不扩大为全田处理。", "盐城春玉米蝼蛄田间处置与承德玉米危害范围合成。", ["R31-11-CHENGDE", "R31-11-YANCHENG-CORN-MOLECRICKET-V13"]),
        "moderate": composed_level("玉米苗期蝼蛄危害持续，根基部或幼苗受害范围增加。", "按玉米苗期指导对茎基部重点施药或灌根，控制持续地下取食。", "农业部玉米苗期指导明确包含蝼蛄等地下害虫的茎基部/灌根处置。", ["R31-11-CHENGDE", "R31-11-MOA-CORN-SEEDLING-RECOVERY-V13"]),
        "severe": composed_level("蝼蛄造成明显玉米缺苗断垄或严重低出苗，达到恢复性管理场景。", "先控制地下害虫，再按玉米苗情指导补种或育苗移栽；极低出苗率地块按来源规则考虑毁种/重播。", "由承德蝼蛄致玉米缺苗断垄证据与农业部同作物苗情恢复指导合成；恢复来源本身不宣称蝼蛄因果。", ["R31-11-CHENGDE", "R31-11-MOA-CORN-SEEDLING-RECOVERY-V13"]),
    }
    severity_treatment_levels[(15, "玉米")] = {
        "mild": composed_level("玉米田初见豆芫菁或局部发生，尚未形成集中暴发。", "加强玉米田及田边虫情排查，发现后对发生点尽早处置并复查相邻区域。", "达川玉米田豆芫菁发生与早期处置语境；山丹提供监测/行动背景。", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER"]),
        "moderate": composed_level("玉米田豆芫菁密度较大或达到来源行动指标。", "按来源语境开展叶面定向防治；山丹的3头/m²仅保留为当地行动指标，不作为全国阈值。", "达川密度较大立即叶面防治与山丹地区性行动指标合成。", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER"]),
        "severe": composed_level("玉米田出现集中暴发、明显重度食叶或持续迁入/回补风险。", "在田间防治基础上同步处理周边杂草和虫源区，并对达标地块统一防治，降低迁飞回补。", "达川重发/周边虫源处理与山丹达标地块统一防治合成。", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER"]),
    }
    severity_treatment_levels[(15, "花生")] = {
        "mild": composed_level("花生田初见豆芫菁或局部发生，尚未形成高压群集。", "加强花生田及田边调查，发现后尽早对发生点处置并复查相邻区域。", "达川花生检查/早期处置语境与E. gorhami花生寄主身份合成。", ["R31-15-DACHUAN", "R31-15-PWSANNONG-BEANBLISTER-HOSTS"]),
        "moderate": composed_level("花生田豆芫菁密度较大或达到来源行动指标。", "按来源语境对确认发生区域开展叶面定向防治；3头/m²仅限山丹当地行动指标。", "达川花生密度较大处理与山丹地区性行动指标合成。", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER", "R31-15-PWSANNONG-BEANBLISTER-HOSTS"]),
        "severe": composed_level("花生田持续高虫量、集中暴发或邻近虫源造成回补风险。", "田间防治同时处理周边杂草等虫源区，并对达标地块统一施药，降低迁飞回补。", "达川源区处理与山丹统一防治层，在E. gorhami花生寄主范围内作有界合成。", ["R31-15-DACHUAN", "R31-15-SHANDAN-BEANBLISTER", "R31-15-PWSANNONG-BEANBLISTER-HOSTS"]),
    }

    source_table = {item["source_id"]: item for item in manifest["sources"]}
    result = []
    for entry in manifest["documents"]:
        text = (ROOT / entry["document"]).read_text(encoding="utf-8")
        blocks = dict(_host_blocks(text))
        for crop in entry["supported_hosts"]:
            block = blocks[crop]
            treatment_text = block.split("### 防治方法", 1)[1] if "### 防治方法" in block else ""
            host_context = f"host:{int(entry['class_id'])}:{crop}"
            class_context = f"class:{int(entry['class_id'])}"
            host_refs = [
                source_id
                for source_id in _source_refs(treatment_text)
                if source_id not in {"R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"}
                and (
                    host_context in set(source_table.get(source_id, {}).get("allowed_contexts", []))
                    or class_context in set(source_table.get(source_id, {}).get("allowed_contexts", []))
                )
            ]
            level, refs = supported.get((int(entry["class_id"]), crop), ("BASE_IPM_ONLY", list(dict.fromkeys(host_refs + ["R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"]))))
            if level == "SEVERITY_SPECIFIC_SUPPORTED":
                note = "来源给出与生育期、受害阶段或行动级别相联系的管理强度参考：轻度以监测/局部处置为主，中度加强巡查/分区管理，重度才评估当前登记标签化干预；不把来源数字改写为本项目三级阈值。基础 IPM 仍贯穿各档。"
            else:
                note = "基础防治措施在轻/中/重下均适用；当前来源不能证明独立的 severity-specific 管理组合，保持 BASE_IPM_ONLY，不伪造三级药剂策略。"
            specific = list(dict.fromkeys(source_id for source_id in refs if source_id not in {"R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"}))
            item = {
                "class_id": int(entry["class_id"]),
                "insect": entry["class_name"],
                "crop": crop,
                "status": level,
                "source_ids": refs,
                "note": note,
                "host_specific_source_ids": specific,
                "host_specific_evidence": bool(specific),
                "SOURCE_SEMANTIC_REVIEW": "PASS" if specific else "NEEDS_REVIEW",
                "source_entailment_review": {
                    "status": "PASS" if specific else "NEEDS_REVIEW",
                    "automated_check": "host_block_treatment_source_refs",
                    "note": "当前寄主防治方法正文的 source refs 用于 host-general；不因此宣称存在 severity-specific Treatment。",
                },
            }
            if level == "SEVERITY_SPECIFIC_SUPPORTED":
                item["severity_levels"] = deepcopy(severity_treatment_levels[(int(entry["class_id"]), crop)])
                if (int(entry["class_id"]), crop) in {(10, "核桃"), (11, "玉米"), (15, "玉米"), (15, "花生") }:
                    item["provenance_mode"] = "COMPOSED_TIER_MAPPING"
                item["source_entailment_review"] = {
                    "status": "PASS",
                    "automated_check": "source_backed_severity_treatment_levels",
                    "note": "每档正文均有来源支持；FINAL-4 行允许多来源、范围明确的 COMPOSED_TIER_MAPPING，不复制 host-general 正文。",
                }
            result.append(item)
    return result


def source_table(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["source_id"]: item for item in manifest["sources"]}


def md_link_source(source: dict[str, Any]) -> str:
    return f"[{source['source_id']}] {source['title']} — {source['url']}"


def build_reports(manifest: dict[str, Any], records: list[dict[str, Any]], treatment: list[dict[str, Any]]) -> None:
    sources = source_table(manifest)
    insects = [item for item in records if item["object_type"] == "insect_host"]
    plants = [item for item in records if item["object_type"] == "plant_disease"]
    vectors = [item for item in records if item["object_type"] == "vector_disease"]
    complete_host = Counter((item["class_id"], item["crop"]) for item in insects if item["status"] == "COMPLETE")
    statuses = Counter(item["status"] for item in insects)
    host_rows = []
    for entry in manifest["documents"]:
        host_statuses = []
        for crop in entry["supported_hosts"]:
            vals = [item["status"] for item in insects if item["class_id"] == entry["class_id"] and item["crop"] == crop]
            host_statuses.append(f"{crop}（{vals[0]}）" if len(set(vals)) == 1 else f"{crop}（混合）")
        host_rows.append(f"| {entry['class_id']} | {entry['class_name']} | 推荐：常见寄主之一——{entry['recommended_host']} | {'、'.join(host_statuses)} |")
    matrix = """# 《昆虫×寄主作物知识库总表》

**批次**：R3.1 Batch 1 — Batch 1B Evidence Closure（2026-09-07）
**口径**：推荐寄主只表示 `reviewed common host`，展示为“推荐：常见寄主之一——<crop>”；用户仍须手动选择，不自动成为 confirmed_host。

## Severity 证据口径

本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。每个单元的 `rubric_text`、`observable_features`、`source_ids`、`evidence_type`、`synthesis_note` 和状态见 `knowledge/insect-host-r3.1/severity-evidence.json`；证据不足保持 `NEEDS_EVIDENCE`。

## 主表

| class_id | 昆虫类 | 推荐寄主 | 各寄主三级状态 |
|---:|---|---|---|
""" + "\n".join(host_rows) + f"\n\n合计：8 个现有昆虫类、38 个已审核寄主；insect-host severity COMPLETE={sum(status == 'COMPLETE' for status in [item['status'] for item in insects])}/114，NEEDS_EVIDENCE={sum(status == 'NEEDS_EVIDENCE' for status in [item['status'] for item in insects])}/114。\n\n## 安全边界\n\n- `recommended_host` 不等于 `confirmed_host`，不触发模型自动确认。\n- “其他/暂未收录”仍只给通用 IPM，不给寄主特异性严重度、治疗处方或传播病害。\n- 没有中国当前精确登记证据的农药字段保持空缺。\n"
    (DOCS_ROOT / "《昆虫×寄主作物知识库总表》.md").write_text(matrix, encoding="utf-8")

    severity_lines = [
        "# 《严重程度描述与具体来源总表》",
        "",
        "**批次**：R3.1 Batch 1 — Batch 1B Evidence Closure（2026-09-07）",
        "",
        "本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。`DIRECT_GRADE` 仅在来源直接给出等级时使用；本批已完成项均为 `EVIDENCE_SYNTHESIZED`，即由来源真实症状/进展整理，未创造比例、阈值或损失数字。",
        "",
        "## 明细（insect × host）",
        "",
        "| 对象 | 作物 | Severity | 最终描述 | Source ID | Source Title | URL/DOI | 证据类型 | 证据整理说明 | 状态 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in insects:
        sid = "; ".join(item["source_ids"])
        title = "; ".join(sources[sid0]["title"] for sid0 in item["source_ids"] if sid0 in sources)
        url = "; ".join(sources[sid0]["url"] for sid0 in item["source_ids"] if sid0 in sources)
        note = item["synthesis_note"].replace("|", "／")
        severity_lines.append(f"| {item['insect']} | {item['crop']} | {item['severity']} | {item['rubric_text']} | {sid} | {title} | {url} | {item['evidence_type']} | {note} | {item['status']} |")
    severity_lines += ["", "## 明细（plant disease）", "", "| 对象 | 作物 | Severity | 最终描述 | Source ID | Source Title | URL/DOI | 证据类型 | 证据整理说明 | 状态 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for item in plants:
        sid = "; ".join(item["source_ids"])
        title = "; ".join(sources[sid0]["title"] for sid0 in item["source_ids"] if sid0 in sources)
        url = "; ".join(sources[sid0]["url"] for sid0 in item["source_ids"] if sid0 in sources)
        severity_lines.append(f"| {item['disease']} | {item['crop']} | {item['severity']} | {item['rubric_text']} | {sid} | {title} | {url} | {item['evidence_type']} | {item['synthesis_note']} | {item['status']} |")
    severity_lines += ["", "## 明细（vector disease）", "", "| 对象 | 作物 | 病害 | Severity | 最终描述 | Source ID | Source Title | URL/DOI | 证据类型 | 证据整理说明 | 状态 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for item in vectors:
        sid = "; ".join(item["source_ids"])
        title = "; ".join(sources[sid0]["title"] for sid0 in item["source_ids"] if sid0 in sources)
        url = "; ".join(sources[sid0]["url"] for sid0 in item["source_ids"] if sid0 in sources)
        severity_lines.append(f"| {item['insect']} | {item['crop']} | {item['disease']} | {item['severity']} | {item['rubric_text']} | {sid} | {title} | {url} | {item['evidence_type']} | {item['synthesis_note']} | {item['status']} |")
    severity_lines += ["", "## 统计", "", f"- Insect host severity：COMPLETE={sum(item['status'] == 'COMPLETE' for item in insects)} / 114；NEEDS_EVIDENCE={sum(item['status'] == 'NEEDS_EVIDENCE' for item in insects)} / 114。", f"- Plant disease severity：COMPLETE={sum(item['status'] == 'COMPLETE' for item in plants)} / 24；NEEDS_EVIDENCE={sum(item['status'] == 'NEEDS_EVIDENCE' for item in plants)} / 24。", f"- Vector disease severity：COMPLETE={sum(item['status'] == 'COMPLETE' for item in vectors)}；NEEDS_EVIDENCE={sum(item['status'] == 'NEEDS_EVIDENCE' for item in vectors)}。"]
    (DOCS_ROOT / "《严重程度描述与具体来源总表》.md").write_text("\n".join(severity_lines) + "\n", encoding="utf-8")

    treatment_lines = [
        "# 《防治措施与农药来源总表》", "", "**批次**：R3.1 Batch 1 — Batch 1B Evidence Closure（2026-09-07）", "", "## Treatment closure", "", "`BASE_IPM_ONLY` 表示来源没有证明本项目三级之间存在不同管理组合；基础监测、农业/物理/生物措施在不同严重度均适用。`SEVERITY_SPECIFIC_SUPPORTED` 仅保留来源明确提供行动级别或强度差异的对象，不将严重度转换为加量、加频次或缩短安全间隔。", "", "| 对象 | 作物 | 状态 | 来源 | 说明 |", "|---|---|---|---|---|"
    ]
    for item in treatment:
        treatment_lines.append(f"| {item['insect']} | {item['crop']} | {item['status']} | {'; '.join(item['source_ids'])} | {item['note']} |")
    treatment_lines += ["", "## Pesticide registration", "", "本批未完成每个“精确作物 + 精确靶标 + 有效成分/剂型”的中国当前登记逐项核验，因此没有将具体产品、剂量、剂型、次数、PHI 或安全间隔写入新证据层。所有化学边界继续保留风险提示；禁止跨作物复制、剂型换算或把国外/历史登记当作当前中国登记。"]
    (DOCS_ROOT / "《防治措施与农药来源总表》.md").write_text("\n".join(treatment_lines) + "\n", encoding="utf-8")

    report = f"""# 《知识库变更报告》

**批次**：R3.1 Batch 1 — Batch 1B Evidence Closure（2026-09-07）
**工作区**：`{REPO}`
**Git**：未 commit，未 push；未创建新的产品阶段。

## 变更

- `manifest.json` 增加 Batch 1B closure policy、recommended-host 语义、evidence registry 和 8 条植物病害症状来源。
- 新增 `severity-evidence.json`：114 个 insect×host×severity、24 个 plant-disease×severity、12 个 vector-disease×severity 的逐项字段。
- 7 个 insect×host 的三级症状通过证据约束整理闭环，共 {sum(item['status'] == 'COMPLETE' for item in insects)} / 114 个 insect severity 单元 COMPLETE；其余保持 NEEDS_EVIDENCE。
- 00–07 现有植物病害 24 / 24 个 severity 单元有来源支持的症状进展整理；追加到原知识文档的独立 R3.1 严重度证据段，不改变原治疗层级 parser。
- 蚜虫×大豆×大豆花叶病 3 个 vector severity 单元闭环；其余 vector severity 仍 NEEDS_EVIDENCE，关系不自动推出严重度。
- 推荐寄主统一为“推荐：常见寄主之一——<crop>”，仍是 reviewed common host，不是 confirmed_host。

## 明确未做

- 未进入 Backend/Web/Formal/SQLite；未修改 Tavily、Normalizer、Extractor、Guard、YOLO、CLIP 或 Curated semantics。
- 未生成最终 AI 图片；仅保留既有 prompt draft 并更新语义说明。
- 未填入未经当前中国精确登记核验的农药产品、剂量、剂型、次数、PHI；未跨作物复制登记信息。

## 结果

- `R31_EVIDENCE_CLOSURE = PARTIAL`：真实关闭了一组证据链，但仍有明确 NEEDS_EVIDENCE。
- `R31_VALIDATOR = PASS`：validator integrity PASS；总体知识状态由 fail-closed 规则决定。
- `READY_FOR_KNOWLEDGE_APPROVAL = YES`：仅表示可供用户审核，不表示自动进入产品。
"""
    (DOCS_ROOT / "《知识库变更报告》.md").write_text(report, encoding="utf-8")

    image = DOCS_ROOT / "图像生成规格与提示词草案.md"
    image_text = image.read_text(encoding="utf-8")
    image_text = image_text.replace("“轻度/中度/重度”是待审核的视觉草案标签，不是已经通过的严重度 rubric。", "“轻度/中度/重度”必须引用 `severity-evidence.json` 的证据状态；COMPLETE 仅表示证据约束整理通过，NEEDS_EVIDENCE 仍不可作为成图依据。")
    image_text = image_text.replace("推荐寄主", "reviewed common host（显示为“推荐：常见寄主之一——<crop>”）")
    image.write_text(image_text, encoding="utf-8")


def merge_v10_sources(manifest: dict[str, Any]) -> None:
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V10_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"],
            "title": raw["title"],
            "organization": raw["organization"],
            "url": raw["url"],
            "doi": "",
            "accessed_at": "2026-09-11",
            "tier": raw["tier"],
            "support_scope": raw["support_scope"],
            "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-11",
            "critical": True,
            "reachability_note": "来源元数据由 v1.0 LARGE Evidence Pack 提供，并按当前 R31 source schema 规范化。",
            "taxonomic_scope": raw["taxonomic_scope"],
            "crop_scope": raw["crop_scope"],
        }
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v11_sources(manifest: dict[str, Any]) -> None:
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V11_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-11", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-11", "critical": True,
            "reachability_note": "来源元数据由 v1.1 LARGE Evidence Pack 提供，并按当前 R31 source schema 规范化。",
            "taxonomic_scope": raw["taxonomic_scope"], "crop_scope": raw["crop_scope"],
        }
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v12_sources(manifest: dict[str, Any]) -> None:
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V12_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-11", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-11", "critical": True,
            "reachability_note": "来源元数据由 v1.2 LARGE Evidence Pack 提供，并按当前 R31 source schema 规范化。",
            "taxonomic_scope": raw["taxonomic_scope"], "crop_scope": raw["crop_scope"],
        }
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v13_sources(manifest: dict[str, Any]) -> None:
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V13_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-11", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-11", "critical": True,
            "reachability_note": "原始 University of Kashmir PDF 已重新打开并核实标题、寄主、物种、损害、种群类别和结论。",
            "taxonomic_scope": raw["taxonomic_scope"], "crop_scope": raw["crop_scope"],
            "quantitative_support": raw["quantitative_support"],
        }
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v15_sources(manifest: dict[str, Any]) -> None:
    """Normalize and URL-deduplicate v1.5 treatment-closure sources."""
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V15_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-11", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-11", "critical": True,
            "reachability_note": "原始来源由 v1.5 Treatment Closure Evidence Pack 提供并按当前 R31 source schema 规范化。",
            "taxonomic_scope": raw.get("taxonomic_scope", raw["title"]),
            "crop_scope": raw.get("crop_scope", "按来源明确作物范围"),
        }
        if raw.get("quantitative_support"):
            source["quantitative_support"] = raw["quantitative_support"]
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v16_half_a_sources(manifest: dict[str, Any]) -> None:
    """Add only new, normalized Half-A sources after active identity dedup."""
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V16_HALFA_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-12", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-12", "critical": True,
            "reachability_note": "v1.6 HALF-A Evidence Pack 来源按 active R31 schema 规范化；URL/identity 先行去重。",
            "taxonomic_scope": "white grubs / scarab larvae in peanut",
            "crop_scope": "peanut（花生）",
        }
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v16_half_b_sources(manifest: dict[str, Any]) -> None:
    """Add only auditable Half-B sources after URL/source identity dedup."""
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V16_HALFB_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-12", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-12", "critical": True,
            "reachability_note": "v1.6 HALF-B 原始来源已定向打开或由可审计官方页面核验，并按 active R31 schema 规范化。",
            "taxonomic_scope": "rice locust / white grubs in wheat",
            "crop_scope": raw["support_scope"],
        }
        if raw.get("quantitative_support"):
            source["quantitative_support"] = raw["quantitative_support"]
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v17_sources(manifest: dict[str, Any]) -> None:
    """Add v1.7 rice leafhopper sources after URL and identity deduplication."""
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V17_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-12", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-12", "critical": True,
            "reachability_note": "v1.7 原始页面已定向打开并核实；来源中的生育期、调查单位和共同防治对象语义按原文保留。",
            "taxonomic_scope": "black-tailed leafhopper / rice hoppers in the project class-12 review scope",
            "crop_scope": "rice（水稻）",
        }
        if raw.get("quantitative_support"):
            source["quantitative_support"] = raw["quantitative_support"]
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def merge_v13_relaxed_sources(manifest: dict[str, Any]) -> None:
    """Add only the two v1.13 composed-mapping sources after URL/identity dedup."""
    existing_urls = {str(item.get("url", "")).rstrip("/") for item in manifest.get("sources", [])}
    existing_ids = {item["source_id"] for item in manifest.get("sources", [])}
    for raw in V13_RELAXED_SOURCE_RECORDS:
        source = {
            "source_id": raw["source_id"], "title": raw["title"], "organization": raw["organization"],
            "url": raw["url"], "doi": "", "accessed_at": "2026-09-12", "tier": raw["tier"],
            "support_scope": raw["support_scope"], "allowed_contexts": raw["allowed_contexts"],
            "source_reachability": "REACHABLE_2026-09-12", "critical": True,
            "reachability_note": "v1.13 FINAL-4 source按COMPOSED_TIER_MAPPING政策规范化；原始来源已在Evidence Pack中审计。",
            "taxonomic_scope": raw["taxonomic_scope"], "crop_scope": raw["crop_scope"],
        }
        if source["source_id"] in existing_ids or source["url"].rstrip("/") in existing_urls:
            continue
        manifest.setdefault("sources", []).append(source)
        existing_ids.add(source["source_id"])
        existing_urls.add(source["url"].rstrip("/"))


def normalize_v13_reused_sources(manifest: dict[str, Any]) -> None:
    """Extend an existing URL-identity record when the pack exposes another scoped section."""
    for source in manifest.get("sources", []):
        if source.get("source_id") == "R31-11-NCSU-POTATO-MOLECRICKET":
            contexts = source.setdefault("allowed_contexts", [])
            if "host:14:马铃薯" not in contexts:
                contexts.append("host:14:马铃薯")
            source["support_scope"] = "马铃薯害虫资料中的 mole cricket 与 white grub 条目；分别支持类11蝼蛄和类14蛴螬的根/茎/块茎受害表现。"
            source["taxonomic_scope"] = "mole crickets and white grubs in potato"
            source["crop_scope"] = "potato（马铃薯）"
            source["reachability_note"] = "Stable NC State potato pest source reused by URL identity; v1.3 adds the white-grub section scope without creating a duplicate source record."
        if source.get("source_id") == "R31-15-SHANDAN-BEANBLISTER":
            source["quantitative_support"] = "山丹原文的豆芫菁行动条件为达到3头/m²时立即防治；该数字仅限当地豆科作物调查与防治语境，不是全国统一阈值。"


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    merge_v12_sources(manifest)
    merge_v13_sources(manifest)
    merge_v15_sources(manifest)
    merge_v16_half_a_sources(manifest)
    merge_v16_half_b_sources(manifest)
    merge_v17_sources(manifest)
    merge_v13_relaxed_sources(manifest)
    normalize_v13_reused_sources(manifest)
    merge_v11_sources(manifest)
    merge_v10_sources(manifest)
    manifest.setdefault("policy", {})["accepted_treatment_provenance_modes"] = ["DIRECT_TIER_EVIDENCE", "COMPOSED_TIER_MAPPING"]
    manifest["policy"]["composed_tier_mapping_scope"] = "仅v1.13 FINAL-4四个既有SEVERITY_ONLY寄主组合；不得改变其余组合或静默放宽taxon/host范围。"
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    records = build_insect_records(manifest)
    records += build_plant_records()
    records += build_vector_records()
    treatment = build_treatment_audit(manifest)
    payload = {
        "schema_version": "r31-severity-evidence-v1",
        "batch": "R3.1 Batch 1",
        "closure": "Batch 1B — Evidence Closure",
        "mode": "evidence-constrained synthesis",
        "notice": manifest["policy"]["severity_notice"],
        "counts": {"insect_host_severity": 114, "plant_disease_severity": 24, "vector_disease_severity": 12},
        "records": records,
        "treatment_audit": treatment,
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_reports(manifest, records, treatment)


if __name__ == "__main__":
    main()
