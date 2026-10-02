<!--
Author: Mauro Risonho de Paula Assumpção
Creation Date: 2026-10-01
Update Date: 2026-10-01
Short Description: Record of real issues encountered and their solutions.
LICENSE MIT
-->
# Troubleshooting — real issues encountered

A log of the errors faced while assembling this environment and how they were solved.

## 1. CMake: `Could not find ... SPIRV-Headers`
```
CMake Error at ggml/src/ggml-vulkan/CMakeLists.txt:14 (find_package):
  Could not find a package configuration file provided by "SPIRV-Headers"
```
**Cause:** the Vulkan backend requires the SPIRV-Headers package.
**Solution:**
```bash
conda install -y -c conda-forge spirv-headers
# and reconfigure with -DCMAKE_PREFIX_PATH="$CONDA_PREFIX"
```

## 2. Build: `'spv' has not been declared`
```
ggml-vulkan.cpp:651: error: 'spv' has not been declared
```
**Cause:** `ggml-vulkan-types.h` includes `<spirv/unified1/spirv.hpp>` via
`__has_include`, but the llama.cpp CMake **does not** add the SPIRV-Headers
include dir to the compiler.
**Solution:** configure passing the conda include:
```bash
cmake -B build ... -DCMAKE_CXX_FLAGS="-I$CONDA_PREFIX/include"
```

## 3. Broken link: `undefined reference to llama_cli(int, char**)`
**Cause:** **two builds running at the same time in the same `build/` directory**
(one in the background + another in the foreground) corrupted objects/`.so`.
**Solution:** never run two simultaneous `cmake --build` in the same `build/`.
```bash
pkill -9 ninja; pkill -9 cmake
cmake --build build --config Release -j"$(nproc)"   # a single build
```

## 4. `error: invalid argument: --mlock`
**Cause:** in recent builds the flag became `--load-mode`.
**Solution:** use `--load-mode mmap+mlock` (already applied in the scripts).
```bash
./llama.cpp/build/bin/llama-server --help | grep -A10 load-mode
```

## 5. `error: invalid argument: -no-cnv`
**Cause:** renamed flag. For a single non-interactive answer use `-st`.
```bash
llama-cli -m model.gguf -st -p "your question"
```

## 6. `--device Vulkan1` invalid when filtering the GPU
**Cause:** with `GGML_VK_VISIBLE_DEVICES=1`, only the NVIDIA is visible and is
**remapped to `Vulkan0`**.
**Solution:** use the env var (recommended in the scripts) **or** `--device Vulkan1`
without the env var — don't mix the two.

## 7. `Can't open bumblebee display.`
**Harmless.** An Optimus/bumblebee warning (Intel iGPU + NVIDIA). It does not
affect inference via Vulkan.

## 8. `sh chat.sh` → `Illegal option -o pipefail`
**Cause:** the scripts are **bash**, not `sh` (dash).
**Solution:** run `./chat.sh` or `bash chat.sh` (never `sh chat.sh`).

## 9. A command "vanished" / ended up inside the chat
If you type a shell command while an interactive `llama-cli` is open, it becomes
a **chat message**. Exit the chat with `/exit` (or Ctrl+C) before running
commands in the shell.

## 10. `KeyboardInterrupt` in the agent traceback
**Not a bug.** It's you pressing **Ctrl+C**. Be careful when **pasting several
commands together**: `./start-server.sh` runs in the foreground (blocks the
terminal) — run the server in one terminal and the agent in **another**.

## 11. `llama-server` warnings at startup (benign)
- `security: no API key is set and CORS allows all origins` (PR #25655):
  solved by setting an API key. `start-server.sh` already passes
  `--api-key "$API_KEY"` (default `local-key`); clients use the same one via
  `API_KEY`. Change it: `API_KEY=mykey ./start-server.sh` and
  `export API_KEY=mykey`.
- `server default port will be changed to :9931 in a future release` (PR #26508):
  informational only. Since we pass `--port 8080` explicitly, we are not
  affected by the default change.
