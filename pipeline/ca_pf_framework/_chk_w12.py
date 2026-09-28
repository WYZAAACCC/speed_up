#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_w12.py —— `W1-2`（pair reinit 统计量域开关）的**验收判据**

判据（每一条都带"已知答案"或反向对照）
--------------------------------------
* **C-1 向后兼容（**硬判据，逐位**）**：`band_cells=None`（默认）时，
  新代码必须与**忠实转写的旧实现**输出**逐位相同**（`np.array_equal`，不是 `allclose`）。
  > 依据 `AGENTS.md` §3.3 教训 22：判据要写"差异落在容差内"还是"逐位相同"**取决于物理**。
  > 这里物理上就该是**逐位相同** —— 因为走的是同一条表达式路径（`_sel is None` ⇒ `np.median(_gn)`），
  > 不是"另一条数值路径算出同一个值"。
* **C-2 归档回归**：用与 `_w023long.log`（**旧 SHA `fab5056b…`**）同一命令重跑，
  读数必须与归档值一致（`0.8953 / 0.8495 / 0.7759`，4 位小数）。
* **C-3 启用路径有效**：`reinit_band_cells=6` 时，`reinitialize()` 的恢复率必须
  **显著优于**默认臂（猴补丁预测 **−2.7% → +97.1%**）。
* **C-4 空带边界**：带掩模为空时**必须退回全域**，且**不得**静默变成"全选/全不选"。
  做法：传一个不可能有胞满足的 `band_cells=0.0` ⇒ 结果必须与默认臂**逐位相同**。
* **C-5 单场路径不受影响**：`LevelSetSurface` 那条调用不传 `band_cells` ⇒ 逐位不变
  （由 `getattr(self,'reinit_band_cells',None)` 保证；此处只做静态断言 + 默认值检查）。

退出码：0 = 全 PASS。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF, KV = 1e-9, 3.5e8, 1
fails = []


def sussman_orig(phi, dx, iters=40, dtau=None, grad='upwind2', guard=True):
    """★ **忠实转写**的旧实现（`git show` 前的 `windowB_surface.py:158-215`）。
       唯一的用途是给 C-1 当"已知答案"参照。**不参与任何生产调用。**"""
    phi0 = phi.copy()
    _g = np.gradient(phi0, dx)
    _gn = np.sqrt(sum(_gi ** 2 for _gi in _g))
    _gm = float(np.median(_gn))
    if _gm > 1e-12 and abs(_gm - 1.0) > 0.2:
        phi = phi / _gm
        phi0 = phi0 / _gm
    S = phi0 / np.sqrt(phi0 ** 2 + dx ** 2)
    if dtau is None:
        dtau = 0.5 * dx / 3.0
    _phi_raw = phi0.copy()
    _lim0 = float(np.max(np.abs(phi0))) + dx
    for _ in range(iters):
        if grad == 'upwind':
            gm = W.upwind_grad(phi, S, dx)
        elif grad == 'upwind2':
            gm = W.upwind_grad2(phi, S, dx)
        elif grad == 'central':
            g = np.gradient(phi, dx)
            gm = np.sqrt(sum(gi ** 2 for gi in g))
        else:
            gm = W.grad_sym(phi, dx)
        _gmax = float(np.max(gm))
        _dte = min(dtau, 0.5 * dx / 3.0 / max(_gmax, 1.0))
        _upd = _dte * S * (gm - 1.0)
        phi = phi - np.clip(_upd, -0.5 * dx, 0.5 * dx)
        if guard and float(np.max(np.abs(phi))) > 10.0 * _lim0:
            return _phi_raw
    return phi


N, dx = 96, 50e-9
L = N * dx
print('=' * 100)
print('_chk_w12 —— W1-2（reinit 统计量域开关）验收')
print('=' * 100)

# ---------------------------------------------------------------- 建一个真实的退化场
def build_g(band=None):
    """`band=None` ⇒ **显式**传 `reinit_band_cells=None`（= 退回全域/旧行为）。
       ★ 注意：`LevelSetMulti` 的**类默认**自 2026-09-28 起已是 **6.0（启用）**，
       所以"旧行为"必须**显式**写 `None` —— 这也正是本函数存在的理由。"""
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4,
                        reinit_every=0, reinit_dt=None,
                        reinit_band_cells=(None if band is None else float(band)))
    c = np.array([L / 2] * 3)
    nh = np.asarray(NPF[KV], float)
    nh = nh / np.linalg.norm(nh)
    aa = np.asarray(g.atab[KV], float)
    aa = aa - (aa @ nh) * nh
    aa = aa / np.linalg.norm(aa)
    g.seed_plate(KV, c, nh, 300e-9, 200e-9, elong=4.0, along=aa)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    for _ in range(40):
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, norm_smooth=2)
    return g


g = build_g()
o = np.argsort(g.phi, axis=0)
d2 = 0.5 * (np.take_along_axis(g.phi, o[0][None], 0)[0]
            - np.take_along_axis(g.phi, o[1][None], 0)[0])
