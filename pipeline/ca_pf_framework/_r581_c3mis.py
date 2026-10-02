#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c3mis.py --- C3 缺的那一块：**块内相邻板条的低角晶界取向差分布**（goal §(18)③）。

## 为什么需要它
goal 对 C3 的判据是「`nslab_n == M` 且 `nf3_col == M−1`；**低角晶界取向差要有实测分布**」。
前一半我已经在用 `series.csv` 判；**后一半（取向差分布）此前完全没做**。

## 数据从哪来（**不猜、先探针**）
* `meta.json` 里有一个 `theta_deg` —— 实测键数 **1128 = C(48,2)**，正好是 48 个场的**逐对**夹角
  ⇒ **引擎自己已经算好了每对变体的取向差**，不需要我去查 Burgers OR 表。
* `snap_*.npz` 的 `region` 给出每个胞属于哪个场 ⇒ 可以判**空间上相邻**的场对。
* `vmap_keys/vals` 给出 场 → 变体。

## 判据
1. **相邻场对**（共享胞面）⇒ 逐对查 `theta_deg` ⇒ 直方图。
2. **「低角晶界」的门槛**：按晶界类型学，**低角晶界一般取 θ ≤ 15°**
   （本仓 `--omega-max-deg 5.0` 是"变体选择"的口径，不是晶界口径 ⇒ **两者要分开报**）。
3. **负对照**：把 场→变体 的映射**随机打乱**，重算分布 ⇒ 必须与实测**不同**
   （否则说明这个分布只反映"哪些变体在场"，不反映"谁挨着谁"）。

