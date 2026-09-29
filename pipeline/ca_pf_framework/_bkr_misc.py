"""_bkr_misc.py —— B1(int8) / §3.3 钉扎 / §6.6 算术 / §4.6 界面带占比 / 平面 F3 对照。"""
import os
import sys
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import windowB_surface as W                                      # noqa: E402
from windowB_pf3d import C_cubic, argmin_normal                  # noqa: E402
from windowB_ti64_variants import variants                       # noqa: E402


def hdr(t):
    print('\n' + '=' * 78)
    print(t)
    print('=' * 78)


C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()

# ---------------------------------------------------------------- B1
hdr('B1  region() 的 int8 上限')
print('源码 :1166-1167  :  return np.argmin(self.phi, axis=0).astype(np.int8)')
for nreg in (127, 128, 129):
    a = np.zeros((nreg, 2, 2, 2))
    r = np.argmin(a, axis=0).astype(np.int8)
    print('   nreg=%3d : argmin 取到 index %3d -> int8 %4d  （最后一行 region=0 会被判成 %d）'
          % (nreg, nreg - 1, r.flat[0] if nreg == 128 else r.flat[0], r.flat[0]))
print('   ⇒ nreg<=127 才安全（nreg=129 时 index 128 -> int8 = -128）')

# 直接演示溢出
i = np.array([128], dtype=np.intp)
print('   演示: np.array([128]).astype(np.int8) =', i.astype(np.int8))

# ------------------------------------------------- §3.3 的钉扎到底是多少
hdr('§3.3 / §6.6  F3 界面的 M_eff：n_ref 究竟是哪个向量')
ng = np.array([0.00999987, 0.0, 0.99995])          # argmin_normal(C,0) 的返回值
print('  de=0 退化解（Fibonacci 第 0 点）n_garbage = %s' % ng)
print('  %-4s %-28s %-10s %-10s %-10s' % ('var', 'n*_v', '(n*·n_g)^2', 'M_eff/M0', '相对 0.0302'))
worst = (0, None)
for v in range(len(EPS0)):
    ns = argmin_normal(C, np.asarray(EPS0[v], float))[0]
    ns = ns / np.linalg.norm(ns)
    c2 = float(ns @ ng) ** 2
    meff = math.exp(-3.5 * c2)
    if meff > worst[0]:
        worst = (meff, v + 1)
    print('  V%-3d %-28s %-10.4f %-10.4f %-10.2f'
          % (v + 1, np.round(ns, 4), c2, meff, meff / math.exp(-3.5)))
print('  ⇒ 最坏变体 V%d：M_eff/M0 = %.4f = 文档假设(0.0302) 的 %.1f 倍'
      % (worst[1], worst[0], worst[0] / math.exp(-3.5)))
print('  ⇒ §6.6 的 d_curv 是按 M_eff=0.0302·M0 算的；按现状代码最坏会 ×%.1f'
      % (worst[0] / math.exp(-3.5)))

# ------------------------------------------------- §6.6 算术
hdr('§6.6 的算术核对（Δx=62.5 nm, N=192, 700 步）')
M0, DF, gam = 1e-9, 3.5e8, 0.396
dx = 62.5e-9
Meff = M0 * math.exp(-3.5)
dt = 0.15 * dx / (M0 * DF)
t = 700 * dt
kmax = 2.0 / dx
d = Meff * gam * kmax * t
print('  M_eff = %.4e ; γ=%.3f ; κ_max = %.4e ; dt = %.6e ; t = %.6e' % (Meff, gam, kmax, dt, t))
print('  d_curv = %.4e m = %.3f nm = %.4f Δx   （文档 7.2 nm / 0.11 Δx）' % (d, d * 1e9, d / dx))
print('  v_tip = M0·Δf = %.3f m/s ; 700 步位移 = %.3f µm  （文档 0.35 / 6.6）'
      % (M0 * DF, M0 * DF * t * 1e6))
print('  比值 = %.0f  （文档 915）' % (M0 * DF * t / d))
for g2, tag in ((1.1, 'wet 臂 γ=1.1'), (0.15, 'γ=0.15')):
    print('  γ_Σ=%.2f (%s): d = %.4f Δx' % (g2, tag, d / dx * g2 / gam))
print('  若 M_eff 取最坏变体（×%.1f）: d = %.3f Δx  ⇒ §6.6 的“0.11 Δx”变成 %.2f Δx'
      % (worst[0] / math.exp(-3.5), d / dx * worst[0] / math.exp(-3.5),
         d / dx * worst[0] / math.exp(-3.5)))

