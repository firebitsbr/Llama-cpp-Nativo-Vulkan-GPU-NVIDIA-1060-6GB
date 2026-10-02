# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Autonomous agent (ReAct via tool-calling) over the local llama-server.
# LICENSE MIT
# -----------------------------------------------------------------------------
"""Autonomous agent (ReAct via tool-calling) running on the local llama-server.

The agent receives a task, decides which tools to call, executes them, observes
the result and ITERATES on its own until done — this loop is what makes the
project "agentic" (vs. a single question/answer turn).

Prerequisites:
  1. conda activate llama-vulkan
  2. ./start-server.sh            (in another terminal)
  3. python agent/run_agent.py "your task here"

Env options:
  BASE_URL   (default http://127.0.0.1:8080/v1)
  MAX_STEPS  (default 10)
  AGENT_ALLOW_SHELL=1  enables the shell tool
  AGENT_ALLOW_NET=1    enables the network tool (http_get)
"""
from __future__ import annotations

import os
import sys

from llm_client import LocalLLM
from tools import dispatch, tool_specs

MAX_STEPS = int(os.environ.get("MAX_STEPS", "10"))

SYSTEM = (
    "You are an autonomous agent running on a Linux system. Solve the user's "
    "task in steps, using the tools: inspect files, run Python code, query the "
    "OS (system_info, gpu_status, list_processes, disk_usage) and, when "
    "allowed, run shell commands (run_shell). Do not make up results — use the "
    "tools to obtain real data. Think about the next step, call ONE or more "
    "tools, observe the output and continue. When the task is complete, reply "
    "with a final text WITHOUT calling tools, summarizing what was done. Be "
    "concise."
)

client = LocalLLM()


def run(task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    tools = tool_specs()

    for step in range(1, MAX_STEPS + 1):
        msg = client.chat(messages, tools=tools, temperature=0.2)
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            print(f"\n=== Final answer (step {step}) ===")
            return msg.get("content") or "(no content)"

        messages.append(msg)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"].get("arguments") or "{}"
            print(f"[step {step}] tool: {name}({args})")
            result = dispatch(name, args)
            preview = result if len(result) < 300 else result[:300] + "…"
            print(f"           -> {preview}")
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "name": name, "content": result}
            )

    return "Step limit reached without a final answer."


def main() -> None:
    task = " ".join(sys.argv[1:]).strip()
    if not task:
        task = input("Task for the agent: ").strip()
    if not task:
        print("No task provided.")
        raise SystemExit(1)
    print(f"Task: {task}\n")
    answer = run(task)
    print(answer)


if __name__ == "__main__":
    main()
