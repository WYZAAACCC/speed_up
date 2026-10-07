#!/bin/bash
# _r262_steptime.sh —— 量各臂的**实际步时**（判断 `--facet-proj 0` 是不是真的更贵）。
cd "$(dirname "$0")" || exit 1
echo "=== 各臂日志里的 's/步' ==="
for f in _w2_r253_L0.log _w2_r253_P0.log _w2_r225_p45L.log _w2_r225_p45P.log \
         _w2_r210_saOddGDT_run.log _w2_r240_run.log; do
  [ -f "$f" ] || { printf '  %-28s (不存在)\n' "$f"; continue; }
  last=$(grep -o '[0-9.]*s/步' "$f" | tail -3 | tr '\n' ' ')
  printf '  %-28s 最近步时: %s\n' "$f" "$last"
done
echo
echo "=== 运行时长 vs 步数（粗估每秒步数）==="
for d in p45L p45P p45L0 p45P0 saSet2EDV; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  [ -f "$f" ] || continue
  st=$(tail -1 "$f" | cut -d, -f1)
  t=$(tail -1 "$f" | cut -d, -f3)
  printf '  %-10s step=%-5s wall_s=%-10s ⇒ %s s/步\n' "$d" "$st" "$t" \
    "$(/root/miniconda3/envs/ml/bin/python -c "
import sys
try:
    print('%.2f' % (float('$t')/max(int('$st'),1)))
except Exception:
    print('?')")"
done
echo
echo "=== 进程与其 CPU/线程 ==="
ps -eo pid,etime,pcpu,nlwp,rss,args --sort=-pcpu 2>/dev/null \
  | grep '_bk_exp[.]py' | grep -v grep \
  | sed 's/--arm dry.*--tag/...--tag/' | head -8
echo
echo "=== 负载 ==="
uptime
nproc
free -m | head -2
