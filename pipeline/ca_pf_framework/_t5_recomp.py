#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_recomp.py --- ★★★★★ 按**连通分量**重测长/宽/厚/长宽比（修正量具）

## 为什么要重测（**同一个错我犯了两次**）
`region` 是**场/变体标签**，**不保证连通**（我在 §151 就写过这句，但后来做形状测量时又默认它连通）。
实测（`_t5_conn.py`）：
* **老场（2–9）**：最大分量占 **92–100%** ⇒ 基本连通（"碎"是 6-连通太严的假象）；
* **新场（10–17）**：最大分量只占 **28–70%** ⇒ **确实被切成几大块**。
**⇒ 所以"按场测形状"对**新场**是错的** —— 应**按分量**测。

## 本脚本（**口径写清**）
1. **连通分解**：**26-连通**（含面/棱/角相邻）—— 对实心形状是物理上更合理的判据
   （体素级 `argmin` 抖动造成的"棋盘缝隙"在 26-连通下会自动愈合）；
2. **只测体素 ≥ `MINV`（默认 100）的分量**（太小的片段无形状可言）；
3. **每个分量**测：长 = PCA-1 跨度 · 宽 = PCA-2 · 厚 = 沿 `n_hab`；
   **长宽比 = 长/宽**，**长厚比 = 长/厚**；并报**实心度**（体积/包围盒）；
4. **汇总**：分量的中位/范围；并按**所属场是老（2–9）还是新（≥10）**分组对比。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

DX = 62.5
VOX = DX ** 3 * 1e-9
MINV = int(sys.argv[2]) if len(sys.argv) > 2 else 100
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
S26 = ndimage.generate_binary_structure(3, 3)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
if nh is not None:
    nh = nh / (np.linalg.norm(nh) + 1e-300)

rows = []
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    lab, nc = ndimage.label(m, structure=S26)
    for ci in range(1, nc + 1):
        idx = np.argwhere(lab == ci).astype(np.float64)
        if idx.shape[0] < MINV:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000.0
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000.0
        if nh is not None:
            T = float((c @ nh).max() - (c @ nh).min() + 1) * DX / 1000.0
        else:
            T = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        bb = float(np.prod(idx.max(0) - idx.min(0) + 1)) * VOX
        rows.append(dict(f=k, n=idx.shape[0], L=L, W=W, T=T,
                         ar=L / max(W, 1e-9), lt=L / max(T, 1e-9),
                         sol=(idx.shape[0] * VOX) / max(bb, 1e-12)))

print('=' * 104)
print('★ %s step %d：**按连通分量**重测（26-连通，只取 ≥%d 体素的分量）' % (TAG, st, MINV))
print('=' * 104)
if not rows:
    print('  （没有满足阈值的分量）'); sys.exit(0)
print('  %-5s %-6s %-8s %-8s %-8s %-9s %-9s %s'
      % ('场', '体素', '长', '宽', '厚', '**长宽比**', '长厚比', '实心度'))
for r in sorted(rows, key=lambda r: (r['f'], -r['n'])):
    grp = '新' if r['f'] >= 10 else '老'
    print('  %-5s %-6d %-8.3f %-8.3f %-8.3f %-9.2f %-9.2f %.2f'
          % ('%d(%s)' % (r['f'], grp), r['n'], r['L'], r['W'], r['T'], r['ar'], r['lt'], r['sol']))

ar = np.array([r['ar'] for r in rows]); lt = np.array([r['lt'] for r in rows])
print()
print('  ── 全部分量（n=%d）──' % len(rows))
print('     长宽比 中位 **%.2f** · 范围 [%.2f, %.2f]' % (np.median(ar), ar.min(), ar.max()))
print('     长厚比 中位 **%.2f** · 范围 [%.2f, %.2f]' % (np.median(lt), lt.min(), lt.max()))
for name, lo, hi in (('<3（不像板条）', 0, 3), ('3–5', 3, 5),
                     ('**5–20（真实区间）**', 5, 20), ('>20', 20, 1e9)):
    mm = (ar >= lo) & (ar < hi)
    print('     长宽比 %-20s **%2d 个（%.0f%%）**' % (name, mm.sum(), 100.0 * mm.sum() / len(ar)))

print()
print('  ── ★ 老场 vs 新场（按分量）──')
print('     %-6s %-8s %-12s %-12s %s' % ('组', '分量数', '长宽比中位', '长厚比中位', '长宽比 ≥5 的比例'))
for name, f in (('老场', lambda x: 2 <= x <= 9), ('新场', lambda x: x >= 10)):
    sub = [r for r in rows if f(r['f'])]
    if not sub:
        print('     %-6s （无）' % name); continue
    a = np.array([r['ar'] for r in sub]); l = np.array([r['lt'] for r in sub])
    print('     %-6s %-8d %-12.2f %-12.2f **%.0f%%**'
          % (name, len(sub), np.median(a), np.median(l), 100.0 * (a >= 5).mean()))
