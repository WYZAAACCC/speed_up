#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_drift_ns.py --- ★★★ `W0-2` + `W0-3`：`|∇d2|` 的**漂移率**与 `norm_smooth` 的关系

为什么要自己做量具（W0-3 的第一次尝试失败记账）
------------------------------------------------
第一版 W0-3 想直接用 `T24_verify_grouping.py` 的两个 `--norm-smooth` 档做单因素对照。
**两个问题**：① `--n0 24` 在 L=3.2 µm 下 `f` 初值已达 **0.0423 > --f-target 0.03**
⇒ 作业在第 5 步就正常结束（不是崩，是我的参数错，`_w03a/b.log` 留有完整输出）；
② ★ **`T24` 根本不打印 `median|∇d2|`** —— 那个量只出现在 `RuntimeWarning` 的文本里。
⇒ **T24 不是这个问题的量具**。本探针自己量。

量什么（全部**只读**，不改引擎）
--------------------------------
* **带内 `median|∇d2|`** —— 完全复刻 `reinitialize()` 的口径（`d2=(φ_k−φ_l)/2`，`|d2|≤6dx`）；
* **带内 `median|∇φ_win|`** —— 与引擎自带"带健康 probe"同口径，便于对账；
* **带胞数**、**界面键数**（`_band_bonds`）；
* **`reinit` 触发次数**（`_reinit_done` / `_reinit_skipped`）与**告警次数**；
* 每一步都带 **step / f / 墙钟**。

单因素：**`norm_smooth ∈ {0, 2}`**，其余逐字相同。
`reinit` 参数与四个出数驱动**完全一致**（`reinit_every=0, reinit_dt=6.0e-7` ⇒ 约每 28 步一次）。

判据
----
* **已知答案**：`norm_smooth` 是本轮为修"各向异性被压缩"引入的**梯度分量平滑**。
  它**同时作用在推进用的法向**上。若它也是 `|∇d2|` 漂移的来源，
  则 `ns=2` 的漂移应显著大于 `ns=0` —— **两个档必须给出不同签名**，否则这个单因素不成立。
* 报告**漂移率**（每步 Δ`median|∇d2|`）而不是水平值（`R4`/教训 #26：水平值不能当依据）。

