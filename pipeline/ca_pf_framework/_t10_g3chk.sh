#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10PRT2
L=_w2_t5_short_$TAG.log
echo "NOW $(date '+%m-%d %H:%M:%S')"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  echo "  引擎在：pid=$EN"
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/    /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "    %s\n", $0}' /proc/$EN/status
  echo -n "    开关："
  tr '\0' ' ' < /proc/$EN/cmdline | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-ed-eta [0-9.]+|\-\-nuc-occ-guard [0-9]+' | tr '\n' ' '
  echo
  echo -n "    环境变量 SEED_*："
  tr '\0' '\n' < /proc/$EN/environ 2>/dev/null | grep -E '^SEED_' | tr '\n' ' '
  echo
else echo "  ⚠ 引擎不在（exit: $([ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo 无)）"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "--- 步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -3 | cut -c1-110
echo "--- 快照 ---"
ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- 代码版本（近期是否改过）---"
for f in windowB_surface.py _bk_exp.py _t5_short.py; do
  echo "  $f  mtime=$(stat -c '%y' $f 2>/dev/null | cut -c1-19)  sha=$(sha256sum $f 2>/dev/null | cut -c1-12)"
done
echo "  引擎启动时刻（进程 START）：$(ps -o lstart= -p ${EN:-1} 2>/dev/null)"
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null
