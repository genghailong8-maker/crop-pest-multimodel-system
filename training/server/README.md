# 服务器训练流程

本目录用于 Linux + NVIDIA GPU 服务器。官方原始数据保持只读，训练划分和输出全部写入项目目录。

## 1. 服务器环境

先确认 `nvidia-smi` 正常，再根据服务器驱动选择 PyTorch 官方 CUDA wheel 地址。不要在不知道 GPU 与驱动版本时盲目安装 CUDA 组件。

```bash
cd /path/to/crop-pest-system
export PYTORCH_INDEX_URL="<与服务器驱动匹配的官方 PyTorch wheel 地址>"
bash training/server/bootstrap.sh
```

环境报告写入 `artifacts/server/environment.json`。若 PyTorch 看不到 CUDA，脚本会停止，避免误用 CPU 进行正式训练。

## 2. 数据准备

把完整官方数据包上传到服务器，然后创建只读软链接并重建相同的去重分组划分：

```bash
export OFFICIAL_DATASET_ROOT="/data/competition/official-package"
bash training/server/prepare_data.sh
```

此步骤不会修改官方数据。服务器将使用固定随机种子 `20260729`，并隔离已发现的冲突重复样本。

## 3. 先冒烟、后正式训练

```bash
bash training/server/run_train.sh smoke
bash training/server/run_train.sh full
```

可通过环境变量覆盖 `MODEL`、`BATCH`、`IMAGE_SIZE`、`WORKERS`、`DEVICE` 和 `EPOCHS`。例如：

```bash
BATCH=16 WORKERS=12 bash training/server/run_train.sh smoke
```

正式训练完成后，重点保留：

- `weights/best.pt`
- `competition-metrics.json`
- 混淆矩阵、PR 曲线和验证样例图
- `artifacts/server/environment.json`

这些文件将用于网页系统接入、比赛指标展示和复现实验。

## 4. 实时训练监控

`run_train.sh` 会自动启动仅监听服务器本机的只读监控服务。监控内容包括：

- 训练与验证框损失、分类损失和 L1/DFL 损失
- 精确率、召回率、mAP50、mAP50-95 和学习率
- 当前轮次、完成比例、耗时、预计剩余时间
- GPU 利用率、显存、温度和功耗

本机首次连接或服务器实例重启后，在 PowerShell 中执行：

```powershell
powershell -ExecutionPolicy Bypass -File training/server/open_monitor_tunnel.ps1
```

随后访问 `http://localhost:3000/training`。页面每 5 秒自动刷新，监控接口只通过 SSH 私有通道访问，不直接暴露到公网。
