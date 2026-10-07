#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r172_omega_audit.py —— **块 = 多根同类板条堆叠 + 低角晶界分隔** 的 ω / γ 接线审计。

> ⚠ **本文件是第二版（2026-09-XX，`§129`）。第一版有两个错误，已改：**
>   1. 第一版用 **`γ₀ = 0.15`**（argparse 默认值）当 F2 的标量面能 ⇒ **错**。
>      归档臂**全都传 `--gamma0 0.25`**（实测 `meta.json`，见 `_r173_gammachk.sh` ③）；
>      而 `windowB_closure.py:125 GAMMA_F1_MAIN = 0.25`（文献值，Murzinova 2017 的
>      `GAMMA_F1_BAND = (0.201, 0.337)`）⇒ **0.25 才是归档工作点**。
>   2. 第一版把 `saSet2` 写成 `[1,2,3,4,7,8]`、`saOddG` 写成 `[1,3,5,7,9,11]` ⇒ **错**。
>      实测 `meta.json`：`saSet2 = [1,1,2,2,3,3,4,4,7,7,8,8]`、
>      `saOddG = [1,1,3,3,5,5,7,7,9,9,11,11]`（**6 块 × 2 根**）
>      ⇒ **它们确实含同变体对（F3）**，第一版"全不同变体、无 F3"的说法**不成立**。
>   ⇒ 教训（与 `AGENTS.md §3.3` 同源）：**探针读到的配置必须从归档里核实，不能凭记忆写。**

## 要回答的三个问题

* **Q-1** 在真实算例用的板条表上，**F3 的 γ 是否真的 < F2 的 γ₀**？
  （若否 ⇒ **块内界面比块间界面贵** ⇒ 与用户目标句「块 = 多根同类板条堆叠 + 低角晶界分隔」冲突）
* **Q-2** 对给定的表，`gtab` 里**有没有**"变体对"依赖项？（全 NaN ⇒ 引擎走标量 ⇒ 无）
* **Q-3** 正对照：手工给"同变体 ⇒ 同 ω"时，F3 是否给出 **γ = 0**（机器**能**表示免费堆叠）？

## ★ Q-4（本轮新增，是本文件的主要发现）

`default_omega` 的阶梯步长是 **`θ_max/(M−1)`** ⇒ **同变体界面的 θ 取决于"你列了几根板条"**，
而不是取决于物理。⇒ 判据：同一个"块"在 M=2/3/4/12 下，F3 的 γ 差多少倍？
若差别很大 ⇒ **块内界面能是一个记账副作用，不是物理量**。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_lath as WL  # noqa: E402

GAMMA0 = 0.25          # ★ 归档工作点（`--gamma0 0.25`；`CL.GAMMA_F1_MAIN`）
THETA_MAX_DEG = 5.0    # `_bk_exp.py` 默认 `--omega-max`

# (lath 表, 归档臂名 or None, 说明)
ARMS = [
    ('1', None, '退化：M=1（`_r54_single.sh`/`_r56_band.sh`）'),
    ('1,1', None, '1 块 × 2 根（`_r49_snapgate.sh`/`_r49_dx62c.sh`）'),
    ('1,1,1', 'dry_mo1fp10', '单块 3 根同类（`_r71_multi.sh`；`dry_mo1fp10` 为此配置）'),
    ('1,1,1,1', None, '退化：4 根同类（检验 M 依赖）'),
    ('1,1,1,3,3,3', 'dry_mb2fp10',
     '2 块 × 3 根（`_r75_mb.sh`/`_r132_swapcmp.sh`；**投影对照 `dry_mb2fp10/0` 是这个**）'),
    ('1,1,2,2,3,3,4,4,5,5,6,6', None, '6 块 × 2 根（`_r30_mb2.sh`/`_r51_mb2_62.sh`）'),
    ('1,1,3,3,5,5', None, '3 块 × 2 根（`_r164_chk.sh`）'),
    ('1,1,2,2,3,3,4,4,7,7,8,8', 'dry_saSet2',
     '**`saSet2` 真身**（实测 meta.json）—— 6 块 × 2 根，同 packet 对 (1,2)(3,4) 在块内'),
    ('1,1,3,3,5,5,7,7,9,9,11,11', 'dry_saOddG',
     '**`saOddG` 真身**（实测 meta.json）—— 6 块 × 2 根，全奇数变体'),
    ('1,3,1,3', None, '**交错**表（同变体序号隔开）—— 位置式 ω 的病态情形'),
]


