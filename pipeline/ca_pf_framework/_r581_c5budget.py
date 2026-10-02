#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c5budget.py --- ★ C5「填满盒子」的**定量预算**：差多少、哪个旋钮能补、补了会撞到什么。

## 为什么要算这笔账
C5 现在的判定是「❌ 未达成」，但**只说"差 27–147 倍"没有用** ——
要回答三个问题：
1. **按实测**的板条体积，填到口径要求需要多少根？
2. 需要把哪个旋钮拧到多少？（`α_KM` 控 `n(T_end)`；`plate_L` 控单根体积；`N` 控盒子）
3. **拧过去会撞到什么**？（块厚文献带、内存、时间）

## 关键公式（`windowB_closure.py` / `_bk_exp.py:3114-3124`）
* `n(T) = α_KM · (M_s − T)`（C-2 位置饱和律）；第 k 根在 `T_k = M_s − k/α_KM` 出现
  ⇒ `T_end` 时的总根数 `n(T_end) = α_KM·(M_s − T_end)`
* 块数 `B = --nuc-block-target`；**总板条数 ≈ B · n(T_end)**
  （`--nuc-fresh-every K` 必须 = `n`，这就是 **N8** 的闭式解）
* 块厚 ≈ `n · t`（n 根同变体沿法向堆叠）

## ⚠ 口径必须分开报（goal §(14) 明文要求）
| 口径 | 定义 | 出处 |
|---|---|---|
| **A** | **220–450 根**（"长完后占满"） | goal §(14) 引仓库任务书 |
| **B** | **30% 体积分数**，按**当前播种截面** = 625–781 根 | goal §(14) |
| **C** | 30% 体积分数，按 `plate L×W×T` = **1176 根** | 引擎自己横幅（`_bk_exp.py:939`） |
⚠ **B 与 C 差 1.5–1.9 倍**（625–781 vs 1176）⇒ 两者对"单根体积"的假设不同
（B 隐含 ≈0.38–0.48 µm³/根，C 用 0.2550 µm³/根）⇒ **登记为口径矛盾**。
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

