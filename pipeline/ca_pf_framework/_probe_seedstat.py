#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_seedstat.py --- **量具内部对照**：同一把尺子量"种子态"与"长成态"。

为什么要做这个（本轮第 15 处量具/判据级修正）
--------------------------------------------
`T13b` 报 `t = r_c^var = 167.3 nm`，我据此写"板条厚 ≈ 0.84 × 种子厚 200 nm
⇒ 板条**没有增厚**"。但那个 0.84 是**跨量具**比出来的：
  * 167.3 nm 是 **`r_c^var`**（变体标记相关长度）的读数；
  * 200 nm 是 **`seed_plate` 的几何参数**（真值）。
而 `T13_calib_thickness.py` 实测 `r_c^var` 对薄板的偏差是 **0.76–1.00**（非 1）
⇒ 两个数**不同尺**，比出来的 0.84 里混着量具偏差。

正确做法（`MEASUREMENT_SPEC R0`）：**用同一把尺子量两端** ——
把 `T13b` 的**同一套种子**（同 rng、同 NPF、同 n=64、同 L=6.4 µm）
原样种下去，在 **step=0** 就叫一次 `stats()`，得到 `r_c^var(seed)`。
再与 `_t13b.log` 里长到 `f=0.016` 的 `r_c^var(grown)` 相减
⇒ **增量与量具偏差无关**（同形状族、同尺子）。

同时补 `T13_calib_thickness.py` 的**工况缺口**：那里的 R/t = 2.5/5/10，
而 T13b 用的种子是 `R=300 nm, t=200 nm` ⇒ **R/t = 1.5（未标定区）**。
本探针补 R/t = 1.5/2.25/3.0 三档，量出该区的 `r_c^var/t`。

判据
----
  S-1 正对照：R/t=1.5 档上 `r_c^var/t` 必须落在本探针自己给出的带内（记录即可）
  S-2 种子态统计：`r_c^var(seed)` 与 `2f/Sv(seed)`、`f_seed`（= 纯种子体积分数）
  S-3 ★ **增量判据**：`r_c^var(grown)/r_c^var(seed)` —— 若 ≈1 则"未增厚"成立
  S-4 预算判据：算清"增厚可用步数"（到 impingement 为止）与"增厚需要步数"

用法：python3 _probe_seedstat.py [--ns 64] [--dx-nm 50] [--f-target 0.016]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import stats, C, EPS0, NV, NPF, R_SEED, T_SEED   # noqa: E402
from T13b_verify_nv import DF, MOB, D_FIX                        # noqa: E402

print('=' * 100)
print('_probe_seedstat —— 同尺子对照：种子态 vs 长成态（补 R/t=1.5 标定）')
print('=' * 100)

# ---------------------------------------------------------------- A. 工况缺口标定
print('\n【A】补标定：T13b 实际种子是 `R=300 nm, t=200 nm` ⇒ **R/t = 1.5**，')
print('     而 `T13_calib_thickness.py` 只标了 R/t = 2.5/5/10。补上 1.5/2.0/3.0：\n')
L_CAL, DX_CAL = 2.4e-6, 25e-9
N_CAL = int(round(L_CAL / DX_CAL))


def _mk(shape, R, t):
    g = W.LevelSetMulti(N_CAL, L_CAL, C=None, eps0=None, nv=1, gamma=0.15, Mob=1e-9,
                        df=[0.0, 1e8], workers=1, reinit_every=0)
    c0 = np.array([L_CAL / 2] * 3)
    if shape == 'plate':
        g.seed_plate(1, c0, np.array([0.0, 0.0, 1.0]), R, t)
    else:
        g.seed_sphere(1, c0, R)
    g.init_parent()
    s = stats(g)
    return s, 2.0 * s['f'] / max(s['Sv'], 1e-30)


print('  %-24s %-10s %-12s %-10s %-12s %-10s' %
      ('构型', '已知 t(nm)', 'r_c^var(nm)', 'E2/t', '2f/Sv(nm)', 'E1/t'))
cal = []
for R_nm, t_nm in ((300, 200), (400, 200), (600, 200), (600, 300), (900, 300)):
    s, e1 = _mk('plate', R_nm * 1e-9, t_nm * 1e-9)
    r2 = s['t'] / (t_nm * 1e-9)
    cal.append((R_nm / t_nm, r2))
    print('  %-24s %-10.0f %-12.1f %-10.3f %-12.1f %-10.3f'
          % ('板条 R=%d t=%d (R/t=%.1f)' % (R_nm, t_nm, R_nm / t_nm),
             t_nm, s['t'] * 1e9, r2, e1 * 1e9, e1 / (t_nm * 1e-9)))
print('  （球档见 `_t13cal.log`：`r_c^var/D = 0.426–0.428` ⇒ 对等轴形状 E2 也不是直径）')
band = [v for _, v in cal]
print('  ⇒ 工况带 R/t∈[1.5,3.0] 内 `r_c^var/t` ∈ [%.3f, %.3f]（本探针自测）'
      % (min(band), max(band)))