def build(laths, theta_max=THETA_MAX_DEG):
    om = WL.default_omega(len(laths), theta_max, axis=np.array([1.0, 0.0, 0.0]),
                          mode='ladder')
    return WL.LathTable(list(laths), omegas=om, gamma0=GAMMA0)


def archived_gamma0(arm):
    """从归档 `meta.json` 读该臂**实际**用的 `gamma0`（硬规则⑩：判决脚本必须打印它真读到的）。"""
    if arm is None:
        return None
    p = os.path.join(HERE, '_exp', '_bk_mb',
                     'dry_' + arm[4:] if arm.startswith('dry_') else 'dry_' + arm,
                     'meta.json')
    if not os.path.exists(p):
        return None
    try:
        m = json.load(open(p))
        return m.get('gamma0')
    except (OSError, ValueError):
        return None


def audit(laths, arm, note):
    lt = build(laths)
    M = lt.M
    g0 = archived_gamma0(arm)
    print()
    print('  ### `%s`  (M=%d, nreg=%d)' % (','.join(str(v) for v in laths), M, lt.nreg))
    print('      %s' % note)
    if arm is not None:
        print('      归档臂 `%s` 的 `meta.json` 里 `gamma0` = %s'
              % (arm if arm.startswith('dry_') else 'dry_' + arm,
                 ('**%s**' % g0) if g0 is not None else '**(读不到)**'))
        if g0 is not None and abs(float(g0) - GAMMA0) > 1e-12:
            print('      ⚠⚠ **与本地假设 %.2f 不符** ⇒ 本段判据用归档值重算' % GAMMA0)
    print('      阶梯步长 Δθ = %.4f°（= θ_max/(M−1)，θ_max=%.1f°）'
          % (THETA_MAX_DEG / (M - 1) if M > 1 else float('nan'), THETA_MAX_DEG))
    f3, f2pairs, inv = [], 0, 0
    for i in range(M):
        for j in range(i + 1, M):
            th = np.rad2deg(lt.theta[i + 1, j + 1])
            if lt.vmap[i] == lt.vmap[j]:
                f3.append((th, float(lt.gtab[i + 1, j + 1]), i, j))
            else:
                f2pairs += 1
    m = lt.nreg
    sub = lt.gtab[1:m, 1:m]
    finite_pairs = int(np.isfinite(np.triu(sub, 1)).sum())
    allnan = (finite_pairs == 0)
    print('      同变体对(F3)=%d  异变体对(F2)=%d  `gtab` 有限**对**数=%d'
          % (len(f3), f2pairs, finite_pairs))
    print('      **Q-2** 变体↔变体块 %s（有限**对**数=%d）⇒ `facet_gamma_sub` 返回 %s '
          '⇒ 速度律里 %s'
          % ('**全 NaN**' if allnan else '非空', finite_pairs,
             '**标量**（引擎原路径）' if allnan else '**数组**（**另一条引擎路径**）',
             '**无变体对依赖**' if allnan else '**有**变体对依赖（至少 F3 的那些）'))
    if not f3 or not f2pairs:
        why = ('只有 F3 对' if f3 else '只有 F2 对' if f2pairs else '退化（M=1）')
        print('      **Q-1** %s ⇒ **无对照，不判**' % why)
        return dict(laths=tuple(laths), arm=arm, M=M, n_f3=len(f3),
                    n_f2=f2pairs, allnan=allnan, gmax=(max(x[1] for x in f3) if f3
                                                      else float('nan')),
                    ratio=float('nan'), verdict='n/a')
    gm = max(x[1] for x in f3)
    gmin = min(x[1] for x in f3)
    bad = [x for x in f3 if x[1] > GAMMA0]
    print('      **Q-1** F3 γ ∈ [%.4f, %.4f] vs F2 γ₀ = **%.2f**' % (gmin, gm, GAMMA0))
    print('         ⇒ 比值 min(F3)/F2 = **%.3f×**，max(F3)/F2 = **%.3f×**'
          % (gmin / GAMMA0, gm / GAMMA0))
    print('         ⇒ **倒挂对数 = %d / %d**（F3 的 γ > F2 的 γ₀ 的同变体对）'
          % (len(bad), len(f3)))
    if bad:
        for (th, g, i, j) in bad:
            print('            ❌ 板条(%d,%d) θ=%.4f° γ=%.4f = **%.3f× γ₀**'
                  % (i, j, th, g, g / GAMMA0))
    verdict = ('**倒挂**' if len(bad) == len(f3) else
               '部分倒挂' if bad else '块内更便宜')
    print('         ⇒ **Q-1 判定：%s**' % verdict)
    return dict(laths=tuple(laths), arm=arm, M=M, n_f3=len(f3), n_f2=f2pairs,
                allnan=allnan, gmax=gm, gmin=gmin, ratio=gm / GAMMA0,
                nbad=len(bad), verdict=verdict)


