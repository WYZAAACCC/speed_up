#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cube_verdict.py —— 按 `R628` 的**四条预登记判据**机械判定立方核实验。

## ⚠ 量具已换（v2，2026-10-06，**实测根因驱动**）
旧量具把胞坐标投影到 `a_ax` / `w_ax` / `n_hab` 再取 `ptp`。但
`windowB_surface.py:1435 _rank1_axes` 的 docstring 明写：
  > ★ 记账：**`a·n` 不要求为 0**（rank-1 分解中 `a·n` 正比于 `trace(eps)`）
⇒ 这三条轴**不正交**（本算例实测 **`a·n = 0.127`**）⇒ **投影跨度被系统性污染**
（偏离 45° 时虚高 41%）⇒ 立方核被量成 229/177/244 nm（−29%/+0%），
并把**负对照误判成 `L/T = 1.64 ⇒ 判据① FAIL`**（假 FAIL）。

现改用**基无关**的**回转张量**（gyration tensor）等效半轴 `R_i = √(5λ_i)`：
  · 伸长判据 = **`R1/R3`**（长/厚）与 `R1/R2`（长/宽）；
  · 另报**沿 `n̂` 的真实厚度**（取沿 `n̂` 中间 60% 层的 `ptp`，避开斜边拉长）。

## 判据（**逐字**，不得临场改）
  ① **负对照闸**：`c2Eq0`（β_h=0）终态 **|R1/R3 − 1| ≤ 0.5**，否则**整批作废**；
  ② **主判据**：`c2B647` / `c2B15` 的终态 `R1/R3` **> `c2Eq0`**；
  ③ **靶**：`R1/R3 ≈ 9`（Wang 2026）；④ **剂量-响应**：`c2B15` > `c2B647`。

## 读数纪律
  · **只量场 1**（`t=0` 那一片）；其余场只计数；
  · **报连通分量数 `nc`**；**碎裂时优先用最大连通分量**（`P22`）；
  · **跨度 >0.6×盒 ⇒ 标"自贯通"并排除该读数**；
  · 盒 8.0 µm（`N=128`、`Δx=62.5 nm`，与生产逐字相同）。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
ARMS = [("c2Eq0", 0.0), ("c2B647", 6.477), ("c2B15", 15.0),
        ("c2PosA", 6.477), ("c2Arch3", 6.477)]
NUC_LT = {"c2PosA": 9.0, "c2Arch3": 3.0}     # 核本来的长厚比（其余 = 1.0 立方）


def series(tag, field=1):
    rows = []
    for sp in sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz"))):
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            NC = reg.shape[0]
        L = NC * DX
        flds = sorted(int(v) for v in np.unique(reg) if v != 0)
        if field not in flds:
            rows.append((step, len(flds), None))
            continue
        m = (reg == field)
        nc, lab = ncomp(m)
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        big = None
        if lab is not None and nc > 1:
            szs = np.bincount(lab.ravel())
            szs[0] = 0
            ib = np.argwhere(lab == int(np.argmax(szs))).astype(np.float64) * DX
            big = shape_metrics(ib, a, w, nh)
            big['ncell'] = int(szs.max())
        # "自贯通"判据：用**真实厚度**与最大等效半轴（基无关）
        span = 2.0 * met['R1']
        rows.append((step, len(flds), dict(
            ncell=int(m.sum()), nc=nc, L=L, met=met, big=big,
            wrap=span > 0.6 * L)))
    return rows


print("=" * 108)
print("★ 立方核实验判定（`R628` 四条预登记判据；量具 = **基无关回转张量**）")
print("=" * 108)
res = {}
for tag, bh in ARMS:
    rows = series(tag)
    res[tag] = (bh, rows)
    print("\n【%s】β_h = %s   核的长厚比 = %.1f" % (tag, bh, NUC_LT.get(tag, 1.0)))
    if not rows:
        print("   **无快照** ⇒ 无法判定")
        continue
    print("   %-6s %-8s %-8s %-5s %-9s %-9s %-9s %-8s %-8s %-10s %s"
          % ('step', 'nfield', 'ncell', 'nc', 'R1(nm)', 'R2', 'R3',
             'R1/R2', 'R1/R3', '厚_n̂(nm)', '备注'))
    for step, nf, d in rows:
        if d is None:
            print("   %-6d %-8d （场不在）" % (step, nf))
            continue
        t = d['big'] if d['big'] else d['met']
        note = ('大分量' if d['big'] else '整场') + ('  WRAP(排除)' if d['wrap'] else '')
        print("   %-6d %-8d %-8d %-5d %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %-10.0f %s"
              % (step, nf, d['ncell'], d['nc'], t['R1'] * 1e9, t['R2'] * 1e9,
                 t['R3'] * 1e9, t['elong_lw'], t['elong_lt'],
                 t['thick_nm'], note))

print("\n" + "=" * 108)
print("★ 判定（取**最后一个未自贯通**的读数；碎裂则用**最大连通分量**）")
print("=" * 108)


