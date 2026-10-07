#!/usr/bin/env python3
"""_r418_film.py —— ★ **§186 机理的最终定案**（从真值快照直接数，不再靠离线重实现）。

## 已知（`_r417` 已证）
* 我从 `region` 独立数的 F3 面数与 `series.csv` 的 `nf3` **逐位对上**（4 条臂全对）
  ⇒ **量具正确**，比较有效。
* `dry_gtB`（`--facet-proj 10 --facet-excl 1`，**归档行为**）step 20：
  `nf3` 3601 → **38**，同时 `nf1` 13326 → **20544（+7218）**、`nf2` 538 → 694。
* `dry_gtC`（`--facet-excl 0`，**本轮修复**）step 20：`nf3` → **3478**（几乎不动）。
* `dry_gtA`（`--facet-proj 0`）：`nf3` → 3612。

## 待判定的假设 H2（`+7218 ≈ 2 × 3563` 的签名）
若每条被抹掉的 F3 界面被**一条 β 膜**取代，则该处从「1 张同变体界面」变成
「**2 张母相-析出界面**」⇒ **ΔF1 ≈ +2 × (−ΔF3)**。
实测 `-ΔF3 = 3601 − 38 = 3563`，`2 × 3563 = 7126`，而 `ΔF1 = +7218` ⇒ **吻合到 1.3%**。
⇒ 本脚本直接从快照**数 β 膜**来独立确认，而不是只靠这个比值。

## 判据
  **P-1 正对照**：`gtA`（投影关闭）的 β 膜应**最小**（基线水平）。
  **P-2**：`gtB` 的"夹在同变体两场之间的 region==0 胞"**显著多于** `gtA`/`gtC`。
  **P-3 账要对上**：`ΔF1` 与 `2 × (−ΔF3)` 的比值落在 [0.8, 1.25]。
"""
import csv
import os
import sys

import numpy as np
from scipy import ndimage

BASE = '_exp/_bk_mb'


def P(s):
    print(s, flush=True)


