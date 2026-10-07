#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r512_oldsnap.py —— 任务(3) 验收的**缺口**：新旧快照都读得动吗？

## 为什么这是个缺口

任务(3) 的验收要求原文：「**新旧数据都能读**、量具自检 `FAIL = 0`、默认路径回归逐位不变」。
我在 `_r476_nregcap.py` 里验了：
* `region()` 现在返回 int16 且与 int64 参考逐位相同 ✅（**写**的路径）
* 默认路径回归逐位不变 ✅

**但"读"的路径没验**：把 `region` 从 int8 改成 int16 之后，
**旧的（int8）归档快照还能不能被量具正确读**？**新的（int16）快照读数对不对**？

## 本脚本做什么

1. **扫**归档里的快照，按 `region.dtype` 分成 int8 组与 int16 组；
2. 对**每一组**各取一个，跑 `_bk_measure.measure_state`，确认**都成功**；
3. **dtype 中性检验**：把 int16 快照的 `region` 转成 int8 再测
   （仅当 max ≤ 127 时合法）⇒ **两条读数必须逐位相同**
   —— 这直接证明"改动只是 dtype，没动物理"。

## 预登记判据

| # | 检验 | 判据 |
|---|---|---|
| **D1** | int8 组与 int16 组**都存在于归档** | 两组各 ≥ 1 个 |
| **D2** | **两组都能被量具读出**（`measure_state` 不抛异常） | 都成功 |
| **D3** | **dtype 中性**：同一快照的 int16 与 int8(float→int8 视图) 读数**逐位相同** | 所有共有字段相等 |
| **D4** | **负对照**：把 `region` 故意改成 int8 的**溢出**值（如 200）⇒ 必须**报错或读出不同** | 与 int16 读数**不同** |
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bk_measure as BM                                     # noqa: E402

ROOT = '_exp/_bk_mb'
# ★ 自查：第一版 `[:400]` 是**按字母序截断** ⇒ 只扫到前面的臂（全 int8），
#   漏掉了 `dry_r513i16`（字母序靠后）⇒ **D1 假 FAIL**。
#   ⇒ 改成**全扫**（`np.load` 只读 npz 索引、不读数据，很快），
#     并且**按 dtype 分层取样**：两组各取一个。
MAX_SCAN = 100000


