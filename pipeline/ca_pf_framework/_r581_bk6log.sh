#!/bin/bash
# _r581_bk6log.sh --- BK6 的日志与活性速查（避免在 pwsh 里转义 awk）
cd "$(dirname "$0")" || exit 1
L=_w2_r581_blk_BK6.log
echo "NOW = $(date '+%F %T')"
echo
echo '── 日志文件 ──'
if [ -f "$L" ]; then
  printf '  字节=%s  最后修改=%s\n' "$(stat -c%s "$L")" "$(date -r "$L" '+%T')"
  printf '  Traceback=%s\n' "$(grep -c '^Traceback' "$L")"
else
  echo '  （没有日志）'
fi
echo
echo '── 日志尾 6 行 ──'
tail -6 "$L" 2>/dev/null | cut -c1-108 | sed 's/^/  /'
echo
echo '── 有没有 pair / 块表 的痕迹 ──'
grep -c 'pair' "$L" 2>/dev/null | sed 's/^/  pair 命中行数=/'
grep -i 'blk\|块' "$L" 2>/dev/null | tail -3 | cut -c1-100 | sed 's/^/  /'
echo
echo '── 在跑的臂 ──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  st=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
  printf '  tag=%-9s pid=%-7s state=%-3s RSS=%-6s 时长=%s\n' "$tag" "$p" "$st" "$rss" "$et"
done
echo
echo '── BK6 的 series.csv 行数（每 5 步一行）──'
wc -l < _exp/_bk_blk/dry_BK6/series.csv 2>/dev/null | sed 's/^/  行数=/'
echo
free -m | sed -n 2p | sed 's/^/  /'
