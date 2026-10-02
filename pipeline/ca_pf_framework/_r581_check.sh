#!/bin/bash
# _r581_check.sh --- 一次性看全：臂 / 产物 / nuc_dbg / 链 / 守卫 / 内存
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T') ==="
echo "--- 臂（ps）---"
ps -eo pid,etime,pcpu,rss,args --no-headers 2>/dev/null | grep _bk_exp.py | grep -v grep | \
  while read -r pid et rss_c pu r rest; do
    t=$(echo "$rest" | awk '{for(i=1;i<=NF;i++) if($i=="--tag") print $(i+1)}')
    printf '  tag=%-9s pid=%-7s 跑=%-9s cpu=%-5s rss=%s\n' "$t" "$pid" "$et" "$pu" "$r"
  done
echo "--- 产物 ---"
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps; do
  d="_exp/_bk_p2/dry_${t}"
  if [ -d "$d" ]; then
    n=$(ls "$d" | wc -l)
    csv=$([ -f "$d/series.csv" ] && wc -l < "$d/series.csv" || echo 0)
    dbg=$([ -f "$d/nuc_dbg.json" ] && stat -c %s "$d/nuc_dbg.json" || echo 0)
    sn=$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)
    printf '  %-9s 文件=%-3s series=%-5s nuc_dbg=%-7s 快照=%s\n' "$t" "$n" "$csv" "$dbg" "$sn"
  else
    printf '  %-9s （无目录）\n' "$t"
  fi
done
echo "--- 超期/归档目录 ---"
ls -1d _exp/_bk_p2/*superseded* 2>/dev/null | sed 's/^/  /'
echo "--- 链 / 守卫 ---"
for pat in _r581_chain _r581_softguard _r581_memguard; do
  n=$(ps -eo args --no-headers 2>/dev/null | grep "$pat" | grep -v grep | wc -l)
  printf '  %-18s 进程=%s\n' "$pat" "$n"
done
tail -2 _w2_r581_chain.log 2>/dev/null | sed 's/^/    chain: /'
echo "--- 内存 ---"
free -m | sed -n 2p | awk '{printf "  已用 %s MB  可用 %s MB\n",$3,$7}'
awk '/MemAvailable/{printf "  MemAvailable = %s MB\n",$2}' /proc/meminfo
