"""Versioned runtime identity for legacy and official competition taxonomies.

The legacy catalog remains the default for backwards compatibility.  Candidate
deployments opt into the official ten-class taxonomy through configuration;
numeric ids are never used without the accompanying taxonomy version.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .catalog import CLASS_CATALOG as LEGACY_CLASS_CATALOG


OFFICIAL_TAXONOMY_VERSION = "official_10class_20260917"
LEGACY_TAXONOMY_VERSION = "legacy_16class"
OFFICIAL_MODEL_SHA256 = "e233fc1971f88288fabed8d37af32047f6d1cb643213d9de0ee61385666479ba"

_OFFICIAL_ROWS = (
    (0, "水稻稻瘟病", "Rice blast", "rice_blast", "病害"),
    (1, "水稻褐斑病", "Rice brown spot", "rice_brown_spot", "病害"),
    (2, "玉米大斑病", "Northern corn leaf blight", "northern_corn_leaf_blight", "病害"),
    (3, "水稻东格鲁病毒病", "Rice tungro", "rice_tungro", "病害"),
    (4, "玉米灰斑病", "Corn gray leaf spot", "corn_gray_leaf_spot", "病害"),
    (5, "芫菁", "Blister beetle", "blister_beetle", "害虫"),
    (6, "蚜虫", "Aphid", "aphid", "害虫"),
    (7, "盲蝽科", "Miridae", "miridae", "害虫"),
    (8, "蝼蛄", "Mole cricket", "mole_cricket", "害虫"),
    (9, "蛴螬", "White grub", "white_grub", "害虫"),
)


def _official_item(row: tuple[int, str, str, str, str]) -> dict[str, Any]:
    class_id, name_zh, name_en, canonical_key, item_type = row
    return {
        "id": class_id,
        "class_id": class_id,
        "name_zh": name_zh,
        "name_en": name_en,
        "canonical_class_name": name_zh,
        "canonical_key": canonical_key,
        "type": item_type,
        "taxonomy_version": OFFICIAL_TAXONOMY_VERSION,
    }


OFFICIAL_CLASS_CATALOG = tuple(_official_item(row) for row in _OFFICIAL_ROWS)
OFFICIAL_CLASS_BY_ID = {item["id"]: item for item in OFFICIAL_CLASS_CATALOG}
OFFICIAL_CLASS_BY_KEY = {item["canonical_key"]: item for item in OFFICIAL_CLASS_CATALOG}


def legacy_catalog() -> list[dict[str, Any]]:
    result = deepcopy(list(LEGACY_CLASS_CATALOG))
    for item in result:
        item.setdefault("taxonomy_version", LEGACY_TAXONOMY_VERSION)
        item.setdefault("canonical_class_name", item.get("name_zh"))
        item.setdefault("canonical_key", f"legacy_class_{item.get('id')}")
    return result


def catalog_for_version(version: str | None) -> list[dict[str, Any]]:
    return deepcopy(list(OFFICIAL_CLASS_CATALOG if version == OFFICIAL_TAXONOMY_VERSION else legacy_catalog()))


def class_by_id(version: str | None, class_id: int) -> dict[str, Any] | None:
    catalog = OFFICIAL_CLASS_BY_ID if version == OFFICIAL_TAXONOMY_VERSION else {
        int(item["id"]): item for item in legacy_catalog()
    }
    item = catalog.get(int(class_id))
    return deepcopy(item) if item else None


def identity_from_item(item: Mapping[str, Any], *, version: str | None = None) -> dict[str, Any]:
    resolved_version = str(version or item.get("taxonomy_version") or LEGACY_TAXONOMY_VERSION)
    name = str(item.get("canonical_class_name") or item.get("name_zh") or item.get("class_name") or "")
    key = str(item.get("canonical_key") or item.get("stable_key") or f"legacy_class_{item.get('id', item.get('class_id'))}")
    return {
        "taxonomy_version": resolved_version,
        "class_id": int(item.get("class_id", item.get("id"))),
        "canonical_key": key.split("::", 1)[-1],
        "canonical_class_name": name,
        "class_name": name,
    }


def identity_for_detection(detection: Mapping[str, Any], version: str | None) -> dict[str, Any] | None:
    try:
        item = class_by_id(version, int(detection["class_id"]))
    except (KeyError, TypeError, ValueError):
        return None
    if item is None:
        return None
    return identity_from_item(item, version=version)


def official_item_for_key(canonical_key: str) -> dict[str, Any] | None:
    item = OFFICIAL_CLASS_BY_KEY.get(canonical_key.split("::", 1)[-1])
    return deepcopy(item) if item else None


def legacy_insect_id_for_key(canonical_key: str) -> int | None:
    return {
        "blister_beetle": 8,
        "aphid": 9,
        "miridae": 10,
        "mole_cricket": 11,
        "white_grub": 14,
    }.get(canonical_key.split("::", 1)[-1])


def is_official(version: str | None) -> bool:
    return version == OFFICIAL_TAXONOMY_VERSION

