#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_degrade.py --- ★★★★★ 长程退化的**根因判定**：老场退化 vs 新场更差

## 要回答的问题（**二分**）
实测：`t5N276` 的长宽比中位从峰值 6.76（step 200）跌到 1.99（step 680）。
**两种互斥的解释：**
| # | 假设 | 预测 |
|---|---|---|
| **H1 老场退化** | **同一根**板条自身**变钝**（内在机制/场间挤压）| **早期就在的场，其长宽比会随时间下降** |
| **H2 新场更差** | 老场**保持**扁，但**新形核的场**本来就不扁 ⇒ 把中位拉下来 | **早期场的比值稳定；新场的初始比值低** |

## 做法（**用已有快照，不需新算例**）
`region == k` 就是**场的身份**（`k` = 场号，跨快照稳定）
⇒ 对每个场追踪 (长, 宽, 厚, 长宽比, 长厚比) 随 step 的变化。

## 输出（**判据预先写死**）
1. **每个"长寿场"（≥4 个快照）的轨迹表**；
2. **按"首次出现 step"分组**：早期组（≤200）vs 晚期组（>200）的**初始长宽比**对比
   ⇒ 若**晚期组的初始值明显低** ⇒ **支持 H2**；
3. **早期组的比值随时间的变化**（首值 → 末值）
   ⇒ 若**显著下降** ⇒ **支持 H1**；
4. **两者可以同时成立**（都要报，不强行二选一）。
"""
import glob
import sys
import numpy as np

DX = 62.5
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not snaps:
    print('  （无快照）'); sys.exit(0)


def measure(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    out = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000.0
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000.0
        if nh is not None:
            ax = nh / (np.linalg.norm(nh) + 1e-300)
            T = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
        else:
            T = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        out[k] = (idx.shape[0], L, W, T, L / max(W, 1e-9), L / max(T, 1e-9))
    return out


data = {}
for P in snaps:
    st = int(P.split('snap_')[1].replace('.npz', ''))
    data[st] = measure(P)
steps = sorted(data)
print('=' * 104)
print('★ %s 长程退化根因判定（快照 %d 张：%s … %s）' % (TAG, len(steps), steps[0], steps[-1]))
print('=' * 104)

# 每个场的首次出现与轨迹
first, traj = {}, {}
for s in steps:
    for k, v in data[s].items():
        first.setdefault(k, s)
        traj.setdefault(k, []).append((s, v[1], v[4]))       # (step, 长, **长宽比=v[4]**)

print()
print('  ── ① 各场的「首次出现 step」与「初始长宽比」──')
print('  %-5s %-10s %-8s %-8s %-10s %s' % ('场', '首现step', '初始长', '初始宽比', '末次step', '末次宽比'))
early, late = [], []
for k in sorted(first):
    tr = traj[k]
    if not tr:
        continue
    f0, l0, a0 = tr[0]
    f1, l1, a1 = tr[-1]
    print('  %-5d %-10d %-8.3f %-8.2f %-10d %.2f' % (k, f0, l0, a0, f1, a1))
    (early if f0 <= 200 else late).append((k, a0))

print()
print('  ── ② H2 检验：早期组 vs 晚期组的**初始**长宽比 ──')
ea = [a for _, a in early]; la = [a for _, a in late]
if ea and la:
    print('     早期组（首现 ≤200）: n=%d 初始中位 = **%.2f**' % (len(ea), np.median(ea)))
    print('     晚期组（首现 >200） : n=%d 初始中位 = **%.2f**' % (len(la), np.median(la)))
    print('     ⇒ %s' % ('**晚期组的初始值明显更低 ⇒ 支持 H2（新场更差）**'
                        if np.median(la) < np.median(ea) - 1.0
                        else '**两组初始值相近 ⇒ H2 不获支持**'))
else:
    print('     （分组样本不足）')

print()
print('  ── ③ H1 检验：**早期场自身**的长宽比随时间变化 ──')
drops = []
for k, a0 in early:
    tr = traj[k]
    if len(tr) < 4:
        continue
    a1 = tr[-1][2]
    drops.append((k, a0, a1, a1 - a0))
if drops:
    print('     %-5s %-10s %-10s %s' % ('场', '初始宽比', '末次宽比', '变化'))
    for k, a0, a1, d in drops:
        print('     %-5d %-10.2f %-10.2f **%+.2f**' % (k, a0, a1, d))
    dd = np.array([d for *_, d in drops])
    print('     ⇒ 早期场变化中位 = **%+.2f**（n=%d）⇒ %s'
          % (np.median(dd), len(dd),
             '**多数早期场自身在退化 ⇒ 支持 H1（老场退化）**'
             if np.median(dd) < -0.5 else '**早期场基本稳定 ⇒ H1 不获支持**'))
else:
    print('     （没有 ≥4 个快照的早期场）')
