#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: System tweaks for thermal control and SSD preservation.
# LICENSE MIT
# -----------------------------------------------------------------------------
# System tweaks to control temperature and spare the SSD.
# REQUIRES sudo. Run it yourself:  sudo ./tune-system.sh
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"   # re-exec under bash if invoked with sh
#
# What it does (all reversible, not persisted after reboot unless noted):
#   1. Caps the GPU power (less heat). Default 70W (HW cap is 88W).
#   2. Lowers vm.swappiness (avoids writing to the SSD swap).
#   3. Shows how to persist.
set -eu

GPU_WATTS="${GPU_WATTS:-70}"       # 70W keeps the 1060 Mobile cooler (cap=88W)
SWAPPINESS="${SWAPPINESS:-10}"     # less swap -> less SSD writes

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run with sudo:  sudo ./tune-system.sh" >&2
  exit 1
fi

echo "[1/3] Capping GPU power to ${GPU_WATTS}W..."
nvidia-smi -pm 1 >/dev/null 2>&1 || true      # persistence mode
nvidia-smi -pl "$GPU_WATTS" || echo "  (failed - some drivers lock the power limit)"

echo "[2/3] Setting vm.swappiness=${SWAPPINESS}..."
sysctl -w vm.swappiness="$SWAPPINESS"

echo "[3/3] Done. To PERSIST after reboot:"
echo "  - swappiness: echo 'vm.swappiness=${SWAPPINESS}' | sudo tee /etc/sysctl.d/99-llama.conf"
echo "  - GPU power:  create a systemd service running 'nvidia-smi -pl ${GPU_WATTS}' at boot"
echo
echo "Revert: sudo nvidia-smi -pl 88 ; sudo sysctl -w vm.swappiness=60"
