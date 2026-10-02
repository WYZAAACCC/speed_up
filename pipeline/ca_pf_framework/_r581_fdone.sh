#!/bin/bash
# _r581_fdone.sh --- F 是**正常跑完**还是**被杀**？（三处对账）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── ① F 的日志尾（正常结束会有收尾横幅；被杀则戛然而止）──'
tail -6 _w2_r581_mn64_F.log 2>/dev/null | cut -c1-96
echo
echo '── ② F 的 CSV（到 250 就是跑完了）──'
wc -l < _exp/_bk_mn64/dry_F/series.csv 2>/dev/null | sed 's/^/  行数=/'
tail -2 _exp/_bk_mn64/dry_F/series.csv 2>/dev/null | cut -d, -f1,9,10,19,24
echo
echo '── ③ F 的产物（有无 meta.json / 收尾文件）──'
ls -la _exp/_bk_mn64/dry_F/ 2>/dev/null | awk '{printf "  %-22s %s\n", $9, $5}' | tail -8
echo
echo '── ④ 看门狗有没有触发过（关键：它 kill -9 **全部** _bk_exp.py）──'
tail -6 _w2_r581_memguard.log 2>/dev/null
echo
echo '── ⑤ 看门狗进程还在吗 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep memguard | grep -v grep | cut -c1-70
echo
echo '── ⑥ 现在还有哪些 _bk_exp 在跑 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | \
  sed -n 's/.*--tag \([^ ]*\).*/  tag=\1/p'
