# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Minimal HTTP client (stdlib) for the local llama.cpp server.
# LICENSE MIT
# -----------------------------------------------------------------------------
"""Minimal HTTP client (stdlib) for the LOCAL llama.cpp server.

Talks to the /v1/chat/completions endpoint on 127.0.0.1 using only urllib —
without the `openai` library and without any external dependency. 100% local.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class LocalLLM:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("BASE_URL", "http://127.0.0.1:8080/v1")).rstrip("/")
        # same default key as start-server.sh (local-key); only valid on localhost
        self.api_key = api_key or os.environ.get("API_KEY", "local-key")

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        timeout: int = 600,
    ) -> dict:
        """Sends a chat request and returns the assistant message (dict).

        The structure follows the pattern: {"role", "content", "tool_calls": [...]}.
        """
        payload: dict = {"model": "local", "messages": messages, "temperature": temperature}
        if tools:
            payload["tools"] = tools

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # localhost
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"HTTP {e.code} from the local server: {detail}") from None
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not reach the local server at {self.base_url}. "
                f"Is ./start-server.sh running? ({e.reason})"
            ) from None

        return body["choices"][0]["message"]
