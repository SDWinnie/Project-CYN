"""Public Intermediary Relay & Cloudflare Tunnel Manager for Project CYN.

Provides zero-config public HTTPS/WSS intermediary relay:
- Launches cloudflared quick tunnel to expose localhost:8080 to the global internet
- Extracts the public https://*.trycloudflare.com URL
- Allows Android Mobile Companion and external browsers to connect from anywhere without port forwarding.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("CYN.Tunnel")

ROOT_DIR = Path(__file__).resolve().parent.parent
CLOUDFLARED_BIN = ROOT_DIR / "tools" / "cloudflared.exe"
TUNNEL_URL_FILE = Path(__file__).resolve().parent / "tunnel_url.txt"

TRYCLOUDFLARE_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def ensure_cloudflared() -> bool:
    """Ensure cloudflared executable exists, auto-downloading if missing."""
    if CLOUDFLARED_BIN.exists():
        return True
    try:
        import urllib.request
        CLOUDFLARED_BIN.parent.mkdir(parents=True, exist_ok=True)
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        logger.info(f"Downloading cloudflared binary from {url}...")
        urllib.request.urlretrieve(url, str(CLOUDFLARED_BIN))
        logger.info("cloudflared binary ready.")
        return True
    except Exception as e:
        logger.error(f"Failed to auto-download cloudflared: {e}")
        return False


class CloudflareTunnelRelay:
    def __init__(
        self,
        local_port: int = 8080,
        port: Optional[int] = None,
        on_url_ready: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.local_port = port if port is not None else local_port
        self.on_url_ready = on_url_ready
        self.public_url: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start cloudflared in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_tunnel, daemon=True)
        self._thread.start()

    def _run_tunnel(self) -> None:
        if not ensure_cloudflared():
            logger.warning("Cloudflare binary not available; public relay offline.")
            return

        cmd = [
            str(CLOUDFLARED_BIN),
            "tunnel",
            "--url",
            f"http://localhost:{self.local_port}",
            "--no-autoupdate",
        ]
        logger.info(f"Initiating Cloudflare Tunnel relay to port {self.local_port}...")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            for line in iter(self.process.stdout.readline, ""):
                if not self._running:
                    break

                # Search for public URL in cloudflared output
                match = TRYCLOUDFLARE_RE.search(line)
                if match:
                    url = match.group(0)
                    if url != self.public_url:
                        self.public_url = url
                        logger.info("==================================================================")
                        logger.info(f">> PUBLIC RELAY INTERMEDIARY URL ACTIVE:")
                        logger.info(f">> {self.public_url}")
                        logger.info(f">> Mobile Companion URL: {self.public_url}?client=android")
                        logger.info("==================================================================")

                        # Write to file for client discovery
                        try:
                            TUNNEL_URL_FILE.write_text(self.public_url, encoding="utf-8")
                        except Exception:
                            pass

                        if self.on_url_ready:
                            self.on_url_ready(self.public_url)

            if self.process:
                self.process.wait()
        except Exception as e:
            logger.error(f"Error running tunnel relay: {e}")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.kill()
            except Exception:
                pass
            self.process = None
        logger.info("Cloudflare tunnel relay stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    relay = CloudflareTunnelRelay(8080)
    relay.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        relay.stop()
