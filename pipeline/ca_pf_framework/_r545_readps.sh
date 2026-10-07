#!/usr/bin/env bash
# _r545_readps.sh —— 读周期播种 A/B（`--nuc-periodic-seed 1`）的对照读数
set -u
cd "$(dirname "$0")"
echo "===== 并行驱动汇总 ====="
tail -14 _w2_r544b_par.log
echo
for t in ps_b8 ps_b3; do
  echo "===== $t ====="
  f="_w2_r537_$t.log"
  [ -f "$f" ] || { echo "  缺 $f"; continue; }
  echo -n "  拒绝行数: "; grep -c '被引擎拒' "$f" || true
  echo -n "  事件行数: "; grep -c '形核\*\* @ step' "$f" || true
  echo "  dbg（末尾那条）:"
  grep -o "dbg={[^}]*}" "$f" | tail -1 | tr ',' '\n' | sed 's/^ */    /'
  echo "  末态:"
  grep -n '^  \[' "$f" | tail -1 | cut -c1-200
  echo
done
echo "===== 末态逐块判据（C3）====="
for t in ps_b8 ps_b3; do
  echo "-- $t --"
  grep -A4 '每块板条数(定义)' "_w2_r537_$t.log" | tail -4
done
