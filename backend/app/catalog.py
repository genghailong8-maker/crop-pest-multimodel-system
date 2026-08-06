from __future__ import annotations


CLASS_CATALOG = [
    {"id": 0, "name_zh": "玉米叶枯病", "name_en": "Corn leaf blight", "crop": "玉米", "type": "病害"},
    {"id": 1, "name_zh": "番茄斑枯病", "name_en": "Tomato Septoria leaf spot", "crop": "番茄", "type": "病害"},
    {"id": 2, "name_zh": "南瓜白粉病", "name_en": "Squash powdery mildew", "crop": "南瓜", "type": "病害"},
    {"id": 3, "name_zh": "马铃薯早疫病", "name_en": "Potato early blight", "crop": "马铃薯", "type": "病害"},
    {"id": 4, "name_zh": "玉米锈病", "name_en": "Corn rust", "crop": "玉米", "type": "病害"},
    {"id": 5, "name_zh": "番茄细菌性斑点病", "name_en": "Tomato bacterial spot", "crop": "番茄", "type": "病害"},
    {"id": 6, "name_zh": "番茄晚疫病", "name_en": "Tomato late blight", "crop": "番茄", "type": "病害"},
    {"id": 7, "name_zh": "马铃薯晚疫病", "name_en": "Potato late blight", "crop": "马铃薯", "type": "病害"},
    {"id": 8, "name_zh": "芫菁", "name_en": "Blister beetle", "crop": "苜蓿及豆科作物", "type": "害虫"},
    {"id": 9, "name_zh": "蚜虫", "name_en": "Aphids", "crop": "玉米", "type": "害虫"},
    {"id": 10, "name_zh": "盲蝽科", "name_en": "Mirid bugs (Miridae)", "crop": "葡萄", "type": "害虫"},
    {"id": 11, "name_zh": "蝼蛄", "name_en": "Mole cricket", "crop": "玉米", "type": "害虫"},
    {"id": 12, "name_zh": "叶蝉科", "name_en": "Leafhoppers (Cicadellidae)", "crop": "芒果", "type": "害虫"},
    {"id": 13, "name_zh": "蝗总科", "name_en": "Grasshoppers (Locustoidea)", "crop": "苜蓿", "type": "害虫"},
    {"id": 14, "name_zh": "蛴螬", "name_en": "White grub", "crop": "玉米", "type": "害虫"},
    {"id": 15, "name_zh": "豆芫菁", "name_en": "Legume blister beetle", "crop": "苜蓿及豆科作物", "type": "害虫"},
]

CLASS_BY_ID = {item["id"]: item for item in CLASS_CATALOG}

