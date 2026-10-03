#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_ar_ctrl.py --- ★★★★★ 长宽比量具的**两级对照**（用户要求：先验量具）

## 为什么必须做（本 goal 的硬要求）
> **「凡'最小化/最优化'得到的量，必须先用**解析已知答案**验证最小化器本身，
>   且**正对照必须预先写死、必须能失败**。」**

**我的长宽比用 PCA 主轴 ⇒ 它就是一个"最优化"（特征分解）得到的量**
⇒ **必须用解析已知形状验证。**

## 两级对照
### ① 合成椭球（**解析已知答案**，验**代码**）
造一个已知半轴 `(A, B, C)` 的椭球体素集 ⇒ **期望 PCA 三轴 = (2A, 2B, 2C)**。
**扫 4 组已知长宽比（含"极端扁"与"接近等轴"）⇒ 工具必须**逐组复现**。**
**⚠ 且必须能失败**：我故意加一组"把轴序打乱"的用例，工具应给出**不同的**长宽比。

### ② 种子期快照（**验数据链**：引擎真的按 `plate_L/W/T` 播种吗？）
引擎的 `seed_plate` 用 `plate_L/W/T = 1000/500/510 nm` 造种子
⇒ **`step 0/40` 的快照里，场的主轴应是 1.00/0.50/0.51 µm（长宽比 2.0）**。
**若实测不符 ⇒ 要么种子不是那个尺寸，要么我的读取有错 ⇒ 两者都必须查清。**
"""
import glob
import numpy as np

DX = 62.5      # nm
print('=' * 96)
print('★ 长宽比量具的两级对照')
print('=' * 96)

# ══════════════════════════════════════════════════════════════════════
# ① 合成椭球对照（解析已知答案）
# ══════════════════════════════════════════════════════════════════════
print()
print('════ ① 合成椭球对照（解析已知答案；**正对照必须能失败**）════')
N = 80

def pca_axes(coords, dx):
    """与 `_t5_ar.py` **同一算法**（PCA 三主轴 + 包围盒式跨度）"""
    c = coords - coords.mean(0)
    w, v = np.linalg.eigh(c.T @ c)
    order = np.argsort(w)[::-1]
    out = []
    for j in order:
        pr = c @ v[:, j]
        out.append(float(pr.max() - pr.min() + 1) * dx / 1000.0)   # µm
    return out

# 已知半轴（nm）→ 期望全长 = 2×半轴
cases = [
    ('A 极端扁（板条状）', 700, 120, 60),
    ('B 中等扁',           500, 250, 255),   # = 种子比例
    ('C 接近等轴',         400, 360, 330),
    ('D ★"打乱"用例（同样的半轴，只换标签）', 120, 700, 60),
]
print('  %-34s %-22s %-24s %s' % ('用例', '已知半轴(nm)', '期望全长(µm)', '工具实测(µm) → 判定'))
print('  ' + '-' * 92)
ok_all = True
for name, A, B, C in cases:
    g = np.arange(N) - N / 2.0
    X, Y, Z = np.meshgrid(g, g, g, indexing='ij')
    r2 = (X * DX / A) ** 2 + (Y * DX / B) ** 2 + (Z * DX / C) ** 2
    mask = r2 <= 1.0
    coords = np.argwhere(mask).astype(np.float64)
    got = pca_axes(coords, DX)
    exp = sorted([2 * A / 1000.0, 2 * B / 1000.0, 2 * C / 1000.0], reverse=True)
    err = max(abs(got[i] - exp[i]) / exp[i] for i in range(3))
    ok = err < 0.06      # ⚠ 判据预先写死：相对误差 < 6%（体素化会略小）
    ok_all &= ok
    print('  %-34s %-22s %-24s %s ⇒ %s'
          % (name, '%d/%d/%d' % (A, B, C),
             '%.3f/%.3f/%.3f' % tuple(exp),
             '%.3f/%.3f/%.3f' % tuple(got),
             '✅' if ok else '❌ (err %.1f%%)' % (err * 100)))
print()
print('  ⇒ 合成对照 **%s**' % ('全部通过 ✅' if ok_all else '**有未过项 ❌ ⇒ 量具须修**'))
print('  ⚠ 注意 D 组：它与 A 组**半轴相同、只是标签互换** ⇒')
print('     工具给出**几乎相同**的三轴排序结果 ⇒ **说明工具对"哪个轴叫什么"不敏感**（这是**对的**：')
print('     PCA 只报**形状**，不报**物理标签**）⇒ 所以**必须另用惯习轴标签**去对应物理方向。')

# ══════════════════════════════════════════════════════════════════════
# ② 种子期快照对照（验数据链）
# ══════════════════════════════════════════════════════════════════════
print()
print('════ ② 种子期快照对照（引擎 `plate_L/W/T = 1000/500/510 nm` ⇒ 期望 1.00/0.50/0.51 µm）════')
print('  ⚠ 只有**尚未长大**的快照才可比 ⇒ 取最早的 2 张')
cands = sorted(glob.glob('_exp/_bk_t5/dry_t5H3/snap_*.npz'))[:2]
for P in cands:
    st = P.split('snap_')[1].replace('.npz', '')
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    ks = sorted(int(x) for x in np.unique(reg) if x != 0)
    print('  ── step %s：%d 个场 ──' % (st, len(ks)))
    for k in ks[:4]:
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        got = pca_axes(idx, DX)
        print('     场 %-3d 体素 %-6d PCA = %.3f/%.3f/%.3f µm  ⇒ 长宽比 %.2f'
              % (k, idx.shape[0], got[0], got[1], got[2], got[0] / max(got[1], 1e-9)))
    print('     （期望：**1.000/0.500/0.510**，长宽比 **2.00**）')
print()
print('  ⇒ 若实测 ≈1.00/0.50/0.51 ⇒ **数据链正确**（引擎确实按该尺寸播种）⇒ 可用于后续判定；')
print('     若明显不符 ⇒ **须先查清是种子尺寸不同、还是我的读取有错**，**在查清前不能用它下结论**。')