def load_meta(tag):
    import json
    p = os.path.join(BASE, tag, 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else None


def film_cells(reg, vmap, st=6):
    """夹在**同变体两个不同场**之间的 `region==0` 胞（β 膜的直接判据）。

    判据：该胞 6-邻域里存在 k1≠k2 且 `vmap[k1]==vmap[k2]`（同变体、不同场）。
    """
    varr = np.zeros(reg.max() + 1, np.int64) - 1
    for k, v in vmap.items():
        if k < len(varr):
            varr[k] = v
    out = np.zeros(reg.shape, bool)
    zero = (reg == 0)
    if not zero.any():
        return 0
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        for s in (1, -1):
            nb = np.roll(reg, s * np.array(d), axis=(0, 1, 2))
            vv = np.where(nb > 0, varr[np.clip(nb, 0, len(varr) - 1)], -1)
            out |= zero & (vv >= 0)
    # 更严：要求邻域里同变体的场号 **≥2 个不同值**
    cnt = np.zeros(reg.shape, np.int8)
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        for s in (1, -1):
            nb = np.roll(reg, s * np.array(d), axis=(0, 1, 2))
            cnt += ((nb > 0) & (varr[np.clip(nb, 0, len(varr) - 1)] >= 0)).astype(np.int8)
    # 直接把"同变体 ≥2 个不同场号"算出来
    nbv = []
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        for s in (1, -1):
            nbv.append(np.roll(reg, s * np.array(d), axis=(0, 1, 2)))
    strike = np.zeros(reg.shape, np.int16) - 1
    for k, v in vmap.items():
        hit = np.zeros(reg.shape, bool)
        for nb in nbv:
            hit |= (nb == k)
        # 该胞的邻域里有没有这个场
        pass
    # 简化且严格：邻域里出现的**场号集合**中，是否存在两个同变体
    masks = {k: np.zeros(reg.shape, bool) for k in vmap}
    for k in vmap:
        for nb in nbv:
            masks[k] |= (nb == k)
    samevar_pair = np.zeros(reg.shape, bool)
    vs = sorted(set(vmap.values()))
    for v in vs:
        ks = [k for k in vmap if vmap[k] == v]
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                samevar_pair |= (masks[ks[i]] & masks[ks[j]])
    return int((zero & samevar_pair).sum())


def face_counts(reg, vmap):
    c1 = c2 = c3 = 0
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        nb = np.roll(reg, d, axis=(0, 1, 2))
        iface = (reg != nb)
        if not iface.any():
            continue
        a, b = reg[iface], nb[iface]
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        z = (lo == 0)
        c1 += int(np.count_nonzero(z))
        nz = ~z
        if nz.any():
            va = np.array([vmap.get(int(x), -1) for x in hi[nz]])
            vb = np.array([vmap.get(int(x), -1) for x in lo[nz]])
            c3 += int(np.count_nonzero(va == vb))
            c2 += int(np.count_nonzero(va != vb))
    return c1, c2, c3


ARMS = [('dry_gtA', '--facet-proj 0 （投影关闭，负对照）'),
        ('dry_gtB', '--facet-proj 10 --facet-excl 1 （**归档行为**）'),
        ('dry_gtC', '--facet-proj 10 --facet-excl 0 （**本轮修复**）')]

P('=' * 90)
P('_r418 —— β 膜直数（真值快照）+ 账目闭合')
P('=' * 90)

# ---- 先解释 gtA 与归档 saSet2 的几何差异（同名义参数却不同 Vt）
P('\n[0] 几何差异核对：`dry_saSet2`（归档）vs `dry_gtA`（本轮）')
m1, m2 = load_meta('dry_saSet2'), load_meta('dry_gtA')
keys = ('N', 'dx_nm', 'laths', 'plate', 'gap_nm', 'multi_block', 'block_gap_nm',
        'omega_max_deg', 'omega_mode', 'facet_proj', 'facet_excl', 'nuc_every',
        'nuc_init', 'grow_stack', 'arm', 'steps', 'gamma0')
for k in keys:
    a = (m1 or {}).get(k, (m1 or {}).get('exp_args', {}).get(k))
    b = (m2 or {}).get(k, (m2 or {}).get('exp_args', {}).get(k))
    if k in (m1 or {}).get('exp_args', {}) or k in (m2 or {}).get('exp_args', {}):
        a = (m1 or {}).get('exp_args', {}).get(k, a)
        b = (m2 or {}).get('exp_args', {}).get(k, b)
    mark = '' if a == b else '   ← **不同**'
    P('    %-16s saSet2=%-24s gtA=%-24s%s' % (k, a, b, mark))

res = {}
for tag, desc in ARMS:
    sp = os.path.join(BASE, tag, 'snap_00020.npz')
    sd = os.path.join(BASE, tag, 'seeds.npz')
    if not os.path.exists(sp):
        P('\n[%s] ✗ 无 step20 快照' % tag)
        continue
    d = np.load(sp)
    s = np.load(sd)
    reg = np.asarray(d['region'], np.int64)
    vk = d['vmap_keys'] if 'vmap_keys' in d.files else s['vmap_keys']
    vv = d['vmap_vals'] if 'vmap_vals' in d.files else s['vmap_vals']
    vmap = {int(k): int(v) for k, v in
            zip(np.asarray(vk).ravel(), np.asarray(vv).ravel())}
    f1, f2, f3 = face_counts(reg, vmap)
    n0 = int((reg == 0).sum())
    film = film_cells(reg, vmap, 6)
    npos = int((reg > 0).sum())
    res[tag] = dict(f1=f1, f2=f2, f3=f3, n0=n0, film=film, npos=npos)
    P('\n[%s] %s   step=20' % (tag, desc))
    P('    F1=%d F2=%d F3=%d   已转变胞=%d   region0 总胞=%d' % (f1, f2, f3, npos, n0))
    P('    ★ **β 膜**（region==0 且邻域里出现**同变体的两个不同场**）= **%d** 胞' % film)

P('\n' + '=' * 90)
P('[判读]')
a, b, c = res.get('dry_gtA'), res.get('dry_gtB'), res.get('dry_gtC')
if a and b and c:
    P('  P-1 正对照（投影关闭时 β 膜最小）：')
    P('      gtA=%d  gtC=%d  gtB=%d  ⇒ %s'
      % (a['film'], c['film'], b['film'],
         '✅ PASS' if (a['film'] <= b['film'] and c['film'] <= b['film']) else '❌ FAIL'))
    P('  P-2 gtB 的 β 膜显著多于 gtA/gtC：gtB/gtC = %.2f×，gtB/gtA = %.2f×'
      % (b['film'] / max(c['film'], 1), b['film'] / max(a['film'], 1)))
    dF1 = b['f1'] - a['f1']
    dF3 = a['f3'] - b['f3']
    P('  P-3 账目：ΔF1 = %+d，−ΔF3 = %+d，2×(−ΔF3) = %+d，比值 = %.3f ⇒ %s'
      % (dF1, dF3, 2 * dF3, dF1 / max(2 * dF3, 1),
         '✅ 吻合（β 膜签名）' if 0.8 <= dF1 / max(2 * dF3, 1) <= 1.25 else '❌ 不吻合'))
P('=' * 90)
