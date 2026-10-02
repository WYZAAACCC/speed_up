#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c1pool.py --- ★★ 合并多个 seed 的初始位点，做**有功效**的 C1 均匀性检验。

## 为什么（goal C1 的困境）
`_r581_c1uni.py` 在实跑的两个 N=160 臂上只拿到 **4 / 5 个位点**
（`B·n(T_end)` 设计上就只有 15–25），`KS/χ²/最近邻` 的功效**极低**
⇒ 只能写"**未能证伪**"，写不出"已证明均匀"。

## 怎么解（`--eng-seed` 已实测可用，见 `_r581_engseed.sh`）
位点在 `_nuc_place_initial`（t=0）一次性生成，采样自 `default_rng(seed)`；
盒子几何逐臂相同 ⇒ **12 个 seed = 同一个均匀分布的 12 组独立样本**
⇒ 合并后样本量 ~70 ⇒ **功效可用**。

## 判据（与 `_r581_c1uni.py` **同一套**，只是样本量不同）
* **U1** 三个一维边缘的 KS vs U(0,L)
* **U2** 八分体 χ²（期望 ≥5 时用渐近式，否则蒙特卡洛）
* **U3** 最近邻中位 vs CSR 带
* **★ 功效对照**：**同时**报"单 seed（n≈6）"与"合并（n≈70）"的 p 值，
  让"功效提升"**看得见**。
* **负对照**：把合并点云人为聚成一团 ⇒ 三判据必须报出 p≈0。
"""
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _r581_c1uni import chi2_octants, csr_band, ks_uniform, nn_median  # noqa


def load_sites(root, seeds):
    out = {}
    for s in seeds:
        p = os.path.join(root, 'dry_s%s' % s, 'nuc_dbg.json')
        if not os.path.exists(p):
            continue
        j = json.load(open(p, encoding='utf-8'))
        st = j.get('nuc_cfg', {}).get('sites', [])
        out[int(s)] = np.array([v for _, v in st], float)
    return out


def report(P, L, label):
    L_ = []
    L_.append('  ── %s（n=%d）──' % (label, len(P)))
    if len(P) < 2:
        L_.append('     ⚠ 点太少，跳过'); return L_, None
    ps = []
    for i, ax in enumerate('xyz'):
        D, pv = ks_uniform(P[:, i] / L, 1.0)
        ps.append(pv)
        L_.append('     KS %s：D=%.4f p=%.4f %s' % (ax, D, pv, '不拒绝' if pv > 0.05 else '**拒绝**'))
    chi2, pv2, cnt = chi2_octants(P, L)
    L_.append('     χ² 八分体：χ²=%.3f p=%.4f %s（计数 %s）'
              % (chi2, pv2, '不拒绝' if pv2 > 0.05 else '**拒绝**', cnt.astype(int).tolist()))
    if len(P) >= 2:
        b5, b95, med = csr_band(len(P), L, reps=3000)
        nm = nn_median(P, L)
        L_.append('     最近邻中位 %.4f µm；CSR 中位 %.4f 带 [%.4f, %.4f] ⇒ %s'
                  % (nm * 1e6, med * 1e6, b5 * 1e6, b95 * 1e6,
                     '落在带内' if b5 <= nm <= b95 else '**落在带外**'))
    L_.append('     ⇒ 最小 p = %.4f' % min(ps + [pv2]))
    return L_, min(ps + [pv2])


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_pool'
    seeds = [int(x) for x in sys.argv[2:]] or list(range(11, 23))
    L = ['=' * 96,
         'R581 —— C1「统计均匀」：**多 seed 合并**做有功效的检验',
         '=' * 96]
    d = load_sites(root, seeds)
    if len(d) < 2:
        L.append('⚠ 只找到 %d 个 seed 的结果 ⇒ 无法合并（如实登记）' % len(d))
        print('\n'.join(L)); return 2
    L.append('找到 %d 个 seed：%s' % (len(d), sorted(d)))
    for s, P in sorted(d.items()):
        L.append('   seed %-4d n=%d' % (s, len(P)))
    allP = np.vstack([d[s] for s in sorted(d)])
    # 盒子尺寸从任一 meta 读（不猜）
    any_meta = glob.glob(os.path.join(root, 'dry_s*/meta.json'))
    Lbox = 1.0
    if any_meta:
        Lbox = float(json.load(open(any_meta[0], encoding='utf-8')).get('L', 1.0))
    L.append('盒子 L = %.4f µm' % (Lbox * 1e6))
    L.append('')
    L.append('=' * 96)
    L.append('★ 功效对照：**同一套判据**，样本量不同')
    L.append('=' * 96)
    a, _ = report(d[sorted(d)[0]], Lbox, '单 seed（对齐实跑的量级）')
    L += a
    L.append('')
    b, pmin = report(allP, Lbox, '**合并 %d 个 seed**' % len(d))
    L += b
    L.append('')
    L.append('=' * 96)
    L.append('── 负对照（合并点云聚成一团 ⇒ 必须被拒）──')
    rng = np.random.default_rng(5)
    Pc = np.clip(rng.normal(0.2, 0.02, allP.shape), 0, 1) * Lbox
    c, pminc = report(Pc, Lbox, '负对照（聚在 (0.2,0.2,0.2)）')
    L += c
    nc_ok = (pminc is not None and pminc < 1e-3)
    L.append('   ⇒ %s' % ('✅ 被拒（判据有分辨力）' if nc_ok else '❌ **没分辨力**'))
    L.append('')
    L.append('=' * 96)
    L.append('★★ 判读')
    if pmin is None:
        L.append('   合并样本太少，判不了')
    elif pmin > 0.05:
        L.append('   ✅ **合并样本下：未能证伪均匀**（最小 p = %.4f）' % pmin)
        L.append('      样本量 n=%d ⇒ 功效**可用**（远好于单臂的 4–5 个）' % len(allP))
    else:
        L.append('   ❌ **拒绝均匀**（最小 p = %.4f）⇒ 生成器有偏，要查' % pmin)
    L.append('   ⚠ 记账：合并检验的是「**生成器**是否均匀」，')
    L.append('      不是"某一次运行"是否均匀 —— 对 C1 的表述而言这正是要问的。')
    txt = '\n'.join(L)
    print(txt)
    open('_w2_r581_c1pool.log', 'w').write(txt + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
