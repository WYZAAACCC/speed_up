#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 所有 _bk_exp 进程的完整参数（取 --tag）'
for P in $(pgrep -x python 2>/dev/null; pgrep -f '_bk_exp.py' 2>/dev/null); do
  [ -d /proc/$P ] || continue
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*)
      TAG=$(echo "$CMD" | grep -oE '\-\-tag [A-Za-z0-9_]+' | head -1)
      printf '  pid=%-7s %-16s %s\n' "$P" "$TAG" "$(echo "$CMD" | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+|\-\-steps [0-9]+' | tr '\n' ' ')"
      ;;
  esac
done | sort -u
echo
echo '=== b62r 的产物与日志'
ls -la _w2_r51_b62r* 2>/dev/null
ls _exp/_bk_mb/dry_b62r/ 2>/dev/null
echo
echo '=== b62q 是否还在'
ls _exp/_bk_mb/dry_b62q/ 2>/dev/null | head -3
