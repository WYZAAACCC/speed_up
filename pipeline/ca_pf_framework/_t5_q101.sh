#!/bin/bash
# _t5_q101.sh --- 三臂进度 + 步对齐比较（有快照就比）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
for t in t5N276F t5FIX t5ETAo t5BKMo; do
  P=$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -c -- "--tag $t")
  printf '  %-9s 末步=%-6s 快照=%-3s 进程=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)" \
    "$([ "$P" -gt 0 ] && echo 在 || echo 停)"
done
echo
echo '════ ★ 步对齐四项（同一 step）════'
timeout 1500 $PY _t5_aralign.py 400,480,560,640 2>&1 | sed -n '4,10p'
echo
echo '════ ★ 若无修复臂快照，则先比对照自身的时间演化 ════'
echo '  （对照宽比：200→6.76 · 320→6.40 · 400→6.54 · 480→6.13 · 终态→3.28–3.38 ⇒ 退化 −49%）'
free -m | sed -n 2p | sed 's/^/  /'
