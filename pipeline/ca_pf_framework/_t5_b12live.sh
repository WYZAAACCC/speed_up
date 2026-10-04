#!/bin/bash
# _t5_b12live.sh --- 查 `t5B12` 是否在正常推进
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo '── 内存 ──'
free -m | sed -n 2p | sed 's/^/  /'
echo '── 日志尾部（看是否在算）──'
tail -6 _w2_t5_short_t5B12.log 2>/dev/null | cut -c1-175 | sed 's/^/  /'
echo '── 步进行数 ──'
printf '  Vt 行数 = %s\n' "$(grep -cE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B12.log 2>/dev/null)"
echo '── 三项诊断（--diag-terms 已开）──'
grep -c '三项量级' _w2_t5_short_t5B12.log 2>/dev/null | sed 's/^/  诊断块数 = /'
grep -E 'Δed 带符号|F1 含母相' _w2_t5_short_t5B12.log 2>/dev/null | tail -4 | cut -c1-185 | sed 's/^/  /'
echo '── 形核事件 ──'
grep -cE '模式 \*\*' _w2_t5_short_t5B12.log 2>/dev/null | sed 's/^/  事件数 = /'
