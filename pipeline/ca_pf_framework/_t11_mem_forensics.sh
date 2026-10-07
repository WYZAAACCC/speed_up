#!/bin/bash
# _t11_mem_forensics.sh —— 追查"28 GB 被谁吃掉"：page cache / slab / 历史 OOM / 当前明细。
OUT=/mnt/f/speed_up/_w2_mem_forensics.txt
{
echo "############ 采集: $(date '+%F %T')"
echo
echo "=== [1] 历史上**所有** OOM 事件（kern.log 全文）==="
grep -anE "Out of memory: Killed process" /var/log/kern.log 2>/dev/null | tail -20
echo "  ---- 计数: $(grep -acE 'Out of memory: Killed process' /var/log/kern.log 2>/dev/null) ----"
echo
echo "=== [2] 每次 OOM 的完整被害者行（含 rss 明细）==="
grep -aE "Out of memory: Killed process|invoked oom-killer" /var/log/kern.log 2>/dev/null | tail -20
echo
echo "=== [3] 当前内存明细（MemTotal/Anon/File/Slab）==="
grep -E "^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapCached|Active|Inactive|SwapTotal|SwapFree|Shmem|Slab|SReclaimable|SUnreclaim|PageTables|Committed_AS|CommitLimit):" /proc/meminfo
echo
echo "=== [4] cgroup 内存明细 ==="
for f in memory.peak memory.current memory.max memory.events memory.stat; do
  if [ -r "/sys/fs/cgroup/$f" ]; then
    echo "  ---- $f ----"
    if [ "$f" = "memory.stat" ]; then
      grep -E "^(anon|file|slab|kernel|pagetables|shmem|sock|swapcached) " "/sys/fs/cgroup/$f"
    else
      echo "    $(cat /sys/fs/cgroup/$f)"
    fi
  fi
done
echo
echo "=== [5] 当前所有 python 进程的 RSS（含已被杀者的痕迹）==="
ps -eo pid,etimes,rss,vsz,comm --sort=-rss 2>/dev/null | head -8
echo
echo "=== [6] VM 启动以来的峰值（如果有 /proc/vmstat 的 pgalloc 等）==="
grep -aE "^(pgalloc|pgfault|pgmajfault|pswpout|pswpin)" /proc/vmstat 2>/dev/null
echo
echo "=== [7] dmesg 里 OOM 前 60 秒的其它内核消息（找线索）==="
dmesg -T 2>/dev/null | grep -aE "21:3[0-9]:|21:36:" | head -20
echo
echo "=== [8] 是否存在 .vhdx 上的 swap 使用痕迹 / 盘写入 ==="
cat /proc/swaps 2>/dev/null
} > "$OUT" 2>&1
echo "已写出 $OUT（$(wc -l < "$OUT") 行）"
