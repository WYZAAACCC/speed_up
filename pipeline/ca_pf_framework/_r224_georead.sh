#!/bin/bash
# _r224_georead.sh —— 从 `_r223` 的日志里抽出 **B-1（块间 nf2(t=0)=0）** 与其它验收量。
cd "$(dirname "$0")" || exit 1
echo "=== 每个候选的验收行 ==="
for t in m2a m2b m4a m4b m4c m4d m6a m6b m6c m6d; do
  f="_w2_r223_${t}.log"
  [ -f "$f" ] || { printf '  %-6s (无日志)\n' "$t"; continue; }
  line=$(grep -E '接触面|分离' "$f" | tail -1)
  cov=$(grep -o 'cov_norm` = [0-9.]*' "$f" | tail -1 | sed 's/.*= //')
  occ=$(grep -o 'n_occ` = [0-9]*/[0-9]*' "$f" | tail -1 | sed 's/n_occ` = //')
  nf3=$(grep -o 'nf3col=[0-9]*' "$f" | tail -1 | sed 's/nf3col=//')
  printf '  %-6s cov_norm=%-7s n_occ=%-6s nf3col=%-4s | %s\n' \
    "$t" "${cov:-?}" "${occ:-?}" "${nf3:-?}" "${line:-（无接触面行）}"
done
echo
echo "=== 一个样本的完整验收段（m6a）==="
grep -B2 -A4 '块内界面自检' _w2_r223_m6a.log | head -14
