#!/bin/bash
# _t10_mon.sh --- 10 µm 算例的 RSS + 构造横幅 + 进度盯守（修正版）
#   修正：原 `_t10_launch.sh` 的盯守按 `--tag` 匹配，抓到了 **_t5_short.py 包装层**（14 MB），
#         不是真引擎。本脚本按**最大 RSS** 挑，且要求 cmdline 含 `_bk_exp.py`。
#   用法：bash _t10_mon.sh <总秒数> [间隔秒]
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10N160
DUR=${1:-10800}
IV=${2:-60}
LOG=_w2_t10_mon.log
: > "$LOG"
echo "══ $TAG 盯守 $(date '+%m-%d %H:%M:%S')（每 ${IV}s，共 ${DUR}s）══" >> "$LOG"
printf '  %-8s %-10s %-9s %-10s %s\n' "t(s)" "RSS(MB)" "峰值(MB)" "步" "备注" >> "$LOG"
PEAK=0
t0=$(date +%s)
while :; do
  el=$(( $(date +%s) - t0 ))
  [ "$el" -ge "$DUR" ] && break
  # ★ 按**最大 RSS** 挑真引擎（cmdline 含 _bk_exp.py）
  BEST=0; BESTP=""
  for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*) ;; *) continue ;; esac
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    R=${R:-0}
    if [ "$R" -gt "$BEST" ]; then BEST=$R; BESTP=$P; fi
  done
  if [ -z "$BESTP" ]; then
    echo "  $el  ⚠ 引擎进程已不在（峰值 ${PEAK} MB）" >> "$LOG"
    break
  fi
  MB=$(( BEST / 1024 ))
  [ "$MB" -gt "$PEAK" ] && PEAK=$MB
  # 步号：优先快照文件名，退回日志末个 [ N] 行
  ST=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  [ -z "$ST" ] && ST=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1 | grep -oE '\[ *[0-9]+\]' | tr -dc '0-9')
  NOTE=""
  # 构造期：把关键词一次性记下来
  if [ ! -f _w2_t10_banner.done ]; then
    B=$(grep -aE '板条 .* nm|块数口径|平行建块|总根数|体积是瓶颈|可容' _w2_t5_short_$TAG.log 2>/dev/null | head -6)
    if [ -n "$B" ]; then
      echo "──── 构造横幅 ────" >> "$LOG"
      echo "$B" | cut -c1-185 | sed 's/^/    /' >> "$LOG"
      echo "──────────────────" >> "$LOG"
      touch _w2_t10_banner.done
    fi
  fi
  printf '  %-8s %-10s %-9s %-10s %s\n' "$el" "$MB" "$PEAK" "${ST:-0}" "$NOTE" >> "$LOG"
  sleep "$IV"
done
{
  echo "── 收尾 $(date '+%H:%M:%S') ──"
  grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | cut -c1-200 | sed 's/^/  /'
  echo "  快照 n=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)"
  free -m | sed -n 2p | sed 's/^/  /'
} >> "$LOG" 2>&1
echo "done" >> "$LOG"
