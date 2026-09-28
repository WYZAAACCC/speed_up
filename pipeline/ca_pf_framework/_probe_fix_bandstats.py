#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_fix_bandstats.py —— ★★★ **验证 Gate A-1 选项①**：把 `_gm`/`_gmax` 从"全域"改成"带内"

为什么这是**唯一正确的隔离实验**
----------------------------------
`_probe_reinit_iter.py` 的 B-1/B-2 是我在**还不知道根因时**设计的：
* B-1 只跑现状；
* B-2 把带外**夹平** —— 而夹平**自己造出新的台阶/折点**，`upwind_grad2` 在新折点上仍有伪尖峰
  ⇒ **它同时改了两个东西**（统计量的域 + 场的形状）⇒ **不是单变量**，无法归因。

本探针**只改一个变量**：算子的统计量取"全域"还是"带内"。其余**逐字相同**。
实现手段：在本进程内**猴补丁**（monkey-patch）模块级 `sussman_reinit`。
> ⚠ **引擎文件一个字节都不改** ⇒ `windowB_surface.py` 的 SHA 保持不变
> ⇒ **不影响任何在跑作业的读数归属**（`R11-c`）。

三臂（**同一状态**上依次做，判据是"前后比较"与"两臂比较"）
------------------------------------------------------------
* **A 现状**：stock `reinitialize()`；
* **B 选项①**：`_gm`/`_gmax` 改为**带内**（`|phi0| <= band_cells*dx`）；
* **C 反向对照**：把算子换成**恒等**（原样返回）⇒ **必须 Δ=0**，
  用来证明"我的量具能分辨出'没改动'"（否则 B 的改善可能是量具噪声）。

同时报 **两把尺子**（中心差分 与 `upwind_grad2`），因为根因正是两者的**全域最大值**相差 68 倍。

用法：python3 _probe_fix_bandstats.py [--N 96] [--dx-nm 50] [--evolve 60] [--iters 100]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402
from _band_health import health, fmt                             # noqa: E402

MOB, DF, KV = 1e-9, 3.5e8, 1
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=96)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--el', type=float, default=4.0)
ap.add_argument('--evolve', type=int, default=60, help='先演化这么多步，制造真实退化')
ap.add_argument('--iters', type=int, default=100)
ap.add_argument('--band-cells', type=float, default=6.0)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx
print('=' * 104)
print('_probe_fix_bandstats —— 验证 Gate A-1 选项①（统计量从全域改成带内），单变量')
print('  N=%d Δx=%.1f nm L=%.2f µm  先演化 %d 步  算子 iters=%d  带=%g·dx'
      % (N, a.dx_nm, L * 1e6, a.evolve, a.iters, a.band_cells))
print('=' * 104)

_ORIG = W.sussman_reinit          # 保存原函数，供 A 臂与恢复


def make_band_variant(band_cells):
    """与 stock **逐字相同**，只把两处统计量的域从全域换成带内。"""
    def _f(phi, dx_, iters=40, dtau=None, grad='upwind2', guard=True):
        phi0 = phi.copy()
        _band = np.abs(phi0) <= band_cells * dx_
        if not _band.any():
            _band = np.ones_like(phi0, dtype=bool)
        _g = np.gradient(phi0, dx_)
        _gn = np.sqrt(sum(_gi ** 2 for _gi in _g))
        _gm = float(np.median(_gn[_band]))                    # ★ 带内
        if _gm > 1e-12 and abs(_gm - 1.0) > 0.2:
            phi = phi / _gm
            phi0 = phi0 / _gm
        S = phi0 / np.sqrt(phi0 ** 2 + dx_ ** 2)
        if dtau is None:
            dtau = 0.5 * dx_ / 3.0
        _phi_raw = phi0.copy()
        _lim0 = float(np.max(np.abs(phi0))) + dx_
        for _ in range(iters):
            if grad == 'upwind':
                gm = W.upwind_grad(phi, S, dx_)
            elif grad == 'upwind2':
                gm = W.upwind_grad2(phi, S, dx_)
            elif grad == 'central':
                g = np.gradient(phi, dx_)
                gm = np.sqrt(sum(gi ** 2 for gi in g))
            else:
                gm = W.grad_sym(phi, dx_)
            _gmax = float(np.max(gm[_band]))                  # ★ 带内
            _dte = min(dtau, 0.5 * dx_ / 3.0 / max(_gmax, 1.0))
            _upd = _dte * S * (gm - 1.0)
            phi = phi - np.clip(_upd, -0.5 * dx_, 0.5 * dx_)
            if guard and float(np.max(np.abs(phi))) > 10.0 * _lim0:
                return _phi_raw
        return phi
    return _f


def identity(phi, dx_, iters=40, dtau=None, grad='upwind2', guard=True):
    return phi.copy()


def two_rulers(g_):
    o = np.argsort(g_.phi, axis=0)
    d = 0.5 * (np.take_along_axis(g_.phi, o[0][None], 0)[0]
               - np.take_along_axis(g_.phi, o[1][None], 0)[0])
    nr = np.abs(d) <= a.band_cells * dx
    gg = np.gradient(d, dx)
    cen = np.sqrt(gg[0] ** 2 + gg[1] ** 2 + gg[2] ** 2)
    S = d / np.sqrt(d ** 2 + dx ** 2)
    uw = W.upwind_grad2(d, S, dx)
    return (float(np.median(cen[nr])), float(np.median(uw[nr])),
            float(np.max(cen)), float(np.max(uw)))


