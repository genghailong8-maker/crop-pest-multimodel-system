from __future__ import annotations

import argparse
import getpass
import secrets

from app.control import hash_password


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--compose",
        action="store_true",
        help="Escape dollar signs for use in a Docker Compose env file.",
    )
    args = parser.parse_args()
    password = getpass.getpass("管理员密码：")
    confirmation = getpass.getpass("再次输入：")
    if not password or password != confirmation:
        raise SystemExit("两次密码不一致或密码为空")
    password_hash = hash_password(password)
    if args.compose:
        password_hash = password_hash.replace("$", "$$")
    print(f"CROP_ADMIN_PASSWORD_HASH={password_hash}")
    print(f"CROP_ADMIN_SESSION_SECRET={secrets.token_urlsafe(48)}")


if __name__ == "__main__":
    main()
