#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r553_f32mem.py —— 实测 `phi_prec='f32'` 的**内存收益**（不靠算术外推）。

## 为什么
`_r550` 测得 f64 的内存定律 `9.01 B/胞·nv + 311.8 B/胞`（留一法 0.13%）。
`R552` 已证 **f32 的 `region()` 与 f64 逐胞相同**（0/110592）、`Σφ` 相对差 2.8e-9。
**⇒ 现在要量的是：`a` 到底从 9.01 降到多少。** 这是"能不能上 10 µm"的唯一依据。

## 判据（先写死）
* **Q1**：f32 的 `a` 必须落在 **[4.0, 6.5] B/胞**。
  理论预期 `9.01 − 4 = 5.01`（`phi` 由 8 → 4 B/胞）。
  落在区间外 ⇒ **先怀疑量具**（本仓已两次栽在"量具没量到目标量"上）。
* **Q2**：`c`（与 `nv` 无关的固定项）**在 f32 与 f64 下必须几乎相同**（差 ≤5%）
  —— 因为固定项是 `pf.Lam` 等，与 `phi` 的 dtype **无关**。
  ⚠ 这一条是**内部一致性正对照**：若它变了，说明我改的东西不止 `phi`。
* **Q3**：据此重算 `N=160`、22 GB 下的 `nv_max` 与**最大转变分数**。
"""
import gc
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

BUDGET_MB = 22 * 1024
V_LATH = 1.0 * 0.5 * 0.51        # µm³


def _walk(o, seen, depth=0):
    if depth > 5 or id(o) in seen:
        return
    seen.add(id(o))
    if isinstance(o, np.ndarray):
        yield o
        return
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk(v, seen, depth + 1)
        return
    if isinstance(o, (list, tuple)):
        for v in o:
            yield from _walk(v, seen, depth + 1)
        return
    d = getattr(o, '__dict__', None)
    if isinstance(d, dict):
        for v in d.values():
            yield from _walk(v, seen, depth + 1)


def fp(N, nv, prec):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, N * 0.0625, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] * (nv + 1), nv=nv, phi_prec=prec)
    seen, tot = set(), 0
    for a in _walk(g, seen):
        tot += a.nbytes
    del g
    gc.collect()
    return tot / 2**20


def fit(prec, pts):
    A = np.array([[nv * N ** 3 / 2**20, N ** 3 / 2**20, 1.0] for N, nv in pts])
    y = np.array([fp(N, nv, prec) for N, nv in pts])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    errs = []
    for k in range(len(pts)):
        idx = [j for j in range(len(pts)) if j != k]
        ck, *_ = np.linalg.lstsq(A[idx], y[idx], rcond=None)
        errs.append(abs(float(ck[0]) * A[k][0] + float(ck[1]) * A[k][1]
                        + float(ck[2]) - y[k]) / max(abs(y[k]), 1e-9))
    return float(coef[0]), float(coef[1]), float(coef[2]), max(errs), y


def main():
    pts = [(32, 8), (32, 32), (48, 16), (48, 32), (64, 24), (64, 48)]
    L = ['=' * 100, 'R553 —— `phi_prec` 的内存收益（实测）', '=' * 100]
    out = {}
    for prec in ('f64', 'f32'):
        a, c, d, err, y = fit(prec, pts)
        out[prec] = (a, c, d)
        L.append('  **%s**：a = **%.3f B/胞**  c = %.1f B/胞  d = %.1f MB  '
                 '（留一法 %.2f%%）' % (prec, a, c, d, 100 * err))
        L.append('        逐点 = %s' % ', '.join('%.1f' % v for v in y))

    a64, c64, _ = out['f64']
    a32, c32, _ = out['f32']
    rows = []
    ok1 = 4.0 <= a32 <= 6.5
    rows.append(('Q1 f32 的 a ∈ [4.0, 6.5]（理论 9.01−4 = 5.01）', ok1,
                 'a32 = **%.3f**（a64 = %.3f，差 %.3f）' % (a32, a64, a64 - a32)))
    ok2 = abs(c32 - c64) / c64 <= 0.05
    rows.append(('Q2 固定项 c 在两种精度下**几乎相同**（≤5%，内部正对照）', ok2,
                 'c64 = %.1f  c32 = %.1f（相对差 %.2f%%）'
                 % (c64, c32, 100 * abs(c32 - c64) / c64)))

    # ---- Q3 重算包线 ----
    L.append('')
    L.append('  ── Q3：N=160（10 µm）在 22 GB 下的包线 ──')
    N160 = 160 ** 3
    for prec, (a, c, _) in out.items():
        per = a * N160 / 2**20
        fix = c * N160 / 2**20
        nv_max = max(int((BUDGET_MB - fix) / per), 0)
        # ⚠⚠ **本行第一版漏了 ×100**：原来写 `frac = nv_max * V_LATH / 1000.0`
        #   那算出来的是**分数**（0.278），却被当成百分数打印 ⇒ 报 "0.2%"。
        #   **一眼可辨的荒谬值就是 tell**：605 根 × 0.255 µm³ 塞进 1000 µm³ 盒
        #   不可能是 0.2%。⇒ 按纪律**修推导**（补 ×100），不放宽任何阈值。
        frac_pct = 100.0 * nv_max * V_LATH / 1000.0      # 10³ µm³ 盒 ⇒ 百分数
        L.append('     **%-3s** 固定 %7.1f MB + 每 nv %6.2f MB ⇒ `nv_max` ≈ **%4d**'
                 ' ⇒ 最大转变分数 **%.1f%%** %s'
                 % (prec, fix, per, nv_max, frac_pct,
                    '✅ **≈30% ⇒ C5 可达**' if frac_pct >= 25 else '❌ 达不到 30%'))
    npass = sum(1 for _, ok, _ in rows if ok)
    L.append('')
    for n, ok, dd in rows:
        L.append('  %-52s %s   %s' % (n, '✅ PASS' if ok else '❌ FAIL', dd))
    L.append('')
    L.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    txt = '\n'.join(L)
    print(txt)
    with open(os.path.join(HERE, '_w2_r553_f32mem.log'), 'w') as fh:
        fh.write(txt + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
