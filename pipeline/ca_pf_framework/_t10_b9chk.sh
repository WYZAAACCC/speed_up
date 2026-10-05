#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10B9
L=_w2_t5_short_$TAG.log
echo "NOW $(date '+%m-%d %H:%M:%S')"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  echo "  ★ 引擎在：pid=$EN"
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/    /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "    %s\n", $0}' /proc/$EN/status
  echo -n "    nv 相关开关："
  tr '\0' ' ' < /proc/$EN/cmdline | grep -oE '\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-nuc-block-target [0-9]+|\-\-N [0-9]+|\-\-dx-nm [0-9.]+' | tr '\n' ' '
  echo
  echo -n "    SEED_* 环境变量："
  tr '\0' '\n' < /proc/$EN/environ 2>/dev/null | grep -E '^SEED_' | tr '\n' ' '
  echo
else
  echo "  ⚠ 引擎不在"
  [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/    exit: /'
fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "--- 日志尾部（判断是构造中还是崩了）---"
if [ -f "$L" ]; then
  echo "  大小 = $(stat -c '%s' "$L") B ；mtime = $(stat -c '%y' "$L" | cut -c1-19)"
  tail -8 "$L" | tr -d '\r' | cut -c1-150 | sed 's/^/    /'
  echo "  --- 错误行 ---"
  grep -aE 'Traceback|Error|error:|❌' "$L" | tail -5 | sed 's/^/    /'
else
  echo "  ⚠ 日志不存在"
fi
echo "--- 形核 / 清理 ---"
echo -n "  形核行 = "; grep -ac 'athermal 形核' "$L" 2>/dev/null
echo -n "  播种清理 = "; grep -ac '\[SEEDCLEAN\]' "$L" 2>/dev/null
echo -n "  SEEDCARVED = "; grep -ac '\[SEEDCARVED\]' "$L" 2>/dev/null
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' "$L" 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null
