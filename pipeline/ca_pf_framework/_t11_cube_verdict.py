#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cube_verdict.py —— 按 `R628` 的**四条预登记判据**机械判定立方核实验。

判据（**逐字**，不得临场改）：
  ① 负对照闸：`c2Eq0`（β_h=0）终态**长厚比 ≈1**（判据：|L/T−1| ≤ 0.5），否则**整批作废**；
  ② 主判据：`c2B647` / `c2B15` 的**终态长厚比 > `c2Eq0`**（⇒ 生长层造出伸长）；
  ③ 靶：长厚比 **≈9**（Wang 2026；判据：落在 [7, 11] 记为"达标"）；
  ④ 剂量-响应：`c2B15` > `c2B647`。

读数纪律（必须随结论一起报）：
  · **只量场 1**（t=0 那一片）；其余场只计数；
  · **逐场报连通分量数 `nc`**（碎裂 ⇒ 跨度量的是碎片云包络，须标记）；
  · **跨度 >0.6×盒 ⇒ 标"自贯通"并排除该读数**（`R625 §4.6.10` 的教训）；
  · 盒 8.0 µm（`N=128`、`Δx=62.5 nm`，与生产逐字相同）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
ARMS = [("c2Eq0", 0.0), ("c2B647", 6.477), ("c2B15", 15.0),
        ("c2PosA", 6.477), ("c2Arch3", 6.477)]
# 各臂的核几何（用于打印"核本来的 L/T"）：默认立方 250³
NUC_LT = {"c2PosA": 9.0, "c2Arch3": 3.0}


def ncomp(mask):
    try:
        from scipy import ndimage
        _, n = ndimage.label(mask, structure=np.ones((3, 3, 3)))
        return int(n)
    except Exception:                                  # noqa: BLE001
        return -1


def series(tag):
    rows = []
    for sp in sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz"))):
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            NC = reg.shape[0]
        L = NC * DX
        flds = sorted(int(v) for v in np.unique(reg) if v != 0)
        if 1 not in flds:
            rows.append((step, len(flds), None))
            continue
        m = (reg == 1)
        idx = np.argwhere(m).astype(np.float64) * DX
        sa, sw, sn = (float(np.ptp(idx @ a)), float(np.ptp(idx @ w)),
                      float(np.ptp(idx @ nh)))
        rows.append((step, len(flds), dict(
            ncell=int(m.sum()), nc=ncomp(m), sa=sa, sw=sw, sn=sn,
            ar_lw=sa / max(sw, 1e-30), ar_lt=sa / max(sn, 1e-30),
            wrap=max(sa, sw, sn) > 0.6 * L, L=L)))
    return rows


print("=" * 106)
print("★ 立方核实验判定（`R628` 四条预登记判据）")
print("=" * 106)
res = {}
for tag, bh in ARMS:
    rows = series(tag)
    res[tag] = (bh, rows)
    print("\n【%s】β_h = %s" % (tag, bh))
    if not rows:
        print("   **无快照** ⇒ 无法判定")
        continue
    print("   %-6s %-8s %-8s %-6s %-9s %-9s %-9s %-8s %-8s %s"
          % ('step', 'nfield', 'ncell1', 'nc', 'span_a_nm', 'span_w_nm',
             'span_n_nm', 'L/W', 'L/T', 'wrap'))
    for step, nf, d in rows:
        if d is None:
            print("   %-6d %-8d (field1 absent)" % (step, nf))
            continue
        print("   %-6d %-8d %-8d %-6s %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %s"
              % (step, nf, d['ncell'], d['nc'] if d['nc'] > 0 else '?',
                 d['sa'] * 1e9, d['sw'] * 1e9, d['sn'] * 1e9,
                 d['ar_lw'], d['ar_lt'], 'WRAP(排除)' if d['wrap'] else ''))

print("\n" + "=" * 106)
print("★ 判定（用**最后一个未自贯通**的读数；若全被排除 ⇒ 无法判定）")
print("=" * 106)


def final(tag):
    rows = res.get(tag, (None, []))[1]
    ok = [(s, d) for s, _, d in rows if d and not d['wrap']]
    return ok[-1] if ok else None


f = {t: final(t) for t, _ in ARMS}
for t, _ in ARMS:
    if f[t] is None:
        print("  %-8s ：**无可用读数（全部自贯通或无快照）**" % t)
    else:
        s, d = f[t]
        print("  %-8s ：step=%-4d  L/W=%-6.2f  **L/T=%-6.2f**  nc=%-3s  胞数=%d"
              % (t, s, d['ar_lw'], d['ar_lt'], d['nc'], d['ncell']))

print()
eq = f.get("c2Eq0")
b6 = f.get("c2B647")
b15 = f.get("c2B15")
pos = f.get("c2PosA")
arch3 = f.get("c2Arch3")

# ★ 正对照闸（新增，`P24`）：核 L/T = 9 的臂 ⇒ 量具**必须**给出 ≈9
if pos is None:
    print("  ⓪ 正对照闸（核 L/T=9 的臂是否被量出 ≈9）：**无法判定**（c2PosA 无读数）")
else:
    v = pos[1]['ar_lt']
    print("  ⓪ 正对照闸（核 L/T=9）：实测 L/T = %.2f ⇒ %s"
          % (v, "✅ PASS（量具有分辨力）" if v >= 6.0
             else "❌ **FAIL ⇒ 量具测不出高长厚比，② 的 FAIL 不可信**"))
if arch3 is not None:
    print("  ⓪b 归档式扁核（核 L/T=3）：实测 L/T = %.2f" % arch3[1]['ar_lt'])

# 判据①
if eq is None:
    print("  ① 负对照闸：**无法判定**（c2Eq0 无可用读数）")
else:
    ok = abs(eq[1]['ar_lt'] - 1.0) <= 0.5
    print("  ① 负对照闸（|L/T−1| ≤ 0.5）：L/T = %.2f ⇒ %s"
          % (eq[1]['ar_lt'], "✅ PASS" if ok else "❌ **FAIL ⇒ 整批作废**"))
# 判据②
if eq and (b6 or b15):
    base = eq[1]['ar_lt']
    for nm, ff in (("c2B647", b6), ("c2B15", b15)):
        if ff is None:
            print("  ② %s：**无法判定**" % nm)
        else:
            print("  ② %s：L/T = %.2f vs 负对照 %.2f ⇒ %s"
                  % (nm, ff[1]['ar_lt'], base,
                     "✅ PASS（>负对照 ⇒ 生长造出伸长）" if ff[1]['ar_lt'] > base
                     else "❌ FAIL（≤负对照 ⇒ 生长**未**造出伸长）"))
else:
    print("  ② 主判据：**无法判定**")
# 判据③
for nm, ff in (("c2B647", b6), ("c2B15", b15), ("c2PosA", pos), ("c2Arch3", arch3)):
    if ff is not None:
        v = ff[1]['ar_lt']
        print("  ③ %s 对靶 ≈9：L/T = %.2f ⇒ %s"
              % (nm, v, "✅ 达标 [7,11]" if 7 <= v <= 11 else "⚠ 未达标"))
# 判据④
if b6 and b15:
    print("  ④ 剂量-响应 c2B15 > c2B647：%.2f vs %.2f ⇒ %s"
          % (b15[1]['ar_lt'], b6[1]['ar_lt'],
             "✅ PASS" if b15[1]['ar_lt'] > b6[1]['ar_lt'] else "❌ FAIL"))
else:
    print("  ④ 剂量-响应：**无法判定**")
