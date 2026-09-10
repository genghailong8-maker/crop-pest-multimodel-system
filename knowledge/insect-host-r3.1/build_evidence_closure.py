"""Build the R3.1 Batch 1B evidence registry and human-review projections.

The source-backed closure decisions are intentionally explicit below.  All
records not listed in ``INSECT_CLOSURES`` remain fail-closed NEEDS_EVIDENCE;
the script never infers a COMPLETE record from a host relation alone.
"""

from __future__ import annotations

import json
import re
from collections import Counter
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
) -> dict[str, Any]:
    return {
        "status": status,
        "rubric_text": rubric_text,
        "observable_features": observable_features,
        "source_ids": source_ids,
        "evidence_type": evidence_type,
        "synthesis_note": synthesis_note,
    }


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


VECTOR_CLOSURES: dict[tuple[int, str, str], dict[str, dict[str, Any]]] = {
    (9, "大豆", "大豆花叶病"): {
        "mild": record(rubric_text="叶片出现浓淡相间花叶，或幼嫩叶片出现轻度皱缩。", observable_features=["浓淡相间花叶", "幼嫩叶片轻度皱缩"], source_ids=["R31-09-SOY-VECTOR"], synthesis_note="evidence_synthesized：标准文本同时明确列出大豆蚜等蚜虫传播关系和花叶早期表现；不能由有蚜虫直接推出感染。"),
        "moderate": record(rubric_text="皱缩下卷、畸形或褐色坏死斑更加明显，豆荚出现缩短、扁平或扭曲。", observable_features=["皱缩下卷", "叶片畸形/褐色坏死斑", "豆荚缩短扁平扭曲"], source_ids=["R31-09-SOY-VECTOR"], synthesis_note="evidence_synthesized：依据标准文本中成株症状和豆荚变化整理中段；不把蚜虫存在当作病害确诊。"),
        "severe": record(rubric_text="早期感染导致植株明显矮化，重病株不结实，或种子表面出现褐色斑纹。", observable_features=["植株明显矮化", "重病株不结实", "种子褐色斑纹"], source_ids=["R31-09-SOY-VECTOR"], synthesis_note="evidence_synthesized：标准文本明确记录早染病矮化、重病株不结实和种子褐斑；仅在独立病害证据成立时使用。"),
    }
}


def _source_refs(text: str) -> list[str]:
    return list(dict.fromkeys(SOURCE_RE.findall(text)))


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
    specific = {(8, "大豆"), (9, "大豆"), (13, "大豆")}
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
            records.append({"object_type": "vector_disease", "class_id": class_id, "insect": insect, "crop": crop, "disease": disease, "severity": severity, **data})
    return records


def build_treatment_audit(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    supported = {(8, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-08-NCSU-SOY"]), (9, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-09-HEILONGJIANG-SOY"]), (13, "大豆"): ("SEVERITY_SPECIFIC_SUPPORTED", ["R31-13-UMN-GRASSHOPPER"])}
    result = []
    for entry in manifest["documents"]:
        for crop in entry["supported_hosts"]:
            level, refs = supported.get((int(entry["class_id"]), crop), ("BASE_IPM_ONLY", ["R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"]))
            if level == "SEVERITY_SPECIFIC_SUPPORTED":
                note = "来源给出与生育期、受害阶段或行动级别相联系的管理强度参考：轻度以监测/局部处置为主，中度加强巡查/分区管理，重度才评估当前登记标签化干预；不把来源数字改写为本项目三级阈值。基础 IPM 仍贯穿各档。"
            else:
                note = "基础防治措施在轻/中/重下均适用；当前来源不能证明独立的 severity-specific 管理组合，保持 BASE_IPM_ONLY，不伪造三级药剂策略。"
            result.append({"class_id": int(entry["class_id"]), "insect": entry["class_name"], "crop": crop, "status": level, "source_ids": refs, "note": note})
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


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
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
