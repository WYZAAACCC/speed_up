#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_reinit_iter.py --- ★★★ `W0-1`：`sussman_reinit` **为什么修不动界面**（判决 H2）

来源（读码，`windowB_surface.py:158-215`）
------------------------------------------
`W0` 之前的实测：演化 60 步后带内 `median|∇d2|` = 0.8558，**100 次 Sussman 迭代只换 Δ=−0.0047**
（`_probe_reinit_norm.py` A-6）。读码后提出**可证伪的机制假说**：

> **H2**：算子内部用**全域**统计量控制步长与归一化，而问题在**带内**：
> * `:182 _gm = median(|∇φ|)`（**全域**）；`:183` 若 `|_gm−1|>0.2` 才整体除以 `_gm`
>   ⇒ 全域中位落在 1±0.2 内时**完全不归一化**，而带内可以严重偏离；
> * `:209 _gmax = max(|∇φ|)`（**全域**）；`:210 _dte = min(dtau, 0.5·dx/3/max(_gmax,1))`
>   ⇒ **只要域内任何一处梯度大，伪时间步就被按比例压小** ⇒ 100 次迭代只干了 10 次的活。

**判决设计（三个方向，各自的"已知答案"）**
--------------------------------------------
* **B-0 现场量**：分别报 **带内** 与 **全域** 的 `median|∇|`、`max|∇|`，以及由它算出的 `_dte/dtau`。
* **B-1 迭代曲线**：`iters ∈ {0,10,100,1000}` 下带内 `median|∇out|` 怎么走。
  * 若 1000 次才开始动 ⇒ **被 `_dte` 节流**（H2 成立）；
  * 若 1000 次也不动 ⇒ 另有原因（`S` 在界面为 0 / `guard` 拒绝）。
* **B-2 H2 的**直接干预**：把带外场**夹到 ±band**（⇒ 全域 `max` 有界）再跑同一算子。
  * **夹外之后若立刻收敛 ⇒ H2 确证**（元凶是全域 `max`，不是算子形式）；
  * 仍不动 ⇒ H2 推翻。
* **B-3 正对照（已知答案）**：解析场 `φ = α·(r − R0)`，`|∇φ| = α` **处处已知**（非界面区 `S≈±1`）。
  * 取 `α = 0.86`（复现实测的亏损量）跑 100 次 ⇒ **必须回到 ≈1**，否则算子本身坏。
  * 取 `α = 0.46`（复现 T24 的读数）再跑一次。

用法：python3 _probe_reinit_iter.py [--N 128] [--dx-nm 25] [--el 4]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF = 1e-9, 3.5e8
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=128)
ap.add_argument('--dx-nm', type=float, default=25.0)
ap.add_argument('--el', type=float, default=4.0)
ap.add_argument('--band-cells', type=float, default=6.0)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx

print('=' * 104)
print('_probe_reinit_iter —— W0-1：`sussman_reinit` 为何修不动界面（判决 H2）')
print('  N=%d Δx=%.1f nm L=%.2f µm' % (N, a.dx_nm, L * 1e6))
print('=' * 104)
print('''
⛔⛔ 【2026-09-28 事后更正 —— 读本日志前必读】
   本探针**打印出来的那几句判决是错的**（数据对、结论错），原因见下：
   * B-0 / B-2 里的 "`_dte/dtau`" 是用 **中心差分** `max|∇d2|` 算的 —— 实测该值为 **1.00**；
   * 而**算子真正用的**是 `max(upwind_grad2)` —— 实测同一场为 **68.5**（`_probe_grad_fixpoint.py`）；
   * ⇒ 真实节流是 **0.0146**，不是 1.0000。本探针据此写下的
     "**未被明显节流，H2 不足以解释**" 一句 **作废**。
   * ✅ 真正有效的读数：B-1 的迭代曲线（0.9436→0.9305@100→**0.8324@1000**，方向错）、
     以及 B-3 的三档正对照 —— 那些都是**直接测量**，不受该口径错误影响。
   * ✅ 结论请以 `_probe_grad_fixpoint.py`（根因）与 `_probe_fix_bandstats.py`（选项①已验证）为准。
   * 教训（与 `R4`、教训 #26 同族）：**报"某个算子被节流了多少"时，必须用那个算子自己的梯度口径**，
     而不是另找一个"看起来等价"的口径 —— 两者的**全域最大值**可以差 68 倍。
''')


def gmag(f):
    g = np.gradient(f, dx)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


# ============================================================ B-3 正对照（不依赖引擎）
print('\n【B-3 正对照：解析场的"已知答案"】φ = α·(r − R0)，真值 |∇φ| ≡ α（非界面区）')
ax_ = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(ax_ - L / 2, ax_ - L / 2, ax_ - L / 2, indexing='ij')
R0 = 12 * dx
r = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
band_an = np.abs(r - R0) <= a.band_cells * dx
for al in (1.0, 0.86, 0.46):
    ph = al * (r - R0)
    b0 = float(np.median(gmag(ph)[band_an]))
    row = []
    for it in (0, 10, 100, 1000):
        out = W.sussman_reinit(ph, dx, iters=it, grad='upwind2')
        row.append('it=%-4d %.4f' % (it, float(np.median(gmag(out)[band_an]))))
    print('   α=%.2f：输入 %.4f  →  %s' % (al, b0, ' | '.join(row)))
