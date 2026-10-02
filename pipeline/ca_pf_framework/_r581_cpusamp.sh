#!/bin/bash
# _r581_cpusamp.sh --- ★★★★★★ **真·逐 step 墙钟**（采样 CPU 时间两次，除以步数差）
#   口径：`utime+stime`（/proc/<pid>/stat 第 14+15 字段，单位 jiffies，100 Hz）
#         ÷ 步数差 ⇒ **每步的 CPU 秒**（多线程 ⇒ 这是**并发和**口径，不是墙钟）
#   ⚠ 按 goal §⑥：**并发和**与**墙钟**分列，不得混算 ⇒ 本脚本明确报**并发和**
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
pick() {  # $1 = tag
  for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
    c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    case "$c" in *"--tag $1 "*) echo "$p"; return;; esac
  done
}
step_of() { tail -1 "_exp/_bk_mn64/dry_$1/series.csv" 2>/dev/null | cut -d, -f1; }
cpu_of() { awk '{print $14+$15}' "/proc/$1/stat" 2>/dev/null; }

echo '── 采样 1 ──'
declare -A P0 S0 C0
for T in F G; do
  p=$(pick "$T"); [ -z "$p" ] && { echo "  $T: 进程不在"; continue; }
  P0[$T]=$p; S0[$T]=$(step_of "$T"); C0[$T]=$(cpu_of "$p")
  echo "  $T: pid=$p step=${S0[$T]} cpu=${C0[$T]} jiffies"
done
echo
echo "  等 120 s…"
sleep 120
echo
echo '── 采样 2 ──'
for T in F G; do
  [ -z "${P0[$T]:-}" ] && continue
  s1=$(step_of "$T"); c1=$(cpu_of "${P0[$T]}")
  ds=$(( s1 - ${S0[$T]} )); dc=$(( c1 - ${C0[$T]} ))
  if [ "$ds" -gt 0 ]; then
    per=$(awk -v d="$dc" -v s="$ds" 'BEGIN{printf "%.2f", d/100.0/s}')
    printf '  %-3s step %s→%s（Δ%s）  cpu Δ%s jiffies ⇒ **并发和 %.2f s/步**\n' \
      "$T" "${S0[$T]}" "$s1" "$ds" "$dc" "$per"
  else
    printf '  %-3s step 未变（%s）  cpu Δ%s jiffies（2 min 内）⇒ **零进展 ⇒ 极慢**\n' \
      "$T" "$s1" "$dc"
  fi
done
echo
echo '── 近期 step 轨迹（从 CSV 尾 12 行取）──'
for T in F G; do
  printf '  %-3s ' "$T"
  tail -12 "_exp/_bk_mn64/dry_$T/series.csv" 2>/dev/null | cut -d, -f1 | tr '\n' ' '
  echo
done
