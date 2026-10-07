#!/usr/bin/env bash
# _r555_wait.sh —— 等 4 µm C1–C6 算例组（f32）跑完并打印对照
set -u
cd "$(dirname "$0")"
for i in $(seq 1 40); do
  n=$(pgrep -f 'tag c6_' | wc -l)
  [ "$n" -eq 0 ] && { echo "（第 $i 次轮询：已无 c6_* 进程）"; break; }
  sleep 60
done
echo
tail -12 _w2_r555_par.log
echo
for t in c6_b4f32 c6_b8f32; do
  echo "===== $t ====="
  f="_w2_r537_$t.log"
  [ -f "$f" ] || { echo "  缺 $f"; continue; }
  echo -n "  拒绝行数: "; grep -c '被引擎拒' "$f" || true
  echo -n "  事件行数: "; grep -c '形核\*\* @ step' "$f" || true
  grep -o "dbg={[^}]*}" "$f" | tail -1 | tr ',' '\n' | sed 's/^ */    /' | head -30
  grep -n '每块板条数(定义)' -A4 "$f" | tail -4
  grep -n '^  \[' "$f" | tail -1 | cut -c1-170
  echo
done
