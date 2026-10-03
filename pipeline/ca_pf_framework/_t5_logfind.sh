#!/bin/bash
# _t5_logfind.sh --- 找对**引擎日志文件**并核对形核行的真实写法
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 与 t5N276 / t5NR 相关的日志文件（按大小）════'
ls -la _w2_t5_*n276*.log _w2_t5_nr*.log _w2_t5_short_t5N*.log _w2_t5_short_t5NR.log 2>/dev/null \
  | awk '{printf "  %-38s %9s 字节  %s %s\n", $9, $5, $6, $7}'
echo
echo '════ ② 从进程命令行找**真正的 stdout 重定向目标**（最可靠）════'
for T in t5N276 t5NR; do
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $T" | awk '{print $1}' | head -1)
  [ -z "$P" ] && { echo "  $T：（无引擎进程）"; continue; }
  echo "  ── $T (pid=$P) ──"
  echo "     stdout → $(readlink /proc/$P/fd/1 2>/dev/null)"
done
echo
echo '════ ③ 用**正确文件**核对形核行（以 t5N276 为例）════'
L=$(readlink /proc/$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5N276' | awk '{print $1}' | head -1)/fd/1 2>/dev/null)
if [ -n "$L" ] && [ -f "$L" ]; then
  echo "  文件 = $L（$(stat -c%s "$L") 字节）"
  echo '  ── 含"形核"的行（末 4 条）──'
  grep -nE '形核' "$L" 2>/dev/null | tail -4 | cut -c1-160 | sed 's/^/     /'
  echo '  ── 模式统计 ──'
  grep -oE '模式 \*\*[a-z]+\*\*' "$L" 2>/dev/null | sort | uniq -c | sed 's/^/     /'
  echo '  ── fresh 出现次数 ──'
  awk '/fresh/{n++} END{print "     " n+0}' "$L"
else
  echo "  ⚠ 拿不到 stdout 目标（$L）"
fi
