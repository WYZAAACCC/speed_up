#!/bin/bash
# _t11_kill_by_tag.sh —— 按 `--tag <X>` **精确**杀掉某个引擎进程，其余保留。
#   为什么不用 `pkill -f`：它匹配完整命令行，会**杀掉自己的 shell**（AGENTS.md §3.10）。
# 用法: bash _t11_kill_by_tag.sh <tag> [tag2 ...]
set -u
if [ $# -eq 0 ]; then echo "用法: $0 <tag> [...]"; exit 2; fi
KILLED=0
for P in $(pgrep -x python); do
  C=$(tr '\0' ' ' < "/proc/$P/cmdline" 2>/dev/null || true)
  case "$C" in
    *_bk_exp.py*)
      for T in "$@"; do
        case "$C" in
          *"--tag $T "*) echo "  → 杀 tag=$T  PID=$P"; kill -9 "$P" 2>/dev/null; KILLED=$((KILLED+1)) ;;
        esac
      done
      ;;
  esac
done
[ "$KILLED" -eq 0 ] && echo "  （没有匹配的引擎进程）"
sleep 2
echo "--- 复查：仍在跑的引擎 ---"
for P in $(pgrep -x python); do
  C=$(tr '\0' ' ' < "/proc/$P/cmdline" 2>/dev/null || true)
  case "$C" in
    *_bk_exp.py*) echo "  PID=$P tag=$(echo "$C" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')" ;;
  esac
done
