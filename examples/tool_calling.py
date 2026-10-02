# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Tool-calling example against the local server (without the openai lib).
# LICENSE MIT
# -----------------------------------------------------------------------------
"""Tool-calling example against the LOCAL server (without the `openai` library).

Uses the minimal HTTP client (stdlib/urllib) in agent/llm_client.py. 100% local.

Prerequisites:
  1. conda activate llama-vulkan
  2. ./start-server.sh   (in another terminal)
  3. python examples/tool_calling.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
from llm_client import LocalLLM  # noqa: E402

client = LocalLLM()


def get_weather(city: str) -> str:
    """Simulated tool (local data)."""
    fake = {"sao paulo": "27°C sunny", "lisboa": "19°C cloudy"}
    return fake.get(city.lower(), "no data")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Returns the current weather of a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
]


def main() -> None:
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when necessary."},
        {"role": "user", "content": "What's the weather in São Paulo?"},
    ]

    msg = client.chat(messages, tools=TOOLS)

    if msg.get("tool_calls"):
        messages.append(msg)
        for call in msg["tool_calls"]:
            args = json.loads(call["function"].get("arguments") or "{}")
            result = get_weather(**args)
            print(f"[tool] {call['function']['name']}({args}) -> {result}")
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": result}
            )
        msg = client.chat(messages)

    print("\nAssistant:", msg.get("content"))


if __name__ == "__main__":
    main()
