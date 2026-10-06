#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vn_direct.py —— ★★ **直接测引擎的瞬时法向速度 `v(n)`**（不再用形状比间接推断）。

## 为什么必须换成这个量具
`R631`/`R635` 我一直用"300 步后的形状速度比 `v_a/v_w`"来推断各向异性 ——
**那是间接量**：它混入了（i）尖端迁移、（ii）毛细/Gibbs–Thomson 弛豫、（iii）体积归一。
⇒ **判据本身应是**：引擎对**给定法向 `n`** 实际推进界面的速度 `v(n)`，
   与设计角函数 `M(n)`（或其凸化 `h(n)`）的比值对照。

## 怎么测（不启算例、不改引擎）
分两层**逐步对照**，定位不一致发生在哪一层：

* **层 A**：设计角函数 `M(n) = exp(−β_h(n·n*)²) · exp(−β_w(n·w)²)`（`exp2` 形式）
  ⇒ `M(a)/M(w) = exp(β_w)`（**纯设计值**）
* **层 B**：引擎的凸化实现 `h(n) = max_j (Vc_j·n)`（`windowB_wulff.fast_support_factory`）
  ⇒ `h(a)/h(w)`（**引擎实际进入平流的速度律**）
* **层 C**：把某一层的 **45° 值**也算出来（凸化是否把凹区填平）

**判据（可 FAIL）**：
  · **V1**：`M(a)/M(w)` 应 = `exp(β_w)`（设计恒等式）
  · **V2**：`h(a)/h(w)` 应 ≈ 仓库 `_r59_wulff3d.py` 的 3.51（`β_w=2.3, dip=0`）
  · **V3**：`M(a)/M(w)` 与 `h(a)/h(w)` **应当不同**（凸化确实改变了速度律）
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_wulff as WL  # noqa: E402

# 与生产/实验一致的几何：n* 沿 z，a 沿 x，w 沿 y
nh = np.array([0.0, 0.0, 1.0])
av = np.array([1.0, 0.0, 0.0])
wv = np.array([0.0, 1.0, 0.0])


def M_design(n, beta_h, beta_w, dip_c=0.0):
    """设计角函数（`exp2` + 可选 45° 凹陷），与 `windowB_surface:5190/5197` 同式。"""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    s = float(n @ nh)
    cw = float(n @ wv)
    ca = float(n @ av)
    # 面内角 θ：cosθ = n·a，sinθ = n·w
    v = np.exp(-beta_h * s ** 2) * np.exp(-beta_w * cw ** 2)
    if dip_c:
        # `exp(−c·sin²2θ)`，sin2θ = 2 sinθ cosθ
        s2 = 2.0 * ca * cw
        v *= np.exp(-dip_c * s2 ** 2)
    return float(v)


def h_engine(n, beta_h, beta_w, dip_c, Vc):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    return float(np.max(np.asarray(Vc, float) @ n))


print("=" * 100)
print("直接测 `v(n)`：设计角函数 `M(n)` vs 引擎凸化 `h(n)`")
print("=" * 100)
for bh, bw, dip in ((6.477, 2.3, 0.0), (6.477, 2.3, 4.0), (6.477, 10.0, 0.0)):
    _vf, Vc, _ = WL.fast_support_factory(nh, av, wv, beta_h=bh, beta_w=bw,
                                         dip_c=dip)
    Vc = np.asarray(Vc, float)
    Ma, Mw = M_design(av, bh, bw, dip), M_design(wv, bh, bw, dip)
    # 45°（面内 a–w 之间）
    m45 = (av + wv) / np.sqrt(2.0)
    M45 = M_design(m45, bh, bw, dip)
    ha, hw = h_engine(av, bh, bw, dip, Vc), h_engine(wv, bh, bw, dip, Vc)
    h45 = h_engine(m45, bh, bw, dip, Vc)
    print("\n  β_h=%.3f  β_w=%.1f  dip_c=%.1f   (凸包顶点 %d)"
          % (bh, bw, dip, Vc.shape[0]))
    print("    层 A（设计 M）:  M(a)=%.4f  M(w)=%.4f  M(45°)=%.4f  ⇒ **M(a)/M(w)=%.3f**"
          % (Ma, Mw, M45, Ma / max(Mw, 1e-300)))
    print("    层 B（引擎 h）:  h(a)=%.4f  h(w)=%.4f  h(45°)=%.4f  ⇒ **h(a)/h(w)=%.3f**"
          % (ha, hw, h45, ha / max(hw, 1e-300)))
    print("    设计恒等式 exp(β_w) = %.3f   ⇒ V1 %s"
          % (np.exp(bw),
             'PASS' if abs(Ma / max(Mw, 1e-300) - np.exp(bw)) < 1e-9 else 'FAIL'))
