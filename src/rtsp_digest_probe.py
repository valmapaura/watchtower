#!/usr/bin/env python3
"""
watchtower - pure-Python RTSP digest-auth explorer.

Talks RTSP directly (no ffmpeg/OpenCV) to demonstrate the exact auth dance
this camera expects:
  1. Send an unauthenticated DESCRIBE -> camera answers 401 + Digest challenge
     (realm="ipc", NO qop)
  2. Compute the digest response: MD5(HA1:nonce:HA2)
  3. Re-send DESCRIBE with the Authorization header -> 200 OK + SDP

Zero dependencies - stdlib only.

Usage:
    python src/rtsp_digest_probe.py
    python src/rtsp_digest_probe.py --config path/to/config.json
    python src/rtsp_digest_probe.py --path /live/ch0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import sys
from pathlib import Path


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def send(sock: socket.socket, req: str) -> str:
    sock.sendall(req.encode())
    sock.settimeout(8)
    data = b""
    while True:
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
        if b"\r\n\r\n" in data and len(data) > len(data.split(b"\r\n\r\n", 1)[0]) + 4:
            # got full headers; SDP body usually arrives in the same recv
            if data.count(b"\r\n") > 40:  # SDP included -> done
                break
    return data.decode(errors="replace")


def parse_challenge(r1: str) -> dict:
    def grab(pattern: str) -> str:
        m = re.search(pattern, r1)
        return m.group(1) if m else ""

    return {
        "realm": grab(r'realm="([^"]+)"'),
        "nonce": grab(r'nonce="([^"]+)"'),
        "qop": grab(r'qop="([^"]+)"'),
    }


def digest_header(ch: dict, method: str, uri: str, user: str, pw: str) -> str:
    ha1 = md5_hex(f"{user}:{ch['realm']}:{pw}")
    ha2 = md5_hex(f"{method}:{uri}")
    if ch["qop"]:
        resp = md5_hex(f"{ha1}:{ch['nonce']}:00000001:0a4f113b:{ch['qop']}:{ha2}")
        return (
            f'Digest username="{user}", realm="{ch["realm"]}", nonce="{ch["nonce"]}", '
            f'uri="{uri}", response="{resp}", qop={ch["qop"]}, '
            f'nc=00000001, cnonce="0a4f113b"'
        )
    # no-qop variant (RFC 2617) - what this camera uses
    resp = md5_hex(f"{ha1}:{ch['nonce']}:{ha2}")
    return (
        f'Digest username="{user}", realm="{ch["realm"]}", '
        f'nonce="{ch["nonce"]}", uri="{uri}", response="{resp}"'
    )


def probe(host: str, port: int, path: str, user: str, pw: str) -> None:
    uri = f"rtsp://{host}:{port}{path}"
    print(f"== watchtower RTSP probe: {uri}")

    sock = socket.create_connection((host, port), timeout=8)
    try:
        r1 = send(
            sock,
            f"DESCRIBE {uri} RTSP/1.0\r\n"
            f"CSeq: 2\r\nUser-Agent: watchtower/1.0\r\nAccept: application/sdp\r\n\r\n",
        )
        status_line = r1.splitlines()[0] if r1 else "(no response)"
        print(f"\n1) DESCRIBE (no auth) -> {status_line}")

        if "401" in status_line:
            ch = parse_challenge(r1)
            print(f"   Digest challenge: realm={ch['realm']!r} nonce={ch['nonce'][:12]}... "
                  f"qop={ch['qop'] or 'none'}")
            auth = digest_header(ch, "DESCRIBE", uri, user, pw)
            r2 = send(
                sock,
                f"DESCRIBE {uri} RTSP/1.0\r\n"
                f"CSeq: 3\r\nAuthorization: {auth}\r\n"
                f"User-Agent: watchtower/1.0\r\nAccept: application/sdp\r\n\r\n",
            )
            status_line2 = r2.splitlines()[0] if r2 else "(no response)"
            print(f"2) DESCRIBE (digest) -> {status_line2}")
            print("\n--- SDP ---")
            print(r2[r2.find("\r\n\r\n") + 4:].strip() or r2)
        else:
            print("   No auth required (or unexpected response):")
            print(r1)
    finally:
        sock.close()


def main() -> None:
    default_config = Path(__file__).resolve().parent.parent / "config.json"
    parser = argparse.ArgumentParser(description="watchtower RTSP digest probe")
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--host", help="override camera host")
    parser.add_argument("--port", type=int, default=554)
    parser.add_argument("--path", default=None, help="stream path, e.g. /live/ch0")
    parser.add_argument("--user", help="override username")
    parser.add_argument("--password", help="override password")
    args = parser.parse_args()

    if args.config.exists():
        cam = json.loads(args.config.read_text(encoding="utf-8"))["camera"]
        host = args.host or cam["host"]
        port = args.port
        path = args.path or cam.get("rtsp_path", "/ch0/")
        user = args.user or cam["username"]
        pw = args.password or cam["password"]
    else:
        host = args.host or "192.168.1.247"
        path = args.path or "/ch0/"
        user = args.user or "admin"
        pw = args.password or ""
        if not pw:
            sys.exit("config.json not found and no --password given.")

    probe(host, port, path, user, pw)


if __name__ == "__main__":
    main()
