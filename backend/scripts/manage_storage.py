from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app import database


def default_backup_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return database.settings.storage_dir / "backups" / f"crop-pest-{stamp}.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description="田诊协同 SQLite 维护工具")
    subparsers = parser.add_subparsers(dest="action", required=True)
    backup = subparsers.add_parser("backup", help="创建 SQLite 在线备份")
    backup.add_argument("--output", type=Path)
    restore = subparsers.add_parser("restore", help="校验备份并恢复；自动先备份当前库")
    restore.add_argument("source", type=Path)
    subparsers.add_parser("check", help="检查数据库完整性和图片路径")
    subparsers.add_parser("purge-expired", help="删除已过期公开病例及其上传图片")
    mark_test = subparsers.add_parser("mark-existing-test", help="将已确认的历史快照标记为测试病例")
    mark_test.add_argument("--before", required=True, help="只标记该 ISO 时间及以前的病例")
    mark_test.add_argument("--expected-count", required=True, type=int)
    args = parser.parse_args()

    database.init_database()
    if args.action == "backup":
        output = database.backup_database(args.output or default_backup_path())
        result = {"action": "backup", "path": str(output), "integrity": "ok"}
    elif args.action == "restore":
        safety_backup = database.backup_database(default_backup_path())
        database.restore_database(args.source)
        result = {
            "action": "restore",
            "source": str(args.source.resolve()),
            "safety_backup": str(safety_backup),
            "integrity": database.integrity_check(),
            "images": database.validate_image_paths(),
        }
    elif args.action == "purge-expired":
        result = {"action": "purge-expired", **database.purge_expired_cases()}
    elif args.action == "mark-existing-test":
        result = {
            "action": "mark-existing-test",
            **database.mark_existing_cases_as_test(args.before, args.expected_count),
            "integrity": database.integrity_check(),
            "images": database.validate_image_paths(),
        }
    else:
        result = {
            "action": "check",
            "integrity": database.integrity_check(),
            "images": database.validate_image_paths(),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("integrity", "ok") == "ok" and result.get("images", {}).get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
