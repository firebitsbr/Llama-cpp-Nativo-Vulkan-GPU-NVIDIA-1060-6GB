<!--
Author: Mauro Risonho de Paula Assumpção
Creation Date: 2026-10-01
Update Date: 2026-10-01
Short Description: Hybrid tuning guide (VRAM+RAM), thermal and SSD-friendly.
LICENSE MIT
-->
# Hybrid Tuning — VRAM 6GB + RAM 64GB, Thermal and SSD

Goal: use **GPU (6GB) + RAM (64GB)** without saturating resources, keeping
**CPU/GPU ideally ≤ 80°C** and **no SSD I/O during inference**
(to extend the SSD's life).

Reference hardware: **i7-7700HQ (4 physical cores / 8 threads)** laptop +
**GTX 1060 Mobile (88W power cap)**. The thermal bottleneck is the **CPU**, which
already sits at ~80°C baseline. That's why the golden rule is:

> **Push as much as possible to the GPU and minimize CPU work.**

## 1. How hybrid mode works (`-ngl`)

`-ngl N` sets how many model layers go to the **GPU (VRAM)**; the rest stays in
**RAM and is processed by the CPU**.

| Situation | `-ngl` | Where it runs |
|---|---|---|
| Model fits in VRAM (e.g. 7B Q4 ≈ 4.4GB) | `99` (all) | 100% GPU |
| Model larger than 6GB (e.g. 14B/32B) | partial (e.g. 20) | GPU + RAM/CPU |

**VRAM rule of thumb:** leave **~1GB free** (the display uses ~400MB). Target ≈ 5GB
for weights + KV-cache on the GPU. Adjust `-ngl` while watching `./monitor.sh`.

Estimate the layers that fit (approximate):
```
gpu_layers ≈ (free_VRAM_GB - KV_cache_GB) / (model_size_GB / n_layers)
```
In practice: start with an `NGL` and raise/lower it watching the VRAM in the monitor.

### Examples
```bash
# 7B Q4 (everything fits) — default
./start-server.sh

# 14B Q4 model (~8.5GB): partial offload, rest in RAM
NGL=20 CTX=4096 ./start-server.sh models/model-14b-q4.gguf
```

## 2. Don't saturate the CPU (heat + stalls)

- **Threads = physical cores (4)**, not 8. Hyperthreading generates more heat with
  little inference gain. It is already the default (`THREADS=4`).
- To prioritize system responsiveness, use **3**:
  ```bash
  THREADS=3 ./start-server.sh
  ```
- **Smaller micro-batch** (`-ub 256`) smooths the heat spikes. Already the default.

## 3. Don't use the SSD (extend its life)

- `--load-mode mmap+mlock` (default when `MLOCK=1`): maps the model and
  **locks it in RAM**. Once loaded, **there are no SSD re-reads** during
  inference. With 64GB of RAM there is plenty of room.
- **Avoid swap** (swap writes to the SSD). Lower `vm.swappiness` and, if possible,
  keep the model locked (mlock already prevents it from going to swap):
  ```bash
  sudo ./tune-system.sh     # applies swappiness=10 and the GPU power-limit
  ```
- If a model is **larger than the mlock limit** (`ulimit -l` ≈ 8GB here),
  mlock fails. In that case turn it off:
  ```bash
  MLOCK=0 ./start-server.sh models/large-model.gguf
  ```
  (or raise the limit in `/etc/security/limits.conf`: `* hard memlock unlimited`).

## 4. Staying ≤ 80°C

The realistic path on a laptop:

1. **Cap the GPU power** (less heat, minimal performance loss):
   ```bash
   sudo nvidia-smi -pl 70        # HW cap is 88W; 70W runs much cooler
   ```
   (done by `./tune-system.sh`). Revert: `sudo nvidia-smi -pl 88`.
2. **Limit the CPU threads** (see section 2) — the main heat source.
3. **Monitor and protect** with automatic shutdown:
   ```bash
   KILL_TEMP=90 ./monitor.sh     # stops llama if CPU or GPU >= 90°C
   ```
   > Honest note: on this laptop the **CPU easily hits ~80°C** under load.
   > A hard 80°C ceiling on the CPU at full load isn't realistic without *undervolt*.
   > The strategy here (everything on the GPU + few threads + power-limit) keeps the
   > CPU nearly idle, which is what actually holds the temperature down.
4. **CPU undervolt** (optional, out of scope for these scripts): tools like
   `intel-undervolt` cut the 7700HQ temperature significantly.

## 5. Context (`CTX`) and memory

- Larger context = more KV-cache = more VRAM/RAM and more heat.
- `--flash-attn auto` (default) **reduces the KV-cache** and helps fit more context.
- Lower `CTX` if VRAM runs short: `CTX=4096 ./start-server.sh`.

## 6. Suggested "cool" profile

```bash
# GPU capped at 70W + low swappiness (once):
sudo ./tune-system.sh

# Conservative server:
THREADS=3 CTX=4096 UBATCH=128 ./start-server.sh

# In another terminal, watching with protection:
KILL_TEMP=88 ./monitor.sh
```

## Quick variable reference

| Var | Default | Effect |
|---|---|---|
| `NGL` | 99 | GPU layers (lower = more on RAM/CPU) |
| `CTX` | 8192 | context size |
| `THREADS` | 4 | CPU threads (= physical cores) |
| `BATCH`/`UBATCH` | 512/256 | prompt batch / micro-batch |
| `MLOCK` | 1 | locks the model in RAM (no SSD I/O) |
| `PORT`/`HOST` | 8080/127.0.0.1 | API address |
