#!/bin/bash
# _t5_b12hang.sh --- 诊断 t5B12 是否卡住（CPU 占用 / 日志时间戳 / 内核态）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12' | awk '{print $1}' | head -1)
echo "  pid = ${P:-（无）}"
if [ -n "$P" ]; then
  echo '── CPU / 内存 / 状态 ──'
  ps -o pid,etime,time,stat,%cpu,%mem,rss --no-headers -p "$P" 2>/dev/null | sed 's/^/  /'
  echo '  （TIME = 累计 CPU 时间；若它远小于 etime ⇒ 在等待/阻塞）'
  echo '── 线程数 ──'
  ls /proc/$P/task 2>/dev/null | wc -l | sed 's/^/  threads = /'
  echo '── 是否在跑内核态（sys 时间）──'
  cat /proc/$P/stat 2>/dev/null | awk '{printf "  utime=%s jiffies  stime=%s jiffies  state=%s\n", $14, $15, $3}'
  echo '── 打开的文件（看是否在写日志）──'
  readlink /proc/$P/fd/1 2>/dev/null | sed 's/^/  stdout -> /'
fi
echo
echo '── 日志最后修改时间（若长时间不变 ⇒ 卡住）──'
stat -c '  %y  %n' _w2_t5_short_t5B12.log 2>/dev/null
date '+  now = %F %T'
echo
echo '── 日志最后 8 行 ──'
tail -8 _w2_t5_short_t5B12.log 2>/dev/null | cut -c1-165 | sed 's/^/  /'
echo
echo '── 相关警告（体积瓶颈 / 尝试被拒）──'
grep -nE '体积是瓶颈|被拒|拒绝|retry|重试' _w2_t5_short_t5B12.log 2>/dev/null | tail -6 | cut -c1-175 | sed 's/^/  /'
