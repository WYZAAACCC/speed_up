#!/bin/bash
# _t5_ellwhy.sh --- ★★★★★ 为什么 ellipse 分支无效果（离线诊断）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① ellipse 分支之后，`v_cell` 还有没有被**重新赋值**（假设 c）════'
LN=$(grep -n "mob_iform == 'ellipse'" windowB_surface.py | head -1 | cut -d: -f1)
echo "  （ellipse 分支起于第 $LN 行）"
echo '  ── 分支结束后 60 行内所有 `v_cell` / `v_n` / `vel` 的赋值 ──'
awk -v s="$LN" 'NR>s && NR<s+90 && /v_cell *=|v_n *=|_vn *=|vel *=|v_cell\[/ {printf "     %d: %s\n", NR, $0}' windowB_surface.py | cut -c1-150
echo
echo '════ ② `mob_beta` 与 `mob_beta_w` 的实际数值（指数项强度）════'
grep -n "beta_h = \|beta_w = \|'--beta-h'\|'--beta-w'" _bk_exp.py | head -8 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ③ ★ 诊断开关：在 ellipse 分支里加一次性 print（_mfac_dt 的统计）—— 先看有没有现成的 ════'
grep -n "mfac_dt\|_g =\|_B =" windowB_surface.py | head -10 | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ④ 分支内 `ndir_` 与 `_s2` 的形状（若 ndir_ 是全 0 或未归一，_s2=0 ⇒ 指数=1，面内项才主导）════'
sed -n '4689,4699p' windowB_surface.py | sed 's/^/  /'
