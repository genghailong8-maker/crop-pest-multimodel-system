# Phase 9 数据库、记录与维护说明

## 数据边界

- 真源是当前电脑的 `backend/runtime/crop-pest.sqlite3`，不使用公网数据库。
- 图片保存在 `backend/runtime/uploads`，数据库和该目录必须一起备份。
- 本机模式下 `GET /api/cases` 默认返回全部病例，`GET /api/trends` 统计全部本机记录。
- 本机病例长期保存，不因 `expires_at` 到期自动删除；需要清理时由用户先备份后手动执行维护命令。
- 已保留的公网兼容模式只有在显式设置 `CROP_PUBLIC_MODE=true` 时才启用公开过滤、编辑令牌和过期清理；默认运行不启用。

## Phase 9 字段

`affected_ratio_percent`、`spread_speed`、`public_consent`、`expires_at`、`diagnostic_risk`、`field_severity` 和 `edit_token_hash` 由最小迁移补入。本机模式的新病例固定 `public_consent=false`、`expires_at=null`，不创建编辑令牌；兼容字段不删除，以避免破坏既有数据库。

## 维护命令

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe scripts\manage_storage.py check
.\.venv\Scripts\python.exe scripts\manage_storage.py backup
.\.venv\Scripts\python.exe scripts\manage_storage.py backup --output runtime\backups\before-demo.sqlite3
.\.venv\Scripts\python.exe scripts\manage_storage.py purge-expired
.\.venv\Scripts\python.exe scripts\manage_storage.py restore runtime\backups\before-demo.sqlite3
```

恢复操作会先自动备份当前数据库，并校验来源数据库完整性。恢复后必须再次运行 `check`；若图片路径缺失，应同步恢复对应的 `runtime/uploads`，不能用占位图片伪造记录。

## 比赛期间建议

1. 开机后先 `check`，再启动后端。
2. 每次重要测试前创建一次时间戳备份，并同步备份 `runtime/uploads`。
3. 本机模式不要设置自动 `purge-expired` 任务；只有用户明确清理数据时才手动执行。
4. SQLite 已启用 WAL、`busy_timeout` 和 `synchronous=NORMAL`，定位为单机演示数据库，不宣称为高并发集群数据库。
