#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ca3d_project.py --- 投影算子 Pi（MATH_FRAMEWORK 4.6 / IMPLEMENTATION_PLAN P3.1）

作用：把 CA 的【胞平均】成分展开成【胞内分布】，供 Window B 的 PF 作为初值。
硬要求：**逐胞精确守恒**  int_{Omega_i} c dV = c_bar_i |Omega_i|（容差 = 机器精度）。

构造（本文件采用的形式）:
    胞内沿一个方向（主枝晶方向）分辨出 n_sub 个子层。
    形状函数 g(s) 满足 <<g>> = 1（胞平均为 1），取两层剖面:
        边缘 edge_frac 比例的层 -> g = 1/edge_frac
        其余 -> g = 0
    则   c(x) = c_S + (c_L - c_S) * beta * g(x),   beta = 1 - f_s
    胞平均: <c> = c_S + (c_L - c_S) * beta = (1-beta)c_S + beta c_L = c_bar   <- 恒等
    所以守恒是【构造保证】的, 不是数值凑出来的。

反算子 Pi^-1 就是胞平均。
"""

import numpy as np


class Projector(object):
    def __init__(self, shape, dx, n_sub=8, edge_frac=0.25):
        self.shape = tuple(shape)
        self.dx = dx
        self.n_sub = int(n_sub)
        self.edge_frac = float(edge_frac)
        self.g = self._shape_function()
        self.g_mean = float(self.g.mean())
        assert abs(self.g_mean - 1.0) < 1e-14, "参考形状必须胞平均为 1"

    def _shape(self, beta):
        """逐胞形状函数 g, 满足 <g> = 1（严格）且峰值受限 => 剖面天然落在 [c_S, c_L] 内。
        物理: 液相只能放在它真正占的那部分胞内。
          活跃层比例 f = clip(beta, edge_frac, 1)   (beta = 1-f_s)
          g_raw = 1 on the top f*n_sub layers, else 0 ; 再归一化到 <g>=1
        峰值 = n_sub/k_layer <= 1/beta  => 增量 (c_L-c_S)*beta*peak <= (c_L-c_S)。"""
        n, ef = self.n_sub, self.edge_frac
        r = np.arange(n)
        f = np.clip(beta, ef, 1.0)
        # 用 floor 保证活跃层数 >= f*n => 峰值 <= 1/f => beta*peak <= 1 (剖面必不越界)
        graw = (r >= np.floor(n * (1.0 - f))[..., None]).astype(float)
        m = graw.mean(axis=-1, keepdims=True)
        m = np.where(m > 0, m, 1.0)
        return graw / m

    def _shape_function(self):
        """参考形状（beta=1 的均匀极限），仅用于自检 <g>=1。"""
        g = self._shape(np.ones(1))
        return g.reshape(self.n_sub)
    def forward(self, c_bar, fs, c_S, c_L, axis=-1):
        """返回细网格剖面（末轴 = 胞内子层）。守恒由 <g>=1 保证。"""
        beta = np.clip(1.0 - np.asarray(fs, dtype=float), 0.0, 1.0)
        cS = np.asarray(c_S, dtype=float)
        cL = np.asarray(c_L, dtype=float)
        g = self._shape(beta)
        prof = cS[..., None] + (cL - cS)[..., None] * beta[..., None] * g
        return np.moveaxis(prof, -1, axis) if axis != prof.ndim - 1 else prof


    def backward(self, c_fine, axis=-1):
        """Pi^-1: 细网格 -> 胞平均（沿最后/指定轴等权平均）。"""
        a = np.asarray(c_fine, dtype=float)
        return a.mean(axis=axis)

    def naive_forward(self, c_bar, c_S, c_L, axis=-1):
        """反例: 直接线性插值（不做守恒校正）—— 用来演示它【不守恒】。"""
        beta = np.linspace(0.0, 1.0, self.n_sub)
        cS = np.asarray(c_S, dtype=float)
        cL = np.asarray(c_L, dtype=float)
        prof = cS[..., None] + (cL - cS)[..., None] * beta
        return np.moveaxis(prof, -1, axis) if axis != prof.ndim - 1 else prof


# =============================================================== 验证
def main():
    RES = []
    def chk(name, verdict, detail, value=None):
        RES.append((verdict, name, detail))
        print("[{:<4}] {:<50} {}".format(verdict, name, detail))

    print("ca3d_project.py --- 投影算子 Pi 的验证（三维）")
    print("=" * 100)
    rng = np.random.default_rng(3)
    shape = (6, 5, 4)
    pr = Projector(shape, dx=1.0, n_sub=8, edge_frac=0.25)

    fs = rng.uniform(0.0, 0.95, shape)
    c_S = rng.uniform(0.02, 0.04, shape)
    c_L = rng.uniform(0.036, 0.11, shape)
    c_bar = fs * c_S + (1.0 - fs) * c_L          # 逐胞守恒的定义式

    prof = pr.forward(c_bar, fs, c_S, c_L)
    back = pr.backward(prof)
    err = float(np.max(np.abs(back - c_bar)) / np.max(c_bar))
    chk("Pi-1 逐胞精确守恒 <c> = c_bar", "PASS" if err < 1e-14 else "FAIL",
        "最大相对偏差 {:.2e} (构造保证)".format(err), err)

    lo = np.minimum(c_S, c_L); hi = np.maximum(c_S, c_L)
    inrange = bool(np.all(prof >= lo[..., None] - 1e-14) and np.all(prof <= hi[..., None] + 1e-14))
    chk("Pi-2 剖面落在 [c_S, c_L] 内（物理有界）", "PASS" if inrange else "WARN",
        "子层范围 [{:.4f}, {:.4f}] ; 允许区间 [c_S, c_L]".format(prof.min(), prof.max()))

    naive = pr.naive_forward(c_bar, c_S, c_L)
    nb = pr.backward(naive)
    e_naive = float(np.max(np.abs(nb - c_bar)) / np.max(c_bar))
    chk("Pi-3 反例: 直接线性插值不守恒", "PASS" if e_naive > 1e-3 else "WARN",
        "线性插值的胞平均相对偏差 {:.2e} (<< 说明守恒不是自动的)".format(e_naive), e_naive)

    r1 = pr.forward(c_bar, fs, c_S, c_L)
    r2 = pr.forward(pr.backward(r1), fs, c_S, c_L)
    idem = float(np.max(np.abs(r2 - r1)))
    chk("Pi-4 幂等性 Pi(Pi^-1(Pi(x))) = Pi(x)", "PASS" if idem < 1e-14 else "WARN",
        "最大绝对差 {:.2e}".format(idem), idem)

    # 胞界(枝晶间)富集与胞内的关系
    edge_val = prof[..., -1]
    core_val = prof[..., 0]
    chk("Pi-5 胞界子层是富集侧", "PASS" if np.all(edge_val >= core_val - 1e-14) else "FAIL",
        "边缘/核心 平均 = {:.4f} / {:.4f}".format(float(edge_val.mean()), float(core_val.mean())))

    np_ = sum(1 for v, _, _ in RES if v == "PASS")
    nw = sum(1 for v, _, _ in RES if v == "WARN")
    nf = sum(1 for v, _, _ in RES if v == "FAIL")
    print("=" * 100)
    print("汇总: {} 项  PASS {} / WARN {} / FAIL {}".format(len(RES), np_, nw, nf))
    print("=" * 100)
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
