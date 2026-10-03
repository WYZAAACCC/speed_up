#!/bin/bash
# _t5_mobcli.sh --- ★★★★★ 迁移率各向异性的**全部 CLI 开关**与默认值（决定能不能"传参即验证"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 所有含 mob 的 add_argument ════'
grep -n "add_argument('--mob" _bk_exp.py | cut -c1-175 | sed 's/^/  /'
echo
echo '════ ② `mob_beta` 从哪来（是不是没有 CLI ⇒ 恒为 0 ⇒ 4668 行永不进入）════'
grep -n "mob_beta" _bk_exp.py | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ③ `kw` 那一行的**全文**（看传了哪些 mob_*）════'
LN=$(grep -n "kw = dict(aniso=" _bk_exp.py | head -1 | cut -d: -f1)
echo "  （kw 起点 = $LN）"
[ -n "$LN" ] && sed -n "${LN},$((LN+12))p" _bk_exp.py | sed 's/^/  /'
echo
echo '════ ④ `advance()` 里 4660-4680 段（`mob_beta` 怎么用）════'
sed -n '4655,4682p' windowB_surface.py | sed 's/^/  /'
