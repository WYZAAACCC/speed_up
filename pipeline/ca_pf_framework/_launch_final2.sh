#!/usr/bin/env bash
# _launch_final2.sh --- **约束链闭合后的最终生产排产**（Round 13，用户未否决 ⇒ 按 (a) 全跑）。
#   规格（五条约束的交集，逐条有实测依据）：
#     ① t/Δx ≥ 3        → t=200 nm（更接近文献 0.51–0.88 µm）/ Δx=50 nm ⇒ 4.0 ✓
#     ② d ≥ 2.5·2R_seed → 2R=600 nm ⇒ d = 1.6 µm ✓（**逐档固定**）
#     ③ L ≥ 4ρ^(−1/3)   → n ≥ 64 ✓
#     ④ Δf ≳ 3.5e8      → 用 D7 文献 ΔG@298 K = 3.5e8 ✓
#     ⑤ 成本 ∝ N^3.8    → L = d·n^(1/3) ⇒ N = 128/161/203
#   已落进 T13b_verify_nv.py 的默认值（R_SEED=300 nm, T_SEED=200 nm, D_FIX=1.6 µm）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import ast
for f in ('T13b_verify_nv.py', 'T16_verify_rve.py', 'T24_verify_grouping.py'):
    ast.parse(open(f).read())
print('SYNTAX OK')
EOF
# T13b：固定 d 设计，三档（N=128/161/203）
setsid nohup "$PY" -u T13b_verify_nv.py --dx-nm 50 --ns 64,128,256 \
        --f-target 0.06 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b pid=$!"
sleep 30
grep -v -e RuntimeWarning -e 'self.reinitialize' _t13b.log | head -18
echo '--- alive ---'
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-62
free -g | head -2
