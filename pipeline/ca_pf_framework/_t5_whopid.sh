#!/bin/bash
# _t5_whopid.sh --- 找出每个引擎 pid 对应的 tag（为"按精确 pid 杀"提供依据）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 引擎进程 → tag 映射（从 /proc/<pid>/cmdline 取，最可靠）════'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{print $1}'); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  TAG=$(echo "$CMD" | grep -oE '\-\-tag [A-Za-z0-9_]+' | head -1 | awk '{print $2}')
  [ -z "$TAG" ] && TAG=$(echo "$CMD" | grep -oE 'dry_t5[A-Za-z0-9_]+' | head -1)
  printf '  pid=%-8s tag=%s\n' "$P" "${TAG:-（未识别）}"
done
echo
echo '════ 对照：引擎命令行前 150 字符（看格式）════'
ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | head -2 | cut -c1-150 | sed 's/^/  /'