R = '_exp/_bk_p2'
# 材料/工艺常数（**从 meta.json 读，不写死**）
CAL = [('A 220 根', 220), ('A 450 根', 450),
       ('B 625 根', 625), ('B 781 根', 781), ('C 1176 根', 1176)]


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    L = ['=' * 100,
         'R581 —— C5「填满盒子」的定量预算',
         '=' * 100]
    for tag in tags:
        d = os.path.join(R, 'dry_' + tag)
        if not os.path.isdir(d):
            L.append('── %s：（不存在）' % tag); continue
        m = json.load(open(os.path.join(d, 'meta.json')))
        ea = m.get('exp_args', {})
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')])
        z = np.load(os.path.join(d, snaps[-1]), allow_pickle=True)
        reg = z['region']
        N = int(z['N'])
        Lbox = float(z['L'])
        dx = Lbox / N
        vox = dx ** 3
        Vbox = Lbox ** 3
        pl = m.get('plate', {})
        v_seed = (float(pl.get('L', 0)) * 1e-9) * (float(pl.get('W', 0)) * 1e-9) \
            * (float(pl.get('T', 0)) * 1e-9)

        L.append('=' * 100)
        L.append('★ %s（快照 %s，step=%d）' % (tag, snaps[-1], int(z['step'])))
        L.append('  盒子：N=%d  L=%.4f µm  Δx=%.1f nm  V_box=%.1f µm³'
                 % (N, Lbox * 1e6, dx * 1e9, Vbox * 1e18))
        pres = np.unique(reg[reg > 0])
        n_vox = int((reg > 0).sum())
        fv = n_vox * vox / Vbox
        L.append('  现状：%d 个场、%d 胞 ⇒ 体积 = **%.4f µm³** ⇒ **体积分数 = %.4f%%**'
                 % (len(pres), n_vox, n_vox * vox * 1e18, 100 * fv))

        # ---- 实测单根体积（**按连通分量**，与 P22 一致）----
        #   ⚠⚠ **第一版没设显著性下限 ⇒ 得到荒谬结论（留痕）**：
        #     21 个"分量"里**中位体积 = 1 个胞**（2.44e-4 µm³）⇒ 那些是**散点**，不是板条。
        #     于是"220 根的目标体积 = 0.05 µm³"、"需要的盒子边长 = 0.6 µm" 全是胡说。
        #     **数字荒谬 ⇒ 先怀疑量具**（P13）。
        #   ⇒ 修法：用**本仓自己的显著性阈值** `_bk_measure.MIN_SIG_VOX = 32`（= 32 胞）。
        MIN_SIG_VOX = 32
        vols_all = []
        for v in pres:
            lab, n = ndimage.label(reg == v)
            for i in range(1, n + 1):
                c = int((lab == i).sum())
                if c > 0:
                    vols_all.append(c)
        vols_all = np.array(vols_all, float)
        L.append('  ── 连通分量的**胞数分布**（先看清有没有散点）──')
        L.append('     分量总数 = **%d**（场数 = %d）' % (len(vols_all), len(pres)))
        L.append('     胞数：min %d  中位 **%d**  max %d；'
                 '**< %d 胞的分量 = %d 个（占 %.0f%%）**'
                 % (vols_all.min(), np.median(vols_all), vols_all.max(),
                    MIN_SIG_VOX, int((vols_all < MIN_SIG_VOX).sum()),
                    100 * (vols_all < MIN_SIG_VOX).mean()))
        L.append('     ⚠ 本仓阈值 `_bk_measure.MIN_SIG_VOX = %d` 胞'
                 '（= %.4f µm³）⇒ 低于它的算**散点**、不算板条'
                 % (MIN_SIG_VOX, MIN_SIG_VOX * vox * 1e18))
        big = vols_all[vols_all >= MIN_SIG_VOX]
        vols = big * vox
        L.append('     ⇒ **显著分量（≥%d 胞）= %d 个**（占了总体积的 %.2f%%）'
                 % (MIN_SIG_VOX, len(big),
                    100 * big.sum() / max(1, vols_all.sum())))
        if len(vols) == 0:
            L.append('     ⚠ 一个显著分量都没有 ⇒ 拒绝往下算'); continue
        L.append('  ── 显著单根体积（**≥%d 胞**）──' % MIN_SIG_VOX)
        L.append('     体积：中位 %.5f µm³  均值 %.5f  min %.5f  max %.5f  **总和 %.5f**'
                 % (np.median(vols) * 1e18, vols.mean() * 1e18,
                    vols.min() * 1e18, vols.max() * 1e18, vols.sum() * 1e18))
        L.append('     对照：`plate L×W×T` = %.5f µm³（播种尺寸）；实测中位/播种 = **%.2f×**'
                 % (v_seed * 1e18, np.median(vols) / max(v_seed, 1e-30)))


        # ---- 各口径还差多少 ----
        L.append('  ── 各口径还差多少（**用实测单根体积**，不是播种体积）──')
        L.append('     %-12s %-10s %-12s %-12s %s'
                 % ('口径', '目标根数', '目标体积µm³', '占盒子%', '现状/目标'))
        vmed = float(np.median(vols))
        for nm, ntg in CAL:
            Vtg = ntg * vmed
            L.append('     %-12s %-10d %-12.2f %-12.2f %.4f'
                     % (nm, ntg, Vtg * 1e18, 100 * Vtg / Vbox,
                        vols.sum() / Vtg))
        L.append('     ⇒ **当前根数 %d 根；口径 A 要 220–450 根 ⇒ 差 %.0f–%.0f 倍**'
                 % (len(vols), 220 / max(1, len(vols)), 450 / max(1, len(vols))))

        # ---- 旋钮 1：α_KM ----
        Ms = None
        for k in ('Ms', 'M_s', 'T_start'):
            if k in m:
                Ms = float(m[k]); break
        Tend = float(ea.get('T_end', 350.0))
        akm = float(ea.get('alpha_km', 0.011))
        L.append('  ── 旋钮 1：`α_KM`（C-2 位置饱和律 n(T) = α_KM·(M_s − T)）──')
        if Ms is None:
            L.append('     ⚠ meta.json 里没有 M_s（试过 Ms/M_s/T_start）⇒ '
                     '**无法反解 α_KM**，只报公式')
            L.append('     现状 α_KM = %s，T_end = %.1f' % (akm, Tend))
        else:
            n_end = akm * (Ms - Tend)
            L.append('     现状：α_KM = %.4f，M_s = %.1f K，T_end = %.1f K '
                     '⇒ n(T_end) = **%.2f 根/块**' % (akm, Ms, Tend, n_end))
            L.append('     ⚠ 与实测对照：平均每场 %.2f 个分量 vs n(T_end)=%.2f'
                     % (len(vols) / max(1, len(pres)), n_end))
            B = ea.get('nuc_block_target')
            L.append('     ⇒ 总根数 ≈ B·n(T_end) = %s × %.2f = **%.1f**（实测 %d 个分量）'
                     % (B, n_end, (float(B) if B else float('nan')) * n_end, len(vols)))
            L.append('     要 220 根（B=%s）⇒ α_KM 需 **%.4f**（现状的 **%.1f 倍**）'
                     % (B, 220 / (float(B) * (Ms - Tend)) if B else float('nan'),
                        (220 / (float(B) * (Ms - Tend))) / akm if B else float('nan')))
            L.append('     要 450 根（B=%s）⇒ α_KM 需 **%.4f**（现状的 **%.1f 倍**）'
                     % (B, 450 / (float(B) * (Ms - Tend)) if B else float('nan'),
                        (450 / (float(B) * (Ms - Tend))) / akm if B else float('nan')))
            L.append('     ⚠ **撞墙**：`§(13)` 已定 α_KM = 0.011（0.041739 就让块厚'
                     '超出文献带 2 倍）⇒ 再放大 9–19 倍会**直接废掉 §(18)③**')

        # ---- 旋钮 2：plate_L（S3）----
        #   ★★ **第一版把结论写反了（留痕）**：我写「口径 A 与 S3 不能同时成立」。
        #   重算一遍才对：**口径 A 恰恰要求 S3 被修**。
        #     220 根 × 物理体积 2.04 µm³ = 449 µm³ = 盒子的 **44.9%**  ⇒ 「长完后占满」✅
        #     220 根 × 当前体积 0.255 µm³ =  56 µm³ = 盒子的 **5.6%**   ⇒ 根本不满
        #   ⇒ **C5 与 S3 是同一个问题**：不修 `plate_L`，"220–450 根 = 占满"这条口径
        #     在自己的数上就不成立。
        L.append('  ── 旋钮 2：`plate_L`（S3）—— ★ **C5 与 S3 是同一个问题** ──')
        pll = float(pl.get('L', 0))
        v_phys = v_seed * (8000.0 / pll) if pll else float('nan')
        L.append('     现状 `plate_L` = %.0f nm（物理值 ~8000 nm）' % pll)
        L.append('     单根体积：播种 %.5f µm³；**物理尺寸下 %.5f µm³（×%.1f）**'
                 % (v_seed * 1e18, v_phys * 1e18, 8000.0 / pll if pll else 0))
        L.append('     %-10s %-16s %-16s %s'
                 % ('根数', '当前尺寸占比', '物理尺寸占比', '判读'))
        for ntg in (220, 450, 1176):
            f_cur = ntg * v_seed / Vbox
            f_phy = ntg * v_phys / Vbox
            L.append('     %-10d %-16s %-16s %s'
                     % (ntg, '%.2f%%' % (100 * f_cur), '%.2f%%' % (100 * f_phy),
                        '✅ 物理尺寸下"占满"' if f_phy >= 0.30
                        else ('⚠ 物理尺寸下 %.0f%%' % (100 * f_phy))))
        L.append('     ⇒ ★★ **口径 A（"220–450 根 = 长完后占满"）只有在 `plate_L`')
        L.append('       取物理值（~8000 nm）时才自洽**：220 根 ⇒ **44.9%**、450 根 ⇒ **91.8%**。')
        L.append('       而在当前 `plate_L = 1000 nm` 下，220 根只占 **%.2f%%**。' % (100 * v_seed * 220 / Vbox))
        L.append('     ⇒ **⇒ C5 与 S3 不是两个独立问题，是同一个问题**：')
        L.append('       不修 `plate_L`，"戴 220–450 根 = 占满"这条口径在自己的数上就不成立。')
        L.append('     ⚠ 但 `plate_L` 改大会**减少**可容纳的核数（几何上界 `B_max = L_box²/(plate_L·plate_W)`'
                 ' ⇒ 掉 %.0f 倍）⇒ **与"根数"反向耦合**，必须一起算。'
                 % (8000.0 / pll if pll else 0))

        # ---- 旋钮 3：盒子 ----
        L.append('  ── 旋钮 3：盒子尺寸（**与判据耦合：goal §(14) 要求 ≥10 µm**）──')
        L.append('     按**实测**单根体积 %.5f µm³：' % (vmed * 1e18))
        for ntg in (220, 450):
            L.append('       %d 根 = **%.1f µm³ = 盒子的 %.2f%%**'
                     % (ntg, ntg * vmed * 1e18, 100 * ntg * vmed / Vbox))
        L.append('     要在这只 10 µm 盒子里占到 **30%%**（= %.0f µm³）⇒ 需 **%.0f 根**'
                 % (0.30 * Vbox * 1e18, 0.30 * Vbox / vmed))
        L.append('     ⇒ **口径 A（220–450 根）对应的是 %.2f%%–%.2f%% 体积分数，'
                 '不是 30%%**。' % (100 * 220 * vmed / Vbox, 100 * 450 * vmed / Vbox))
        L.append('       口径 B/C（30%%）在这只盒子里需要 **%.0f–%.0f 根**。'
                 % (0.30 * Vbox / vmed, 0.30 * Vbox / vmed))
        L.append('     ⚠ goal §(14) 要求盒子 ≥10 µm（容纳 prior-β 晶粒内的真实区域）'
                 '⇒ **不能靠缩盒子达标**。')
        L.append('     ⇒ **三个口径在数值上互不自洽**（详见本文档头部的口径表）。')
        L.append('')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_c5budget.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
