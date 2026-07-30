"""HttpFileService — the agent's FileService port over HTTP (infrastructure).

Plain stdlib urllib; chunk bytes go as octet-stream, metadata as JSON. The only
place the agent's network details live.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from agent.ports import FileService


class HttpFileService(FileService):
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def _json(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self._base + path, data=data, method=method)
        if data is not None:
            req.add_header("content-type", "application/json")
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else None

    def get_manifest(self, path: str) -> list[str]:
        result = self._json("GET", f"/files/manifest?path={urllib.parse.quote(path)}")
        return [str(h) for h in result["hashes"]]

    def missing_chunks(self, hashes: list[str]) -> list[str]:
        result = self._json("POST", "/chunks/missing", {"hashes": hashes})
        return [str(h) for h in result["missing"]]

    def put_chunk(self, chunk_hash: str, data: bytes) -> None:
        req = urllib.request.Request(f"{self._base}/chunks/{chunk_hash}", data=data, method="PUT")
        req.add_header("content-type", "application/octet-stream")
        with urllib.request.urlopen(req):
            pass

    def get_chunk(self, chunk_hash: str) -> bytes:
        with urllib.request.urlopen(f"{self._base}/chunks/{chunk_hash}") as resp:
            body: bytes = resp.read()
        return body

    def commit_manifest(self, path: str, hashes: list[str]) -> None:
        self._json("PUT", "/files/manifest", {"path": path, "hashes": hashes})
