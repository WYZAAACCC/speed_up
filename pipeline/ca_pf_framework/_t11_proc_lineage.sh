#!/bin/bash
# _t11_proc_lineage.sh —— 追 PID 血统，定位 OOM dump 里那个 15.2 GiB 的 python(12383) 是什么。
OUT=/mnt/f/speed_up/_w2_proc_lineage.txt
{
echo "############ 采集: $(date '+%F %T')"
echo
echo "=== [1] 当前所有 python 进程 + 父进程 + 起始时刻 ==="
ps -eo pid,ppid,lstart,etimes,rss,vsz,args --sort=pid 2>/dev/null | grep -aE "python|PID" | head -20
echo
echo "=== [2] 当前所有进程里 ppid 链路（含 6712/6750 附近的 Relay）==="
ps -eo pid,ppid,comm 2>/dev/null | awk 'NR==1 || $1>=5100' | head -40
echo
echo "=== [3] 我起过的工具脚本是否还在跑 ==="
for p in $(pgrep -f "_t11_" 2>/dev/null); do
  echo "  PID $p: $(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | head -c 160)"
done
echo "  （空 = 我的工具都已退出）"
echo
echo "=== [4] 当前 RSS Top（含非 python）==="
ps -eo pid,ppid,rss,vsz,comm --sort=-rss 2>/dev/null | head -8
echo
echo "=== [5] 当前内存总览 ==="
free -m
grep -E "^(MemAvailable|SwapFree|SwapCached):" /proc/meminfo
} > "$OUT" 2>&1
echo "已写出 $OUT"
