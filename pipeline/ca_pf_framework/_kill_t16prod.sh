#!/usr/bin/env bash
# _kill_t16prod.sh --- 按 cwd + cmdline 精确杀掉 T16 正规跑的 python 进程（不做进程名一刀切）。
set -u
for P in $(pgrep -x python); do
  CWD=$(readlink /proc/$P/cwd 2>/dev/null || echo '?')
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T16_verify_rve*)
      echo "KILL pid=$P cwd=$CWD"
      kill -9 "$P" ;;
  esac
done
sleep 2
echo '--- remaining python ---'
pgrep -a python | head
echo '--- mem ---'
free -g | head -2
