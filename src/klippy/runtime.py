"""Owned llama.cpp process. No external installation or cloud service is used."""
import asyncio
import os
import secrets
import socket
import subprocess
from pathlib import Path

import httpx

from .conversation import LocalLLM
from .models import ModelUnavailable, verify_pack


class LlamaRuntime:
    def __init__(self):
        self.process = None
        self.port = None
        self.api_key = secrets.token_urlsafe(32)

    async def start(self, root: Path):
        manifest = await asyncio.to_thread(verify_pack, root)
        if self.process:
            self.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        binary = (root / manifest["runtime"]["binary"]).resolve()
        model = (root / manifest["runtime"]["model"]).resolve()
        args = [str(binary), "--model", str(model), "--host", "127.0.0.1", "--port", str(self.port),
                "--ctx-size", "2048", "--threads", str(min(os.cpu_count() or 2, 4)),
                "--parallel", "1", "--n-gpu-layers", "0", "--api-key", self.api_key]
        try:
            self.process = subprocess.Popen(args, cwd=binary.parent, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                for _ in range(240):
                    if self.process.poll() is not None:
                        raise ModelUnavailable("Bundled language engine exited; manual controls remain available")
                    try:
                        response = await client.get(f"http://127.0.0.1:{self.port}/health",
                                                    headers={"Authorization": "Bearer " + self.api_key})
                        if response.status_code == 200:
                            return LocalLLM(self.port, self.api_key)
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.25)
        except OSError:
            self.close()
            raise ModelUnavailable("Bundled language engine could not start") from None
        except BaseException:
            self.close()
            raise
        self.close()
        raise ModelUnavailable("Bundled language engine startup timed out")

    def close(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=4)
            self.process = None
