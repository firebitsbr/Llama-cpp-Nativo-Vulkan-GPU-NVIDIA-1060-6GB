<!--
Author: Mauro Risonho de Paula Assumpção
Creation Date: 2026-10-01
Update Date: 2026-10-01
Short Description: Setup guide for the native llama.cpp (Vulkan) environment on the GTX 1060.
LICENSE MIT
-->
# Setup — Native Llama.cpp (Vulkan) on the GTX 1060 6GB

Complete guide to **replicate the environment from scratch**. Tested on Ubuntu 24.04,
kernel 7.0, i7-7700HQ + GTX 1060 Mobile 6GB, NVIDIA driver 580.

## 0. System prerequisites

Confirm the NVIDIA driver (provides the Vulkan ICD) and the Vulkan headers:

```bash
nvidia-smi                       # driver 580+ , GTX 1060
vulkaninfo --summary | grep deviceName   # should list the NVIDIA
dpkg -l | grep libvulkan-dev     # system Vulkan headers/loader
gcc --version && git --version   # base toolchain
```

If something is missing:
```bash
sudo apt install -y libvulkan-dev vulkan-tools build-essential git
```

## 1. Conda environment with build toolchain

> Note: the anaconda base here is Python 3.14 (too new for AI libs),
> so we create a dedicated environment on **Python 3.11**.

```bash
conda create -y -n llama-vulkan -c conda-forge \
  python=3.11 cmake ninja shaderc spirv-headers git pkg-config
conda activate llama-vulkan
```

- `shaderc` provides **glslc** (the shader compiler).
- `spirv-headers` is **required** by the current llama.cpp Vulkan backend.

## 2. Clone and build llama.cpp with Vulkan

```bash
cd /home/test/Downloads/Github/Llama-cpp-Nativo-Vulkan-GPU-NVIDIA-1060-6GB
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
cd llama.cpp

cmake -B build -G Ninja \
  -DGGML_VULKAN=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_CURL=OFF \
  -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DCMAKE_CXX_FLAGS="-I$CONDA_PREFIX/include"

cmake --build build --config Release -j"$(nproc)"
```

> **Why `-DCMAKE_CXX_FLAGS="-I$CONDA_PREFIX/include"`?**
> `ggml-vulkan-types.h` does `#if __has_include(<spirv/unified1/spirv.hpp>)`,
> but the llama.cpp CMake **does not** propagate the SPIRV-Headers include dir.
> Without this flag the build fails with `'spv' has not been declared`.

Binaries are generated in `llama.cpp/build/bin/`: `llama-cli`, `llama-server`,
`llama-bench`, `llama-quantize`, ...

### Verify the GPU
```bash
./build/bin/llama-cli --list-devices
# Vulkan0: Intel(R) HD Graphics 630   (iGPU)
# Vulkan1: NVIDIA GeForce GTX 1060    (<- this one)
```

## 3. Download a model (GGUF)

```bash
cd ..
mkdir -p models
hf download bartowski/Qwen2.5-7B-Instruct-GGUF \
  Qwen2.5-7B-Instruct-Q4_K_M.gguf --local-dir models
```

## 4. Python stack (minimal and local)

The agent uses only the **standard library** (urllib) to talk to the local
server — without the `openai` dependency. We only need `huggingface_hub` to
download models:

```bash
pip install "huggingface_hub[cli,hf_transfer]"
```

> Optional: if you want to use agent frameworks, `langchain`/`langgraph` are
> available, but they are not required for this project's agent.

## 5. Use

```bash
conda activate llama-vulkan
./start-server.sh                 # local HTTP server at http://127.0.0.1:8080/v1
./chat.sh                         # terminal chat
python examples/tool_calling.py   # tool-calling example
./monitor.sh                      # real-time temperatures/VRAM
```

## 6. Reproduce the environment on another machine

```bash
conda env create -f environment.yml    # recreates the conda env
# then repeat steps 2 and 3 (build llama.cpp + download the model)
```

See [01-TUNING-HIBRIDO.md](01-TUNING-HIBRIDO.md) for VRAM+RAM/thermal/SSD
and [02-TROUBLESHOOTING.md](02-TROUBLESHOOTING.md) for known issues.
