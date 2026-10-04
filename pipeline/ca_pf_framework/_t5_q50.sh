#!/bin/bash
# _t5_q50.sh --- 查 t5B6 是否在推进（判"卡住" vs "首次形核贵"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B6' | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  ps -o pid,etime,time,stat,%cpu --no-headers -p "$P" | sed 's/^/  进程 /'
else
  echo '  ⚠ 进程不在'
fi
printf '  末步 = %s ｜ Vt 行 = %s ｜ 快照 = %s ｜ 事件 = %s ｜ 被拒 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5B6/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -cE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B6.log 2>/dev/null)" \
  "$(ls -1 _exp/_bk_t5/dry_t5B6/snap_*.npz 2>/dev/null | wc -l)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_t5B6.log 2>/dev/null)" \
  "$(grep -c '被引擎拒' _w2_t5_short_t5B6.log 2>/dev/null)"
echo '  ── 日志尾部（看是否在算）──'
tail -4 _w2_t5_short_t5B6.log 2>/dev/null | cut -c1-170 | sed 's/^/  /'
echo '  ── 日志最后修改时间 ──'
stat -c '  %y' _w2_t5_short_t5B6.log 2>/dev/null
echo '  ── 对照：t5N276F（同 nv=276）的构造耗时参照 ──'
grep -nE 'ckpt.*ckpt_A.npz' _w2_t5_short_t5N276F.log 2>/dev/null | head -2 | cut -c1-140 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
