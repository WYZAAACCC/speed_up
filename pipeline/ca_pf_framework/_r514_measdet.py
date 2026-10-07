#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r514_measdet.py —— **量具确定性检验**：`measure_state` 对**同一输入**跑两次，结果一样吗？

## 为什么这是必须查的（`_r512` 的 D3 FAIL 引出来的）

`_r512` 的 D3 想验"int16 vs int8 只是 dtype 差别"，
做法是 `measure_state(reg)` vs `measure_state(reg.astype(np.int8))`。
在 **int8 臂**上这两者**输入完全相同**（`astype` 是恒等），**却报出
`f3_pos_n` / `f3_std_n` 不同** ⇒ 只可能是**量具本身不确定**。

**⇒ 若量具不确定，用户的硬要求「一定确保测量工具的正确性」就直接失守** ——
所有基于 `f3_pos_*` 的结论（F3 面位置、界面迁移量）都带随机抖动。

## 本脚本

1. **确定性**：同一 `reg` 连续调用 N 次，逐字段比对；
2. 找出**哪些字段**不确定，并量化抖动幅度；
3. **定位来源**：查 `measure_state` 里用到随机/集合遍历/浮点归约的地方；
4. **负对照**：确认"输入不同 ⇒ 输出必不同"（否则是量具没在工作）。

## 预登记判据

| # | 检验 | 判据 |
|---|---|---|
| **E1** | 同一输入 N 次调用**逐字段相同** | 全部相同 |
| **E2** | 若 E1 FAIL ⇒ **必须定位到具体字段与代码行** | 给出字段名 + 抖动量级 |
| **E3** | **负对照**：把 `reg` 改一个胞 ⇒ 输出**必须**变 | 至少一个字段变 |
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bk_measure as BM                                     # noqa: E402

NREP = 5


def main():
    print('=' * 92)
    print('R514  量具确定性检验（`_bk_measure.measure_state`）')
    print('=' * 92)
    fs = sorted(glob.glob('_exp/_bk_mb/dry_abA/snap_*.npz'))
    if not fs:
        print('✗ 找不到 abA 快照')
        return 2
    f = fs[len(fs) // 2]
    z = np.load(f)
    reg = z['region']
    N = int(z['N'])
    dx = float(z['L']) / N
    vmap = {int(a): int(b) for a, b in zip(z['vmap_keys'], z['vmap_vals'])}
    print('  快照：%s  dtype=%s  max=%d' % (os.path.basename(f), reg.dtype, int(reg.max())))
    print('  连续调用 %d 次，逐字段比对' % NREP)
    print()

    ms = [BM.measure_state(reg, dx, z['n_hab'], z['w_ax'], z['a_ax'], vmap)
          for _ in range(NREP)]
    keys = sorted(ms[0].keys())

    def _eq(a, b):
        """★ #101：**NaN-aware** 相等 —— 两次都是 NaN ⇒ 视为**相同**。
        ⚠ 第一版只改了数组分支、**漏了标量分支** ⇒ `f3_pos_n`（Python float NaN）
          仍被 `nan == nan → False` 误判成"不同"。**这条是补的第二刀。**"""
        if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
            return bool(np.array_equal(np.asarray(a, float),
                                       np.asarray(b, float), equal_nan=True))
        try:
            af, bf = float(a), float(b)
        except (TypeError, ValueError):
            return a == b
        if af != af and bf != bf:
            return True                       # 两个都是 NaN
        if af != af or bf != bf:
            return False                      # 一个 NaN、一个不是
        return af == bf

    bad = []
    for k in keys:
        vals = [m[k] for m in ms]
        same = True
        for v in vals[1:]:
            if not _eq(vals[0], v):
                same = False
                break
        if not same:
            # 量化抖动
            try:
                arr = np.asarray([np.asarray(v, float) for v in vals])
                spread = float(np.nanmax(arr) - np.nanmin(arr))
                rel = spread / max(abs(float(np.nanmean(arr))), 1e-300)
            except Exception:
                spread, rel = float('nan'), float('nan')
            bad.append((k, spread, rel, vals[0], vals[1]))
    print('  ── E1 同一输入 %d 次是否逐字段相同 ──' % NREP)
    if not bad:
        print('     ✅ **全部 %d 个字段逐位相同** ⇒ 量具是确定的' % len(keys))
    else:
        print('     ❌ **%d / %d 个字段不确定**：' % (len(bad), len(keys)))
        for (k, sp, rel, v0, v1) in bad:
            print('        `%s`：抖动量级 %.4e（相对 %.3e）' % (k, sp, rel))
            print('           第 1 次 = %s' % (np.asarray(v0).ravel()[:4].tolist()
                                             if isinstance(v0, np.ndarray) else v0))
            print('           第 2 次 = %s' % (np.asarray(v1).ravel()[:4].tolist()
                                             if isinstance(v1, np.ndarray) else v1))
    print()

    # ---- E3 负对照 ----
    reg2 = reg.copy()
    # 改一个胞（找一个非 0 的改成 0）
    idx = np.argwhere(reg2 != 0)
    if len(idx):
        i, j, k = idx[len(idx) // 2]
        reg2[i, j, k] = 0
    m2 = BM.measure_state(reg2, dx, z['n_hab'], z['w_ax'], z['a_ax'], vmap)
    def _eq(a, b):
        """★ #101：NaN-aware 相等（两次都是 NaN ⇒ 视为相同）。"""
        if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
            return bool(np.array_equal(np.asarray(a, float),
                                       np.asarray(b, float), equal_nan=True))
        try:
            af, bf = float(a), float(b)
            if af != af and bf != bf:
                return True                      # 两个 NaN
            return af == bf
        except (TypeError, ValueError):
            return a == b
    changed = [k for k in keys if not _eq(ms[0][k], m2[k])]
    print('  ── E3 负对照：改 1 个胞 ⇒ 输出必须变 ──')
    print('     变化字段数 = %d / %d ⇒ **%s**'
          % (len(changed), len(keys), '✅ PASS（量具有分辨力）' if changed else '❌ FAIL'))
    print('     变化的字段：%s' % changed[:8])
    print()
    print('=' * 92)
    print('★ 结论：%s' % ('量具**确定**' if not bad else '量具**不确定** ⇒ 必须修'))
    print('=' * 92)
    return 0 if not bad else 3


if __name__ == '__main__':
    sys.exit(main())
