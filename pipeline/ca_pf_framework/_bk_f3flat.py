#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_f3flat.py —— 从快照直接量 **F3 界面的平整度**（`f3_std_n`，沿 `n*` 的标准差）。

为什么要单独一个工具：`V-3g` 测的是界面的**平均位置** `f3_pos` 在两次形核之间动多少。
如果界面本身**变粗糙了**，平均位置当然会晃 —— 那就不是"界面在迁移"，而是"界面不平了"。
`f3_std_n` 正好是区分这两件事的那个量，但它**没写进 `series.csv`**（只在 stdout 的日志行里）
⇒ 从快照重算，才能对**归档算例**也量一遍（归档的幂等日志早没了）。

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
            vk = z['vmap_keys']; vv = z['vmap_vals']
            vmap = {int(a): int(b) for a, b in zip(vk, vv)}
            # F3 胞：某胞的 6-邻域里同时出现场 i 与场 j、且 vmap[i]==vmap[j]
            acc = []
            fields = [k for k in np.unique(reg) if k > 0]
            for i in fields:
                mi = (reg == i)
                for j in fields:
                    if j <= i or vmap.get(int(i)) != vmap.get(int(j)):
                        continue
                    # 用膨胀相交近似"相邻"（比逐面遍历便宜，判据只需相对比较）
                    from scipy import ndimage
                    adj = mi & ndimage.binary_dilation(reg == j)
                    if adj.sum() < 8:
                        continue
                    idx = np.argwhere(adj).astype(float)
                    pr = (idx @ nh) * dx
                    acc.append(pr)
            if not acc:
                print('    %-14s 无 F3' % os.path.basename(sp))
                continue
            cat = np.concatenate(acc)
            # ★ 单位（Round 16 修）：`cat` 是**米** —— 第一版直接按 nm 打印 ⇒ 全是 0.0，
            #   而"× 物理板条厚"那一栏又拿米去比 nm ⇒ 报出 1e8 倍的荒唐比值。
            #   本仓库同类错已第三次（`robust_thickness`、A-8 的 Vt）。
            std_nm = cat.std() * 1e9
            span_nm = (cat.max() - cat.min()) * 1e9
            # ★★ 同时给**权威口径**的值：`_bk_measure.measure_state` 的 `f3_std_n`
            #   （逐面判 F3，与日志/判据同一把尺）。我自己的"膨胀相交"口径会把
            #   对角邻居也算进来 ⇒ 数值偏大 ⇒ **两个口径不可混着比**。
            import _bk_measure as BM
            _mm = BM.measure_state(reg, dx, nh, np.asarray(z['w_ax'], float),
                                   np.asarray(z['a_ax'], float), vmap)
            ref_nm = float(_mm['f3_std_n']) * 1e9
            print('    %-14s step=%-5s F3胞=%6d  **std(n*) = %6.1f nm**'
                  '（= %.3f × 物理板条厚）  跨度=%.0f nm'
                  '   ‖ 权威口径 `_bk_measure.f3_std_n` = **%.1f nm**（= %.3f × t）'
                  % (os.path.basename(sp), z['step'], cat.size, std_nm,
                     std_nm / t_ph, span_nm, ref_nm, ref_nm / t_ph))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
