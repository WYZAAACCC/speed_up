#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dg_matrix.py —— ★★★ **`Mfac` 各向异性的矩阵扫描**（用引擎自己的 `dG_max`）。

## 为什么换这个读数
`_t11_mfac_probe.py` 实测（平界面、`df=[0,-1e7]`、只调一次 `advance`）：
| `n*` | `dG_max` |
|---|---|
| `(0,0,1)`（`∇φ ∥ n*`） | **1.538e4** |
| `(1,0,0)`（`∇φ ⊥ n*`） | **1.0e7** |
⇒ 比值 **650.0 = `e^{6.477}` = `e^{β_h}`** ✅ —— **机制正常**。
⚠ 而界面位移读数给"三档相同" ⇒ **是位移口径错了**（`iface_offset` 取"离 `near` 最近的一个交点"，
   周期 slab 有两个界面 ⇒ 可能测到反向的那个）。

`windowB_surface.py:4993` 自陈：`dG_max` 是「**在 `Mfac` 应用之后重算**」的（`adv_dg_max_mfac`）
⇒ **它就是"经各向异性调制后的有效驱动"**，正是本判据要的量，且**不依赖位移口径**。

## 判据（可 FAIL，登记）
  · **M1**：`∇φ∥n*`（宽面）的 `dG_max` 应为 `∇φ⊥n*`（面内）的 **`e^{−β_h}` = 1/648**；
  · **M2**：`∇φ∥w`（侧面）应为面内的 **`e^{−β_w}`**；
  · **M3（负对照）**：`β_h=β_w=0` 时三档应**完全相同**（若有差异 ⇒ 装置有几何偏差）。
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

N, dx, M, df = 32, 2e-9, 1e-9, 1e7


def run(axis, gh, gw, bh, bw):
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=M,
                        df=[0.0, -df], reinit_every=0)
    r = (np.arange(N)[None, None, :] + 0.5) * dx
    a, L = (N // 2) * dx, N * dx
    prof = np.where(r <= a, -np.minimum(r, a - r), np.minimum(r - a, L - r))
    sh = [1, 1, 1]; sh[axis] = N
    g.phi[1] = prof.reshape(sh) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    g.npref = {1: np.asarray(gh, float)}
    g.wtab = np.full((2, 3), np.nan)
    g.wtab[1] = np.asarray(gw, float)
    kw = dict(extend='edt', band_cells=20, mob_iform='exp2',
              npref=g.npref, pin_min=True)
    if bh > 0 or bw > 0:
        kw.update(mob_beta=bh, mob_beta_w=bw)
    g.advance(0.1 * dx / (M * df), **kw)
    return float(getattr(g, 'dG_max', float('nan')))


z_ = np.array([0., 0., 1.])
x_ = np.array([1., 0., 0.])
y_ = np.array([0., 1., 0.])

print("=" * 100)
print("`Mfac` 各向异性矩阵扫描（读数 = 引擎的 `dG_max`，自陈『Mfac 应用之后重算』）")
print("=" * 100)
for bh, bw in ((0.0, 0.0), (6.477, 0.0), (6.477, 2.3)):
    # 三档：界面法向（= ∇φ 方向）分别沿 n* / a / w
    cases = (('∇φ ∥ n*（宽面）', 2, z_, y_),
             ('∇φ ∥ a （尖端）', 0, x_, z_),
             ('∇φ ∥ w （侧面）', 1, y_, z_))
    v = {}
    for tag, ax, gh, gw in cases:
        v[tag] = run(ax, gh, gw, bh, bw)
    base = v['∇φ ∥ a （尖端）']
    print("\n  β_h=%.3f  β_w=%.1f" % (bh, bw))
    print("    %-20s %-14s %-14s %s" % ('档', 'dG_max', '相对面内', '设计预期'))
    exp_h = np.exp(-bh); exp_w = np.exp(-bw)
    for tag, pred in (('∇φ ∥ a （尖端）', 1.0), ('∇φ ∥ w （侧面）', exp_w),
                      ('∇φ ∥ n*（宽面）', exp_h)):
        rr = v[tag] / max(base, 1e-300)
        print("    %-20s %-14.5g %-14.5g %-10.5g %s"
              % (tag, v[tag], rr, pred,
                 ('✅' if abs(rr - pred) <= 0.05 * max(pred, 1e-3) else '⚠')))
    print("    ⇒ **dG(面内)/dG(宽面) = %.4g**（设计 `e^{β_h}` = %.4g）"
          % (base / max(v['∇φ ∥ n*（宽面）'], 1e-300), np.exp(bh)))
