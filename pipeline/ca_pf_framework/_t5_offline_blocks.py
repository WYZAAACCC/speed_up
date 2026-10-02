#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_offline_blocks.py --- ★★★★★ **从快照离线重算块表**（判据③④⑥ 的判定路径）

## 为什么需要它（用户要求 + 上轮发现的限制）
* 用户逐字要求：「把仿真过程的**全部数据保存在 F 盘**下，以便之后**用新量具重新测量**」
* 上轮实测限制：**在线块列的分辨率 = `lcm(--every, --pair-every)` = 100 步**
  （块表只在 `it % pair_every == 0` 时算，`_bk_exp.py` 的 `_pair_now` 门控）
* 而 **快照是 `--snap-every 40`**，且**快照里有 `region`**
  ⇒ **可以离线重算，分辨率 40 步（比在线更密）** ✓

## 口径（**先写死**）
* 一个**块** = 同一**变体**的、在 `region` 图上 **6-连通（周期）** 的一块区域；
  块内不同**场**就是不同**板条**（`vmap[k] = v`）—— 定义见 `_bk_measure.blocks()` 的 docstring
* 本脚本**只用 `region` + `dx` + `vmap`**（不传 `eps0_var`/`npf_var`/`axes_var`），
  理由：那三样需要 `_bk_exp.py` 的模块级 `EPS0`/`NPF` 表，
  而**块数 / 每块板条数 / 变体数这几个量不依赖它们**。
  ⚠ **记账**：`r_selfac`（自协调残差）**需要** `eps0_var` ⇒ **本脚本不给它**
  ⇒ 判据⑥ 的 `r_selfac` 仍取**在线列**（100 步分辨率）。

## 用法
  python _t5_offline_blocks.py <run目录>        # 扫该目录全部 snap_*.npz
  python _t5_offline_blocks.py <run目录> 40     # 只看每 40 步
"""
import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5L62'
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        print('  ⚠ %s 里没有 snap_*.npz' % d)
        return 1
    try:
        import _bk_measure as BM
    except Exception as e:
        print('  ❌ import _bk_measure 失败：%s' % e)
        return 1

    print('=' * 104)
    print('★ 从快照**离线重算**块表：%s（%d 个快照）' % (d, len(snaps)))
    print('=' * 104)
    print('  %-6s %-8s %-10s %-12s %-10s %-12s %s'
          % ('step', 'N', 'nblk 总', 'nblk_sig', 'n_var_sig', 'n_habit',
             'blk_laths（每块板条数，前 8 个）'))
    print('  ' + '-' * 98)
    for f in snaps:
        st = int(re.search(r'snap_(\d+)\.npz', f).group(1))
        try:
            with np.load(f, allow_pickle=False) as z:
                keys = set(z.files)
                if 'region' not in keys:
                    print('  %-6d ⚠ 快照里没有 `region`（键：%s）' % (st, sorted(keys)[:8]))
                    continue
                reg = np.asarray(z['region']).astype(np.int32)
                N = int(np.asarray(z['N']).item()) if 'N' in keys else reg.shape[0]
                L = float(np.asarray(z['L']).item()) if 'L' in keys else N * 62.5e-9
                dx = L / N
                vk = np.asarray(z['vmap_keys']).ravel() if 'vmap_keys' in keys else None
                vv = np.asarray(z['vmap_vals']).ravel() if 'vmap_vals' in keys else None
                vmap = ({int(a): int(b) for a, b in zip(vk, vv)} if vk is not None
                        else {k: ((k - 1) % 12) + 1 for k in range(1, int(reg.max()) + 1)})
            b = BM.blocks(reg, dx, vmap)
            bl = b.get('blk_laths', '')
            print('  %-6d %-8d %-10s %-12s %-10s %-12s %s'
                  % (st, N, b.get('nblk', '?'), b.get('nblk_sig', '?'),
                     b.get('n_var_sig', '?'), b.get('n_habit', '?'),
                     str(bl)[:34]))
        except Exception as e:
            print('  %-6d ❌ 失败：%s: %s' % (st, type(e).__name__, str(e)[:60]))
    print('=' * 104)
    return 0


if __name__ == '__main__':
    sys.exit(main())
