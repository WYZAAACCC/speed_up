#!/bin/bash
# _t5_vrconsume.sh --- ★★★★★ `var_rule` 在哪里被消费？`random` 那一支为什么没生效？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `var_rule` 的全部出现（含被传进去的地方）════'
grep -n "var_rule" _bk_exp.py windowB_surface.py windowB_pf3d.py windowB_km.py 2>/dev/null | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② `_bk_exp.py:1791` 附近（看它传给了谁）════'
sed -n '1780,1800p' _bk_exp.py | nl -ba -v1780 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ③ `nucleate()` 的签名与 `var_rule` 参数 ════'
grep -n "def nucleate" windowB_surface.py | sed 's/^/  /'
grep -n "var_rule" windowB_pf3d.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ④ 在 windowB_surface.py 里找"选变体"的逻辑（random / argmax / drv）════'
grep -nE "random|argmax|drv\b|np\.argmax" windowB_surface.py 2>/dev/null \
  | grep -iE "var|drv|variant|random" | head -20 | cut -c1-160 | sed 's/^/  /'
