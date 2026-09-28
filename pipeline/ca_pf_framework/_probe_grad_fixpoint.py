#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_grad_fixpoint.py —— ★★★ `N1` 的**最深一层**：算子的不动点 ≠ 我们量的 `|∇d2| = 1`？

触发本探针的实测（`_w01.log` B-1）
----------------------------------
在**引擎真实 `d2`** 上，**节流比 `_dte/dtau` = 1.0000（完全没有被节流）**、**全域中位 1.0000（不预归一化）**，
即"两套保险都没被压住"的最好条件下：

```
iters  带内 median|∇|   带内 median|Δ|
0      0.9436          0.0000e+00
10     0.9424          1.1064e-11     ← 场几乎逐位没动
```

而**同一算子**在解析场 α=0.86 上，**10 次迭代就从 0.8591 走到 0.8764**（Δ = +0.017）。
⇒ 差别不在"迭代次数"、不在"节流"、不在"预归一化" —— **在算子对 `|∇φ|` 的度量本身**。

假说 **H3**
-----------
`Sussman` 的更新量是 `_upd = _dte · S · (gm − 1)`，其中 **`gm = upwind_grad2(phi, S, dx)`**（`:203`）。
**若在引擎那种"阶梯状"的 `d2` 上 `upwind_grad2` 评出 ≈1**（而中心差分评出 0.9436），
则 `(gm − 1) ≈ 0` ⇒ **算子认为"已经到不动点了"，于是什么都不做**。
⇒ **算子的不动点（`upwind_grad2` 口径）与我们报的 `|∇d2|`（中心差分口径）不是同一个量。**

判据（**两把尺子必须同时量同一个场**，这是本探针的全部要点）
------------------------------------------------------------
* **正对照（解析场 α=0.86）**：两把尺子应**互相吻合**（都 ≈0.86）⇒ 说明"两把尺子不一致"不是量具的锅；
* **判决（引擎真实 `d2`）**：
  * 若 `median(upwind_grad2) ≈ 1.0` 而 `median(|np.gradient|) ≈ 0.94` ⇒ **H3 成立**，
    且**这才是 `reinit` 修不动的第一性原因**（比"节流"更根本）；
  * 若两把尺子都 ≈0.94 ⇒ **H3 推翻**，回到"另外找为什么 `(gm−1)` 推不动"。

同时报 `upwind_grad`（一阶）与 `grad_sym`，以区分"是二阶 ENO 特有的问题"还是通用问题。

⚠ 本探针**只读**：只调用引擎的**模块级纯函数**与读数，不改任何默认、不改引擎文件。
用法：python3 _probe_grad_fixpoint.py [--N 96] [--dx-nm 50] [--el 4]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF, KV = 1e-9, 3.5e8, 1
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=96)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--el', type=float, default=4.0)
ap.add_argument('--band-cells', type=float, default=6.0)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx
print('=' * 104)
print('_probe_grad_fixpoint —— N1 最深一层：算子的不动点 vs 我们量的 |∇d2|')
print('  N=%d Δx=%.1f nm L=%.2f µm' % (N, a.dx_nm, L * 1e6))
print('=' * 104)


def rulers(phi, near, tag):
    """同一个场，四把尺子同时量（全部在带内取中位）。"""
    S = phi / np.sqrt(phi ** 2 + dx ** 2)                       # 与 :186 逐字相同
    g = np.gradient(phi, dx)
    cen = np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)
    uw2 = W.upwind_grad2(phi, S, dx)
    uw1 = W.upwind_grad(phi, S, dx)
    gs = W.grad_sym(phi, dx)
    out = dict(cen=float(np.median(cen[near])),
               uw2=float(np.median(uw2[near])),
               uw1=float(np.median(uw1[near])),
               gs=float(np.median(gs[near])),
               cen_max=float(np.max(cen)), uw2_max=float(np.max(uw2)))
    print('\n【%s】带胞 %d' % (tag, int(near.sum())))
    print('   中心差分 `|np.gradient|` (我们报的那个) = **%.4f**' % out['cen'])
    print('   一阶迎风   `upwind_grad`                 = **%.4f**' % out['uw1'])
    print('   ★二阶迎风 `upwind_grad2`（**算子驱动的那个**) = **%.4f**' % out['uw2'])
    print('   `grad_sym`                              = **%.4f**' % out['gs'])
    print('   ⇒ `upwind_grad2 − 中心` = **%+.4f**  （若 ≈0 ⇒ 两把尺子一致；若 ≈+0.05 ⇒ H3 成立）'
          % (out['uw2'] - out['cen']))
    return out


# ---------------------------------------------------------------- 正对照：解析场
ax_ = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(ax_ - L / 2, ax_ - L / 2, ax_ - L / 2, indexing='ij')
r = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
R0 = 12 * dx
alpha = 0.86
ph_an = alpha * (r - R0)
near_an = np.abs(ph_an) <= a.band_cells * dx
an = rulers(ph_an, near_an, '正对照：解析径向场（真值 |∇φ| ≡ %.2f，两把尺子应互相吻合）' % alpha)

# ---------------------------------------------------------------- 判决：引擎真实 d2
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
o = np.argsort(g.phi, axis=0)
d2 = 0.5 * (np.take_along_axis(g.phi, o[0][None], 0)[0]
            - np.take_along_axis(g.phi, o[1][None], 0)[0])
near = np.abs(d2) <= a.band_cells * dx
eng = rulers(d2, near, '判决：引擎真实 `d2 = (φ_k−φ_l)/2`（新鲜种子，未演化）')

