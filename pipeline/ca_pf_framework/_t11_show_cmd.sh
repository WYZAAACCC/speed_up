#!/bin/bash
# _t11_show_cmd.sh —— 打印**所有** `_bk_exp.py` 进程的关键字段（out/tag/steps），并查它的 cwd。
#   为什么要它：我先前以为某算例写到 `_exp/_bk_t5/dry_<tag>`，但那个目录**不存在**
#   ⇒ 不能靠"我以为的输出路径"，必须读进程自己的命令行（硬步骤 A）。
echo "=== _bk_exp.py 进程 ==="
for P in $(pgrep -x python); do
  C=$(tr '\0' ' ' < "/proc/$P/cmdline" 2>/dev/null || true)
  case "$C" in
    *_bk_exp.py*)
      echo "PID=$P"
      echo "$C" | grep -o -- '--out [^ ]*' | sed 's/^/   /'
      echo "$C" | grep -o -- '--tag [^ ]*' | sed 's/^/   /'
      echo "$C" | grep -o -- '--steps [^ ]*' | sed 's/^/   /'
      echo "$C" | grep -o -- '--nuc-shape [^ ]*' | sed 's/^/   /'
      echo "$C" | grep -o -- '--nuc-block-target [^ ]*' | sed 's/^/   /'
      echo "   cwd = $(readlink /proc/$P/cwd 2>/dev/null)"
      echo "   RSS = $(awk '/VmRSS/{printf "%.2f GB", $2/1048576}' /proc/$P/status 2>/dev/null)"
      ;;
  esac
done
echo "=== 候选输出目录（按修改时间）==="
for D in /mnt/f/speed_up/_exp/_bk_t5 /mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5; do
  [ -d "$D" ] || continue
  echo "-- $D"
  ls -1dt "$D"/dry_* 2>/dev/null | head -4 | while read -r X; do
    echo "   $(stat -c '%y' "$X" | cut -c1-19)  $(basename "$X")"
  done
done
