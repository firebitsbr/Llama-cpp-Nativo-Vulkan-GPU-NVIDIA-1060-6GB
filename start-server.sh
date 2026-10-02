#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Starts the llama.cpp server (local HTTP API) on the GTX 1060 via Vulkan.
# LICENSE MIT
# -----------------------------------------------------------------------------
# Starts the llama.cpp server (local HTTP API) on the NVIDIA GTX 1060 GPU via Vulkan.
# HYBRID + thermal + SSD-friendly profile (i7-7700HQ laptop / 1060 Mobile).
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"   # re-exec under bash if invoked with sh
#
# Usage:  ./start-server.sh [model.gguf]
# Ex.:    NGL=20 CTX=4096 ./start-server.sh models/large-model.gguf
set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${1:-$ROOT/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"               # explicit port (immune to the :9931 change, PR #26508)
API_KEY="${API_KEY:-local-key}"    # authenticates the API (silences security warning, PR #25655)

# --- HYBRID settings (VRAM 6GB + RAM 64GB) ---
CTX="${CTX:-8192}"        # context; smaller = less VRAM/RAM and less heat
NGL="${NGL:-99}"          # GPU layers. 99=all. Model > 6GB -> reduce
                          # (e.g. 14B Q4 -> ~20); the rest runs on RAM/CPU.
THREADS="${THREADS:-4}"   # = PHYSICAL cores (4). Avoid 8 (hyperthread = + heat)
BATCH="${BATCH:-512}"     # prompt batch
UBATCH="${UBATCH:-256}"   # smaller micro-batch = smaller heat spikes
MLOCK="${MLOCK:-1}"       # 1 = locks the model in RAM (avoids SSD I/O after load)

# Forces ONLY the NVIDIA GPU (Intel iGPU is left out)
export GGML_VK_VISIBLE_DEVICES="${GGML_VK_VISIBLE_DEVICES:-1}"

if [[ ! -f "$MODEL" ]]; then
  echo "Model not found: $MODEL" >&2
  exit 1
fi

ARGS=(
  -m "$MODEL"
  --host "$HOST" --port "$PORT"
  --api-key "$API_KEY"
  -ngl "$NGL" -c "$CTX"
  -t "$THREADS" --threads-batch "$THREADS"
  -b "$BATCH" -ub "$UBATCH"
  --flash-attn auto     # reduces KV-cache and heat
  --jinja               # tool calling (agentic)
  --no-webui
)
# mmap+mlock: maps and LOCKS the model in RAM -> no SSD re-reads during use
[[ "$MLOCK" == "1" ]] && ARGS+=(--load-mode mmap+mlock)

echo "GPU: NVIDIA (Vulkan) | ngl=$NGL ctx=$CTX threads=$THREADS mlock=$MLOCK"
echo "API: http://$HOST:$PORT/v1   (model: $(basename "$MODEL"))  [api-key: $API_KEY]"
exec "$ROOT/llama.cpp/build/bin/llama-server" "${ARGS[@]}"
