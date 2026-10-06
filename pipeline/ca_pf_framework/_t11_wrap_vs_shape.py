#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_wrap_vs_shape.py —— 判别 `t5AD_700/1000` 的"长宽比掉到 1.25"是**绕盒假象**还是**真形态**。

## 判据（决定性）
  对每个场、沿每条主轴：
    * **朴素跨度** `span_naive = (max − min + 1)·Δx`（就是现有量具用的口径）；
    * **周期最小弧跨度** `span_per = L − max_gap`，其中 `max_gap` 是该轴上坐标排序后的最大空隙
      （**含环绕空隙**：`L − x_max + x_min`）。
  若 `span_naive ≫ span_per` ⇒ 该场**跨盒自贯通** ⇒ 朴素口径把它读成"长条"或"等轴"都是**假象**。

## 为什么要它
  `R625 §4.6.9` 实测 `t5AD_700/1000` 的长宽比中位掉到 **1.25–1.27**（而 `5.0` 臂是 4.72）。
  两种解释：① 真形态退化；② **核长 4.48 µm 在 5 µm 盒里绕盒** ⇒ PCA 口径失效。
  ⇒ **必须分开**（用户 ⑧ 明确要求监控"周期边界有没有正确发挥作用"）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
DX = 62.5e-9


def spans_naive(x, L):
    return x.max() - x.min() + DX


def spans_periodic(x, L):
    """周期最小包围弧长 = L −（最大空隙，含环绕空隙）。"""
    s = np.sort(x)
    if s.size < 2:
        return DX
    gaps = np.diff(s)
    wrap_gap = L - (s[-1] - s[0])
    return L - max(gaps.max(), wrap_gap)


def analyze(d, tag, el):
    sn = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
    if not sn:
        return None
    with np.load(sn[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        N = reg.shape[0]
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    L = N * DX
    out = []
    for k in sorted(int(v) for v in np.unique(reg) if v != 0):
        idx = np.argwhere(reg == k).astype(np.float64) * DX
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        row = {'k': k, 'ncell': idx.shape[0]}
        sp_n, sp_p = [], []
        for j in range(3):
            proj = idx @ v[:, o[j]]
            sp_n.append(spans_naive(proj, L))
            sp_p.append(spans_periodic(proj, L))
        # 用周期口径算长宽比（主轴两轴）
        srt = np.argsort(sp_p)[::-1]
        row['ar_naive'] = sp_n[0] / max(sp_n[1], 1e-30)
        row['ar_per'] = sp_p[srt[0]] / max(sp_p[srt[1]], 1e-30)
        row['selfspan'] = bool(sp_n[0] > 0.6 * L)
        out.append(row)
    return dict(tag=tag, el=el, L=L, rows=out)


ARMS = [("t5AB_B", "dry_t5AB_B", 3.75), ("t5AD_500", "dry_t5AD_500", 5.0),
        ("t5AD_700", "dry_t5AD_700", 7.0), ("t5AD_1000", "dry_t5AD_1000", 10.0),
        ("t5AB_A", "dry_t5AB_A", None)]
res = []
for tag, sub, el in ARMS:
    r = analyze(os.path.join(ROOT, "_exp", "_bk_t5", sub), tag, el)
    if r:
        res.append(r)

print("=" * 108)
print("绕盒 vs 真形态：朴素包围盒跨度  vs  周期最小弧跨度")
print("=" * 108)
print("  %-11s %-6s %-5s %-6s %-10s %-10s %-8s %-9s"
      % ('臂', 'elong', '盒L/um', '场数', 'β比(朴素)', 'β比(周期)', '自贯通', '结论'))
print("  " + "-" * 104)
for r in res:
    if not r['rows']:
        continue
    an = np.median([x['ar_naive'] for x in r['rows']])
    ap = np.median([x['ar_per'] for x in r['rows']])
    ns = sum(1 for x in r['rows'] if x['selfspan'])
    verdict = ('**绕盒假象**' if abs(an - ap) > 0.15 * max(an, ap) or ns > 0
               else '真形态')
    print("  %-11s %-6s %-5.1f %-6d %-10.2f %-10.2f %-8s %-9s"
          % (r['tag'], r['el'], r['L'] * 1e6, len(r['rows']), an, ap,
             "%d/%d" % (ns, len(r['rows'])), verdict))

print("\n" + "=" * 108)
print("★ 判读规则（预登记）")
print("=" * 108)
print("""  · 若某臂「自贯通」场数 > 0 且 朴素≠周期 ⇒ **该臂的朴素长宽比不可用**（绕盒假象）
  · 若两口径接近且无自贯通 ⇒ 朴素口径可用，长宽比是**真形态**
  · ⚠ 用户 ⑧ 的监控项「板条长出盒子外时周期边界有没有正确发挥作用」
    在本量具上的投影就是这一列「自贯通」。""")
for r in res:
    if r['rows'] and r['el'] == 7.0:
        print(f"\n  【{r['tag']}】逐场（前 8 个）：")
        for x in r['rows'][:8]:
            print("    场 %-3d 胞数 %-6d  β比 朴素 %6.2f  周期 %6.2f  自贯通 %s"
                  % (x['k'], x['ncell'], x['ar_naive'], x['ar_per'],
                     '是' if x['selfspan'] else '否'))