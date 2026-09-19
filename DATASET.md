# 数据集说明

本仓库只提交数据集的目录约定、类别清单、去重划分和审计结果，不提交完整训练图片与标注数据。这样可以让 Work 了解训练代码需要什么，同时避免把大体积或受来源约束的原始数据放进普通 Git 仓库。

## 当前官方数据口径

| 项目 | 数量 |
|---|---:|
| 原始图片 | 4,164 |
| 清洗后图片 | 4,154 |
| 隔离的冲突/重复图片 | 10 |
| 训练划分 | 3,321 |
| 验证划分 | 833 |
| 类别 | 16 |
| 固定随机种子 | 20260729 |

清洗、重复组和隔离记录见 `data/official/splits/split-report.json`、`data/official/splits/quarantine-conflicting-labels.txt` 和 `artifacts/dataset-audit/`。

## 目录结构

克隆仓库后，若需要实际训练，应在 `data/official/` 下按以下布局提供外部数据包：

```text
data/official/
├── dataset.yaml
├── images/
│   └── all/                 # 官方图片文件
├── labels/
│   └── all/                 # 与图片对应的 YOLO 标注文件
└── splits/
    ├── train-portable.txt   # 仓库内可移植的相对路径划分
    ├── val-portable.txt
    ├── train.txt            # 历史生成文件，保留原始绝对路径记录
    ├── val.txt
    └── quarantine-*.txt
```

`data/official/dataset.yaml` 已使用仓库相对路径，并默认引用 `train-portable.txt` 与 `val-portable.txt`。两份 portable 清单分别包含 3,321 和 833 条 `images/all/...` 相对路径；原始 `train.txt` 和 `val.txt` 不改写，以保留历史审计记录。

## 16 个类别

| class_id | 类别 | 清洗后总数 | train | val |
|---:|---|---:|---:|---:|
| 0 | 玉米叶枯病 | 163 | 130 | 33 |
| 1 | 番茄斑枯病 | 126 | 101 | 25 |
| 2 | 南瓜白粉病 | 111 | 89 | 22 |
| 3 | 马铃薯早疫病 | 94 | 75 | 19 |
| 4 | 玉米锈病 | 99 | 79 | 20 |
| 5 | 番茄细菌性斑点病 | 92 | 74 | 18 |
| 6 | 番茄晚疫病 | 94 | 75 | 19 |
| 7 | 马铃薯晚疫病 | 86 | 69 | 17 |
| 8 | 芫菁 | 425 | 340 | 85 |
| 9 | 蚜虫 | 425 | 339 | 86 |
| 10 | 盲蝽科 | 425 | 339 | 86 |
| 11 | 蝼蛄 | 425 | 340 | 85 |
| 12 | 叶蝉科 | 427 | 342 | 85 |
| 13 | 蝗总科 | 425 | 340 | 85 |
| 14 | 蛴螬 | 371 | 297 | 74 |
| 15 | 豆芫菁 | 370 | 293 | 77 |

## 获取与运行

完整数据包不在本仓库中。训练服务器准备流程见 `training/server/README.md` 和 `training/server/prepare_data.sh`；训练入口见 `training/train_detector.py`。Work 做前后端结构分析、后端测试和前端构建时不需要下载完整数据集或模型权重。

不要把个人电脑路径、服务器挂载路径、上传病例图片或运行时 SQLite 放入 Git。外部数据准备完成后，应先执行数据审计，再开始正式训练。
