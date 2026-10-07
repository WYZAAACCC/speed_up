#!/bin/bash
# _r427_watch.sh —— A/B 双臂进度监控（只读，不干扰仿真）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== $(date '+%F %T') ==="
for t in abA abB; do
  f="_r426_${t}.log"
  d="_exp/_bk_mb/dry_${t}"
  echo "---- 臂 $t"
  if [ -f "$f" ]; then
    echo "   日志行数 = $(wc -l < "$f")"
    grep -c 'athermal 形核' "$f" 2>/dev/null | sed 's/^/   形核事件数 = /'
    grep -c 'Traceback' "$f" 2>/dev/null | sed 's/^/   Traceback = /'
    grep -E '^\s*\[ *[0-9]+\]' "$f" | tail -1 | sed 's/^/   末行: /'
  else
    echo "   ✗ 无日志"
  fi
  if [ -f "$d/series.csv" ]; then
    echo "   CSV 行数 = $(($(wc -l < "$d/series.csv") - 1))"
    "$PY" -c "
import csv
rows=list(csv.DictReader(open('$d/series.csv')))
r=rows[-1]
print('   step=%s  Vt=%s  nslab=%s  nf3=%s  nf2=%s' % (r.get('step'), r.get('Vt'), r.get('nslab_n'), r.get('nf3'), r.get('nf2')))
print('   blk_nprof =', r.get('blk_nprof'))
print('   blk_laths =', r.get('blk_laths'))
"
  else
    echo "   （尚无 series.csv —— 还在构造/播种阶段）"
  fi
  # ⚠ 自纠错：`pgrep -f "--tag $t"` 会被引号搞坏（"only one pattern can be provided"）。
  #   改用 `pgrep -f` 单一模式 + `awk` 过滤，且**按 cwd/命令行**双重确认。
  _P=$(ps -eo pid=,etime=,rss=,args= | grep -F -- "--tag $t" | grep -v grep | head -1)
  if [ -n "$_P" ]; then
    echo "$_P" | awk '{printf "   进程: pid=%s 已跑=%s RSS=%.2f GB\n", $1, $2, $3/1048576}'
  else
    echo "   进程已退出（或已跑完）"
  fi
done
echo "=== 内存 ==="
free -g | head -2
