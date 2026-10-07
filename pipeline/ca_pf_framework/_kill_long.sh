#!/usr/bin/env bash
# _kill_long.sh --- 只杀 T16_verify_rve / T13b_verify_nv 两个长作业（按 cmdline 精确匹配）。
set -u
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T16_verify_rve*|*T13b_verify_nv*)
      echo "KILL pid=$P"; kill -9 "$P" ;;
  esac
done
sleep 2
echo '--- remaining ---'
pgrep -a python | cut -c1-80
