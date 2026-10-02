#!/bin/bash
# _r581_refill.sh --- ★★★★★★ **决定性检查**：E/F/G 的脚本有没有传 `--nuc-sites-refill`？
#   代码（`windowB_surface.py:1961-1979`，R481 自己写的）：
#     t=0 一次撒 `n = nuc_init` 个位点，**用过即 `pop` 移除**
#     ⇒ 池子耗尽后 `if sites and n_fresh > 0` 直接不成立 ⇒ **再也形不了核**
#     ⇒ **"定律要核、池子没有"** 的静默缺口
#   ⚠ `sites_refill=False`（**默认**）⇒ 一个字都不进
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '################ ① 各队列脚本里有没有 --nuc-sites-refill / --nuc-init ################'
for f in _r581_mn64.sh _r581_mn64b.sh _r581_mn64c.sh _r581_mn64d.sh \
         _r581_mn64e.sh _r581_mn64f.sh _r581_mn64g.sh _r581_mn64h.sh _r581_mn64j.sh _r581_mn64k.sh; do
  [ -f "$f" ] || continue
  r=$(grep -c -- '--nuc-sites-refill' "$f" 2>/dev/null)
  i=$(grep -oE '\-\-nuc-init [0-9]+' "$f" 2>/dev/null | sort -u | tr '\n' ' ')
  printf '  %-22s sites-refill=%-3s nuc-init=%s\n' "$f" "$r" "${i:-（未传，默认 6）}"
done
echo
echo '################ ② 各臂**实际**命令行里的这两个参数（从日志横幅抓）################'
for T in A B C D E F G J20 J37 K1 K2 K3; do
  f="_w2_r581_mn64_${T}.log"
  [ -f "$f" ] || f="_w2_r581_mn64${T}.log"
  [ -f "$f" ] || continue
  r=$(grep -oE '\-\-nuc-sites-refill [0-9]+' "$f" 2>/dev/null | tail -1)
  i=$(grep -oE '\-\-nuc-init [0-9]+' "$f" 2>/dev/null | tail -1)
  printf '  %-4s %-28s %s\n' "$T" "${i:-（未传）}" "${r:-（未传 ⇒ 默认 False）}"
done
echo
echo '################ ③ 引擎自己有没有提示"位点用尽" ################'
for T in E F G; do
  f="_w2_r581_mn64_${T}.log"
  [ -f "$f" ] || continue
  printf '  %-3s ' "$T"
  grep -oE '位点[^，。]{0,20}' "$f" 2>/dev/null | sort -u | head -3 | tr '\n' ' '
  echo
done
echo
echo '################ ④ R481 的开关定义（默认值）################'
grep -n "nuc-sites-refill\|sites_refill" _bk_exp.py 2>/dev/null | head -6 | cut -c1-104 | sed 's/^/  /'
