#!/bin/bash
# _t5_mobaniso.sh --- ★★★★★ 查"迁移率各向异性"（= 伸长机制）到底有没有在跑
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① CLI 里的迁移率各向异性参数（定义 + 默认值）════'
grep -n "add_argument('--mob-aniso'\|add_argument('--mob-wulff'\|add_argument('--mob-beta'\|add_argument('--mob-ratio'\|add_argument('--mob-iform'\|add_argument('--mob-dip'" _bk_exp.py | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ② 引擎里 `mob_aniso` 的实际取值（怎么算出来的）════'
grep -n "mob_aniso" _bk_exp.py | head -12 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ③ 我的启动器有没有传这些 ════'
grep -n "mob-aniso\|mob-wulff\|mob-ratio\|mob-iform\|mob-beta" _t5_short.py | cut -c1-140 | sed 's/^/  /'
echo '  （空 = 没传 ⇒ 用引擎默认）'
echo
echo '════ ④ ★ 运行横幅里与"迁移率/各向异性"有关的行（**我先前漏读的**）════'
for t in t5H3 t5AD_700; do
  L=$(ls _w2_t5_short_$t.log _w2_t5_ad_$t.log 2>/dev/null | head -1)
  echo "  ── $t （$L）──"
  grep -nE "迁移率|各向异性|mob|钉扎|pin" "$L" 2>/dev/null | head -8 | cut -c1-155 | sed 's/^/     /'
done