# ------------------------------------------------- §4.6 界面带占比
hdr('§4.6 的“界面带 0.023% of cells @ N=192”核对')
for tag, A_um2 in (('1 根 4×2×0.25 µm 板条', 2 * (4 * 2) + 2 * (4 * 0.25) + 2 * (2 * 0.25)),
                   ('6 根同上（§9.2 主臂）', 6 * (2 * (4 * 2) + 2 * (4 * 0.25) + 2 * (2 * 0.25))),
                   ('6 根 4×0.5×0.25 µm（R1 口径）', 6 * (2 * (4 * .5) + 2 * (4 * .25) + 2 * (.5 * .25)))):
    box_um3 = (12.0) ** 3
    band_um3 = A_um2 * (3 * 0.0625)        # |φ|<1.5Δx 的带厚 = 3Δx
    print('   %-28s A=%.2f µm² ⇒ 带体积/盒 = %.4f%%' % (tag, A_um2, 100 * band_um3 / box_um3))
print('   对照 R1 归档实测 nif（|φ_K|≤1.5Δx 的胞数，N=192）：')
import csv
p = os.path.join(HERE, '_exp', 'e4_lath6', 'series.csv')
with open(p) as f:
    rows = list(csv.DictReader(f))
nif = np.array([float(r['nif']) for r in rows])
print('      e4_lath6 : nif 首=%.0f (%.3f%%) 末=%.0f (%.3f%%) max=%.0f (%.3f%%)'
      % (nif[0], 100 * nif[0] / 192 ** 3, nif[-1], 100 * nif[-1] / 192 ** 3,
         nif.max(), 100 * nif.max() / 192 ** 3))
print('   ⇒ 文档的 0.023%% 比 R1 归档的*单变体*读数（0.10–0.73%%）低 4.5–32 倍')

# ------------------------------------------------- 平面 F3 对照
hdr('§6.6 正对照：**平面** F3 界面一步都不应该动')
N, dxp = 32, 25e-9
L = N * dxp
X = (np.arange(N) + 0.5) * dxp
XX, YY, ZZ = np.meshgrid(X, X, X, indexing='ij')
nstar = argmin_normal(C, np.asarray(EPS0[0], float))[0]
nstar = nstar / np.linalg.norm(nstar)
for tag, n in (('轴对齐 n=(0,0,1)', np.array([0., 0., 1.])), ('惯习面 n=n*_1', nstar)):
    eps_dup = [np.asarray(EPS0[0], float), np.asarray(EPS0[0], float)]
    g = W.LevelSetMulti(N, L, C=C, eps0=eps_dup, gamma=0.15, Mob=1e-9,
                        df=[0.0, 3.5e8, 3.5e8], workers=1,
                        reinit_every=0, reinit_dt=6e-7, reinit_band_cells=6.0)
    g.phi[:] = 1e3
    d = (XX - L / 2) * n[0] + (YY - L / 2) * n[1] + (ZZ - L / 2) * n[2]
    g.phi[1] = d
    g.phi[2] = -d
    g.npref = {1: nstar}
    reg0 = g.region().copy()
    dtp = 0.15 * dxp / (1e-9 * 3.5e8)
    dgs, flips = [], []
    for it in range(40):
        g.advance(dtp, aniso=0.0, npref=g.npref, band_cells=20, mob_beta=3.5,
                  mob_beta_w=0.0, adv_grad='proj2')
        dgs.append(float(g.dG_max))
        flips.append(int((g.region() != reg0).sum()))
    print('  %-18s dG_max 首/末 = %.3e / %.3e J/m³ ；40 步内 region 翻转总数 = %d'
          % (tag, dgs[0], dgs[-1], sum(flips)))
print('  ⇒ 平界面 κ≡0 ⇒ 驱动力逐位为 0 ⇒ 完全不动（支持 §6.6 的一半）')

# ------------------------------------------------- 变体转动的真实角
hdr('§2.2 的 r_α：引擎里根本没有取向自由度')
print('  LevelSetMulti 的属性表只有 df/eps0/npref/atab/wtab（见 :1060-1089）；')
print('  没有任何地方存 ω_α 或 r_α ⇒ “层级 1”下 θ 只能是外部输入。')
print('  已核对：_pair_normals 只用 eps0 差 ⇒ 同变体两条板的 ncmp 相同（= 垃圾向量）。')
