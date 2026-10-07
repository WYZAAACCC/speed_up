#!/usr/bin/env python3
"""_r449_f2adjudicate.py —— ★★ **C22b 的 +12.89% 是谁的错：量具还是我的解析预期？**

## 背景
`§201` 补的 `nf2` 自证里：
* C22a（正对照，`f2_faces > 0`）**PASS**（429）
* **C22b（定量，`f2_faces == n_y·n_z`）FAIL**：实测 **429** vs 我的解析 **380**（+12.89%）
* C22c（分辨力，同变体 ⇒ `f2_faces == 0`）**PASS**
* C22d（负对照，分开 ⇒ 0）**PASS**

**⇒ 先别改判据**（把判据放宽去迁就预期是本仓库明令禁止的）。
**先用一个独立方法把"真值"数出来**：
  直接对 `region` 做 `(reg==A) & (roll(reg)==B)` 的**逐轴逐向**计数 ——
  与 `_bk_measure` 用的是**不同的一段代码**（我在这里手写）。
再与 `_bk_measure.f2_faces` 和我的解析式比。
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import _bk_measure as BM       # noqa: E402

N, dx = 64, 62.5e-9
c0 = np.array([N / 2.0, N / 2.0, N / 2.0]) * dx
T = 250e-9
W, AL = 320e-9, 1200e-9
_d = 4 * T
_amx = dict(n=np.array([1.0, 0, 0]), w=np.array([0.0, 0, 1.0]),
            a=np.array([0.0, 1.0, 0.0]))


def build(fb):
    reg = np.zeros((N, N, N), np.int8)
    reg[BM._synth_slab(N, dx, c0 + np.array([-_d / 2, 0.0, 0.0]),
                       dict(n=_d / 2, w=W, a=AL), _amx)] = 1
    reg[BM._synth_slab(N, dx, c0 + np.array([+_d / 2, 0.0, 0.0]),
                       dict(n=_d / 2, w=W, a=AL), _amx)] = fb
    return reg


reg = build(4)
vmap = {1: 1, 2: 1, 3: 1, 4: 3, 5: 3, 6: 3}
P = print
P('=' * 88)
P('_r449 —— C22b 的裁决：谁错了？')
P('=' * 88)

# ---- 1) 独立数：A-B 逐轴逐向的邻接对数（**手写，不复用 `_bk_measure`**）
P('\n[1] 独立计数（手写 `np.roll`，逐轴逐向）')
tot = 0
for ax in (0, 1, 2):
    for s in (1, -1):
        nb = np.roll(reg, s, axis=ax)
        c = int(np.count_nonzero((reg == 1) & (nb == 4)))
        tot += c
        P('    轴%d 向%+d ：场1→场4 邻接 = %d' % (ax, s, c))
P('    ⇒ 独立计数合计（**双向都算**）= **%d** ⇒ 除以 2 = **%d**'
  % (tot, tot // 2))

# ---- 2) `_bk_measure` 的值
m = BM.measure_state(reg, dx, np.array([1.0, 0, 0]), np.array([0.0, 0, 1.0]),
                     np.array([0.0, 1.0, 0.0]), vmap)
P('\n[2] `_bk_measure.f2_faces` = **%d**；`f3_faces` = %d'
  % (m['f2_faces'], m['f3_faces']))

# ---- 3) 我的解析式
iy = np.abs((np.arange(N) + 0.5) * dx - c0[1]) <= W
iz = np.abs((np.arange(N) + 0.5) * dx - c0[2]) <= AL
P('\n[3] 我的解析式 `n_y · n_z`：n_y = %d，n_z = %d ⇒ **%d**'
  % (int(iy.sum()), int(iz.sum()), int(iy.sum()) * int(iz.sum())))
P('    各轴上的占据胞数（**直接量**）：')
for ax, nm in ((0, 'x'), (1, 'y'), (2, 'z')):
    occ = np.zeros(N, bool)
    idx = np.argwhere(reg == 1)
    occ[idx[:, ax]] = True
    P('      场1 在 %s 轴占 %d 个胞（%d..%d）'
      % (nm, int(occ.sum()), int(np.argmax(occ)), int(N - 1 - np.argmax(occ[::-1]))))

# ---- 4) 裁决
P('\n' + '=' * 88)
P('[裁决]')
P('  独立计数 = %d（双向） ⇒ 单向 = %d' % (tot, tot // 2))
P('  `_bk_measure.f2_faces` = %d' % m['f2_faces'])
P('  我的解析式 = %d' % (int(iy.sum()) * int(iz.sum())))
if m['f2_faces'] == tot // 2:
    P('  ⇒ **量具对**：`f2_faces == 独立单向计数** ⇒ **我的解析式写错了**')
elif m['f2_faces'] == int(iy.sum()) * int(iz.sum()):
    P('  ⇒ **我的解析式对**：`f2_faces == n_y·n_z` ⇒ **量具多算了**（要查）')
else:
    P('  ⇒ **两者都不等** ⇒ 三方不一致，须继续查')
P('=' * 88)
