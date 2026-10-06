#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_flat_aniso.py —— ★★★ **判据 F-flat**：平界面 + 各向异性迁移率 ⇒ 速度是否 = `Mfac`？

## 为什么这是唯一能把"`Mfac` 计算"与"几何/平流"分开的实验
`_chk_w2.py` 已验证：**平界面 + 常数驱动（各向同性 `Mob`）⇒ `v/(MΔf) = 1.0000`**
（EDT 扩展 20dx）。但它**从未在各向异性迁移率下跑过**。
本脚本在**同一装置**上只加一件事：**令界面法向分别指向 `n*` / `a` / `w`**，测三个速度。

## 判据（可 FAIL，先登记）
  · **F1（装置自洽）**：与 `_chk_w2.py` 同构型（`n*` 沿 z）在**各向同性**下应给 **1.0000**；
  · **F2（核心）**：各向异性下，三个取向的 `v/(MΔf)` 之比应 = `Mfac` 在该取向的值之比：
      `Mface(n*) = exp(−β_h)`、`Mface(a) = 1`、`Mface(w) = exp(−β_w)`
    ⇒ 预期 `v(a) : v(w) : v(n*) = 1 : e^{−2.3} : e^{−6.477} = 1 : 0.100 : 0.00154`
    ⇒ **`v(a)/v(n*)` 应 ≈ 648**（`β_h=6.477`）
  · **F3（负对照）**：`mob_beta=0` 时三个取向应**相同**（若不同 ⇒ 装置有几何偏差）。

## 装置（照抄 `_chk_w2.py` 的 `slab` 初值，**周期自洽**）
  `a = (N//2)·dx`；`φ = −min(z, a−z)`（`z≤a`）/ `+min(z−a, L−z)`（`z>a`）
  ⇒ **一列两个界面**，法向沿 ±z；`reinit_every=0` ⇒ 只测平流。
  `dt = 0.1·dx/(MΔf)`（显式给定）。
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from windowB_surface import LevelSetMulti  # noqa: E402


def make(N, dx, axis, gh, gz, kind='slab'):
    """`axis` = **界面法向所沿的晶格轴**（0=x / 1=y / 2=z）；
    `gh` = 惯习面法向 `n*`；`gz` = 宽度轴 `w`。

    ⚠ 记账（本脚本第一版的**装置缺陷**）：第一版 slab 恒沿 z 建，
      而只是换 `gh` ⇒ `(∇φ·n*)²` 恒为 0 ⇒ **三个"取向"测的是同一个面**，判据无效。
      修法：**slab 建在 `axis` 上**，使界面法向真的指向该轴。
    """
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=1e-9, df=[0.0, -1e7],
                      reinit_every=0)
    r = (np.arange(N)[None, None, :] + 0.5) * dx          # 沿 axis 的坐标
    L = N * dx
    a = (N // 2) * dx
    prof = np.where(r <= a, -np.minimum(r, a - r),
                    np.minimum(r - a, L - r))
    shape = [1, 1, 1]
    shape[axis] = N
    g.phi[1] = prof.reshape(shape) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    # ★ 轴：`_nh` 必须让 `∇φ`（沿 `axis`）落在 `n*`（用平方 ⇒ ± 不限）；
    #   `_wv` 必须给**所有场**同一行（多畴路径用 `wtab[1]`）
    g.npref = {1: np.asarray(gh, float)}
    g.wtab = np.full((2, 3), np.nan)
    g.wtab[1] = np.asarray(gz, float)
    return g


def run(axis, gh, gz, N=48, dx=2e-9, M=1e-9, df=1e7, nstep=40, band_cells=20,
        mob_beta=0.0, mob_beta_w=0.0):
    g = make(N, dx, axis, gh, gz)
    near = g.near0
    # ★ 记账（第一版的**装置缺陷**）：`iface_offset` 的 `axis` **默认 2（z）**；
    #   我却在 x/y 上建 slab ⇒ 沿 z 找交点必然失败 ⇒ 读数 0.0000（假 FAIL）。
    #   ⇒ 必须把 `axis` 传进去。
    _, z0 = g.iface_offset(1, 0, axis, near=near)
    dt = 0.1 * dx / (M * df)
    kw = dict(extend='edt', band_cells=band_cells, mob_iform='exp2',
              npref=g.npref, pin_min=True)
    if mob_beta > 0.0 or mob_beta_w > 0.0:
        # ★ `mob_beta` 与 `mob_aniso` 不能同时非零（`:5260` 明确报错：会双重调制）
        kw.update(mob_beta=mob_beta, mob_beta_w=mob_beta_w)
    for _ in range(nstep):
        g.advance(dt, **kw)
    _, z1 = g.iface_offset(1, 0, axis, near=near)
    if not (np.isfinite(z0) and np.isfinite(z1)):
        return float('nan')
    return abs(z1 - z0) / (nstep * dt) / (M * df)


if __name__ == '__main__':
    z_ = np.array([0., 0., 1.])
    x_ = np.array([1., 0., 0.])
    y_ = np.array([0., 1., 0.])
    print("=" * 96)
    print("判据 F-flat：平界面 + 各向异性迁移率 ⇒ v/(MΔf) 是否 = Mfac？")
    print("=" * 96)
    # --- F1：装置自洽（各向同性）---
    v_iso = run(2, z_, y_, mob_beta=0.0, mob_beta_w=0.0)
    print("  F1 装置自洽（mob_beta=0，应 1.0000）      : v/(MΔf) = **%.4f**  %s"
          % (v_iso, 'PASS' if abs(v_iso - 1) < 0.02 else 'FAIL'))
    print()
    # --- F2：三个取向（各向异性）---
    BH, BW = 6.477, 2.3
    # (标签, 界面法向所沿轴, n*, w)
    cases = (('∇φ ∥ n*（宽面）', 2, z_, y_),
             ('∇φ ∥ a （尖端面）', 0, x_, z_),
             ('∇φ ∥ w （侧面）', 1, y_, z_))
    res = {}
    print("  F2 三个取向（β_h=%.3f, β_w=%.1f）" % (BH, BW))
    print("  %-22s %-14s %-14s %s" % ('取向', 'v/(MΔf) 实测', 'Mfac 预测', '实测/预测'))
    for tag, ax, gh, gz in cases:
        v = run(ax, gh, gz, mob_beta=BH, mob_beta_w=BW)
        res[tag] = v
        e = np.zeros(3); e[ax] = 1.0
        c2h = float(np.asarray(gh, float) @ e) ** 2
        c2w = float(np.asarray(gz, float) @ e) ** 2
        pred = np.exp(-BH * c2h) * np.exp(-BW * c2w)
        print("  %-22s %-14.5f %-14.6g %s"
              % (tag, v, pred, ('%.4g' % (v / pred)) if pred > 0 else '—'))
    print()
    ka = res['∇φ ∥ a （尖端面）']
    kw = res['∇φ ∥ w （侧面）']
    kh = res['∇φ ∥ n*（宽面）']
    print("  ⇒ **v(a)/v(w) = %.4g**（设计 `e^{β_w}` = %.4g）"
          % (ka / max(kw, 1e-300), np.exp(BW)))
    print("  ⇒ **v(a)/v(n*) = %.4g**（设计 `e^{β_h}` = %.4g）"
          % (ka / max(kh, 1e-300), np.exp(BH)))
