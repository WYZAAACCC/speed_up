#!/bin/bash
# _r103_chk.sh —— R103 启动与内存核对
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date '+%F %T')"
echo "_bk_exp 进程数：$(ps -eo args --no-headers | grep -c '[_]bk_exp.py')"
ps -eo pid,etimes,rss,args --no-headers | grep '[_]bk_exp.py' | \
  awk '{printf "  pid=%-7s %5ss  rss=%6.0f MB  tag=%s\n", $1, $2, $3/1024, $NF}'
echo
echo "--- 空闲内存 ---"
free -g | head -2
echo
echo "--- 日志 ---"
for t in saPair saOdd saPairE0; do
  L="_w2_r103_${t}.log"
  if [ -f "$L" ]; then
    printf -- '--- %-9s %s B  %s\n' "$t" "$(stat -c %s "$L")" "$(stat -c %y "$L" | cut -c1-19)"
    grep -E "多块播种|block-gap|精确判据|播种后|^   块[0-9]：|dt=" "$L" | head -5
    tail -1 "$L" | cut -c1-140
  else
    printf -- '--- %-9s （日志未出现）\n' "$t"
  fi
done
echo
echo "--- 数据目录 ---"
for t in saPair saOdd saPairE0; do
  d="_exp/_bk_mb/dry_$t"
  [ -d "$d" ] && printf '  %-9s 快照 %s\n' "$t" "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
done
echo
echo "--- 启动脚本输出 ---"
cat _w2_r103_run.log 2>/dev/null || echo "（无 _w2_r103_run.log）"
