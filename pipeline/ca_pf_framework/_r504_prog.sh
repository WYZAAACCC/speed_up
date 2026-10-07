#!/usr/bin/env bash
# R504 —— 看 abA 进度 + R503 各臂的"块数口径"启动横幅
set -u
cd "$(dirname "$0")"
echo "--- abA ---"
tail -1 _exp/_bk_mb/dry_abA/series.csv 2>/dev/null | cut -c1-44
printf '  行数: %s\n' "$(wc -l < _exp/_bk_mb/dry_abA/series.csv 2>/dev/null || echo 0)"
echo
echo "--- R503 启动横幅 ---"
for T in r503B0 r503B1 r503B8 r503BIG; do
  echo "[$T]"
  grep -E '块数口径|总根数 = B|几何上界|超过几何上界' "_w2_r503_${T}.log" 2>/dev/null \
    | head -5 | sed 's/^/    /'
done
echo
echo "--- 进程 ---"
ps -eo pid,etimes,pcpu,args --sort=-pcpu | grep '[_]bk_exp' | cut -c1-56
uptime