# ---------------------------------------------------------------- 建场 + 演化出真实退化
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=None)
c = np.array([L / 2] * 3)
nh = np.asarray(NPF[KV], float)
nh = nh / np.linalg.norm(nh)
aa = np.asarray(g.atab[KV], float)
aa = aa - (aa @ nh) * nh
aa = aa / np.linalg.norm(aa)
g.seed_plate(KV, c, nh, 300e-9, 200e-9, elong=a.el, along=aa)
g.init_parent()
dt = 0.15 * dx / (MOB * DF)
if a.evolve:
    print('   演化 %d 步（reinit_dt=None ⇒ 期间**不触发** reinit，保证 A/B/C 的初态是同一个）…'
          % a.evolve)
    for _ in range(a.evolve):
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, norm_smooth=2)

cen0, uw0, cenmax0, uwmax0 = two_rulers(g)
print('\n【共同初态】带内 中心差分 `med|∇d2|` = **%.4f** ；`upwind_grad2` = **%.4f**' % (cen0, uw0))
print('   全域最大：中心差分 = **%.2f** ；**`upwind_grad2` = %.2f**  ⇒ 真实节流 = **%.4f**'
      % (cenmax0, uwmax0, min(1.0, 1.0 / max(uwmax0, 1.0))))
print('   （★ 两者的**全域最大值**相差 %.1f×，而带内中位只差 %.4f —— 这就是根因所在）'
      % (uwmax0 / max(cenmax0, 1e-9), abs(uw0 - cen0)))

# ---------------------------------------------------------------- 三臂
res = {}
for tag, fn, note in (
        ('A 现状（全域统计）', _ORIG, 'stock'),
        ('B 选项①（带内统计）', make_band_variant(a.band_cells), 'band'),
        ('C 反向对照（恒等算子）', identity, 'identity')):
    W.sussman_reinit = fn
    # 让配对重初始化用我们的 iters（`LevelSetMulti.sussman_reinit` 透传 self.reinit_iters）
    g.reinit_iters = a.iters
    reg_b = g.region()
    nbb = int(sum((reg_b != np.roll(reg_b, -1, ax)).sum() for ax in range(3)))
    before = two_rulers(g)
    import warnings as _w
    with _w.catch_warnings(record=True) as rec:
        _w.simplefilter('always')
        g.reinitialize()
    nw = sum(1 for r in rec if 'pair reinit' in str(r.message))
    after = two_rulers(g)
    reg_a = g.region()
    nba = int(sum((reg_a != np.roll(reg_a, -1, ax)).sum() for ax in range(3)))
    res[tag] = dict(before=before, after=after, flips=int((reg_a != reg_b).sum()),
                    nb=(nbb, nba), warn=nw,
                    rdone=getattr(g, '_reinit_done', 0), rskip=getattr(g, '_reinit_skipped', 0))
    print('\n【%s】%s' % (tag, note))
    print('   带内 `med|∇d2|` 中心差分：%.4f → **%.4f**（Δ = **%+.4f**，恢复率 **%+.3f**）'
          % (before[0], after[0], after[0] - before[0],
             (after[0] - before[0]) / max(1e-9, 1.0 - before[0])))
    print('   带内 `upwind_grad2`（算子口径）：%.4f → **%.4f**（Δ = **%+.4f**）'
          % (before[1], after[1], after[1] - before[1]))
    print('   `region()` 翻转 = **%d**；界面键 %d → %d（**%.4f×**）'
          % (res[tag]['flips'], nbb, nba, nba / max(nbb, 1)))
    print('   本臂 reinit：执行 %d / 跳过 %d，告警 %d 次'
          % (res[tag]['rdone'], res[tag]['rskip'], nw))

W.sussman_reinit = _ORIG          # 恢复，保持进程干净

print('\n' + '=' * 104)
print('【判决：Gate A-1 选项① 是否有效】')
A, B, Cc = res['A 现状（全域统计）'], res['B 选项①（带内统计）'], res['C 反向对照（恒等算子）']
dA = A['after'][0] - A['before'][0]
dB = B['after'][0] - B['before'][0]
dC = Cc['after'][0] - Cc['before'][0]
print('   A 现状   Δ中心 = **%+.4f**    B 选项① Δ中心 = **%+.4f**    C 恒等 Δ中心 = **%+.4f**'
      % (dA, dB, dC))
print('   ★ 反向对照自证量具可用：C 臂 Δ = %.2e（必须 ≈0）⇒ %s'
      % (dC, 'PASS' if abs(dC) < 1e-9 else 'FAIL（量具有噪声，结论不可用）'))
if abs(dC) < 1e-9 and dB > dA + 0.005:
    print('   ⇒ ★★★ **选项① 有效**：同一个初态、同一台算子、只改统计量的域，')
    print('      带内中位改善从 **%+.4f** 提到 **%+.4f**（恢复率 %.3f → %.3f）'
          % (dA, dB, dA / max(1e-9, 1 - A['before'][0]), dB / max(1e-9, 1 - B['before'][0])))
    print('      ⇒ Gate A-1 应选 **①**（并配 `reinit_strict` 作硬守卫）。')
elif abs(dC) < 1e-9:
    print('   ⇒ 选项① **未显示优势**（Δ 差 %.4f ≤ 0.005）⇒ 需换构型或加长演化再判，')
    print('      **不得**据此宣称"改统计量的域就好了"。')
print('\n   ⚠ 猴补丁只在**本进程**内生效，`windowB_surface.py` **一个字节未改**（SHA 不变）')
print('      ⇒ 不影响任何在跑作业的读数归属（`R11-c`）。')
print('=' * 104)
