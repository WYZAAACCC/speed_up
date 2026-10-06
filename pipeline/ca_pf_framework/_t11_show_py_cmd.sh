#!/bin/bash
# _t11_show_py_cmd.sh —— 打印所有 python 进程的完整命令行 / cwd / RSS（不杀任何进程）。
# 用途：重启前**取回**正在跑的算例的**逐字命令行**（免得靠回忆重建参数）。
for p in $(pgrep -x python); do
  [ -r "/proc/$p/cmdline" ] || continue
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  case "$c" in
    *_bk_exp.py*)
      echo "PID $p"
      echo "  CWD: $(readlink /proc/$p/cwd 2>/dev/null)"
      echo "  RSS: $(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null) kB"
      echo "  CMD: $c"
      echo
      ;;
  esac
done
echo "---- python 进程总数: $(pgrep -x python | wc -l) ----"
