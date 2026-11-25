"""cimhub_core.mermaid.download_mermaid: non-ASCII diagram text is sent as UTF-8, not refused."""

from __future__ import annotations

import base64

import requests

from cimhub_core import mermaid


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        return [b"png"]


def test_non_ascii_text_downloads(tmp_path, monkeypatch):
    urls = []
    monkeypatch.setattr(mermaid.requests, "get", lambda url, **kwargs: urls.append(url) or _Response())
    assert mermaid.download_mermaid("classDiagram\n  class Line { r Ω }", str(tmp_path / "out.png"))
    encoded = urls[0].removeprefix("https://mermaid.ink/img/")
    assert base64.b64decode(encoded).decode("utf-8").endswith("r Ω }")
    assert (tmp_path / "out.png").read_bytes() == b"png"


def test_a_network_error_returns_false(tmp_path, monkeypatch):
    def fail(url, **kwargs):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(mermaid.requests, "get", fail)
    assert mermaid.download_mermaid("graph TD; a-->b", str(tmp_path / "out.png")) is False
