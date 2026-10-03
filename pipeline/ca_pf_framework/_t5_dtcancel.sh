#!/bin/bash
# _t5_dtcancel.sh --- ★★★★★ 验证 §234 机制假设：`_mfac_dt` 是否被用于**重定 dt**（⇒ 抵消）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `_mfac_dt` 在三个分支之后**还有没有被用到**（4737 行之后）════'
LN=$(grep -n '_mfac_dt = Mfac' windowB_surface.py | head -1 | cut -d: -f1)
echo "  （exp2 分支的赋值在第 $LN 行）"
awk -v s="$LN" 'NR>=s && NR<s+40 && /_mfac_dt|dt *=|dt_eff|dtime/ {printf "     %d: %s\n", NR, $0}' windowB_surface.py | cut -c1-150
echo
echo '════ ② 全文件里 `_mfac_dt` 的每一处（含使用，不只赋值）════'
grep -n '_mfac_dt' windowB_surface.py | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ③ `apply` / 推进函数里 dt 是否被乘/除过 ════'
grep -n "dt = dt\|dt \*=\|/= .*mfac\|dt_eff\|effective.*dt" windowB_surface.py | head -10 | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ④ ★ 关键：`_g` 在"面内"取值 —— 直接算给三个角度（离线解析复算）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import numpy as np
B = 1.0/9.0
print('  mob_ratio=9 ⇒ B=1/9=%.4f' % B)
print('  %-28s %s' % ('方向', '_g = B/sqrt(B²cos²θ + sin²θ)'))
for name, th in (('沿 w（θ=0，_ca=1,_sw=0）', 0.0),
                 ('45°', np.pi/4),
                 ('沿 a（θ=90°，_ca=0,_sw=1）', np.pi/2)):
    ca, sw = np.cos(th), np.sin(th)
    g = B/np.sqrt(B*B*ca*ca + sw*sw)
    print('  %-28s **%.4f**' % (name, g))
print()
print('  ⇒ 沿 w **1.0000**（全速）· 沿 a **0.1111**（慢 9 倍）')
print('  ⇒ **设计说 h(a)/h(w)=9（a 快）⇒ 代码给的恰好相反（a 慢）**')
print('  ⚠ 但若这个乘子同时进入 dt 重标定 ⇒ 净效应为 0（与实测 Δ≈0 一致）')
PYEOF
