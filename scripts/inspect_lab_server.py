from __future__ import annotations

import os
import sys

import paramiko


COMMAND = r"""
set -e
printf '=== identity ===\n'
id
printf '=== mounts ===\n'
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS / /data
df -h / /data
printf '=== docker ===\n'
docker info --format 'root={{.DockerRootDir}} driver={{.Driver}}' 2>&1 || true
docker ps --format 'container={{.ID}} name={{.Names}} image={{.Image}}' 2>&1 || true
printf '=== data target ===\n'
if [ -e /data/ghl ]; then ls -ld /data/ghl; else echo '/data/ghl does not exist'; fi
printf '=== cpu ===\n'
grep -m1 -o 'avx2' /proc/cpuinfo || true
"""


def main() -> None:
    password = os.environ.pop("GHL_SSH_PASSWORD", "")
    if not password:
        raise SystemExit("未收到 SSH 凭据")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        "192.168.15.133",
        port=22,
        username="root",
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=10,
        banner_timeout=10,
        auth_timeout=20,
    )
    try:
        _, stdout, stderr = client.exec_command(COMMAND, timeout=30)
        output = stdout.read().decode("utf-8", errors="replace")
        errors = stderr.read().decode("utf-8", errors="replace")
        status = stdout.channel.recv_exit_status()
    finally:
        client.close()
    sys.stdout.write(output)
    if errors:
        sys.stderr.write(errors)
    raise SystemExit(status)


if __name__ == "__main__":
    main()
