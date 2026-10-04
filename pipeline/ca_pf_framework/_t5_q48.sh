#!/bin/bash
# _t5_q48.sh --- t5B12N 快速状态
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12N' | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  ps -o pid,etime,time,stat,%cpu --no-headers -p "$P" | sed 's/^/  进程 /'
else
  echo '  ⚠ 进程不在'
fi
printf '  末步 = %s ｜ Vt 行 = %s ｜ 形核事件 = %s ｜ 被拒 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5B12N/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -cE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B12N.log 2>/dev/null)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_t5B12N.log 2>/dev/null)" \
  "$(grep -c '被引擎拒' _w2_t5_short_t5B12N.log 2>/dev/null)"
echo '  ── 日志尾部 ──'
tail -4 _w2_t5_short_t5B12N.log 2>/dev/null | cut -c1-165 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
