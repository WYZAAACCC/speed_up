#!/bin/bash
# _r581_oomchk.sh --- p2_m20 到底怎么死的？（**问内核，不猜**）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '########## ① 内核日志里的 OOM / kill（dmesg）##########'
if command -v dmesg >/dev/null 2>&1; then
  dmesg 2>/dev/null | grep -iE 'out of memory|oom-kill|killed process|Killed process' | tail -8 \
    || echo '  （dmesg 里没有 OOM 记录，或没有权限读）'
else
  echo '  （没有 dmesg）'
fi
echo
echo '########## ② journalctl（若有）##########'
journalctl -k --no-pager 2>/dev/null | grep -iE 'oom|killed process' | tail -5 \
  || echo '  （journalctl 不可用/无记录）'
echo
echo '########## ③ p2_m20 的日志：**有没有报错/收尾横幅** ##########'
f=_w2_r581_p2_p2_m20.log
if [ -f "$f" ]; then
  printf '  大小=%s  mtime=%s  Traceback=%s\n' "$(stat -c%s "$f")" \
    "$(date -r "$f" '+%T')" "$(grep -c '^Traceback' "$f")"
  echo '  ── 末 6 行 ──'
  tail -6 "$f" | cut -c1-100 | sed 's/^/    /'
  echo '  ── 有没有"正常结束"的标志 ──'
  grep -cE '判决|已落盘|DONE|完成' "$f" | sed 's/^/    命中收尾关键词行数=/'
else
  echo '  （没有日志）'
fi
echo
echo '########## ④ p2_m20 的目录内容（有没有半成品）##########'
for d in _exp/*/dry_p2_m20; do
  [ -d "$d" ] || continue
  echo "  $d："
  ls -la "$d" 2>/dev/null | awk 'NR>3{printf "    %-22s %s\n", $9, $5}'
done
echo
echo '########## ⑤ 现在在跑什么 ##########'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  st=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  pid=%-7s tag=%-10s state=%-3s RSS=%s MB\n' "$p" "${tag:-?}" "$st" "$rss"
done
echo
echo '########## ⑥ 内存 ##########'
free -m | sed -n 2,3p
