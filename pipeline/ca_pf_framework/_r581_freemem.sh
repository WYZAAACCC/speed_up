#!/bin/bash
# _r581_freemem.sh --- 腾内存：停 p2_m12ov（**只停进程，数据一个字节不删**）
# 理由（R184）：用户授权做 N=160 的 A/B，而每臂要 ~10–12 GB；
# `p2_m12ov` 占 9 GB、且它 `--steps 4000` 而只跑到 ~step 55
# ⇒ **按 ~26 s/步外推，它还要 ~28 h 才跑完 ⇒ 不可能完成**（P34：外推前先验标度）。
# ⇒ 停它是"最保守"的选择（数据保留、可续跑），换来 A/B 的内存。
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 停之前 ──'
for p in $(pgrep -f '_bk_exp.py.*--tag p2_m12ov' 2>/dev/null); do
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  echo "  p2_m12ov pid=$p RSS=${rss}MB"
done
echo '  ── 它的产物（**必须还在**）──'
for d in _exp/_bk_p2/dry_p2_m12ov; do
  [ -d "$d" ] || continue
  printf '    %s\n' "$d"
  printf '      series.csv 行数=%s  step=%s  快照数=%s\n' \
    "$(wc -l < "$d/series.csv" 2>/dev/null)" \
    "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)" \
    "$(ls "$d" 2>/dev/null | grep -c '^snap_')"
done
echo
for p in $(pgrep -f '_bk_exp.py.*--tag p2_m12ov' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && echo "  TERM pid=$p"
done
sleep 5
for p in $(pgrep -f '_bk_exp.py.*--tag p2_m12ov' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && echo "  KILL pid=$p"
done
sleep 2
echo
echo '── 停之后 ──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  tag=%-9s pid=%-7s RSS=%sMB\n' "${tag:-?}" "$p" "$rss"
done
echo
echo '── p2_m12ov 的数据**还在**吗 ──'
ls _exp/_bk_p2/dry_p2_m12ov/ 2>/dev/null | tr '\n' ' '
echo
free -m | sed -n 2p | sed 's/^/  /'
