#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r560_softmem.py —— **`elastic_soft=True` 的内存代价**（复核 `R550` 的内存包线）。

## 为什么要复核 —— 一个可能的**重大遗漏**
`windowB_surface.py:3288-3294` 写着（这条注释本身在 `§174.5 D-1` 修过一次）：
> 实际的类属性在 `__init__` 里被设成 **`self.elastic_soft = True`**（Round 139，用户批准）
> —— 而 `_bk_exp.py` **从不**覆盖它 ⇒ **生产算例一律走 soft 路径**。
> `soft=None` 只是"沿用类属性"，**不是"默认关"**。

而 `:3327-3330`：
```python
if soft:
    if self.pf.phi.dtype == np.bool_:
        self.pf.phi = self.pf.phi.astype(np.float64)   # ← bool(1 B/胞) → float64(8 B/胞)
```
⇒ **`soft=True` 会给 `pf.phi` 加 7 B/胞 × nv。**

**⚠ 而 `_r550` / `_r553` 的内存量具只"构造引擎"、从不调 `elastic_driving()`**
⇒ **那次量到的是"bool 的 `pf.phi`"**（`a = 9.01 = g.phi 8 + pf.phi 1`）。
**⇒ 若生产确实走 soft，则生产的内存包线要重算，`R550 §6` 的结论可能翻转。**

## 判据（**先写死**）
| # | 判据 | 期望 |
|---|---|---|
| **S1** | 调一次 `elastic_driving()` 后 `pf.phi.dtype` 必须是 **float64**（而构造完是 bool） | 是 |
| **S2** | 实测 `a`（每 `nv` 的边际内存）在 **soft 后** 比 soft 前**大 ≥ 6 B/胞** | 成立 |
| **S3** | 用 soft 后的 `a` **重算** N=160 的 `nv_max` 与最大转变分数 | 报出 |
| **S4** | `g.phi` 的 `phi_prec='f32'` **仍然**把 `g.phi` 那一半减半（soft 不抵消它） | 成立 |
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
V_LATH = 1.0 * 0.5 * 0.51


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


def fp(N, nv, prec, do_soft):
    """构造引擎；`do_soft=True` 时**真的调一次 `elastic_driving()`**（触发 dtype 转换）。"""
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, N * 0.0625, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] * (nv + 1), nv=nv, phi_prec=prec)
    g.init_parent()
    rng = np.random.default_rng(3)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * 0.0625
    g.seed_plate(1, rng.random(3) * Lc * 0.5 + Lc * 0.25, nrm, 120e-9, 300e-9)
    g.advance(dt=1e-9)          # 走一步（会把 `pf.phi` 按 soft 分支写）
    d_soft = bool(getattr(g, 'elastic_soft', False))
    dt_before = g.pf.phi.dtype
    if do_soft:
        g.elastic_driving()     # ★ 真正触发 soft 分支
    dt_after = g.pf.phi.dtype
    seen, tot, phi_pf = set(), 0, 0
    for a in _walk(g, seen):
        tot += a.nbytes
        if a.shape == g.pf.phi.shape:
            phi_pf = max(phi_pf, a.nbytes)
    del g
    gc.collect()
    return (tot / 2**20, str(dt_before), str(dt_after), d_soft, phi_pf / 2**20)


def fit(N, nv_list, prec, do_soft):
    A = np.array([[nv * N ** 3 / 2**20, N ** 3 / 2**20, 1.0] for nv in nv_list])
    y = np.array([fp(N, nv, prec, do_soft)[0] for nv in nv_list])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(coef[0]), float(coef[1]), float(coef[2])


def main():
    L = ['=' * 100,
         'R560 —— `elastic_soft` 的内存代价（复核 R550 的包线）', '=' * 100]
    # 先确认类属性到底是什么
    eps1 = [np.asarray(EPS0[0], float)]
    g0 = W.LevelSetMulti(32, 32 * 0.0625, C=C, eps0=eps1, gamma=0.25, Mob=1e-9,
                         df=[0.0, 0.0], nv=1)
    cls_soft = getattr(g0, 'elastic_soft', 'ABSENT')
    L.append('  实测类属性 `g.elastic_soft` = **%s**' % cls_soft)
    L.append('  （代码注释 `:3288-3294` 声称是 True 且 `_bk_exp.py` 不覆盖 ⇒ 生产走 soft）')
    del g0
    gc.collect()

    outs = {}
    s1_ok = None
    for do_soft in (False, True):
        tag = 'soft' if do_soft else 'hard'
        r = fp(32, 8, 'f64', do_soft)
        L.append('')
        L.append('  ── do_soft=%-4s ⇒ `pf.phi.dtype`：调用前 **%s** → 调用后 **%s**'
                 % (do_soft, r[1], r[2]))
        a, c, d = fit(64, [12, 24, 48], 'f64', do_soft)
        L.append('     N=64 拟合：**a = %.3f B/胞**  c = %.1f B/胞' % (a, c))
        outs[tag] = (a, c)
        if do_soft:
            s1_ok = (r[2] == 'float64')
    L.append('')
    da = outs['soft'][0] - outs['hard'][0]
    L.append('  ▶ S2 **soft 让 `a` 增加 %.3f B/胞**（判据 ≥6）⇒ %s'
             % (da, '✅ PASS ⇒ **R550 的包线要重算**' if da >= 6
                else '❌ 未复现 ⇒ soft 没有想象的内存代价'))
    L.append('  ▶ S1 `soft` 后 `pf.phi.dtype == float64`：%s'
             % ('✅ PASS' if s1_ok else '❌ FAIL'))

    # S3：用两种 a 重算 N=160
    L.append('')
    L.append('  ── S3：N=160（10 µm）在 22 GB 下的 `nv_max`（**用实测的 a**） ──')
    N160 = 160 ** 3
    for tag, a in (('hard（R550 的原口径）', outs['hard'][0]),
                   ('**soft（生产实际）**', outs['soft'][0])):
        for prec, dphi in (('f64', 0.0), ('f32', -4.0)):
            aa = a + dphi          # f32 只减 `g.phi` 那 4 B/胞
            c = outs['soft'][1]
            per = aa * N160 / 2**20
            fix = c * N160 / 2**20
            nv_max = max(int((BUDGET_MB - fix) / per), 0)
            pct = 100.0 * nv_max * V_LATH / 1000.0
            L.append('     %-22s + `%s` ⇒ a=%.2f B/胞，每 nv %5.2f MB ⇒ '
                     '`nv_max` ≈ **%4d** ⇒ 转变分数 **%.1f%%**'
                     % (tag, prec, aa, per, nv_max, pct))
    L.append('')
    L.append('  ⚠ S4 记账：`--phi-prec f32` 只动 `g.phi`（−4 B/胞），'
             '**动不了 `pf.phi` 那 8 B/胞** ⇒ soft 下 f32 的收益被摊薄。')

    npass = sum([bool(s1_ok), da >= 6])
    L.append('')
    L.append('★ 汇总：S1=%s  S2=%s（%d/2）'
             % ('PASS' if s1_ok else 'FAIL', 'PASS' if da >= 6 else 'FAIL', npass))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r560_softmem.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
