#!/bin/bash
# _t5_q72.sh --- t5B6np 是否卡住？（对比历史日志写入间隔与 CPU 时间增长）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep 't5B6np' | grep -v grep | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  ps -o pid,etime,time,pcpu,stat --no-headers -p "$P" | sed 's/^/  进程 /'
  echo "  （第 3 列 = 累计 CPU 时间；若它在增长 ⇒ 在算；若不动 ⇒ 卡）"
else
  echo '  ⚠ 进程不在'
fi
echo '── 日志写入时间 / 现在 ──'
stat -c '  日志 %y' _w2_t5_short_t5B6np.log 2>/dev/null
date '+  现在 %F %T'
echo '── 末步 / Vt 行数 / 快照 ──'
printf '  末步 = %s ｜ Vt 行数 = %s ｜ 快照 = %s ｜ 事件 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5B6np/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -cE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B6np.log 2>/dev/null)" \
  "$(ls -1 _exp/_bk_t5/dry_t5B6np/snap_*.npz 2>/dev/null | wc -l)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_t5B6np.log 2>/dev/null)"
echo '── 历史写入节奏（Vt 行的 step 号）──'
grep -oE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B6np.log 2>/dev/null | grep -oE '[0-9]+' | tr '\n' ' ' | sed 's/^/  /'
echo
echo '── 日志尾部（看是否在算某一步）──'
tail -2 _w2_t5_short_t5B6np.log 2>/dev/null | cut -c1-170 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
