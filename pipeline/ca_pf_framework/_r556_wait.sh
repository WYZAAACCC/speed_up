#!/usr/bin/env bash
# _r556_wait.sh —— 等 f64/f32 单变量 A/B 跑完，判决"剖面噪声是不是 f32 带来的"
set -u
cd "$(dirname "$0")"
for i in $(seq 1 40); do
  n=$(pgrep -f 'tag prec_' | wc -l)
  [ "$n" -eq 0 ] && { echo "（第 $i 次轮询：已无 prec_* 进程）"; break; }
  sleep 60
done
echo
tail -10 _w2_r556_par.log
echo
for t in prec_f64 prec_f32; do
  f="_w2_r537_$t.log"
  echo "===== $t ====="
  [ -f "$f" ] || { echo "  缺 $f"; continue; }
  echo -n "  拒绝="; grep -c '被引擎拒' "$f" || true
  echo -n "  事件="; grep -c '形核\*\* @ step' "$f" || true
  grep -n '每块板条数(定义)' -A4 "$f" | tail -4
  grep -n '^  \[' "$f" | tail -1 | cut -c1-110
  echo
done
echo "===== R1/R2 判决（噪声来源）====="
for t in prec_f64 prec_f32; do
  f="_w2_r537_$t.log"
  [ -f "$f" ] || continue
  P=$(grep -o 'blk_nprof = \[[^]]*\]' "$f" | tail -1)
  R=$(grep -o 'blk_nruns = \[[^]]*\]' "$f" | tail -1)
  echo "  $t: $P"
  echo "        $R"
done
