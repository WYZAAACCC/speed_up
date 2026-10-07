#!/bin/bash
# _r1_proc.sh --- 看某个 pid 是否在工作（状态/CPU 时间/RSS），并对照构造耗时
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
P=${1:-8534}
if [ ! -d "/proc/$P" ]; then
  echo "pid $P : **已不存在**"
else
  ps -o pid,stat,etimes,time,rss --no-headers -p "$P"
  echo "cmdline: $(tr '\0' ' ' < /proc/$P/cmdline | cut -c1-80)"
  echo "线程数: $(ls /proc/$P/task 2>/dev/null | wc -l)"
fi
echo
echo "=== 对照：既有 N=192 算例的构造耗时 ==="
for d in mid192_ns4 mid192_s2_ns4 equi192_ns4; do
  t=$(grep -oE '构造 [0-9.]+ s' "_exp/$d/log.txt" 2>/dev/null | head -1)
  echo "  $d : ${t:-（日志里没有该行）}"
done
echo
echo "=== mid192_ns4b 的 log 行数与 mtime ==="
wc -l < _exp/mid192_ns4b/log.txt
date -r _exp/mid192_ns4b/log.txt +%H:%M:%S
echo "现在: $(date +%H:%M:%S)"
