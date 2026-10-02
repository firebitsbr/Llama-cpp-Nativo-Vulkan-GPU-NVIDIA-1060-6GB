#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Author: Mauro Risonho de Paula Assumpção
# Creation Date: 2026-10-01
# Update Date: 2026-10-01
# Short Description: Real-time thermal and resource monitor (GPU/CPU/VRAM/RAM).
# LICENSE MIT
# -----------------------------------------------------------------------------
# Real-time thermal + resource monitor (GPU/CPU/VRAM/RAM).
# Shows a warning above 80°C and, optionally, protects the hardware.
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"   # re-exec under bash if invoked with sh
#
# Usage:           ./monitor.sh
# Auto protection: KILL_TEMP=90 ./monitor.sh   (kills llama-server if CPU or GPU >= 90°C)
set -u

WARN="${WARN:-80}"          # °C: warning level
KILL_TEMP="${KILL_TEMP:-0}" # °C: 0 = disabled. If >0, stops llama when reached.
INTERVAL="${INTERVAL:-2}"

have_sensors=0; command -v sensors >/dev/null && have_sensors=1

cpu_temp() {
  if [[ $have_sensors == 1 ]]; then
    sensors 2>/dev/null | awk -F'[+°]' '/Package id 0/{print int($2); exit}'
  else
    local t; t=$(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | sort -rn | head -1)
    [[ -n "$t" ]] && echo $((t/1000)) || echo 0
  fi
}

printf "%-8s %-7s %-7s %-14s %-12s %s\n" "TIME" "GPU°C" "CPU°C" "VRAM(MiB)" "GPU%" "STATUS"
while true; do
  read -r gtemp gutil vused vtotal < <(nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total \
      --format=csv,noheader,nounits 2>/dev/null | tr ',' ' ')
  ctemp=$(cpu_temp)
  status="ok"
  (( ${gtemp:-0} >= WARN || ${ctemp:-0} >= WARN )) && status="HOT (>=${WARN}C)"

  printf "%-8s %-7s %-7s %-14s %-12s %s\n" "$(date +%H:%M:%S)" \
     "${gtemp:-?}" "${ctemp:-?}" "${vused:-?}/${vtotal:-?}" "${gutil:-?}" "$status"

  if (( KILL_TEMP > 0 )) && (( ${gtemp:-0} >= KILL_TEMP || ${ctemp:-0} >= KILL_TEMP )); then
    echo ">> PROTECTION: temperature >= ${KILL_TEMP}C. Stopping llama-server/llama-cli..."
    pkill -INT -f 'llama-server' 2>/dev/null
    pkill -INT -f 'llama-cli'    2>/dev/null
    break
  fi
  sleep "$INTERVAL"
done
