#!/bin/bash
# _t5_q64.sh --- t5B6np 生存性检查
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 所有引擎进程 ──'
ps -eo pid,etime,time,pcpu,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v grep | while read -r PID ET TM CPU REST; do
  TAG=$(printf '%s' "$REST" | sed -n 's/.*--tag \([A-Za-z0-9_]*\).*/\1/p')
  echo "  pid=$PID tag=${TAG:-?} etime=$ET cpu_time=$TM %cpu=$CPU"
done
echo '── t5B6np 进度 ──'
printf '  末步 = %s ｜ Vt 行数 = %s ｜ 事件 = %s ｜ 快照 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5B6np/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -cE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B6np.log 2>/dev/null)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_t5B6np.log 2>/dev/null)" \
  "$(ls -1 _exp/_bk_t5/dry_t5B6np/snap_*.npz 2>/dev/null | wc -l)"
echo '── 日志最后修改 / 现在 ──'
stat -c '  日志 %y' _w2_t5_short_t5B6np.log 2>/dev/null
date '+  现在 %F %T'
echo '── Vt 尾部 3 行 ──'
grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B6np.log 2>/dev/null | tail -3 | cut -c1-120 | sed 's/^/  /'
echo '── 日志尾部 3 行 ──'
tail -3 _w2_t5_short_t5B6np.log 2>/dev/null | cut -c1-150 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
