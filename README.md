<!--
Author: Mauro Risonho de Paula Assumpção
Creation Date: 2026-10-01
Update Date: 2026-10-01
Short Description: Overview of the native llama.cpp (Vulkan) project on the GTX 1060 6GB.
LICENSE MIT
-->
# [Draft] Native Llama.cpp (Vulkan) — NVIDIA GTX 1060 6GB GPU

Environment to run **native Vulkan-accelerated llama.cpp** on the GTX 1060 6GB and
to build **AI / agentic** applications in Python.

> **100% local and offline.** All inference runs on your GPU (Vulkan) and the
> server listens only on `127.0.0.1`. The server speaks a compatible HTTP
> *protocol* (the `/v1/chat/completions` route), but **there are no calls to
> cloud services** and the project **does not depend on the `openai` library**
> (the client is stdlib). The only part that uses the internet is the initial
> model download (`hf download`). The agent is offline by default (network tool
> disabled).

## What is already in place
- Conda environment **`llama-vulkan`** (Python 3.11) with the build toolchain
  (cmake, ninja, shaderc/glslc, spirv-headers).
- **llama.cpp** built with the **Vulkan** backend in `llama.cpp/build/bin/`
  (`llama-cli`, `llama-server`, `llama-bench`, `llama-quantize`, ...).
- Recommended model downloaded: `models/Qwen2.5-7B-Instruct-Q4_K_M.gguf` (~4.4 GB).
- Local agent in pure Python (stdlib): `agent/` (urllib client + loop + tools).

## Quick start

```bash
conda activate llama-vulkan

# 1) Local HTTP server (on the NVIDIA GPU)
./start-server.sh                 # http://127.0.0.1:8080/v1

# 2) Chat directly in the terminal
./chat.sh

# 3) Tool-calling example (with the server running in another terminal)
python examples/tool_calling.py

# 3b) AUTONOMOUS agent (multi-step loop with tools)
python agent/run_agent.py "Read README.md and summarize it in 3 bullets."

# 4) Monitor temperature/VRAM/RAM in real time
./monitor.sh

# 5) (optional, requires sudo) cap the GPU power + reduce swap
sudo ./tune-system.sh
```

## Documentation
- [docs/00-SETUP.md](docs/00-SETUP.md) — replicate the environment from scratch.
- [docs/01-TUNING-HIBRIDO.md](docs/01-TUNING-HIBRIDO.md) — VRAM+RAM, thermal, SSD.
- [docs/02-TROUBLESHOOTING.md](docs/02-TROUBLESHOOTING.md) — known issues.
- [docs/03-AGENTE.md](docs/03-AGENTE.md) — how the project is agentic and how to extend it.

## GPU: Intel vs NVIDIA
The machine has an Intel iGPU + GTX 1060. The scripts force the NVIDIA GPU via
`GGML_VK_VISIBLE_DEVICES=1`. To list the devices:

```bash
./llama.cpp/build/bin/llama-cli --list-devices
```

## Tips for 6 GB of VRAM (hybrid VRAM+RAM mode)
- `NGL=99` (all layers on the GPU) fits for 7B Q4_K_M models.
- Model larger than 6GB: partial offload, the rest on RAM/CPU: `NGL=20 ./start-server.sh large-model.gguf`.
- Adjust the context if memory runs short: `CTX=4096 ./start-server.sh`.
- `--load-mode mmap+mlock` (default) locks the model in RAM and avoids SSD I/O.
- Full details in [docs/01-TUNING-HIBRIDO.md](docs/01-TUNING-HIBRIDO.md).

## Rebuild llama.cpp (e.g. after `git pull`)
```bash
conda activate llama-vulkan
cd llama.cpp
cmake -B build -G Ninja -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_CURL=OFF -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DCMAKE_CXX_FLAGS="-I$CONDA_PREFIX/include"
cmake --build build --config Release -j"$(nproc)"
```
> The `-DCMAKE_CXX_FLAGS="-I$CONDA_PREFIX/include"` flag is required so the
> compiler can find `spirv/unified1/spirv.hpp` (SPIRV-Headers from conda).

## Recreate the conda environment
```bash
conda env create -f environment.yml
```

## License
This project is licensed under the **MIT License** — see [LICENSE](LICENSE).

> Note: the upstream `llama.cpp/` folder is a separate project with its own
> license (MIT, by the ggml-org authors) and is not covered by this repository.

Copyright (c) 2026 Mauro Risonho de Paula Assumpção
