#!/bin/bash
# _r581_stoparm.sh <tag> [TERM|KILL] --- **只停一个臂**（不动别的，不删任何数据）
cd "$(dirname "$0")" || exit 1
TAG="${1:?用法: bash _r581_stoparm.sh <tag> [TERM|KILL]}"
SIG="${2:-TERM}"
P=$(pgrep -f -- "--tag ${TAG}[[:space:]]" || true)
if [ -z "$P" ]; then echo "  找不到 tag=${TAG} 的进程"; exit 0; fi
for x in $P; do
  CWD=$(readlink /proc/$x/cwd 2>/dev/null || echo '?')
  echo "  停 pid=$x  tag=${TAG}  cwd=$CWD  (SIG$SIG)"
  kill -"$SIG" "$x" 2>/dev/null || true
done
sleep 10
LEFT=$(pgrep -f -- "--tag ${TAG}[[:space:]]" | wc -l)
echo "  剩余 ${LEFT} 个"
free -m | sed -n 2p
echo "  ⚠ 已落盘的 series.csv / snap_*.npz / meta.json **一律不删**；"
echo "     重跑前用 `_r581_p2.py --archive-old`（mv 归档改名）"
