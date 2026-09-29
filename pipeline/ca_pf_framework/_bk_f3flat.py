#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_f3flat.py —— 量 **F3 界面的平整度**，**逐对**算，再报逐对值与平均。

★★ 为什么必须**逐对**（Round 17 的教训 —— 我在这一个量上连错两次）：
  `_bk_measure.f3_std_n` 把**所有对的 F3 胞汇在一起**求标准差。
  当块里有 k 张界面时，它们分布在 `n*` 的不同位置上
  ⇒ 汇总标准差**主要反映"界面之间的间距"**，而不是"单张界面有多粗糙"。
  实测（`_bk_stdtrend.py` 从 `f3_std_m` 列读）：
      eng12（5 张界面）@200 步 = 333 nm；cl1b（界面更少）@1000 步 = 195 nm
  ⇒ 我先后得出过两个结论 ——「归档的界面是钉死的」和「归档的界面粗糙 3.5 倍」——
    **两个都是这个混淆造成的伪影**。
  ⇒ 正确口径：**逐对算 std，再看逐对值的分布**。

用法：
    python3 _bk_f3flat.py _exp/_bk_eng/eng_eng12 _exp/_bk_closed/dry_cl1b
"""
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
from scipy import ndimage                                       # noqa: E402


def main(argv):
    for d in (argv[1:] or ['_exp/_bk_eng/eng_eng12']):
        p = os.path.join(_HERE, d)
        snaps = sorted(glob.glob(os.path.join(p, 'snap_*.npz')))
        mp = os.path.join(p, 'meta.json')
        if not snaps or not os.path.exists(mp):
            print('%-34s （缺快照或 meta）' % d)
            continue
        meta = json.load(open(mp, encoding='utf-8'))
        t_ph = float((meta.get('plate') or {}).get('T_physical')
                     or (meta.get('plate') or {}).get('T', 250.0))
        print('--- %s（%d 个快照；物理板条厚 %.0f nm）' % (d, len(snaps), t_ph))
        for sp in snaps:
            z = np.load(sp, allow_pickle=True)
            reg = z['region']
            dx = float(z['L']) / reg.shape[0]
            nh = np.asarray(z['n_hab'], float)
            nh = nh / (np.linalg.norm(nh) + 1e-300)
            vmap = {int(a): int(b) for a, b in zip(z['vmap_keys'], z['vmap_vals'])}
            fields = [int(k) for k in np.unique(reg) if k > 0]
            per = []
            for i in fields:
                mi = (reg == i)
                for j in fields:
                    if j <= i or vmap.get(i) != vmap.get(j):
                        continue
                    adj = mi & ndimage.binary_dilation(reg == j)
                    if adj.sum() < 8:
                        continue
                    pr = (np.argwhere(adj).astype(float) @ nh) * dx      # 米
                    per.append((i, j, float(pr.std()) * 1e9, adj.sum(),
                                float(pr.mean()) * 1e9))
            if not per:
                print('    %-14s 无 F3' % os.path.basename(sp))
                continue
            stds = [x[2] for x in per]
            print('    %-14s step=%-5s 对数=%d  **逐对 std(n*)：%s nm**'
                  '  平均=%.1f（= %.3f × t）  最大=%.1f'
                  % (os.path.basename(sp), z['step'], len(per),
                     '/'.join('%.0f' % s for s in stds),
                     float(np.mean(stds)), float(np.mean(stds)) / t_ph,
                     max(stds)))
            # 界面**位置**的跨度（这才是被 `f3_std_n` 混淆进去的那个量）
            means = [x[4] for x in per]
            print('        （界面位置沿 n* 的跨度 = %.0f nm ≈ %.1f × t；'
                  '**这一项随界面张数增长，正是 `f3_std_n` 被它主导的来源**）'
                  % (max(means) - min(means),
                     (max(means) - min(means)) / t_ph))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
