#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r549_membudget.py —— **任务(5) 的内存可行性包线**（实测，不是算出来的）。

## 为什么必须实测
任务(5) 要求"使板条与块**长满整个盒子**"（C5），且"在本机**内存**与可接受用时之内"。
而引擎的状态是**稠密**的：`phi` 形状 `(nreg, N, N, N)`，`nreg = nv + 1`
（`windowB_surface.py:920`，**dtype 是 float64 ⇒ 8 B/胞**）。

⇒ 先算一笔账（**这是待验证的解析式，不是结论**）：
    `phi` = `nv · N³ · 8` 字节
    * 4 µm 盒（N=64）、填 30%：单根 0.255 µm³ ⇒ 需 **75 根** ⇒ `phi` ≈ 75·64³·8 = **157 MB** ✅
    * 10 µm 盒（N=160）、填 30%：需 **1176 根** ⇒ `phi` ≈ 1176·160³·8 = **38.6 GB** ❌ **远超 22 GB**
    ⇒ **【推理】C5 在 10 µm 盒上可能根本放不下** —— 必须实测确认。

## 本量具做三件事
1. **实测**每个 (N, nv) 组合的真实 RSS 增量（`LevelSetMulti` 构造前后）。
2. **把实测值与解析式 `a·nv·N³ + b` 拟合**，给出每胞字节数 `a`（应当 ≈ 8 或更高）。
   ⇒ 这是"用解析已知答案验证量具"：**若拟合出的 `a` 与代码里的 dtype 对不上，先怀疑量具**。
3. 用拟合式**外推**出 22 GB 预算下的可行 `(N, nv)` 包线，并**回代**几个任务(5) 候选配置。

## 判据（先写死）
* **M1**：`a` 落在 **[8, 40] B/胞**（`phi` 是 8 B；其余数组与副本会把有效值抬高）。
  超出 ⇒ **量具或模型有问题**，不得直接外推。
