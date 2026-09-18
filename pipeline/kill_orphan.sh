#!/bin/bash
# 杀掉第一次失败的 AD 版 c1 残留进程（PID 165822）。
#
# 【教训】MOOSE 打印 "Aborting as solve did not converge" **不等于进程退出** ——
# 它会 "Solve failed, cutting timestep" 后继续用更小的 dt 重试，
# 一路砍到 dtmin 才真正 abort。所以我以为它已经死了，实际它还在跑，
# 白占一个核并污染其他测量。
# **判据：看到日志说 Aborting，要 ps 确认进程真的没了。**
TARGET=165822
if kill -0 "$TARGET" 2>/dev/null; then
  CMD=$(tr '\0' ' ' < /proc/$TARGET/cmdline 2>/dev/null)
  echo "  确认 PID=$TARGET 是: $CMD"
  kill -9 "$TARGET" 2>/dev/null
  sleep 2
  echo "  已杀"
else
  echo "  PID=$TARGET 已不存在"
fi
echo
echo "剩余 MOOSE 进程："
ps -eo pid,etime,comm | grep phase_field | grep -v grep | sed 's/^/  /'
echo "可用内存 $(free -g | awk 'NR==2{print $7}') GB"
