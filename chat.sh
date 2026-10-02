#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Interactive terminal chat with llama.cpp on the GTX 1060 (Vulkan).
# LICENSE MIT
# -----------------------------------------------------------------------------
# Interactive terminal chat on the NVIDIA GTX 1060 GPU via Vulkan (thermal/SSD-friendly profile).
# Usage: ./chat.sh [model.gguf]
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"   # re-exec under bash if invoked with sh
set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${1:-$ROOT/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf}"
CTX="${CTX:-8192}"
NGL="${NGL:-99}"
THREADS="${THREADS:-4}"
MLOCK="${MLOCK:-1}"
export GGML_VK_VISIBLE_DEVICES="${GGML_VK_VISIBLE_DEVICES:-1}"

ARGS=(
  -m "$MODEL"
  -ngl "$NGL" -c "$CTX"
  -t "$THREADS" --threads-batch "$THREADS"
  -b 512 -ub 256
  --flash-attn auto
  --jinja
)
[[ "$MLOCK" == "1" ]] && ARGS+=(--load-mode mmap+mlock)

exec "$ROOT/llama.cpp/build/bin/llama-cli" "${ARGS[@]}"
