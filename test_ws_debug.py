#!/usr/bin/env python3
"""Test LangBot plugin debug WebSocket endpoint."""

from __future__ import annotations

import asyncio
import json
import sys

WS_URL = "ws://20252025.top:40511/plugin/debug/ws"


async def test_connection(url: str) -> None:
    try:
        import websockets
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
        import websockets

    print(f"=== LangBot Plugin Debug WS Test ===")
    print(f"URL: {url}\n")

    try:
        async with websockets.connect(url, open_timeout=15, close_timeout=5) as ws:
            print("[OK] WebSocket connected")
            print(f"     Remote: {ws.remote_address}")
            print(f"     Local:  {ws.local_address}")

            # LangBot debug protocol uses JSON action requests
            # Try waiting for any server-initiated message
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                print(f"\n[RECV] Server message: {msg[:300]}")
            except asyncio.TimeoutError:
                print("\n[INFO] No server-initiated message (normal for debug endpoint)")

            # Send a minimal protocol probe (register_plugin without valid container)
            probe = {
                "seq_id": 1,
                "action": "register_plugin",
                "data": {
                    "plugin_container": {},
                    "prod_mode": False,
                    "plugin_debug_key": "",
                },
            }
            await ws.send(json.dumps(probe))
            print(f"\n[SENT] register_plugin probe")

            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"[RECV] Response: {resp[:500]}")
                data = json.loads(resp)
                if data.get("success") is False:
                    print(f"[INFO] Server rejected probe (expected): {data.get('message', data.get('error', ''))}")
                elif data.get("success") is True:
                    print("[OK] Server accepted connection — ready for plugin debug")
            except asyncio.TimeoutError:
                print("[WARN] No response to register_plugin probe within 5s")

            print("\n=== Result ===")
            print("WebSocket endpoint is REACHABLE and accepts connections.")
            print("To load the plugin, run:")
            print("  cd AutoLearnPlugin && cp .env.example .env")
            print(f"  # Set DEBUG_RUNTIME_WS_URL={url}")
            print("  python -m langbot_plugin.cli.__init__ run")

    except Exception as e:
        print(f"\n[FAIL] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else WS_URL
    asyncio.run(test_connection(url))