用法：python3 _probe_drift_ns.py [--N 96] [--dx-nm 50] [--steps 120] [--el 4]
"""
import os
import sys
import time
import argparse
import warnings

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF = 1e-9, 3.5e8
KV = 1
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=96)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--steps', type=int, default=120)
ap.add_argument('--el', type=float, default=4.0)
ap.add_argument('--band-cells', type=float, default=6.0)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx
print('=' * 108)
print('_probe_drift_ns —— `|∇d2|` 漂移率 vs `norm_smooth`（单因素）')
print('  N=%d Δx=%.1f nm L=%.2f µm steps=%d  reinit: every=0 dt=6.0e-7（与出数驱动一致）'
      % (N, a.dx_nm, L * 1e6, a.steps))
print('=' * 108)


def gm(f):
    g = np.gradient(f, dx)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def stats(g_, bc):
    """引擎口径的带内统计（只读）。"""
    o = np.argsort(g_.phi, axis=0)
    ka, la = o[0], o[1]
    pha = np.take_along_axis(g_.phi, ka[None], 0)[0]
    phb = np.take_along_axis(g_.phi, la[None], 0)[0]
    d2 = 0.5 * (pha - phb)
    nr = np.abs(d2) <= bc * g_.dx
    if nr.sum() < 50:
        return dict(med_d2=np.nan, med_phi=np.nan, nband=int(nr.sum()),
                    gmax=float(np.max(gm(d2))), gm_all=float(np.median(gm(d2))))
    return dict(med_d2=float(np.median(gm(d2)[nr])),
                med_phi=float(np.median(gm(pha)[nr])),
                nband=int(nr.sum()),
                gmax=float(np.max(gm(d2))),
                gm_all=float(np.median(gm(d2))))


def bonds(reg):
    n = 0
    for ax in range(3):
        n += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return n


out = {}
for ns in (0, 2):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
    c = np.array([L / 2] * 3)
    nh = np.asarray(NPF[KV], float)
    nh = nh / np.linalg.norm(nh)
    aa = np.asarray(g.atab[KV], float)
    aa = aa - (aa @ nh) * nh
    aa = aa / np.linalg.norm(aa)
    g.seed_plate(KV, c, nh, 300e-9, 200e-9, elong=a.el, along=aa)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    print('\n---- norm_smooth = %d ----' % ns)
    print('   step      f        med|∇d2|   med|∇φ|   max|∇d2|   med全域  带胞    界面键   reinit(do/skip) 告警  步时')
    rows = []
    t0 = time.time()
    for st in range(0, a.steps + 1, 20):
        if st:
            for _ in range(20):
                with warnings.catch_warnings(record=True) as rec:
                    warnings.simplefilter('always')
                    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                              mob_beta=3.5, mob_beta_w=2.3, norm_smooth=ns)
                out.setdefault('warn%d' % ns, []).append(
                    sum(1 for r in rec if 'pair reinit' in str(r.message)))
        s = stats(g, a.band_cells)
        reg = g.region()
        f = float((reg > 0).sum()) / N ** 3
        dn, ds = getattr(g, '_reinit_done', 0), getattr(g, '_reinit_skipped', 0)
        el_ = time.time() - t0
        print('   %-6d  %.5f   %.4f     %.4f    %8.2f   %.4f   %-7d %-7d %d/%d            %-4s  %.1fs'
              % (st, f, s['med_d2'], s['med_phi'], s['gmax'], s['gm_all'],
                 s['nband'], bonds(reg), dn, ds,
                 out.get('warn%d' % ns, [0])[-1] if out.get('warn%d' % ns) else 0, el_))
        rows.append((st, f, s['med_d2'], s['med_phi'], s['gmax'], s['gm_all'],
                     s['nband'], bonds(reg)))
    out['rows%d' % ns] = rows

print('\n' + '=' * 108)
print('【单因素判决】')
r0, r2 = out['rows0'], out['rows2']
d0 = r0[-1][2] - r0[0][2]
d2_ = r2[-1][2] - r2[0][2]
n0_, n2_ = r0[0][6], r2[0][6]
print('   norm_smooth=0：带内 med|∇d2| %.4f → %.4f（Δ=%+.4f，%d 步，%.2e/步）；带胞 %d → %d（%+.1f%%）'
      % (r0[0][2], r0[-1][2], d0, a.steps, d0 / a.steps, n0_, r0[-1][6],
         (r0[-1][6] / max(n0_, 1) - 1) * 100))
print('   norm_smooth=2：带内 med|∇d2| %.4f → %.4f（Δ=%+.4f，%d 步，%.2e/步）；带胞 %d → %d（%+.1f%%）'
      % (r2[0][2], r2[-1][2], d2_, a.steps, d2_ / a.steps, n2_, r2[-1][6],
         (r2[-1][6] / max(n2_, 1) - 1) * 100))
if abs(d2_ - d0) > 0.02:
    print('   ⇒ ★ 两档漂移**可分辨**（|Δ差| = %.4f）：`norm_smooth` **确实是漂移的一个来源**。' % abs(d2_ - d0))
else:
    print('   ⇒ 两档漂移**不可分辨**（|Δ差| = %.4f < 0.02）：`norm_smooth` **不是** 0.46 的主因，' % abs(d2_ - d0))
    print('      ⇒ 主因在别处（演化本身 / 多区域 / 更长时间）。')
print('   ⚠ 判据用**漂移率**（每步 Δ），不用水平值（`R4`、教训 #26）。')
print('   ⚠ 本探针只读；`reinit_strict` 未打开（那是 W0-5 的仪表线）。')
print('=' * 108)
