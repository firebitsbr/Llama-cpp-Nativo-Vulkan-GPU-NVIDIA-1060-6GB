<!--
Author: Mauro Risonho de Paula Assumpção
Creation Date: 2026-10-01
Update Date: 2026-10-01
Short Description: How to make the project agentic (model + tools + loop).
LICENSE MIT
-->
# Making the project agentic

"Agentic" = the model **decides and acts over multiple steps**, using tools,
observing results and **iterating on its own** until the task is done — instead of
just answering a question in a single turn.

## The 3 layers

```
┌─ Model (Qwen2.5-7B) ── runs on the GPU via llama.cpp (Vulkan)
│
├─ Local HTTP server ── ./start-server.sh  (--jinja enables tool calling)
│
└─ Agent loop ── agent/run_agent.py  (decide → call tool → observe → repeat)
        ├─ HTTP client ── agent/llm_client.py  (stdlib/urllib, without `openai`)
        └─ Tools ── agent/tools.py  (files, python, shell, http)
```

What already existed: the **first two layers** (model on the GPU + API with tool
calling). What actually makes the project agentic is the **third layer**: the loop.

## The agent loop (ReAct via tool-calling)

`agent/run_agent.py` does, on each step:
1. sends the history + list of tools to the model;
2. if the model returns `tool_calls`, it runs each tool and appends the
   observation (`role: tool`) to the history;
3. repeats until the model replies **without** calling tools (final answer)
   or reaches `MAX_STEPS`.

## Run

```bash
conda activate llama-vulkan
./start-server.sh                                  # terminal 1
python agent/run_agent.py "your task here"         # terminal 2
```

Examples:
```bash
python agent/run_agent.py "Read README.md and summarize it in 3 bullets."
AGENT_ALLOW_SHELL=1 python agent/run_agent.py "Run 'nvidia-smi' and tell me the GPU temperature."
```

Variables: `BASE_URL`, `MAX_STEPS` (default 10), `AGENT_ALLOW_SHELL=1`.

## Interacting with the operating system (Linux)

The agent has **read-only OS inspection tools** (always on) and one **action**
tool (`run_shell`, opt-in):

```bash
# Inspection (without enabling anything):
python agent/run_agent.py "What's the GPU temperature and the disk usage?"

# OS actions (shell commands) — enable explicitly:
AGENT_ALLOW_SHELL=1 python agent/run_agent.py "List the 5 largest files in ~/Downloads."
```

`run_shell` runs any Linux command (`shell=True`), but **blocks known destructive
patterns** (`rm -rf /`, `mkfs`, `dd of=/dev/...`, `shutdown`, fork bomb, etc.)
and has a 60s timeout.

## Included tools (`agent/tools.py`)

| Tool | What it does | Security |
|---|---|---|
| `list_dir` | lists a directory | confined to the project root |
| `read_file` | reads a text file | confined to the root |
| `write_file` | creates/overwrites a file | confined to the root |
| `run_python` | runs Python code | separate process, 30s timeout |
| `system_info` | OS, kernel, CPU, RAM, uptime, load | **read-only**, always on |
| `gpu_status` | GPU: temp, VRAM, usage, power | **read-only**, always on |
| `list_processes` | top processes by CPU | **read-only**, always on |
| `disk_usage` | disk usage (`df -h`) | **read-only**, always on |
| `run_shell` | runs a Linux command | **off** by default (`AGENT_ALLOW_SHELL=1`) + denylist |
| `http_get` | HTTP(S) GET | **off** by default (`AGENT_ALLOW_NET=1`); project is offline |

## Adding a new tool

1. Write the function in `agent/tools.py` (return `str`).
2. Register it in `REGISTRY` with the JSON schema of the parameters.
3. Add the description in `_DESCRIPTIONS`.
Done — the agent starts seeing it automatically.

## Reliability tips (7B model)

- The agentic **plumbing** is solid; the reasoning quality depends on the model.
  A 7B sometimes gets logic wrong. For complex tasks, use a larger model
  (e.g. 14B Q4 with partial offload — see [01-TUNING-HIBRIDO.md](01-TUNING-HIBRIDO.md)).
- A low `temperature` (0.2) is already used for more deterministic answers.
- Clear instructions and decomposed tasks improve the result a lot.

## Local HTTP client (without `openai`)

`agent/llm_client.py` is a minimal client in **stdlib (urllib)** that POSTs to
`http://127.0.0.1:8080/v1/chat/completions`. The project **does not depend on the
`openai` library** — everything is local. Any framework (langchain/langgraph)
can also talk to that same local endpoint, but it is not required.
