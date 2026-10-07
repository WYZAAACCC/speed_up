#!/bin/bash
# _r279_killsaOddGDT.sh —— 停掉 `saOddGDT`（低价值 + 最慢），把 CPU 让给更高价值的实验。
#
# ## 为什么可以停（**先论证，再动手**）
# * **价值**：`saOddGDT` 是 `_r210` 的第二臂，只为给 `saSet2DT` 一个"非自协调几何"的对照；
#   而 `saSet2DT` **已跑满 400 步**并给出了三类界面的主结论（`§145.2`）。
# * **成本**：实测 **~22 s/步** ⇒ 400 步还要 **~2 小时**。
# * **要腾出的算力给谁**：**R165 在 `--facet-proj 0` 下的重跑**（`§144` 的 P0 跟进）
#   —— 它直接检验"把界面能通道接回来之后，F2 配对 γ 是否终于显出效应"。
#
# ## 安全规程（`AGENTS.md §3.10`/`§3.11`）
# 1. **不用 `pkill -f`**（会杀掉含同串的**自己的 shell**）；
# 2. **按 PID 杀**，PID 由 `--tag saOddGDT` **精确匹配** cmdline 得到；
# 3. 杀前**打印** pid / cwd / cmdline 以便核对；
# 4. 杀后**复验**：该 PID 消失、且**其它臂仍在**（不许误伤）。
cd "$(dirname "$0")" || exit 1

echo "=== ① 杀前快照：所有 _bk_exp.py 进程 ==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
  printf '  pid=%-7s tag=%-12s cwd=%s\n' "$p" "${tag:-?}" \
    "$(readlink /proc/$p/cwd 2>/dev/null)"
done

echo
echo "=== ② 精确定位 saOddGDT ==="
TARGETS=""
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  case "$cl" in
    *"--tag saOddGDT"*) TARGETS="$TARGETS $p" ;;
  esac
done
if [ -z "$TARGETS" ]; then
  echo "  ⚠ 没找到 saOddGDT（可能已结束）⇒ 不做任何事"
else
  echo "  ⇒ 目标 PID：$TARGETS"
  echo "  ⇒ 二次核对（cmdline 里必须含 --tag saOddGDT 且**不含**其它 tag）："
  for p in $TARGETS; do
    cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    n=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | wc -l)
    printf '     pid=%s  出现 "tag" 次数=%s  %s\n' "$p" "$n" \
      "$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tr '\n' ' ')"
    if [ "$n" != "1" ]; then echo "     ❌ 可疑 ⇒ **拒绝杀**"; TARGETS=""; break; fi
  done
fi

if [ -n "$TARGETS" ]; then
  echo
  echo "=== ③ 发送 SIGTERM ==="
  for p in $TARGETS; do kill -TERM "$p" 2>/dev/null && echo "  TERM -> $p"; done
  sleep 5
  echo "=== ④ SIGTERM 后仍在的，才用 SIGKILL ==="
  for p in $TARGETS; do
    if kill -0 "$p" 2>/dev/null; then
      kill -9 "$p" 2>/dev/null && echo "  KILL -> $p"
    else
      echo "  $p 已退出"
    fi
  done
fi

sleep 3
echo
echo "=== ⑤ 杀后复验 ==="
echo "  剩余 _bk_exp.py 进程："
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
  printf '     pid=%-7s tag=%-12s\n' "$p" "${tag:-?}"
done
echo "  ⇒ 期望：p45L / p45P / p45L0 / p45P0 / saSet2EDV **仍在**，saOddGDT **消失**"
echo
echo "=== ⑥ 查孤儿（cwd 带 (deleted) 的）==="
found=0
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  c=$(readlink "/proc/$p/cwd" 2>/dev/null)
  case "$c" in *"(deleted)"*) echo "  ⚠ 孤儿 pid=$p cwd=$c"; found=1 ;; esac
done
[ "$found" = "0" ] && echo "  ✅ 无孤儿"
