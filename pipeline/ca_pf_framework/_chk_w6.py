#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_w6.py --- W-6 判据：Stefan 的「面储存 -> 回吐」时序 + 驱动协议（不只守恒量）。

背景：M4 的老备注说「Stefan 只做了'推给邻居'、还没做'先存进面 Γ、再由面扩散/回吐'」
      —— 读代码发现**机制已实现**（ 的 (a) 段存 Γ； 做
      McLean 局部平衡交换 + 保守面扩散 + 离带回吐）。所以本判据改为证明**时序与协议**：

  A. **正确协议**（每步 advance + update_Gamma）：体+面守恒 < 1e-6 ✓；Γ 维持在 McLean 附近。
  B. **存储步隔离**：逐步测 Δ(体) + Δ(面) —— 界面扫过的**那一步**必须逐位守恒（< 1e-9）。
  C. **负对照**（只 advance、不调 update_Gamma）：被扫出的溶质**滞留面 Γ**（不回吐），
     且界面移走后离带胞的 Γ **脱离账本** ⇒ 账面出现亏损（≫1e-6）⇒ 证据表明
     **驱动必须每步调 update_Gamma**（M2/B1 原来都没调 —— 本轮已补）。

记账：这是**驱动协议**的判据，不是 surface 类的判据（类的机制本身是对的）。
"""
import numpy as np

from windowB_surface import LevelSetMulti

ok = {}


def rec(tag, verdict, extra=''):
    ok[tag] = verdict
    print('   %-58s %-7s %s' % (tag, verdict, extra))


def setup(N=32, dx=1e-8, df=1e8, c0=0.036):
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=1e-9, df=[0.0, df],
                      reinit_every=0)
    z = (np.arange(N)[None, None, :] + 0.5) * dx
    L = N * dx
    a = 0.25 * L
    g.phi[1] = np.where(z <= a, -np.minimum(z, a - z),
                        np.minimum(z - a, L - z)) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    g.c = np.full((N, N, N), c0)
    g.Gam = np.zeros((N, N, N))
    return g


N, dx = 32, 1e-8
v_if = 1e-9 * 1e8
dt = 0.05 * dx / v_if
tau, Ds = 1e-9, 1e-20
print('==== W-6 Stefan「面储存 -> 回吐」时序 + 驱动协议 ====')

# ---------------- A. 正确协议：advance + update_Gamma ----------------
g = setup(N=N, dx=dx)
mb0, ms0 = g.totals()
dmax = 0.0
for _ in range(30):
    mb, ms = g.totals()
    g.advance(dt, extend='edt', band_cells=20)
    g.update_Gamma(dt, tau_ex=tau, D_s=Ds)
    mb2, ms2 = g.totals()
    dmax = max(dmax, abs((mb2 + ms2) - (mb + ms)) / max(abs(mb0 + ms0), 1e-30))
mb1, ms1 = g.totals()
relA = abs((mb1 + ms1) - (mb0 + ms0)) / max(abs(mb0 + ms0), 1e-30)
print('   A. 正确协议 30 步：体 %+.3e ; 面 %+.3e mol ; 累积相对漂移 %.2e（单步最大 %.2e）'
      % (mb1 - mb0, ms1 - ms0, relA, dmax))
rec('W6-1A 正确协议（每步 advance+update_Gamma）体+面守恒 < 1e-6',
    'PASS' if relA < 1e-6 else 'FAIL', 'rel=%.2e' % relA)
Geq = g.Gamma_eq(g.c)
m = g.cell_area_geom() > 0
devA = float(np.abs(g.Gam[m] - Geq[m]).max() / max(np.abs(Geq[m]).max(), 1e-300))
rec('W6-2A Γ 维持在 McLean 平衡附近（|Γ-Γ_eq|/Γ_eq < 1e-2）',
    'PASS' if devA < 1e-2 else 'FAIL', 'dev=%.2e' % devA)

# ---------------- B. 存储步隔离（逐步测） ----------------
g2 = setup(N=N, dx=dx)
worst = 0.0
t0 = sum(g2.totals())
found = 0
for k in range(30):
    mb, ms = g2.totals()
    g2.advance(dt, extend='edt', band_cells=20)
    mb2, ms2 = g2.totals()
    d = abs((mb2 + ms2) - (mb + ms))
    if d > 0:
        worst = max(worst, d / max(abs(t0), 1e-30))
        found += 1
print('   B. 单步隔离：%d 个"有胞翻转"的步，单步最大相对不平衡 %.2e'
      % (found, worst))
rec('W6-3B 存储步本身逐位守恒（单步相对 < 1e-9）',
    'PASS' if worst < 1e-9 else 'FAIL', 'max=%.2e（%d 个活动步）' % (worst, found))

# ---------------- C. 负对照：只 advance ----------------
g3 = setup(N=N, dx=dx)
mb0c, ms0c = g3.totals()
fh = []
for _ in range(30):
    g3.advance(dt, extend='edt', band_cells=20)
    mb, ms = g3.totals()
    fh.append(ms)
mb1c, ms1c = g3.totals()
fh = np.array(fh)
relC = abs((mb1c + ms1c) - (mb0c + ms0c)) / max(abs(mb0c + ms0c), 1e-30)
print('   C. 负对照（只 advance）：面 %+.3e mol ; 账面漂移 %.2e' % (ms1c - ms0c, relC))
rec('W6-4C 负对照：面 Γ 净增（溶质滞留面、不回吐）',
    'PASS' if (ms1c - ms0c) > 0 else 'FAIL', 'd_face=%+.3e' % (ms1c - ms0c))
rec('W6-5C 负对照：会计出现亏损（≫1e-6）=> 驱动必须调 update_Gamma',
    'PASS' if relC > 1e-6 else 'FAIL', 'rel=%.2e' % relC)

nP = sum(1 for v in ok.values() if v == 'PASS')
nF = sum(1 for v in ok.values() if v == 'FAIL')
print()
print('W-6 汇总: PASS %d / FAIL %d' % (nP, nF))
if nF:
    print('FAIL 项: %s' % [k for k, v in ok.items() if v == 'FAIL'])
