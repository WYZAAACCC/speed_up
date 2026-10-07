#!/usr/bin/env bash
# _t16prod.sh --- T16 正规跑（**D17 修复后的平流格式 `proj2`**）。
#   规格依据（全部实测，见 WINDOWB_EXECUTION_PLAN.md §D12 决策）：
#     L = 9.6 µm（配置 A）、Δx = 50 nm ⇒ N=192 ⇒ 14.7 s/步、6.34 GB（T3 实测）
#     d = ρ^(-1/3) = 2.068 µm ⇒ **L/d = 4.64 ≥ 4**（D12d 盒子下限）
#     采样 f ≈ 0.10（D12e："刚碰撞后"；f_imp ≈ (π/4)(t/d) ≈ 0.038）
#     判据 M6p 用 **p25**（D16c）；守卫：逐变体绕盒 + 界面膨胀
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
exec $PY -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 --f-target 0.10 --adv proj2
