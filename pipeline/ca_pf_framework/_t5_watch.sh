#!/bin/bash
# _t5_watch.sh --- 看两臂进度（避开 PowerShell 的引号/`$f:` 解析坑）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 编排器日志 ──'
tail -8 _w2_t5_ab2.log 2>/dev/null | sed 's/^/  /'
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | cut -c1-82 | sed 's/^/  /'
echo '── A（overlap=62.5，核 0-7）尾部 ──'
tail -3 _w2_t5_ab2_A.log 2>/dev/null | cut -c1-112 | sed 's/^/  /'
echo '── B（overlap=0，核 8-15）尾部 ──'
tail -3 _w2_t5_ab2_B.log 2>/dev/null | cut -c1-112 | sed 's/^/  /'
echo '── 引擎日志的步进读数 ──'
for t in t5o62 t5o0; do
  printf '  %-6s: %s\n' "$t" \
    "$(grep -oE '\[\s*[0-9]+\]\s+Vt=[0-9.]+' "_w2_t5_short_$t.log" 2>/dev/null | tail -1)"
done
echo '── 内存 ──'
free -m | sed -n 2p | sed 's/^/  /'