## ⚠ 量具自检（先过解析已知答案）
造一个已知的三场构型，手工算出应有的相邻对与角度 ⇒ 必须逐位一致。
"""
import itertools
import json
import os
import sys

import numpy as np

R = '_exp/_bk_p2'
LOW_ANGLE_DEG = 15.0


def probe(tag):
    """探针：把 `theta_deg` 的**键格式**打出来（不许猜）。"""
    d = os.path.join(R, 'dry_' + tag)
    m = json.load(open(os.path.join(d, 'meta.json')))
    td = m.get('theta_deg')
    print('  `theta_deg` 类型=%s 项数=%s' % (type(td).__name__,
                                            len(td) if td is not None else 'None'))
    if td:
        ks = list(td.keys())[:5]
        print('    前 5 个键 = %r' % (ks,))
        print('    前 5 个值 = %r' % ([td[k] for k in ks],))
        nv = m.get('nv')
        print('    nv=%s ⇒ C(nv,2)=%s ⇒ %s'
              % (nv, nv * (nv - 1) // 2 if isinstance(nv, int) else '?',
                 '✅ 与项数吻合' if isinstance(nv, int)
                 and len(td) == nv * (nv - 1) // 2 else '⚠ 不吻合'))
    print('    omega_max_deg = %s（这是**变体选择**口径，不是晶界口径）'
          % m.get('omega_max_deg'))
    return m, td


def key_of(td, a, b):
    """容错地取 (a,b) 的夹角。

    ★ 实测键格式（`_bk_exp.py:1508`）：**`'%d-%d'`（短横）**。
      第一版只试了 `'a,b'` / `'(a, b)'` / `'[a, b]'` ⇒ **0 命中**
      ⇒ 工具正确地**拒绝给结论**（"一对都没查到 ⇒ 拒绝给结论"）。
      **⇒ 守卫起作用了：宁可不报，也不报错数。**
    """
    for k in ('%d-%d' % (a, b), '%d-%d' % (b, a),
              '%d,%d' % (a, b), '%d,%d' % (b, a),
              '(%d, %d)' % (a, b), '(%d, %d)' % (b, a),
              '[%d, %d]' % (a, b), '[%d, %d]' % (b, a)):
        if k in td:
            return float(td[k])
    return None


def selftest():
    """解析已知答案 —— ★ **第一版的"解析值"我自己算错了，留痕**。

    ## 第一次自检 FAIL 的经过
    我造 `reg[0:4]=1, reg[4:8]=2, reg[8:12]=3`（N=12）并写死"相邻对只应是 (1,2) 与 (2,3)"。
    实测给出 **(1,2) / (1,3) / (2,3)** ⇒ 报 FAIL。

    **真相：错的是我的"解析值"，不是量具。** 盒子是**周期**的 ⇒
    场 3 占据 `[8,12)`、场 1 占据 `[0,4)`，两者**跨周期边界相邻** ⇒ `(1,3)` **本来就该在**。

    ⇒ 按本仓纪律（`R2 §1`：「量具的第一次自检是 FAIL 的 —— 我预登记算错了，不是量具错。
       **没有放宽阈值，而是改推导**」），我**改推导**并**加一个非周期用例把两种情形隔离**。
    """
    L = ['  ── 量具自检（解析已知答案；**周期与非周期分开**）──']
    ok = True

    # ---- 用例 A：**周期**盒（场 1 与场 3 跨边界相邻）----
    N = 12
    reg = np.zeros((N, N, N), np.int16)
    reg[0:4, :, :] = 1
    reg[4:8, :, :] = 2
    reg[8:12, :, :] = 3
    got = set(adjacent_pairs(reg))
    want = {(1, 2), (2, 3), (1, 3)}          # ← 改对后的解析值（含跨周期那一对）
    okA = got == want
    ok &= okA
    L.append('    A【周期】解析=%s 实测=%s ⇒ %s'
             % (sorted(want), sorted(got), '✅' if okA else '❌'))
    L.append('       （场 3 占 [8,12)、场 1 占 [0,4) ⇒ **跨周期边界**(1,3) 本来就该在）')

    # ---- 用例 B：**非周期位置**（三段都不碰边界）⇒ (1,3) 必须消失 ----
    regB = np.zeros((N, N, N), np.int16)
    regB[1:4, :, :] = 1
    regB[4:7, :, :] = 2
    regB[7:10, :, :] = 3
    gotB = set(adjacent_pairs(regB))
    wantB = {(1, 2), (2, 3)}
    okB = gotB == wantB
    ok &= okB
    L.append('    B【非周期】解析=%s 实测=%s ⇒ %s'
             % (sorted(wantB), sorted(gotB), '✅' if okB else '❌'))

    # ---- 负对照 1：把场 3 整段去掉 ⇒ (2,3) 与 (1,3) 都必须消失 ----
    regC = reg.copy()
    regC[8:12] = 0
    gotC = set(adjacent_pairs(regC))
    nc1 = (2, 3) not in gotC
    ok &= nc1
    L.append('    负对照1（去掉场 3）：相邻对=%s ⇒ (2,3) %s'
             % (sorted(gotC), '已消失 ✅' if nc1 else '仍在 ❌'))

    # ---- 负对照 2：**只差一个胞**（把场 2 缩到 3 胞）⇒ 必须量出不同结果 ----
    regD = reg.copy()
    regD[7, :, :] = 1                      # 场 2 由 4 胞变 3 胞
    gotD = adjacent_pairs(regD)
    nc2 = gotD != sorted(got)
    ok &= nc2
    L.append('    负对照2（场 2 少 1 胞）：%s ⇒ %s'
             % (gotD, '✅ 有分辨力' if nc2 else '❌ **判据对 1 胞变化不敏感**'))

    L.append('    ⇒ 自检：%s' % ('✅ PASS' if ok else '❌ FAIL ⇒ 不许用下面的数'))
    return ok, L


def adjacent_pairs(reg):
    """共享一个**胞面**的场对（6 邻域，含周期）。**只看两个场都 > 0 的位置。**"""
    out = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        m = (a > 0) & (b > 0) & (a != b)
        if not m.any():
            continue
        u = np.unique(np.stack([a[m], b[m]], 1), axis=0)
        for x, y in u:
            out.add((int(min(x, y)), int(max(x, y))))
    return sorted(out)


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    L = ['=' * 96,
         'R581 —— C3 缺的一块：**块内相邻板条的低角晶界取向差分布**',
         '=' * 96]
    ok, sub = selftest()
    L += sub
    if not ok:
        print('\n'.join(L)); print('\n❌ 自检不过 ⇒ 拒绝给判读'); return 2
    L.append('')
    for tag in tags:
        d = os.path.join(R, 'dry_' + tag)
        if not os.path.isdir(d):
            L.append('── %s：（不存在）' % tag); continue
        L.append('=' * 96)
        L.append('★ %s' % tag)
        L.append('  ── 探针：`theta_deg` 的键格式 ──')
        m, td = probe(tag)
        if not td:
            L.append('  ⚠ 没有 theta_deg ⇒ 跳过'); continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')])
        if not snaps:
            L.append('  ⚠ 没有快照 ⇒ 跳过'); continue
        z = np.load(os.path.join(d, snaps[-1]), allow_pickle=True)
        reg = z['region']
        vmap = {int(a): int(b) for a, b in zip(z['vmap_keys'], z['vmap_vals'])}
        L.append('  用 %s（step=%d）' % (snaps[-1], int(z['step'])))
        pairs = adjacent_pairs(reg)
        L.append('  ── 空间上相邻的场对（共享胞面，含周期）──')
        L.append('     相邻场对数 = **%d**' % len(pairs))
        rows = []
        miss = 0
        for a, b in pairs:
            th = key_of(td, a, b)
            if th is None:
                miss += 1
                continue
            rows.append((a, b, vmap.get(a, -1), vmap.get(b, -1), th))
        if miss:
            L.append('     ⚠ 有 %d 对在 `theta_deg` 里查不到（键格式待查）' % miss)
        if not rows:
            L.append('     ⚠ 一对都没查到 ⇒ **拒绝给结论**'); continue
        th = np.array([r[4] for r in rows], float)
        L.append('     查到 %d 对；θ 的 min/中位/max = %.3f / %.3f / %.3f 度'
                 % (len(th), th.min(), np.median(th), th.max()))
        # 直方图
        bins = [0, 5, 10, 15, 30, 45, 60, 90]
        h, _ = np.histogram(th, bins=bins)
        L.append('     ── 取向差直方图（度）──')
        for i in range(len(h)):
            bar = '#' * int(40 * h[i] / max(1, h.max()))
            L.append('       [%2d,%3d)  %3d 对  %-40s' % (bins[i], bins[i + 1], h[i], bar))
        nlo = int((th <= LOW_ANGLE_DEG).sum())
        L.append('     ⇒ **θ ≤ %.0f° 的低角晶界：%d / %d = %.1f%%**'
                 % (LOW_ANGLE_DEG, nlo, len(th), 100 * nlo / len(th)))
        # ★★★ 关键判据：这个分布是**涌现的**还是**参数化强加的**？
        #   ⚠ 第一版用"相邻互异值的间隔"去比 —— 那个统计量**不稳**
        #     （它把"有哪些值"和"值等于多少"混在一起，且遇到重复/缺失会误报）。
        #   ⇒ 改成**直接检验公式**：`ladder` 的定义是
        #     `θ(a,b) = |a−b| · θ_max/(nv−1)`（`windowB_lath.py:158` 的 `default_omega`）。
        #     逐对代入 ⇒ **全部命中**才算"强加"。
        _om = m.get('omega_mode')
        _omx = m.get('omega_max_deg')
        _nv = m.get('nv')
        L.append('     ── ★★ 这个分布是"涌现"还是"参数化强加"？ ──')
        L.append('       互异 θ 值：%s'
                 % np.array2string(np.unique(th), precision=6, separator=', '))
        if _om == 'ladder' and _omx and _nv:
            _dth = float(_omx) / (float(_nv) - 1.0)
            L.append('       `omega_mode = **ladder**`、`omega_max_deg = %s`、`nv = %s`'
                     % (_omx, _nv))
            L.append('       ⇒ 定义（`windowB_lath.default_omega`, `windowB_lath.py:158`）：'
                     '**θ(a,b) = |a−b| · θ_max/(nv−1) = |a−b| · %.6f°**' % _dth)
            dev = np.array([abs(t_ - abs(a - b) * _dth)
                            for a, b, _, _, t_ in rows], float)
            L.append('       逐对代入公式：**最大偏差 = %.3e 度**（%d 对）'
                     % (dev.max(), len(dev)))
            if dev.max() < 1e-9:
                L.append('       ⇒ ❌ **全部命中 ⇒ 这个"取向差分布"是 `ladder` '
                         '参数化强加的，不是涌现的**')
                L.append('       ⇒ ★ 注意：**同变体的场（如 1/2/3/4）本应 θ = 0**'
                         '（同一变体 = 同一取向 = 没有晶界），而 ladder 给它们 '
                         '0.106/0.213/0.319°。')
            else:
                L.append('       ⇒ ⚠ 不是纯 ladder ⇒ 需要再查（偏差最大的那几对）')
                L.append('          %s' % [(a, b, round(t_, 6))
                                           for (a, b, _, _, t_), d_ in zip(rows, dev)
                                           if d_ > 1e-9][:5])
            L.append('       ⚠ 这**不是本轮新发现**：本仓 `R30_AUDIT_LEDGER §129` / `_r182` /')
            L.append('         `_r205` 第 7 条已登记为 **P1-45**（`ladder` 把 θ_max 均分 ⇒')
            L.append('         块内 γ 跨 M=2…20 变 **7.91 倍**；`--omega-mode perstep` 是它的开关，**默认关**）。')
            L.append('         `_r183` 也记了建模意图：「真实块内确实可能存在转动梯度」。')
            L.append('       ⇒ **C3 的"取向差分布"这一条：分布存在，但它是"给定的"、')
            L.append('         不是从晶界动力学里涌现的 ⇒ 不能算"实测分布"通过。**')
        L.append('     ⚠ 记账：`meta.json` 的 `omega_max_deg = %s` 是**变体选择**口径'
                 '（`--laths` 的 Ω 上界），**不是**晶界角度口径 ⇒ 两者分开报。'
                 % m.get('omega_max_deg'))
        # 逐对明细（前 12）
        L.append('     ── 明细（前 12 对）──')
        L.append('       %-6s %-6s %-8s %-8s %s' % ('场A', '场B', '变体A', '变体B', 'θ(度)'))
        for a, b, va, vb, t_ in rows[:12]:
            L.append('       %-6d %-6d %-8d %-8d %.3f' % (a, b, va, vb, t_))
        # ★ 负对照：随机打乱 场→变体 的映射
        rng = np.random.default_rng(20261002)
        flds = sorted({r[0] for r in rows} | {r[1] for r in rows})
        vlist = [vmap.get(f, -1) for f in flds]
        obs_med = float(np.median(th))
        null = []
        for _ in range(400):
            perm = rng.permutation(vlist)
            mp = dict(zip(flds, perm))
            t2 = [key_of(td, mp[r[0]], mp[r[1]]) for r in rows]
            t2 = [x for x in t2 if x is not None]
            if t2:
                null.append(float(np.median(t2)))
        null = np.array(null)
        L.append('     ── 负对照：打乱 场→变体 映射 ──')
        L.append('       实测 θ 中位 = %.3f°；打乱后中位 = %.3f°（5%%–95%% = %.3f–%.3f）'
                 % (obs_med, np.median(null), np.percentile(null, 5),
                    np.percentile(null, 95)))
        pv = float((null <= obs_med).mean())
        L.append('       ⇒ p = P(打乱 ≤ 实测) = **%.4f** ⇒ %s'
                 % (pv, '✅ 实测显著更低（相邻关系不是随机的）'
                    if pv < 0.05 else '⚠ 与"随机配对"不可区分'))
        L.append('')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_c3mis.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