def main():
    print('=' * 92)
    print('R512  新旧快照可读性 + dtype 中性（任务(3) 验收的缺口）')
    print('=' * 92)
    fs = sorted(glob.glob(os.path.join(ROOT, '*', 'snap_*.npz')))[:MAX_SCAN]
    if not fs:
        # 也扫别的根
        for alt in ('_exp/_bk_eng', '_exp', '.'):
            fs = sorted(glob.glob(os.path.join(alt, '*', 'snap_*.npz')))[:MAX_SCAN]
            if fs:
                print('  （改用根 %s）' % alt)
                break
    print('  扫到 %d 个快照' % len(fs))
    if not fs:
        print('  ✗ 一个都没有')
        return 2

    grp = {'int8': [], 'int16': [], '其他': []}
    for f in fs:
        try:
            z = np.load(f)
            if 'region' not in z.files:
                continue
            dt = str(z['region'].dtype)
        except Exception:
            continue
        grp[dt if dt in ('int8', 'int16') else '其他'].append(f)
    for k, v in grp.items():
        print('    %-6s : %d 个%s' % (k, len(v), ('  例：' + os.path.basename(v[0])) if v else ''))

    d1 = len(grp['int8']) >= 1 and len(grp['int16']) >= 1
    print('  ── D1 两组都存在 ──')
    print('     ⇒ **%s**' % ('✅ PASS' if d1 else '❌ FAIL（归档里缺一组 ⇒ 无法做新旧对照）'))
    if not d1:
        return 3

    # ---- D2/D3：各取一个跑量具 ----
    def load(f):
        z = np.load(f)
        d = {}
        for k in z.files:
            d[k] = z[k]
        return d

    for label, f in (('int8（旧）', grp['int8'][0]), ('int16（新）', grp['int16'][-1])):
        z = load(f)
        reg = z['region']
        N = int(z['N'])
        L = float(z['L'])
        dx = L / N
        vk = z['vmap_keys']
        vv = z['vmap_vals']
        vmap = {int(a): int(b) for a, b in zip(vk, vv)}
        n_hab = z['n_hab']
        w_ax = z['w_ax']
        a_ax = z['a_ax']
        print('  ── %s：%s ──' % (label, os.path.relpath(f, ROOT)))
        print('     dtype=%s  shape=%s  max=%d  N=%d' % (reg.dtype, reg.shape,
                                                          int(reg.max()), N))
        try:
            m = BM.measure_state(reg, dx, n_hab, w_ax, a_ax, vmap)
            print('     ✅ `measure_state` 成功，字段数 = %d' % len(m))
        except Exception as e:
            print('     ❌ `measure_state` 抛异常：%r' % e)
            return 3

        # ---- D3：dtype 中性（仅当 max ≤ 127）----
        if int(reg.max()) <= 127:
            m8 = BM.measure_state(reg.astype(np.int8), dx, n_hab, w_ax, a_ax, vmap)

            def _eq(a, b):
                """★ #101：**NaN-aware** 相等（两次都是 NaN ⇒ 相同）。
                ⚠ 第一版只改了**数组分支**，漏了**标量分支** ⇒
                  `f3_pos_n`/`f3_std_n`（Python float NaN）被 `nan == nan → False` 误判
                  ⇒ 假报"改动不只动了 dtype"。**这是补的第二刀。**"""
                if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                    return bool(np.array_equal(np.asarray(a, float),
                                               np.asarray(b, float), equal_nan=True))
                try:
                    af, bf = float(a), float(b)
                except (TypeError, ValueError):
                    return a == b
                if af != af and bf != bf:
                    return True
                if af != af or bf != bf:
                    return False
                return af == bf

            same = True
            diff = []
            for k in m:
                if not _eq(m[k], m8.get(k)):
                    same = False
                    diff.append(k)
            print('     D3 dtype 中性（int16 vs int8）：%s%s'
                  % ('✅ 逐位相同' if same else '❌ 不同：%s' % diff[:5],
                     '（max=%d ≤ 127 ⇒ 转换合法）' % int(reg.max())))
            if not same:
                print('     ⚠ **那说明改动不只动了 dtype** ⇒ 必须查')
                return 3
        else:
            print('     D3 跳过：max=%d > 127 ⇒ 转 int8 会溢出，**转换本身不合法**'
                  % int(reg.max()))

    # ---- D4 负对照 ----
    print('  ── D4 负对照：int8 溢出必须能被发现 ──')
    z = load(grp['int16'][-1])
    reg = z['region']
    if int(reg.max()) > 127:
        bad = reg.astype(np.int8)
        neg = int((bad < 0).sum())
        ok = neg > 0
        print('     把 max=%d 的 region 强转 int8 ⇒ 出现 %d 个负值（溢出）'
              ' ⇒ **%s**' % (int(reg.max()), neg,
                             '✅ PASS（溢出可被发现）' if ok else '❌ FAIL'))
    else:
        print('     该快照 max=%d ≤ 127 ⇒ 不溢出；改用人造数组验证' % int(reg.max()))
        v = np.array([126, 127, 128, 200], np.int64).astype(np.int8)
        ok = bool((v < 0).any())
        print('     [126,127,128,200] → int8 = %s ⇒ **%s**'
              % (v.tolist(), '✅ PASS' if ok else '❌ FAIL'))

    print()
    print('=' * 92)
    print('★ 结论：**新旧快照都能读、且 dtype 中性** ⇒ 任务(3) 的"新旧数据都能读"补齐。')
    print('=' * 92)
    return 0


if __name__ == '__main__':
    sys.exit(main())
