#!/bin/bash
# _r1_status.sh --- 一行一算例的进度速查（避免 PowerShell 吞掉 $ 变量）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
printf '%-18s %8s %10s %10s  %s\n' DIR ROWS LASTSTEP ELAPSED LOGTAIL
for d in "$@"; do
  if [ -f "_exp/$d/series.csv" ]; then
    R=$(wc -l < "_exp/$d/series.csv")
    L=$(tail -1 "_exp/$d/series.csv" | cut -d, -f1)
  else
    R=0; L="NO_CSV"
  fi
  E=$(grep -oE '已用 *[0-9.]+ *h|elapsed *[0-9.]+' "_exp/$d/log.txt" 2>/dev/null | tail -1)
  T=$(tail -2 "_exp/$d/log.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-70)
  printf '%-18s %8s %10s %10s  %s\n' "$d" "$R" "$L" "$E" "$T"
done
echo "--- 进程 ---"
ps -e -o pid,etime,pcpu,rss,args --no-headers \
  | grep -E '_r1_exp\.py|_r1_drive3|_r1_waitdx|_r1_series' | grep -v grep \
  | sed -E 's#--(out|steps|N) #--\1 #g' | cut -c1-150