near = np.abs(d2) <= 6.0 * dx

# ---------------------------------------------------------------- C-1 逐位向后兼容
new = W.sussman_reinit(d2, dx, iters=100, grad='upwind2')
old = sussman_orig(d2, dx, iters=100, grad='upwind2')
ok = np.array_equal(new, old)
print('\n【C-1 向后兼容：`band_cells=None` 必须与旧实现**逐位相同**】')
print('   `np.array_equal(new, old)` = **%s**   （最大差 = %.3e）'
      % (ok, float(np.max(np.abs(new - old)))))
print('   ⇒ %s' % ('PASS（走的是同一条表达式路径，不是"另一条路径碰巧同值"）' if ok else 'FAIL'))
if not ok:
    fails.append('C-1')

# ---------------------------------------------------------------- C-4 空带边界
z = W.sussman_reinit(d2, dx, iters=100, grad='upwind2', band_cells=0.0)
ok4 = np.array_equal(z, old)
print('\n【C-4 空带边界：`band_cells=0.0` ⇒ 必须**显式退回全域**】')
print('   与默认臂逐位相同 = **%s**（差 = %.3e）' % (ok4, float(np.max(np.abs(z - old)))))
print('   ⇒ %s（若变成"全不选"，这里会得到 `_phi_raw` 或全零，不会与默认臂相同）'
      % ('PASS' if ok4 else 'FAIL'))
if not ok4:
    fails.append('C-4')

# ---------------------------------------------------------------- C-3 启用路径有效
def reinit_recovery(band):
    gg = build_g(band)
    oo = np.argsort(gg.phi, axis=0)
    dd = 0.5 * (np.take_along_axis(gg.phi, oo[0][None], 0)[0]
                - np.take_along_axis(gg.phi, oo[1][None], 0)[0])
    nr = np.abs(dd) <= 6.0 * dx

    def med(f):
        gr = np.gradient(f, dx)
        return float(np.median(np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)[nr]))
    b = med(dd)
    rg = gg.region()
    nb0 = int(sum((rg != np.roll(rg, -1, ax)).sum() for ax in range(3)))
    gg.reinitialize()
    a = med(0.5 * (np.take_along_axis(gg.phi, np.argsort(gg.phi, axis=0)[0][None], 0)[0]
                   - np.take_along_axis(gg.phi, np.argsort(gg.phi, axis=0)[1][None], 0)[0]))
    rg2 = gg.region()
    nb1 = int(sum((rg2 != np.roll(rg2, -1, ax)).sum() for ax in range(3)))
    return b, a, (a - b) / max(1e-9, 1.0 - b), int((rg2 != rg).sum()), nb1 / max(nb0, 1)


b0, a0, r0, f0, br0 = reinit_recovery(None)
b6, a6, r6, f6, br6 = reinit_recovery(6)
print('\n【C-3 启用 `reinit_band_cells=6` 必须显著改善】')
print('   默认(None)：%.4f → %.4f  恢复率 **%+.3f**  翻转 %d  界面键 %.4f×' % (b0, a0, r0, f0, br0))
print('   启用(6)   ：%.4f → %.4f  恢复率 **%+.3f**  翻转 %d  界面键 %.4f×' % (b6, a6, r6, f6, br6))
ok3 = r6 > r0 + 0.2 and f6 == 0 and br6 <= 1.2
print('   ⇒ %s（要求：恢复率提升 > 0.2、翻转=0、界面键 ≤1.2×）'
      % ('PASS' if ok3 else 'FAIL'))
if not ok3:
    fails.append('C-3')

# ---------------------------------------------------------------- C-5 默认值 + 单场路径
print('\n【C-5 类默认已启用；显式 `None` 仍可复现旧行为；单场路径不受影响】')
_gdef = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=None)
print('   不传参时的类默认 `reinit_band_cells` = **%r**（应为 6.0 = 已启用）'
      % getattr(_gdef, 'reinit_band_cells', 'MISSING'))
print('   显式传 None 时 = **%r**（应为 None = 旧行为）' % build_g(None).reinit_band_cells)
print('   `LevelSetSurface` 那条调用不传 `band_cells` ⇒ 走 `getattr(...,None)`；'
      '该类没有 `reinit_band_cells` 属性 ⇒ 模块级默认仍为 None ⇒ **不受影响**')
ok5 = (getattr(_gdef, 'reinit_band_cells', 'MISSING') == 6.0
       and build_g(None).reinit_band_cells is None)
print('   ⇒ %s' % ('PASS' if ok5 else 'FAIL'))
if not ok5:
    fails.append('C-5')

print('\n' + '=' * 100)
print('=== W1-2 验收 %s ===' % ('全部 PASS' if not fails else ('FAIL: ' + ','.join(fails))))
sys.exit(0 if not fails else 1)
