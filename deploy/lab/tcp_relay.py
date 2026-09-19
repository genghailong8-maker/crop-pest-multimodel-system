#!/usr/bin/env python3
"""Small TCP bridge from the Docker host gateway to a loopback SSH tunnel."""

import argparse
import select
import socket
import socketserver


class RelayHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        upstream = socket.create_connection(
            (self.server.target_host, self.server.target_port), timeout=5
        )
        try:
            sockets = [self.request, upstream]
            while True:
                readable, _, _ = select.select(sockets, [], [], 30)
                if not readable:
                    continue
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    destination = upstream if source is self.request else self.request
                    destination.sendall(data)
        finally:
            upstream.close()


class RelayServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", required=True)
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-host", default="127.0.0.1")
    parser.add_argument("--target-port", type=int, required=True)
    args = parser.parse_args()

    with RelayServer((args.listen_host, args.listen_port), RelayHandler) as server:
        server.target_host = args.target_host
        server.target_port = args.target_port
        server.serve_forever()


if __name__ == "__main__":
    main()
