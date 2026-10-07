#!/usr/bin/env bash
# _r333_prog3.sh -- 正确目录名（dry_<tag>）下的进度
D=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb
echo "=== arms (dry_<tag>) ==="
for n in dry_saSet2P0 dry_saSet2F2P0 dry_near200 dry_mid200 dry_far200 dry_saSet2EDV; do
  d="$D/$n"
  if [ ! -d "$d" ]; then printf "%-18s (no dir)\n" "$n"; continue; fi
  f="$d/snapshots.csv"
  if [ -f "$f" ]; then
    nl=$(wc -l < "$f")
    last=$(tail -1 "$f" | cut -d, -f1-3)
    printf "%-18s lines=%-5s last=%s\n" "$n" "$nl" "$last"
  else
    printf "%-18s files: %s\n" "$n" "$(ls "$d" | tr '\n' ' ')"
  fi
done
echo
echo "=== newest files in dry_saSet2P0 ==="
ls -lat --time-style=+%H:%M "$D/dry_saSet2P0" | head -8
echo "=== newest files in dry_near200 ==="
ls -lat --time-style=+%H:%M "$D/dry_near200" | head -8
