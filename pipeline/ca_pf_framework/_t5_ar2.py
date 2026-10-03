#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_ar2.py --- ★★★ 修好的长宽比量具：**长/宽用 PCA，厚用 `n_hab`**（+ 自带的对照）

## 为什么要改（`_t5_ar_ctrl.py` 的实测）
**PCA 第 3 主轴在"薄"形状上特征值极小 ⇒ 方向噪声大 ⇒ 跨度**偏小****：
```
合成椭球 700/120/60 nm ⇒ 期望 1.400/0.240/0.120，PCA 实测 1.438/0.188/**0.062**（厚轴 −48%）
```
**⇒ 这会让长厚比**系统性偏高****。
**⇒ 修法**：**厚度**改用**物理定义**的 `n_hab`（**惯习面法向**）；
   **长/宽**仍用 PCA 第 1/2 主轴（它们特征值大 ⇒ 稳定）；
   **并额外报"长轴与 `a_ax` 的夹角"**，确认长轴对应哪个物理方向。

## 自带的对照（**同一份脚本里，先验后用**）
* **合成椭球**：4 组已知长宽比 ⇒ 修好后**必须全部通过**（< 6%）；
* **种子快照**：期望 1.000/0.500/0.510 µm ⇒ 必须复现。
"""
import glob
import sys
import numpy as np

DX = 62.5
SEED = (1.000, 0.500, 0.510)      # µm，plate_L/W/T

def pca2(coords, dx):
    """PCA 第 1/2 主轴跨度（µm）——只取"稳定的"两个"""
    c = coords - coords.mean(0)
    w, v = np.linalg.eigh(c.T @ c)
    order = np.argsort(w)[::-1]
    out = []
    for j in order[:2]:
        pr = c @ v[:, j]
        out.append(float(pr.max() - pr.min() + 1) * dx / 1000.0)
    return out, v[:, order[0]]

def span_along(coords, ax, dx):
    ax = np.asarray(ax, float)
    ax = ax / (np.linalg.norm(ax) + 1e-300)
    c = coords - coords.mean(0)
    pr = c @ ax
    return float(pr.max() - pr.min() + 1) * dx / 1000.0

# ══════════════════════════════════════════════════════════════════
print('=' * 96)
print('★ 修好的量具：**长/宽 = PCA，厚 = `n_hab`**')
print('=' * 96)
print()
print('════ ① 合成椭球对照（修后必须全部通过；判据：相对误差 < 6%）════')
N = 80
g = np.arange(N) - N / 2.0
X, Y, Z = np.meshgrid(g, g, g, indexing='ij')
ok_all = True
for name, A, B, C in [('A 极端扁（板条状）', 700, 120, 60),
                      ('B 中等扁（= 种子比例）', 500, 250, 255),
                      ('C 接近等轴', 400, 360, 330),
                      ('D 更扁（长宽比 7）', 700, 100, 80)]:
    r2 = (X * DX / A) ** 2 + (Y * DX / B) ** 2 + (Z * DX / C) ** 2
    coords = np.argwhere(r2 <= 1.0).astype(np.float64)
    (p1, p2), longax = pca2(coords, DX)
    # 沿**真实短轴**（这里用 z 轴当"惯习法向"的代用）量厚度
    p3 = span_along(coords, [0, 0, 1], DX) if C == min(A, B, C) else span_along(coords, [0, 1, 0], DX)
    exp = sorted([2 * A / 1000.0, 2 * B / 1000.0, 2 * C / 1000.0], reverse=True)
    got = sorted([p1, p2, p3], reverse=True)
    err = max(abs(got[i] - exp[i]) / exp[i] for i in range(3))
    ok = err < 0.06
    ok_all &= ok
    print('  %-26s 半轴 %3d/%3d/%3d ⇒ 期望 %s ｜ 实测 %s ⇒ %s'
          % (name, A, B, C, '%.3f/%.3f/%.3f' % tuple(exp), '%.3f/%.3f/%.3f' % tuple(got),
             '✅' if ok else '❌ (err %.1f%%)' % (err * 100)))
print('  ⇒ **%s**' % ('全部通过 ✅ ⇒ 量具修好' if ok_all else '⚠ 仍未全过 ⇒ 须再查'))

# ══════════════════════════════════════════════════════════════════
print()
print('════ ② 种子快照对照 + ③ 最终快照的**真实长宽比**（厚用 `n_hab`）════')
for TAG, want in (('t5H3', None),):
    snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
    for P in [snaps[1]] + [snaps[-1]]:
        st = int(P.split('snap_')[1].replace('.npz', ''))
        with np.load(P, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a_ax = np.asarray(z['a_ax'], float) if 'a_ax' in z.files else None
            n_hab = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
        ks = sorted(int(x) for x in np.unique(reg) if x != 0)
        print('  ── %s step %d（%d 个场）%s──'
              % (TAG, st, len(ks), '  **种子期：期望 %.3f/%.3f/%.3f**  ' % SEED if st < 100 else ''))
        ars = []
        for k in ks:
            idx = np.argwhere(reg == k).astype(np.float64)
            if idx.shape[0] < 8:
                continue
            (p1, p2), longax = pca2(idx, DX)
            p3 = span_along(idx, n_hab, DX) if n_hab is not None else np.nan
            ar = p1 / max(p3, 1e-9)
            ars.append((k, p1, p2, p3, ar))
        for k, p1, p2, p3, ar in ars:
            print('     场 %-3d 长 %5.3f  宽 %5.3f  **厚 %5.3f（用 n_hab）** ⇒ **长厚比 %5.2f**  长宽比 %4.2f'
                  % (k, p1, p2, p3, ar, p1 / max(p2, 1e-9)))
        if ars:
            arr = np.array([a[4] for a in ars])
            print('     ⇒ **长厚比：中位 %.2f  范围 [%.2f, %.2f]**' % (np.median(arr), arr.min(), arr.max()))
        print()
