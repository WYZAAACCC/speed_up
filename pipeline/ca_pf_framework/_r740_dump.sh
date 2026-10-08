#!/usr/bin/env bash
# _r740_dump.sh <root> <tag...> —— 逐臂 dump `nuc_dbg.json` 的关键键（判"通道是否触发"）。
set -uo pipefail
cd /mnt/f/speed_up/pipeline/ca_pf_framework
ROOT="$1"; shift
PY=/root/miniconda3/envs/ml/bin/python
for T in "$@"; do
  echo "########## $T ##########"
  "$PY" -u _r740_keys.py "$ROOT" "$T" 2>&1 \
    | grep -E 'n_events_by_mode|n_events_by_requested|^  (fresh|stack|attach)|n_fresh_fallback|n_eng_ev|pending_fresh|nuc_iface_nucleation|nfsv|block_edge|sites_refilled|n_activated|iface_|^  (ok|cov|att|exc|nocand|oob)' \
    | sed 's/^/  /'
  echo
done