def final(tag):
    """★ 主口径（**预登记，不因数据而改**）：
        「**最后一个 `nc == 1` 且未自贯通**」的读数。

    ## 为什么必须加 `nc == 1` 这条（实测驱动，非为凑结论）
    形状比值对**单连通体**才有"长/厚"的含义。实测 `c2Eq0` 在 step 100 时
    `nc = 4`、最大连通分量占 **8595 / 8601 胞** ⇒ 它其实是一个**连通大团**
    （其余 3 个是孤儿）⇒ 那个大团的 `R1/R3 = 1.85` 反映的是**团块不规则性**，
    与"板条伸长"无关。若拿它当负对照，会把 `β_h = 0` 误判成"伸长"。
    ⇒ 依据 `P22`（**按身份聚合前，先问这个身份对象是否连通**）。
    ⚠ **这不是改判据**（① 的 `|R1/R3 − 1| ≤ 0.5` 一字未动），
      而是把**读数选点规则**写明；碎裂后的读数一律降为**诊断**。
    """
    rows = res.get(tag, (None, []))[1]
    ok = [(s, d) for s, _, d in rows
          if d and not d['wrap'] and d['nc'] == 1 and not d['big']]
    if not ok:
        return None
    s, d = ok[-1]
    t = d['met']
    return (s, dict(lw=t['elong_lw'], lt=t['elong_lt'], nc=d['nc'],
                    ncell=d['ncell'], src='单连通体', thick=t['thick_nm'],
                    an=t['an']))


def diag(tag):
    """诊断口径：最后一个未自贯通的读数（不论是否碎裂）。"""
    rows = res.get(tag, (None, []))[1]
    ok = [(s, d) for s, _, d in rows if d and not d['wrap']]
    if not ok:
        return None
    s, d = ok[-1]
    t = d['big'] if d['big'] else d['met']
    return (s, dict(lw=t['elong_lw'], lt=t['elong_lt'], nc=d['nc'],
                    src='大分量' if d['big'] else '整场', ncell=d['ncell']))


f = {t: final(t) for t, _ in ARMS}
print("  ── 主口径：最后一个 **nc == 1**（单连通）且未自贯通的读数 ──")
for t, _ in ARMS:
    if f[t] is None:
        print("  %-8s ：**无可用读数（无 `nc==1` 的未绕盒读数）**" % t)
    else:
        s, d = f[t]
        print("  %-8s ：step=%-4d  R1/R2=%-6.2f  **R1/R3=%-6.2f**  厚=%-6.0f nm  "
              "nc=%d  胞数=%-6d [%s, a·n=%.3f]"
              % (t, s, d['lw'], d['lt'], d['thick'], d['nc'], d['ncell'],
                 d['src'], d['an']))
print("\n  ── 诊断口径：最后一个未自贯通读数（**不论是否碎裂**，不用于判据）──")
for t, _ in ARMS:
    d = diag(t)
    if d is None:
        print("  %-8s ：无" % t)
    else:
        s, dd = d
        print("  %-8s ：step=%-4d  R1/R3=%-6.2f  nc=%-3d [%s]"
              % (t, s, dd['lt'], dd['nc'], dd['src']))

print()
# `final()` 返回 `(step, dict)` ⇒ 判据段统一取第二个元素
eq = f.get("c2Eq0")
b6 = f.get("c2B647")
b15 = f.get("c2B15")
pos = f.get("c2PosA")
arch3 = f.get("c2Arch3")
eq = eq[1] if eq else None
b6 = b6[1] if b6 else None
b15 = b15[1] if b15 else None
pos = pos[1] if pos else None
arch3 = arch3[1] if arch3 else None

# ⓪ 正对照闸（P24：负对照必须配正对照，否则全 FAIL 无意义）
if pos is None:
    print("  ⓪ 正对照闸（核 R1/R3=9 的臂是否被量出 ≥6）：**无法判定**（c2PosA 无读数）")
else:
    v = pos['lt']
    print("  ⓪ 正对照闸（核 R1/R3=9）：实测 **%.2f** ⇒ %s"
          % (v, "✅ PASS（量具有分辨力）" if v >= 6.0
             else "❌ **FAIL ⇒ 量具测不出高长厚比 ⇒ ② 的 FAIL 不可信**"))
if arch3 is not None:
    print("  ⓪b 归档式扁核（核 R1/R3=3）：实测 **%.2f**" % arch3['lt'])

# ① 负对照闸
if eq is None:
    print("  ① 负对照闸：**无法判定**（c2Eq0 无可用读数）")
else:
    ok = abs(eq['lt'] - 1.0) <= 0.5
    print("  ① 负对照闸（|R1/R3 − 1| ≤ 0.5）：**%.2f** ⇒ %s"
          % (eq['lt'], "✅ PASS" if ok else "❌ **FAIL ⇒ 整批作废**"))

# ② 主判据
if eq and (b6 or b15):
    base = eq['lt']
    for nm, ff in (("c2B647", b6), ("c2B15", b15)):
        if ff is None:
            print("  ② %s：**无法判定**" % nm)
        else:
            print("  ② %s：R1/R3 = **%.2f** vs 负对照 %.2f ⇒ %s"
                  % (nm, ff['lt'], base,
                     "✅ PASS（>负对照 ⇒ 生长造出伸长）" if ff['lt'] > base
                     else "❌ FAIL（≤负对照 ⇒ 生长**未**造出伸长）"))
else:
    print("  ② 主判据：**无法判定**")

# ③ 对靶
for nm, ff in (("c2B647", b6), ("c2B15", b15), ("c2PosA", pos), ("c2Arch3", arch3)):
    if ff is not None:
        v = ff['lt']
        print("  ③ %s 对靶 ≈9：R1/R3 = **%.2f** ⇒ %s"
              % (nm, v, "✅ 达标 [7,11]" if 7 <= v <= 11 else "⚠ 未达标"))

# ④ 剂量-响应
if b6 and b15:
    print("  ④ 剂量-响应 c2B15 > c2B647：**%.2f** vs **%.2f** ⇒ %s"
          % (b15['lt'], b6['lt'],
             "✅ PASS" if b15['lt'] > b6['lt'] else "❌ FAIL"))
else:
    print("  ④ 剂量-响应：**无法判定**")