# ---------------------------------------------------------------- 追查：更新量被谁压住了？
#   动机（`_w01.log` B-1）：iters=100 只把带内中位从 0.9436 挪到 0.9305（**方向还错了**），
#   `median|Δ| = 1.4e-10 m = 0.14 nm`，而带本身宽 ±6dx = ±300 nm ⇒ **改动量是带宽的 0.05%**。
#   而 `(gm−1) ≈ −0.088` ⇒ 按 `_upd = _dte·S·(gm−1)` 不该这么小 ⇒ 逐项把抑制因子量出来。
print('\n' + '=' * 104)
print('【追查】把 `sussman_reinit` 的每一步抑制因子逐项量出来（复刻 `:177-215` 的算式）')
S_e = d2 / np.sqrt(d2 ** 2 + dx ** 2)
gm_e = W.upwind_grad2(d2, S_e, dx)
gm_med_band = float(np.median(gm_e[near]))
gmax_e = float(np.max(gm_e))
_gcen = np.gradient(d2, dx)
gm_all_med = float(np.median(np.sqrt(sum(t ** 2 for t in _gcen))))
dtau = 0.5 * dx / 3.0
dte = min(dtau, 0.5 * dx / 3.0 / max(gmax_e, 1.0))
lim0 = float(np.max(np.abs(d2))) + dx
upd = np.clip(dte * S_e * (gm_e - 1.0), -0.5 * dx, 0.5 * dx)
print('   `S` 带内中位           = %.4f' % float(np.median(S_e[near])))
print('   `gm = upwind_grad2` 带内中位 = **%.4f**  ⇒ `(gm−1)` 带内中位 = **%+.4f**'
      % (gm_med_band, gm_med_band - 1.0))
print('   ★ `_gmax = max(gm)` **全域** = **%.4f**   ← 决定 `_dte`' % gmax_e)
print('   `dtau = 0.5dx/3` = %.4e   `_dte` = %.4e  ⇒ **`_dte/dtau` = %.4f**'
      % (dtau, dte, dte / dtau))
print('   预归一化判据：`_gm = median|∇φ|` **全域** = %.4f ⇒ `|_gm−1|` = %.4f %s（阈值 0.2）'
      % (gm_all_med, abs(gm_all_med - 1.0),
         '⇒ **会归一化**' if abs(gm_all_med - 1.0) > 0.2 else '⇒ **不归一化**'))
print('   单步预测 `median|_upd|` 带内 = **%.4e m**（= %.3f nm）'
      % (float(np.median(np.abs(upd[near]))), float(np.median(np.abs(upd[near]))) * 1e9))
print('   被 clip 的胞数 = %d / %d' % (int((np.abs(dte * S_e * (gm_e - 1.0)) > 0.5 * dx).sum()),
                                     d2.size))
print('   发散守卫门槛：`10·_lim0` = %.4e ；迭代后 `max|phi|` 需低于它才不被整场拒绝'
      % (10.0 * lim0))
_act = W.sussman_reinit(d2, dx, iters=1, grad='upwind2')
print('   ★ 实际 `sussman_reinit(iters=1)` 的 `median|Δ|` 带内 = **%.4e m**（= %.3f nm）'
      % (float(np.median(np.abs(_act - d2)[near])), float(np.median(np.abs(_act - d2)[near])) * 1e9))
print('   ⇒ 若"单步预测"与"实际"**数量级差很多** ⇒ 抑制在 `guard`/`clip` 里；')
print('     若**一致地小** ⇒ 抑制在 `_dte`（即全域 `_gmax`）里 —— 那就是 `N1` 的定量主因。')

print('\n' + '=' * 104)
print('【判决 H3】')
gap_an = abs(an['uw2'] - an['cen'])
gap_en = abs(eng['uw2'] - eng['cen'])
print('   正对照两把尺子的差 = **%.4f**（小 ⇒ 尺子本身没问题）' % gap_an)
print('   引擎场上两把尺子的差 = **%.4f**' % gap_en)
if gap_en > 0.03 and gap_an < 0.01 and eng['uw2'] > eng['cen']:
    print('   ⇒ ★★★ **H3 成立**：在引擎的阶梯状 `d2` 上，')
    print('      `upwind_grad2` 评出 **%.4f**，而中心差分只有 **%.4f**。' % (eng['uw2'], eng['cen']))
    print('      算子的更新量 ∝ `(gm − 1)` ⇒ 它**认为已经到不动点了，于是不做任何事**。')
    print('      ⇒ **`reinit` 修不动的第一性原因：算子的不动点（迎风口径）≠ 我们报的 `|∇d2|`（中心差分口径）。**')
    print('      ⇒ 这比"全域统计量选错域"更根本：即使把 `_gm`/`_gmax` 改成带内，`(gm−1)` 仍是 0。')
    print('      ⇒ Step A-1 的选项要**增加一条**：④ 统一口径（让算子驱动 `np.gradient` 口径的量，')
    print('         或把"带健康"的定义改成 `upwind_grad2` 口径并**如实说明我们报的是哪一个**）。')
elif gap_en <= 0.03:
    print('   ⇒ **H3 推翻**：两把尺子在引擎场上也一致（差 %.4f）' % gap_en)
    print('      ⇒ 那 `(gm−1)` 不为 0，`reinit` 不动就另有原因（回到 `S`、`clip`、`guard` 三条去查）。')
else:
    print('   ⇒ 结果不整齐（正对照差 %.4f 也要看）⇒ **不下结论**，需换构型复测。' % gap_an)
print('\n   ⚠ 本探针只读；未改引擎任何默认。四把尺子都在**同一个场**上取带内中位，口径可比。')
print('=' * 104)
