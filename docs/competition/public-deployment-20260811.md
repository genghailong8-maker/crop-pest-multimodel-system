# Phase 9 公网部署历史方案（已取消）

> 2026-08-12 用户决定系统只在当前电脑运行。本文件中的公网、Sites、Cloudflare、域名、固定 HTTPS 隧道和跨电脑方案不再执行，也不再是 Phase 9 验收条件。

当前有效运行方式：

- 前端：`http://localhost:3000/`
- FastAPI：`http://127.0.0.1:8000/`
- SQLite、病例图片和报告：当前电脑长期保存
- detector 8870、Qwen3-VL 8890：仅通过绑定 `127.0.0.1` 的私有 SSH 隧道连接服务器 GPU
- `CROP_PUBLIC_MODE=false`：默认且唯一的交付配置

本机启动、停止和健康检查请以 `demo-runbook.md` 和 `inference/README.md` 为准。下列历史设计代码被保留但默认停用，避免删除已测试代码造成无关回归：Sites Worker、origin secret、公开同意、30 天过期、编辑令牌和公网限流。

<!-- 以下原公网方案仅作历史记录，不执行。 -->

## 已实现的架构

浏览器只访问 Sites 同源地址。Sites Worker 将 `/health` 和 `/api/*` 转发到当前主机的固定 HTTPS 地址，并在服务端注入 `X-Crop-Origin-Secret`；密钥不会进入浏览器。FastAPI、SQLite、图片、8870 detector 隧道和 8890 Qwen3-VL 隧道仍在当前主机，两个模型服务不直接暴露公网。

公网 Worker 已实现：管理页 404、主机未配置时 503、禁止缓存 API 响应、传递 Cloudflare 客户端 IP。`web/.openai/hosting.json` 继续保持 D1/R2 为 `null`。

## 需要用户人工准备

到固定公网地址阶段前，请准备：

1. 一个可用域名；可在任意正规注册商购买。
2. 一个 Cloudflare 账号，并把域名添加到该账号。
3. 按 Cloudflare 提示，把域名注册商处的 nameserver 改为 Cloudflare 分配的两个地址，等待状态变为 Active。
4. 在当前 Windows 主机安装 `cloudflared`，并在浏览器完成 `cloudflared tunnel login` 授权。
5. 选择一个后端子域名，例如 `api.example.com`；不要把 8870/8890 端口直接映射公网。

这些步骤完成后再继续创建固定 tunnel、DNS 路由和 Sites 发布。用户不应在聊天中发送 Cloudflare 密钥；只需在本机或 Sites 的 secret 管理中设置。

## 固定地址阶段的环境变量

FastAPI 主机：

```text
CROP_PUBLIC_MODE=true
CROP_PUBLIC_ORIGIN_SECRET=<随机长密钥>
CROP_ALLOWED_ORIGINS=https://<正式-sites-域名>
CROP_PUBLIC_RETENTION_DAYS=30
CROP_PUBLIC_UPLOADS_PER_HOUR=10
CROP_PUBLIC_ANALYSES_PER_HOUR=20
CROP_VLM_MAX_CONCURRENCY=2
```

Sites Worker：

```text
CROP_PUBLIC_MODE=true
CROP_API_ORIGIN=https://api.<你的域名>
CROP_ORIGIN_SECRET=<与后端相同的随机长密钥>
```

## 单机启动、检查与停止

模型与 8870/8890 隧道按 `inference/README.md` 启动。然后分别在两个 PowerShell 窗口运行：

```powershell
cd C:\Users\genghailong\Documents\编程大赛\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd C:\Users\genghailong\Documents\编程大赛\web
npm.cmd run dev
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8870/health
Invoke-RestMethod http://127.0.0.1:8890/v1/models
Invoke-WebRequest http://localhost:3000/
```

停止时在对应窗口按 `Ctrl+C`，再按 `inference/README.md` 关闭隧道和远程服务。不要用广域进程清理命令。

## 发布验收

- 正式 Sites 域名只能访问用户页；`/review`、`/training` 和管理 API 返回 404。
- 无 origin secret 的直连 API 请求返回 403；无病例编辑令牌的修改请求返回 403。
- 主机离线时返回“识别服务暂时未开放”，页面不显示伪造结果。
- 从另一台电脑、Chrome、Edge 和手机完成真实用例后，才记录跨电脑验收通过。
