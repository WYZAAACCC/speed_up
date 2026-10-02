#!/bin/bash
# _r581_p2env.sh --- `p2_m12ov` 当年跑在**哪一档分配器**上？（决定性的交叉验证）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① `_r581_p2.py` 里怎么起 `_bk_exp.py` 的 ════'
if [ -f _r581_p2.py ]; then
  grep -n 'MALLOC\|env -u\|subprocess\|Popen\|cmd *= *\[' _r581_p2.py 2>/dev/null | head -12 | cut -c1-130 | sed 's/^/  /'
else
  echo '  （没有 _r581_p2.py）'
fi
echo
echo '════ ② 起它的那些 .sh 里有没有 MALLOC ════'
for f in _r581_p2.sh _r581_mqueue.sh _r581_mqueue2.sh _r581_mqueue3.sh _r581_mqueue4.sh; do
  [ -f "$f" ] || continue
  n=$(grep -c 'MALLOC' "$f" 2>/dev/null || echo 0)
  printf '  %-22s MALLOC 行数=%s\n' "$f" "$n"
  grep -n 'MALLOC' "$f" 2>/dev/null | head -3 | sed 's/^/      /' | cut -c1-120
done
echo
echo '════ ③ 直接找：谁在起 p2_ 系列 ════'
grep -ln 'p2_' *.sh 2>/dev/null | head -6 | sed 's/^/  /'
echo
echo '════ ④ 那些脚本里的 MALLOC 用法 ════'
for f in $(grep -ln 'p2_' *.sh 2>/dev/null | head -4); do
  echo "  ── $f ──"
  grep -n 'MALLOC\|env ' "$f" 2>/dev/null | head -4 | cut -c1-126 | sed 's/^/    /'
done
echo
echo '════ ⑤ 当前 A/B 的现场 ════'
tail -4 _w2_r581_alloc160b.log 2>/dev/null | sed 's/^/  /'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  r=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  tag=%-9s RSS=%sMB\n' "${tag:-?}" "$r"
done
free -m | sed -n 2p | sed 's/^/  /'
