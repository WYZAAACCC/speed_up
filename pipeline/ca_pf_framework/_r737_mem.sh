#!/usr/bin/env bash
# _r737_mem.sh —— 实测当前 `_bk_exp.py` 的 RSS 与内存总况（M-0 判据的实测部分）。
set -uo pipefail
echo "=== _bk_exp.py 进程（含 VmRSS）==="
FOUND=0
for P in $(pgrep -f '[_]bk_exp.py'); do
  FOUND=1
  RSS=$(grep VmRSS /proc/$P/status 2>/dev/null | awk '{print $2}')
  echo "  pid=$P  RSS=$((RSS/1024)) MB  etime=$(ps -o etime= -p $P | tr -d ' ')  cpus=$(grep Cpus_allowed_list /proc/$P/status | awk '{print $2}')"
  echo "    tag: $(ps -o args= -p $P | grep -o -- '--tag [A-Za-z0-9_]*')"
done
[ $FOUND -eq 0 ] && echo "  （无 _bk_exp.py）"
echo
echo "=== 内存总况 ==="
free -m | sed 's/^/  /'
echo
echo "=== launcher ==="
pgrep -af '_r736_ab2' | sed 's/^/  /' || echo "  （无）"
echo
echo "=== 各臂 series.csv ==="
for t in S_off S_on; do
  f=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq200/dry_$t/series.csv
  if [ -f "$f" ]; then echo "  $t: $(wc -l < "$f") 行  mtime=$(date -r "$f" '+%H:%M:%S')"; else echo "  $t: 尚无"; fi
done
echo "  now = $(date '+%H:%M:%S')"
