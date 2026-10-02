#!/bin/bash
# _r581_emg.sh --- 🚨 内存急救：看清谁在吃内存 + 看门狗有没有动
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ 内存 ════'
free -m | sed 's/^/  /'
echo
echo '════ 所有 _bk_exp 进程（按 RSS 降序）════'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  rss=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
  et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
  printf '%s\t%s\t%s\t%s\n' "${rss:-0}" "$p" "${tag:-?}" "$et"
done | sort -rn | awk '{printf "  RSS=%-8.0f MB  pid=%-7s tag=%-10s 时长=%s\n", $1/1024, $2, $3, $4}'
echo
echo '════ 其它 python / 大进程（前 8）════'
ps -eo rss,pid,etime,comm --no-headers 2>/dev/null | sort -rn | head -8 | \
  awk '{printf "  RSS=%-8.0f MB  pid=%-7s %-10s %s\n", $1/1024, $2, $4, $3}'
echo
echo '════ 看门狗状态 ════'
ps -eo pid,args --no-headers 2>/dev/null | grep '_r581_memguard' | grep -v grep | cut -c1-100 | sed 's/^/  /'
echo '  ── 日志尾 ──'
tail -6 _w2_r581_memguard.log 2>/dev/null | sed 's/^/  /'
echo
echo '════ 被保护名单（看门狗不会杀这些）════'
echo '  p2_m12ov p2_m20 p2_m12 p2_m12b p2_b5 p2_m20b'
echo '  ⇒ **TUNED/ARENA/PLAIN 不在名单里 ⇒ 看门狗会杀它们！**'