print('   ⇒ 正对照的读法：若 α=1.00 保持 ≈1、且 α<1 的能回到 ≈1 ⇒ **算子形式本身可用**。')

# ============================================================ B-0 现场量（引擎里的真实 d2）
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
KV = 1
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
G = gmag(d2)
gm_band, gm_all = float(np.median(G[near])), float(np.median(G))
gx_all, gx_band = float(np.max(G)), float(np.max(G[near]))
dtau = 0.5 * dx / 3.0
dte_ratio = min(dtau, 0.5 * dx / 3.0 / max(gx_all, 1.0)) / dtau
print('\n【B-0 现场量】引擎里真实的配对半差分 `d2 = (φ_k−φ_l)/2`')
print('   `median|∇d2|`：**带内 %.4f**  vs  **全域 %.4f**' % (gm_band, gm_all))
print('   `max|∇d2|`   ：  带内 %.2f    vs  **全域 %.2f**   ← 驱动 `_dte`' % (gx_band, gx_all))
print('   ⇒ `|_gm−1|` 用全域 = %.4f  %s（阈值 0.2）'
      % (abs(gm_all - 1), '⇒ **不归一化**' if abs(gm_all - 1) <= 0.2 else '⇒ 会归一化'))
print('   ⇒ `_dte / dtau` = **%.4f**  ⇒ 100 次迭代只等于 **%.1f** 次满步'
      % (dte_ratio, 100 * dte_ratio))

# ============================================================ B-1 迭代曲线
print('\n【B-1 迭代曲线】域内 `max|∇d2|` 未做任何处理（= 引擎现状）')
print('   iters   带内 median|∇|   带内 median|Δ|   max|out|')
for it in (0, 10, 100, 1000):
    out = W.sussman_reinit(d2, dx, iters=it, grad='upwind2')
    print('   %-6d  %.4f            %.4e      %.3g'
          % (it, float(np.median(gmag(out)[near])),
             float(np.median(np.abs(out - d2)[near])), float(np.max(np.abs(out)))))

# ============================================================ B-2 H2 的直接干预
#   把带外夹到 ±band ⇒ 全域 max 有界 ⇒ 若这是元凶，收敛应立刻出现。
print('\n【B-2 H2 干预】把带外场夹到 ±band（`±%.0f·dx`）后跑同一算子' % a.band_cells)
LIM = a.band_cells * dx
d2c = np.where(near, d2, np.sign(d2) * LIM)
Gc = gmag(d2c)
print('   夹外后：全域 `median|∇|` = %.4f，全域 `max|∇|` = %.2f ⇒ `_dte/dtau` = **%.4f**'
      % (float(np.median(Gc)), float(np.max(Gc)),
         min(dtau, 0.5 * dx / 3.0 / max(float(np.max(Gc)), 1.0)) / dtau))
for it in (0, 10, 100):
    out = W.sussman_reinit(d2c, dx, iters=it, grad='upwind2')
    print('   iters=%-5d 带内 median|∇| = **%.4f**' % (it, float(np.median(gmag(out)[near]))))

# ============================================================ 判决
print('\n' + '=' * 104)
print('【判决】')
_pa = float(np.median(gmag(W.sussman_reinit(0.86 * (r - R0), dx, iters=100,
                                            grad='upwind2'))[band_an]))
print('   正对照（解析 α=0.86，100 次）：**%.4f** %s' % (_pa, '⇒ 算子本身可用' if _pa > 0.95
      else '⇒ 算子本身也修不动（更根本）'))
if dte_ratio < 0.5:
    print('   ★ 现场 `_dte/dtau` = **%.4f** ⇒ **H2 成立的方向明确**：' % dte_ratio)
    print('     全域 `max|∇d2|` = %.2f 把伪时间步压到 %.1f%%，100 次迭代只等于 %.0f 次。'
          % (gx_all, dte_ratio * 100, 100 * dte_ratio))
    print('     `_gmax` 由**域内任意一处的陡梯度**决定（含远离界面处），与"带内要不要重初始化"无关。')
else:
    print('   现场 `_dte/dtau` = %.4f ⇒ **未被明显节流**，H2 不足以解释"100 次不动"。' % dte_ratio)
    print('   ⇒ 转查 `S = φ/√(φ²+dx²)` 在界面处趋 0（修正量按构造在零等值面上消失），')
    print('     以及 `:183` 全域归一化阈值（`|_gm−1|>0.2`）是否让带内亏损被漏掉。')
print('   ⚠ 本探针只读，不改任何引擎行为；所有读数都是对**未改动**的 `sussman_reinit` 的调用。')
print('=' * 104)