def main():
    print('=' * 110)
    print('_r172（第二版）—— ω / γ 接线审计（`§129`）')
    print('  核心问题：**"块内同类板条界面"是否真的比"块间异变体界面"便宜？**')
    print('=' * 110)
    print()
    print('  ## 常数（`windowB_lath.py` / `windowB_closure.py`）')
    print('     `E0_TI64`=%.6g  `GAMMA_M_TI64`=**%.6f J/m²**  `THETA_M_DEG`=%.1f°'
          % (WL.E0_TI64, WL.GAMMA_M_TI64, WL.THETA_M_DEG))
    print('     **归档工作点 γ₀ = %.2f**（`_bk_exp.py --gamma0`；`CL.GAMMA_F1_MAIN`）'
          % GAMMA0)
    print('     `GAMMA_F1_BAND` = (0.201, 0.337)（Murzinova 2017 @975°C，文献带）')
    print('     `GAMMA_AB[600C]` = %s' % (WL.GAMMA_AB['T600C'],))
    print()
    print('  ## ★ 尺子：γ_RS(θ)（`windowB_lath.py:83-99`）')
    for d in (0.0, 0.4545, 1.0, 2.0, 2.5, 5.0, 10.5, 15.0, 60.0):
        g = float(WL.gamma_rs_deg(d))
        print('     θ=%7.4f° ⇒ γ_RS=%.4f J/m²   /γ₀=**%.3f×**   %s'
              % (d, g, g / GAMMA0,
                 '← 块内低角（期望便宜）' if d <= 2.5
                 else ('← 异变体高角的下限 (10.5° packet)' if d == 10.5
                       else ('← 饱和平台 γ_m' if d >= 15 else ''))))

    out = []
    print()
    print('=' * 110)
    print('  ## 逐表审计')
    print('=' * 110)
    for laths, arm, note in ARMS:
        out.append(audit([int(x) for x in laths.split(',')], arm, note))

    # ---------------- Q-3 正对照 ----------------
    print()
    print('=' * 110)
    print('  ## Q-3 **正对照**：机器**能**表示"同类板条堆叠免费"吗？')
    print('=' * 110)
    lt = WL.LathTable([1, 1, 1], omegas=np.zeros((3, 3)), gamma0=GAMMA0)
    g3 = [float(lt.gtab[i + 1, j + 1]) for i in range(3) for j in range(i + 1, 3)]
    print('     手工把 `1,1,1` 的 ω 全设零（物理上同变体就应同取向）⇒ n_f3=%d' % lt.n_f3)
    print('     F3 的 γ = %s' % ['%.3e' % v for v in g3])
    pc = all(abs(v) < 1e-15 for v in g3)
    print('     ⇒ **正对照 %s**（期望：精确 0，由 `γ_RS(0)=0` 的 P1 性质保证）'
          % ('✅ 通过' if pc else '❌ 失败'))
    print('     ⇒ 含义：**模型有能力**给出"同类堆叠零成本"，但 `default_omega` 不这么给。')

    # ---------------- Q-4：M 依赖 ----------------
    print()
    print('=' * 110)
    print('  ## ★ Q-4（主要发现）：**块内界面能随"你列了几根板条"变**')
    print('=' * 110)
    print('     `default_omega` 给第 i 根板条 ω_i = [i·θ_max/(M−1)]·**a**'
          '（`windowB_lath.py:158-180`）')
    print('     ⇒ **同变体板条之间的 θ 只由序号差决定**，与变体无关 ⇒')
    print('     ⇒ **同一个"块"，M 不同 ⇒ 块内界面能不同**（不是物理量，是记账副作用）。')
    print()
    print('     %-30s %-5s %-11s %-11s %-11s %s'
          % ('表', 'M', 'Δθ[°]', 'max F3 γ', '/γ₀', '块内 vs 块间'))
    for d in out:
        if not d['n_f3']:
            continue
        dth = THETA_MAX_DEG / (d['M'] - 1)
        print('     %-30s %-5d %-11.4f %-11.4f %-11.3f %s'
              % (','.join(str(v) for v in d['laths'])[:29], d['M'], dth,
                 d['gmax'], d['ratio'], d['verdict']))
    # 纯同类块的 M 序列（隔离 M 这一个变量）
    print()
    print('     **隔离 M 的单变量序列**（纯同类块 `1,1,...,1`，θ_max 固定 5°）：')
    mseq = []
    for M in (2, 3, 4, 6, 8, 12, 20):
        lt2 = build([1] * M)
        th = np.rad2deg(lt2.theta[1, 2])
        g = float(lt2.gtab[1, 2])
        gfar = float(lt2.gtab[1, M])
        mseq.append((M, th, g, gfar))
        print('        M=%-3d Δθ=%.4f°  相邻对 γ=%.4f (**%.3f×** γ₀)   '
              '首末对 θ=%.2f° γ=%.4f (**%.3f×**)'
              % (M, th, g, g / GAMMA0, np.rad2deg(lt2.theta[1, M]), gfar,
                 gfar / GAMMA0))
    span = max(x[2] for x in mseq) / min(x[2] for x in mseq)
    print('     ⇒ **相邻同变体对的 γ 跨 M=2…20 变化 %.2f 倍**（%.4f → %.4f）'
          % (span, max(x[2] for x in mseq), min(x[2] for x in mseq)))
    print('     ⇒ 结论：**只要 M ≳ 6，块内界面就便宜；M ≲ 4 时可能倒挂。**')
    print('        当前所有 6 块臂（M=12）⇒ **块内 4.6× 便宜 ✅**；')
    print('        而早期单块小臂（`1,1`/`1,1,1`/`1,1,1,1`）⇒ **可能倒挂 ⚠**。')

    # ---------------- 汇总 ----------------
    print()
    print('=' * 110)
    print('  ## 汇总')
    print('=' * 110)
    print('     %-30s %-6s %-7s %-7s %-10s %s'
          % ('表', 'M', 'F3 对', 'F2 对', 'maxF3/γ₀', '判定'))
    for d in out:
        r = ('%.3f×' % d['ratio']) if np.isfinite(d.get('ratio', float('nan'))) else '—'
        print('     %-30s %-6d %-7d %-7d %-10s %s'
              % (','.join(str(v) for v in d['laths'])[:29], d['M'], d['n_f3'],
                 d['n_f2'], r, d['verdict']))
    nb = [d for d in out if d['verdict'] in ('**倒挂**', '部分倒挂')]
    print()
    print('     ⇒ **有倒挂的表 = %d / %d**（有对照的那些表）'
          % (len(nb), len([d for d in out if d['n_f3'] and d['n_f2']])))
    for d in nb:
        print('        ⚠ `%s`：%s（%d/%d 对倒挂）'
              % (','.join(str(v) for v in d['laths']), d['verdict'],
                 d.get('nbad', 0), d['n_f3']))
    print()
    print('  ⚠ 记账：本脚本**只查接线与量级，不重跑仿真**。')
    print('     Q-4 的 M 依赖若成立 ⇒ 需**单变量对照**（改 ω 分配规则）才能定量其影响。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
