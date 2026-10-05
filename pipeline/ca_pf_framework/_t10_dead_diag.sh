#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "=== ① 引擎进程 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10B9 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  echo "  ★ 引擎在：pid=$EN"
  ps -o pid,etime,pcpu,stat --no-headers -p "$EN" | sed 's/^/    /'
  awk '/^VmRSS|^VmHWM|^VmSwap|^State|^Threads/{printf "    %s\n", $0}' /proc/$EN/status
else
  echo "  ❌ 引擎不在"
fi
echo "=== ② exit 文件 ==="
if [ -f _w2_t10_exit.txt ]; then cat _w2_t10_exit.txt | sed 's/^/  /'; else echo "  （无 exit 文件）"; fi
echo "=== ③ 日志 ==="
L=_w2_t5_short_t10B9.log
if [ -f "$L" ]; then
  echo "  大小 = $(stat -c '%s' "$L") B"
  echo "  mtime = $(stat -c '%y' "$L" | cut -c1-19)"
  echo "  距上次写入 = $(( $(date +%s) - $(stat -c '%Y' "$L") )) s"
  echo "  --- 末尾 8 行 ---"
  tail -8 "$L" | tr -d '\r' | cut -c1-150 | sed 's/^/    /'
  echo "  --- 错误/异常行（末 5）---"
  grep -aE 'Traceback|Error|error|Killed|MemoryError|❌|看门狗|WARNING' "$L" 2>/dev/null | tail -5 | tr -d '\r' | cut -c1-150 | sed 's/^/    /'
else
  echo "  ❌ 日志不存在"
fi
echo "=== ④ 事件 / 步 ==="
echo -n "  形核事件行 = "; grep -ac 'athermal 形核' "$L" 2>/dev/null
echo -n "  块数 = "; grep -ao '共 [0-9]* 块' "$L" 2>/dev/null | tail -1
echo -n "  末个步进 = "; grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -1 | cut -c1-90
echo "=== ⑤ 内存 ==="
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "=== ⑥ 其他相关进程 ==="
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E 'bk_exp|_t10_sw2|verdict' | grep -v grep | cut -c1-90 | sed 's/^/  /'
echo "=== ⑦ swap 盯守尾 ==="
tail -4 _w2_t10_swapfix2.log 2>/dev/null | sed 's/^/  /'
echo "=== ⑧ dmesg 里的 OOM / kill ==="
dmesg 2>/dev/null | tail -40 | grep -iE 'oom|killed|out of memory|t10B9|bk_exp' | tail -8 | sed 's/^/  /' || echo "  （读不到 dmesg）"
echo "=== ⑨ 数据目录 ==="
ls -la _exp/_bk_t5/ 2>/dev/null | grep -E 't10B9|t10PRT2' | sed 's/^/  /'
ls _exp/_bk_t5/dry_t10B9/ 2>/dev/null | head -8 | sed 's/^/    /'
