#!/bin/bash
# _t5_final_state.sh --- ★ t5H3 结束后的**全状态核查**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 进程（还有谁在跑）════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '[_]bk_exp.py|[_]t5_auto_judge|[_]t5_wait' \
  | sed 's/^/  /' | cut -c1-92
echo
echo '════ ② 两臂末态 ════'
for t in t5H3 t5V2; do
  printf '  ── %s ──\n' "$t"
  printf '     末步 = %s   行数 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(wc -l < _exp/_bk_t5/dry_$t/series.csv 2>/dev/null)"
  printf '     形核=%s fresh=%s 被拒=%s   模式: %s\n' \
    "$(grep -c 'athermal 形核' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -c '模式 \*\*fresh\*\*' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -c '被引擎拒' _w2_t5_short_$t.log 2>/dev/null)" \
    "$(grep -oE '模式 \*\*[a-z]+\*\*' _w2_t5_short_$t.log 2>/dev/null | sort | uniq -c | tr '\n' ' ')"
done
echo
echo '════ ③ t5H3 结束原因（日志末尾）════'
tail -6 _w2_t5_short_t5H3.log 2>/dev/null | cut -c1-118 | sed 's/^/  /'
echo
echo '════ ④ 自动判定日志（末尾 8）════'
tail -8 _w2_t5_auto_judge.log 2>/dev/null | sed 's/^/  /'
echo
echo '════ ⑤ 内存 ════'
free -m | sed -n 2p | sed 's/^/  /'