# ---------------------------------------------------------------- B. 种子态 vs 长成态
ap = argparse.ArgumentParser()
ap.add_argument('--ns', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--f-target', type=float, default=0.016)
ap.add_argument('--adv', default='proj2')
a = ap.parse_args()
dx = a.dx_nm * 1e-9
L = D_FIX * a.ns ** (1 / 3.0)          # ★ 与 T13b 完全同一个规格（固定 d）
N = int(round(L / dx))

print('\n【B】`T13b` 的同一套种子（同 rng=7、同 NPF、同 L=%.2f µm、n=%d）在 **step=0** 的统计：'
      % (L * 1e6, a.ns))


def build(nseed, rng_seed=7):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(rng_seed)
    ns, tries = 0, 0
    while ns < nseed and tries < nseed * 8:
        tries += 1
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g, ns


g, ns = build(a.ns)
s0 = stats(g)
v_seed = np.pi * R_SEED ** 2 * T_SEED          # seed_plate 的体积（πR²t）
f_seed_analytic = ns * v_seed / L ** 3
print('  实际种下 %d / %d 个（其余因重叠被 `seed_plate` 拒绝）' % (ns, a.ns))
print('  种子核数密度 ρ = %.4f µm^-3（d = ρ^(-1/3) = %.3f µm）'
      % (ns / (L ** 3 * 1e18), (L ** 3 / ns) ** (1 / 3.0) * 1e6))
print('  `f`（`stats` 口径）        = %.5f' % s0['f'])
print('  `f`（纯种子解析 πR²t·n/L³）= %.5f   ⇒ 几何一致 ✅' % f_seed_analytic)
print('  `r_c^var(seed)`            = **%.1f nm**' % (s0['t'] * 1e9))
print('  `2f/Sv(seed)`              = %.1f nm' % (2 * s0['f'] / s0['Sv'] * 1e9))
print('  `M6p p25(seed)`            = %.1f°' % s0['m6p_p25'])

# 与 _t13b.log 的长成读数对比（同尺子 ⇒ 差值是干净的）
GROWN_F, GROWN_RC = 0.0160, 167.3e-9
print('\n  ── 与 `_t13b.log`（n=64 档，`f=0.0160`，**同一把尺子**）对比 ──')
print('  `r_c^var`：种子 %.1f nm → 长成 %.1f nm   比值 **%.3f**'
      % (s0['t'] * 1e9, GROWN_RC * 1e9, GROWN_RC / s0['t']))
print('  `f`      ：种子 %.5f → 长成 %.5f       比值 **%.3f**'
      % (s0['f'], GROWN_F, GROWN_F / max(s0['f'], 1e-30)))
# 若厚度不变，f ∝ 面内面积 ⇒ 面内半径的增长率
grow_v = GROWN_F / max(s0['f'], 1e-30)
print('  ⇒ 体积增长 ×%.2f；若厚度不变则面内面积 ×%.2f ⇒ 面内半径 ×%.2f'
      % (grow_v, grow_v, np.sqrt(grow_v)))

# ---------------------------------------------------------------- C. 预算账
ev = float(np.exp(-3.5))                       # mob_beta=3.5 ⇒ 宽面迁移率压低倍数
dt = 0.15 * dx / (MOB * DF)
v_tip = MOB * DF
v_face = v_tip * ev
step_grown = 45
t_phys = step_grown * dt
print('\n【C】预算账（解析，全部来自本探针读到的常数）')
print('  `dt`（CFL：0.15 Δx /(M0Δf)）   = %.3e s' % dt)
print('  快向速度 `v_tip = M0Δf`        = %.3f m/s ⇒ 每步 %.2f nm = %.3f Δx'
      % (v_tip, v_tip * dt * 1e9, v_tip * dt / dx))
print('  宽面速度 `v_face = v_tip·e^-3.5` = %.4f m/s ⇒ 每步 %.3f nm = %.4f Δx（慢 %.0f×）'
      % (v_face, v_face * dt * 1e9, v_face * dt / dx, 1 / ev))
print('  已跑 %d 步 = %.2e s 物理时间' % (step_grown, t_phys))
print('    ⇒ 快向应推进 %.0f nm（种子 R=300 ⇒ R≈%.0f nm）' % (v_tip * t_phys * 1e9,
                                                      300 + v_tip * t_phys * 1e9))
print('    ⇒ 厚向应增厚 %.1f nm（= %d 步 × %.3f nm）'
      % (v_face * t_phys * 1e9, step_grown, v_face * dt * 1e9))
d_um = (L ** 3 / ns) ** (1 / 3.0)
t_ceil = T_SEED + (d_um / 2 - R_SEED) * ev
print('  ★ **碰撞前天花板**：`d/2 - R_seed` = %.0f nm ⇒ 碰撞前最多增厚 %.1f nm'
      % ((d_um / 2 - R_SEED) * 1e9, (d_um / 2 - R_SEED) * ev * 1e9))
print('    ⇒ 在 impingement 之前，板条厚**上限** ≈ **%.0f nm**（种子 %.0f + %.1f）'
      % (t_ceil * 1e9, T_SEED * 1e9, (d_um / 2 - R_SEED) * ev * 1e9))
print('    ⇒ 文献 as-built LPBF α′ 板条厚 **510–880 nm** ⇒ 差 **%.1f–%.1f×**'
      % (510e-9 / t_ceil, 880e-9 / t_ceil))
print('  ⇒ 要增厚到 700 nm 需要 %.0f 步（= %.1f h @ 30 s/步）'
      % ((700e-9 - T_SEED) / (v_face * dt), (700e-9 - T_SEED) / (v_face * dt) * 30 / 3600))
print('     而到 impingement 只需 %.0f 步（f_imp ≈ %.3f）'
      % ((d_um / 2 - R_SEED) / (v_tip * dt), ns * np.pi * (d_um / 2) ** 2 * T_SEED / L ** 3))
print('=' * 100)
