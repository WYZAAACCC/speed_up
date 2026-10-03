#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_robust.py --- ★ 稳健性检验：**"带延伸"的场数对阈值敏感吗？**

## 为什么要它
**§149/§150 的结论"step 1000 出现 8 个带延伸的场"用了阈值 `fill < 0.10` —— 而那个阈值是**我定的****。
**⇒ 若结论只是阈值的产物（例如阈值稍微一动，8 就变成 0 或 24），那它**不是物理结论**。**

## 判据（**预先写死**）
扫一串阈值 `T ∈ {0.06, 0.08, 0.10, 0.12, 0.14, 0.16}`，对 step **800** 与 **1000** 各数一次：
| 观察 | 结论 |
|---|---|
| **800 恒为 0，且 1000 在**一段**阈值区间内都 ≈8** | ⇒ **稳健**（有平台）⇒ 结论**不是阈值产物** |
| **8 只在一个孤立阈值上出现** | ⇒ **不稳健** ⇒ 须改用别的量（如"最大轴/次大轴"的比值）描述该形貌 |
"""
import numpy as np

DX = 62.5
THRS = [0.06, 0.08, 0.10, 0.12, 0.14, 0.16]

def fills(step):
    P = '_exp/_bk_t5/dry_t5H3/snap_%05d.npz' % step
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    out = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k)
        if idx.size == 0:
            continue
        lo, hi = idx.min(0), idx.max(0)
        vol = int(np.prod(hi - lo + 1))
        out[k] = float(idx.shape[0]) / max(vol, 1)
    return out

print('=' * 84)
print('★ 稳健性：阈值扫描（"带延伸" = fill < T）')
print('=' * 84)
data = {}
for st in (800, 1000):
    try:
        data[st] = fills(st)
    except Exception as e:
        print('  ⚠ step %d 读不到：%s' % (st, e))
print('  %-8s %-10s %-10s %s' % ('阈值T', 'step800', 'step1000', 'step1000 里被判为带延伸的场'))
print('  ' + '-' * 74)
for T in THRS:
    row = []
    for st in (800, 1000):
        if st not in data:
            row.append('—'); continue
        n = sum(1 for v in data[st].values() if v < T)
        row.append(str(n))
    fs = []
    if 1000 in data:
        fs = sorted(k for k, v in data[1000].items() if v < T)
    print('  %-8.2f %-10s %-10s %s' % (T, row[0], row[1], fs if fs else '（无）'))

print()
print('  ── 判据（预先写死）──')
if 1000 in data:
    vals = [sum(1 for v in data[1000].values() if v < T) for T in THRS]
    zs = [sum(1 for v in data[800].values() if v < T) for T in THRS] if 800 in data else None
    print('  step1000 的计数序列（T 递增）= %s' % vals)
    if zs is not None:
        print('  step800  的计数序列（T 递增）= %s' % zs)
    # 找平台：计数在某个阈值区间内保持不变
    plateau = {}
    for T, v in zip(THRS, vals):
        plateau.setdefault(v, []).append(T)
    big = {v: ts for v, ts in plateau.items() if len(ts) >= 2 and v > 0}
    print()
    if big:
        for v, ts in sorted(big.items()):
            print('  ✅ 计数 **%d** 在阈值 %s 上**保持不变** ⇒ **有平台 ⇒ 稳健**' % (v, ts))
    else:
        print('  ⚠ **没有平台**（每个阈值给不同计数）⇒ **不稳健** ⇒ 须改用别的量描述该形貌')
    if zs is not None and all(z == 0 for z in zs):
        print('  ✅ 且 step 800 在**全部**阈值下都是 **0** ⇒ "涌现"这一条**极稳健**')
    elif zs is not None:
        print('  ⚠ step 800 在部分阈值下非 0 ⇒ "涌现"的起点**对阈值敏感**，须谨慎')
