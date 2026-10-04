#!/bin/bash
# _t5_q83.sh --- 两臂进度 + burst 序列
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5BK1 t5B6np; do
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $t" | grep -v grep | awk '{print $1}' | head -1)
  printf '  %-8s 末步=%-6s 事件=%-4s 快照=%-3s 进程=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -cE '模式 \*\*' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)" \
    "${P:-无}"
done
echo
echo '════ ★ burst 每档核数（新 vs 旧）════'
/root/miniconda3/envs/ml/bin/python _t5_burstcnt.py 2>&1 | head -22
echo
free -m | sed -n 2p | sed 's/^/  /'
