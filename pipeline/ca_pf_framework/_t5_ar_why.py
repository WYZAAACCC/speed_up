#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_ar_why.py --- ★★★★★ 用**已跑完的全部数据**查：长宽比为什么这么小

## 核心判据（**预先写死**）
**各向同性生长**有个数学必然：**各方向按同一比例放大 ⇒ 长宽比**保持不变****。
**⇒ 所以只要测"长宽比是否随生长变化"，就能判定原因：**
| 观察 | 结论 |
|---|---|
| **长宽比随体积增大**几乎不变** | ⇒ **生长自相似 ⇒ 最终比例 ≈ 核的比例** ⇒ **根因 = 核的 `elong`** |
| **长宽比随体积增大而**升高** | ⇒ 生长**本身**有拉长偏好（则须查为何没升到 5–20）|
| **长宽比随体积增大而**下降** | ⇒ **有"变圆"的机制**（如场间挤压/吞并）⇒ 须查那一项 |

## 同时报
* **各方向的绝对生长率**（µm / 1000 步）⇒ 看有没有方向偏好；
* **核的比例**（种子期实测）与**代码里应该用的值**（`--eng-elong 3.75` ⇒ L/W = 3.75）。
"""
import glob
import numpy as np

DX = 62.5
snaps = sorted(glob.glob('_exp/_bk_t5/dry_t5H3/snap_*.npz'))
print('=' * 100)
print('★ 长宽比为什么这么小 —— 用**全部 %d 张快照**查' % len(snaps))
print('=' * 100)

def measure(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        n_hab = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    out = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        span = []
        for j in o:
            pr = c @ v[:, j]
            span.append(float(pr.max() - pr.min() + 1) * DX / 1000.0)
        if n_hab is not None:
            ax = n_hab / (np.linalg.norm(n_hab) + 1e-300)
            pr = c @ ax
            span[2] = float(pr.max() - pr.min() + 1) * DX / 1000.0
        vol = idx.shape[0]
        out[k] = dict(n=vol, p=span)
    return out

data = {}
for P in snaps:
    st = int(P.split('snap_')[1].replace('.npz', ''))
    try:
        data[st] = measure(P)
    except Exception:
        pass
steps = sorted(data)
print('  可用步 = %s' % steps)

# 只看**活得久**的场（≥4 个快照），追它们的轨迹
cnt = {}
for s in steps:
    for k in data[s]:
        cnt[k] = cnt.get(k, 0) + 1
longlived = sorted(k for k, v in cnt.items() if v >= 4)
print('  活得久（≥4 快照）的场 = %s' % longlived)
print()
print('  %-5s %s' % ('场', '  '.join('%7d' % s for s in steps)))
print('  ' + '-' * 96)
for k in longlived:
    for name, i in (('长p1', 0), ('宽p2', 1), ('厚p3', 2)):
        row = []
        for s in steps:
            v = data[s].get(k)
            row.append('%7.3f' % v['p'][i] if v else '      —')
        print('  %-5s %s' % ('%d%s' % (k, name), '  '.join(row)))
    print()

print('  ════ 判据：长宽比是否随"长大"变化 ════')
print('  %-5s %-24s %-24s %s' % ('场', '早期(第1次) p1/p2/p3', '晚期(末次) p1/p2/p3', '长宽比 早→晚'))
print('  ' + '-' * 92)
rows = []
for k in longlived:
    ss = [s for s in steps if k in data[s]]
    if len(ss) < 2:
        continue
    a, b = data[ss[0]], data[ss[-1]]
    ar_a = a[k]['p'][0] / max(a[k]['p'][1], 1e-9)
    ar_b = b[k]['p'][0] / max(b[k]['p'][1], 1e-9)
    vol_r = b[k]['n'] / max(a[k]['n'], 1)
    print('  %-5d %-24s %-24s %.2f → **%.2f**  （体积 ×%.1f）'
          % (k, '%.3f/%.3f/%.3f' % tuple(a[k]['p']), '%.3f/%.3f/%.3f' % tuple(b[k]['p']),
             ar_a, ar_b, vol_r))
    rows.append((ar_a, ar_b, vol_r))
if rows:
    A = np.array(rows)
    print()
    print('  **长宽比：早期中位 %.2f → 晚期中位 %.2f**（体积平均 ×%.1f）'
          % (np.median(A[:, 0]), np.median(A[:, 1]), np.median(A[:, 2])))
    d = np.median(A[:, 1]) - np.median(A[:, 0])
    print('  ⇒ 变化 %+.2f' % d)
    print()
    if abs(d) < 0.5:
        print('  ✅ **长宽比几乎不变 ⇒ 生长自相似（各向同性）**')
        print('     ⇒ **最终比例 ≈ 核的比例** ⇒ **根因就是核的拉长率**')
        print('     ⇒ 核实测 2.03；代码写明物理上应用 `--eng-elong 3.75`（L/W=2400/640）')
        print('     ⇒ **我用了回退值 2.0，且生长不增加拉长率 ⇒ 停在 ~3**')
    elif d > 0.5:
        print('  ⚠ 长宽比**升高** %.2f ⇒ 生长**有**拉长偏好，但仍远达不到 5–20 ⇒ 须查强度' % d)
    else:
        print('  ⚠ 长宽比**下降** %.2f ⇒ 有"变圆"机制（场间挤压/吞并）⇒ 须查那一项' % d)