* **M2**：拟合式对**留出的一个测点**（hold-out）预测误差 ≤ **30%**。
* **M3**：给出 22 GB 下 **4 µm 与 10 µm 盒各自能容纳的最大 `nv`**。
"""
import gc
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

try:
    import psutil
    _PROC = psutil.Process(os.getpid())
    def rss_mb():
        return _PROC.memory_info().rss / 2**20
except Exception:                                               # noqa: BLE001
    def rss_mb():
        with open('/proc/self/statm') as fh:
            return int(fh.read().split()[1]) * 4096 / 2**20


BUDGET_GB = 22.0        # `AGENTS.md §1.3`：WSL 实测可用 22–23 GB，**规划用 22**
L_BOX_UM = 4.0
V_LATH_UM3 = 1.0 * 0.5 * 0.51        # 1000 × 500 × 510 nm ⇒ 0.255 µm³


def measure(N, nv, dx_um):
    """构造一个 `LevelSetMulti(N, L, nv=nv)`，返回 RSS 增量（MB）。"""
    gc.collect()
    r0 = rss_mb()
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, N * dx_um, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] * (nv + 1), nv=nv)
    r1 = rss_mb()
    del g
    gc.collect()
    return r1 - r0


def main():
    L = ['=' * 100, 'R549 —— 任务(5) 的内存包线（实测）', '=' * 100]
    pts = []
    for N, nv, dx in ((32, 8, 0.125), (32, 16, 0.125), (48, 16, 0.0833),
                      (48, 24, 0.0833), (64, 24, 0.0625)):
        mb = measure(N, nv, dx)
        pts.append((N, nv, mb))
        L.append('  N=%-4d nv=%-4d ⇒ RSS 增量 = **%8.1f MB**'
                 '（解析 `phi` 单独 = %7.1f MB）'
                 % (N, nv, mb, nv * N ** 3 * 8 / 2**20))

    # ---- 拟合 `RSS = a·nv·N³/2^20 + b`（最小二乘，两参数） ----
    A = np.array([[nv * N ** 3 / 2**20, 1.0] for N, nv, _ in pts])
    y = np.array([mb for _, _, mb in pts])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    a, b = float(coef[0]), float(coef[1])
    L.append('')
    L.append('  ── 拟合 `RSS(MB) = a · nv·N³/2²⁰ + b`（全 5 点） ──')
    L.append('     **a = %.2f B/胞**（`phi` 本身是 **8 B/胞**，float64）' % a)
    L.append('     b = %.1f MB（与 N、nv 无关的固定开销）' % b)
    ok1 = 8.0 <= a <= 40.0
    L.append('     ⇒ M1（a ∈ [8,30] B/胞）：%s' % ('✅ PASS' if ok1 else
                                                 '❌ FAIL ⇒ **先怀疑量具/模型，不得外推**'))

    # ---- M2：留一法（hold-out）—— 用其余 4 点拟合，预测第 5 点 ----
    errs = []
    for k in range(len(pts)):
        idx = [j for j in range(len(pts)) if j != k]
        Ak = A[idx]
        ck, *_ = np.linalg.lstsq(Ak, y[idx], rcond=None)
        pred = float(ck[0]) * A[k][0] + float(ck[1])
        errs.append(abs(pred - y[k]) / max(abs(y[k]), 1e-9))
    worst = max(errs)
    L.append('     M2 留一法最大相对预测误差 = **%.1f%%**（判据 ≤30%%）⇒ %s'
             % (100 * worst, '✅ PASS' if worst <= 0.30 else '❌ FAIL'))

    # ---- M3：22 GB 下的包线 ----
    L.append('')
    L.append('  ── M3：**%.0f GB 预算**下的可行包线（用上面的拟合式外推） ──' % BUDGET_GB)
    budget_mb = BUDGET_GB * 1024
    for name, N, dx_um, L_um in (('4 µm 盒', 64, 0.0625, 4.0),
                                 ('10 µm 盒', 160, 0.0625, 10.0)):
        per = a * N ** 3 / 2**20          # 每个 nv 要多少 MB
        nv_max = int((budget_mb - b) / per)
        # 填 30% 需要多少根
        V_box = L_um ** 3
        need = int(0.30 * V_box / V_LATH_UM3)
        L.append('     %-9s N=%-4d Δx=%.0f nm｜每个 `nv` 要 **%.1f MB**'
                 ' ⇒ `nv_max` ≈ **%d**'
                 % (name, N, dx_um * 1000, per, nv_max))
        L.append('              填 30%% 需 **%d 根** ⇒ %s'
                 % (need, '✅ **放得下**（占预算 %.0f%%）'
                    % (100.0 * need * per / budget_mb) if need <= nv_max else
                    '❌ **放不下**（需 %d > `nv_max` %d，超 %.1f×）'
                    % (need, nv_max, need / max(nv_max, 1))))

    # ---- 回代任务(5) 的候选配置 ----
    L.append('')
    L.append('  ── 回代任务(5) 的候选配置 ──')
    for lbl, N, dx_um, nv in (('归档尺度 N=64, nv=120（本轮短跑）', 64, 0.0625, 120),
                              ('R507 §5 的 N=160, nv=540', 160, 0.0625, 540),
                              ('R507 §5 的 N=160, nv=223', 160, 0.0625, 223),
                              ('**填满 4 µm 盒**：N=64, nv=77', 64, 0.0625, 77),
                              ('**填满 10 µm 盒**：N=160, nv=1176', 160, 0.0625, 1176)):
        mb = a * nv * N ** 3 / 2**20 + b
        L.append('     %-34s ⇒ 预测 RSS = **%8.1f MB**（%.1f GB）%s'
                 % (lbl, mb, mb / 1024,
                    '✅' if mb <= budget_mb else '❌ **超预算**'))

    npass = sum([bool(ok1), worst <= 0.30])
    L.append('')
    L.append('★ 汇总：M1=%s  M2=%s（%d/2）'
             % ('PASS' if ok1 else 'FAIL', 'PASS' if worst <= 0.30 else 'FAIL',
                npass))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r549_membudget.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
