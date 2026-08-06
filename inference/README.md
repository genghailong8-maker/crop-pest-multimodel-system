# GPU 推理服务

该服务只负责加载服务器上的检测权重并返回归一化检测框。病例存储、图片质检、类别中文映射、诊断摘要和人工复核仍由 `backend/` 负责。

服务器端默认加载：

```text
runs/detect/official-baseline-yolo26n-e120-b64/weights/best.pt
```

部署与启动：

```bash
cd /root/autodl-tmp/crop-pest-system
python -m pip install -r inference/requirements.txt
chmod +x inference/run_server.sh
inference/run_server.sh start
```

服务默认仅监听 `127.0.0.1:8870`。本机运行 `inference/open_tunnel.ps1` 后，把后端配置为：

```text
CROP_DETECTOR_ENDPOINT=http://127.0.0.1:8870/v1/detect
```

如设置 `CROP_INFERENCE_API_KEY`，本机后端还需设置同值的 `CROP_DETECTOR_API_KEY`。
