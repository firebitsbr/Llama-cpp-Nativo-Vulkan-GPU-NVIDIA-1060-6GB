# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Agent tools (files, OS inspection, shell, and network).
# LICENSE MIT
# -----------------------------------------------------------------------------
"""Agent tools.

Each tool returns a string (what the model "observes"). Security:
- File operations are confined to the project root (no path traversal).
- OS inspection tools (system_info, gpu_status, list_processes, disk_usage)
  are READ-ONLY and always available.
- run_shell (OS actions) only runs if AGENT_ALLOW_SHELL=1 and blocks known
  destructive commands.
- Everything has a timeout.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_OUTPUT = 6000  # limits the size of observations returned to the model


def _safe_path(path: str) -> Path:
    """Resolves the path and ensures it stays inside the project root."""
    p = (ROOT / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise ValueError(f"Path outside the project: {p}")
    return p


def _clip(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT else text[:MAX_OUTPUT] + "\n...[truncado]"


def list_dir(path: str = ".") -> str:
    p = _safe_path(path)
    if not p.is_dir():
        return f"Error: {path} is not a directory."
    items = []
    for child in sorted(p.iterdir()):
        items.append(child.name + ("/" if child.is_dir() else ""))
    return "\n".join(items) or "(empty)"


def read_file(path: str) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"Error: file not found: {path}"
    return _clip(p.read_text(errors="replace"))


def write_file(path: str, content: str) -> str:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content)} chars to {p.relative_to(ROOT)}"


def run_python(code: str) -> str:
    """Runs a Python snippet in a separate process (timeout 30s)."""
    try:
        out = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=30, cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return "Error: timeout (30s)."
    return _clip((out.stdout + out.stderr).strip() or "(no output)")


# Destructive command patterns blocked even with AGENT_ALLOW_SHELL=1.
_DANGEROUS = re.compile(
    r"\brm\s+-[a-z]*r[a-z]*f?\s+(/|~|\*)"      # rm -rf / | ~ | *
    r"|\bmkfs\b|\bfdisk\b|\bparted\b"            # format/partition
    r"|\bdd\b[^|]*\bof=/dev/"                      # dd to device
    r"|>\s*/dev/sd|>\s*/dev/nvme"                  # overwrite disk
    r"|\b(shutdown|reboot|halt|poweroff|init)\b"  # shutdown/reboot
    r"|:\(\)\s*\{.*\|.*&\s*\}"                     # fork bomb
    r"|\bchmod\s+-R\s+0*\s+/"                      # chmod -R 0 /
    r"|\bmv\s+/\s|/etc/passwd|/etc/shadow",       # touch critical files
    re.IGNORECASE,
)


def run_shell(command: str) -> str:
    """Runs a shell command on Linux. Disabled unless AGENT_ALLOW_SHELL=1."""
    if os.environ.get("AGENT_ALLOW_SHELL") != "1":
        return "Error: shell disabled. Set AGENT_ALLOW_SHELL=1 to enable."
    if _DANGEROUS.search(command):
        return f"Blocked: potentially destructive command refused -> {command!r}"
    try:
        out = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60, cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return "Error: timeout (60s)."
    tag = "" if out.returncode == 0 else f"[exit {out.returncode}] "
    return _clip(tag + ((out.stdout + out.stderr).strip() or "(no output)"))


def _cmd(args: list[str], timeout: int = 15) -> str:
    """Runs a fixed command (no shell) and returns the output."""
    exe = shutil.which(args[0])
    if not exe:
        return f"(command '{args[0]}' not found)"
    try:
        out = subprocess.run([exe, *args[1:]], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"(timeout on {args[0]})"
    return (out.stdout + out.stderr).strip()


def system_info() -> str:
    """General system info: OS, kernel, CPU, memory, uptime, load."""
    u = platform.uname()
    lines = [f"OS: {u.system} {u.release}", f"Host: {u.node}", f"Arch: {u.machine}"]
    try:
        with open("/proc/uptime") as f:
            up = float(f.read().split()[0])
        lines.append(f"Uptime: {int(up // 3600)}h {int((up % 3600) // 60)}min")
    except OSError:
        pass
    try:
        with open("/proc/loadavg") as f:
            lines.append("LoadAvg: " + " ".join(f.read().split()[:3]))
    except OSError:
        pass
    lines.append(f"CPUs: {os.cpu_count()}")
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for ln in f:
                k, _, v = ln.partition(":")
                mem[k] = v.strip()
        lines.append(f"Mem total: {mem.get('MemTotal','?')} | available: {mem.get('MemAvailable','?')}")
    except OSError:
        pass
    return _clip("\n".join(lines))


def gpu_status() -> str:
    """NVIDIA GPU status (name, temperature, VRAM, utilization)."""
    out = _cmd([
        "nvidia-smi",
        "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
        "--format=csv,noheader",
    ])
    return _clip(out or "(nvidia-smi unavailable)")


def list_processes(limit: int = 10) -> str:
    """Top processes by CPU usage (default 10)."""
    limit = max(1, min(int(limit), 40))
    out = _cmd(["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"])
    if not out:
        return "(ps unavailable)"
    rows = out.splitlines()
    return _clip("\n".join(rows[: limit + 1]))


def disk_usage() -> str:
    """Disk usage of mounted filesystems (df -h)."""
    return _clip(_cmd(["df", "-h", "-x", "tmpfs", "-x", "devtmpfs"]) or "(df unavailable)")


def http_get(url: str) -> str:
    """Simple GET (http/https only). OFFLINE by default: needs AGENT_ALLOW_NET=1."""
    if os.environ.get("AGENT_ALLOW_NET") != "1":
        return "Error: network disabled (offline project). Set AGENT_ALLOW_NET=1 to enable."
    if not url.startswith(("http://", "https://")):
        return "Error: http/https only."
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agent/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 (validated above)
            return _clip(r.read(MAX_OUTPUT * 2).decode(errors="replace"))
    except Exception as e:  # noqa: BLE001
        return f"Request error: {e}"


# Registry: name -> (function, JSON schema in the tools format used by the
# LOCAL server on 127.0.0.1 — no cloud).
REGISTRY = {
    "list_dir": (
        list_dir,
        {"type": "object",
         "properties": {"path": {"type": "string", "description": "directory (relative to the root)"}},
         "required": []},
    ),
    "read_file": (
        read_file,
        {"type": "object",
         "properties": {"path": {"type": "string"}},
         "required": ["path"]},
    ),
    "write_file": (
        write_file,
        {"type": "object",
         "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
         "required": ["path", "content"]},
    ),
    "run_python": (
        run_python,
        {"type": "object",
         "properties": {"code": {"type": "string", "description": "Python code"}},
         "required": ["code"]},
    ),
    "run_shell": (
        run_shell,
        {"type": "object",
         "properties": {"command": {"type": "string"}},
         "required": ["command"]},
    ),
    "http_get": (
        http_get,
        {"type": "object",
         "properties": {"url": {"type": "string"}},
         "required": ["url"]},
    ),
    "system_info": (
        system_info,
        {"type": "object", "properties": {}, "required": []},
    ),
    "gpu_status": (
        gpu_status,
        {"type": "object", "properties": {}, "required": []},
    ),
    "list_processes": (
        list_processes,
        {"type": "object",
         "properties": {"limit": {"type": "integer", "description": "number of processes (default 10)"}},
         "required": []},
    ),
    "disk_usage": (
        disk_usage,
        {"type": "object", "properties": {}, "required": []},
    ),
}

_DESCRIPTIONS = {
    "list_dir": "Lists files/folders in a project directory.",
    "read_file": "Reads the contents of a project text file.",
    "write_file": "Creates/overwrites a project text file.",
    "run_python": "Runs a Python code snippet and returns the output.",
    "run_shell": "Runs a shell command on Linux (needs AGENT_ALLOW_SHELL=1; blocks destructive commands).",
    "http_get": "Performs an HTTP(S) GET (OFFLINE by default; needs AGENT_ALLOW_NET=1).",
    "system_info": "Shows OS, kernel, CPU, memory, uptime and load (read-only).",
    "gpu_status": "Shows NVIDIA GPU status: temp, VRAM, utilization, power (read-only).",
    "list_processes": "Lists the processes using the most CPU (read-only).",
    "disk_usage": "Shows filesystem disk usage (df -h, read-only).",
}


def tool_specs() -> list[dict]:
    """Builds the tools list in the protocol format (local server)."""
    return [
        {"type": "function",
         "function": {"name": name, "description": _DESCRIPTIONS[name], "parameters": schema}}
        for name, (_fn, schema) in REGISTRY.items()
    ]


def dispatch(name: str, arguments: str) -> str:
    """Runs the tool by name with the arguments (JSON string)."""
    if name not in REGISTRY:
        return f"Error: unknown tool '{name}'."
    fn, _schema = REGISTRY[name]
    try:
        kwargs = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return f"Error: invalid arguments (JSON): {arguments}"
    try:
        return str(fn(**kwargs))
    except Exception as e:  # noqa: BLE001
        return f"Error running {name}: {e}"
