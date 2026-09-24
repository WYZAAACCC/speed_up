#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ca3d_solute.py --- 在三维 CA 上加【液相溶质输运】，把胞界成分从亚网格闭式升级为解出来的场

这直接关掉 CA3D_REPORT.md 局限 #1。

模型（逐胞有限体积，三维）：
  未知量: 亚网格固相分数 f_s(x,t)、液相成分 c_L(x,t)、固相平均成分 c_S(x,t)
  记号  A = (1-f_s) c_L  （单位体积内的液相溶质量, 无量纲）

  (1) 凝固再分配（局部杠杆律/界面平衡分配, k 为分配系数）
        df_s 固相生长 -> 固相取走 k c_L df_s, 液相失去同样多:
            c_S <- (c_S f_s + k c_L df) / (f_s + df)
            A   <- A - k c_L df
      无扩散时该式严格退化为 Scheil:  c_L = c0 (1-f_s)^(k-1)   [见验证 S1]

  (2) 液相扩散（只在液相中输运, 通道面积随液相分数收缩）
        dA/dt = div( D_L (1-f_s) grad c_L )
      显式有限体积, 稳定性 dt <= dx^2/(2 D_L)

  凝固区间: 胞被 CA 捕获后, 在局部凝固时间 dt_f = dT0/(G R) 内 f_s 由 0 线性到 1。
  dt_f = 1.73e-4 s 是 MATH_FRAMEWORK 4.5 实测值。

输出（这正是 Window B / Window C 需要的两个场）：
  c_L -> 枝晶间 / 晶界的富集成分（Window C 的输入）
  c_S -> 枝晶核心成分（Window B 的输入）
  Gamma_GB = sum[(c_L-c0)(1-f_s)] V_cell / A_GB  -> 单位晶界面积的溶质过剩（有限量）
"""

import math
import os
import numpy as np

from ca3d import CA3D, IRF, OFFSETS, C0_V, K_V, M_L, T_LIQ, T_SOL, F_MIN

D_L_DEFAULT = 9.5e-9      # m2/s  液相扩散 (V in Ti64)  [L] JOM 2018
DT_F_DEFAULT = 1.73e-4    # s     局部凝固时间 dT0/(GR)   [T] 见 MATH_FRAMEWORK 4.5
FLOOR_ML = 1e-6           # 液相分数的下限（避免 0 除）
MOLAR_DENSITY = 9.8e4     # mol/m3   Ti64 的摩尔密度 (rho/M)  [T]


class CA3DSolute(CA3D):
    def __init__(self, nx, ny, nz, dx, irf=None, seed=12345,
                 D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT, tortuosity=1.0):
        CA3D.__init__(self, nx, ny, nz, dx, irf=irf, seed=seed, chem_local=False)
        self.D_L = D_L
        self.dt_f = dt_f
        self.tort = tortuosity
        self.fs = np.zeros(self.shape)                 # 亚网格固相分数
        self.c_sol = np.full(self.shape, C0_V)         # 未开始凝固时取 c0（不参与统计）
        self.started = np.zeros(self.shape, dtype=bool)  # 是否已开始凝固
        # 主变量: A_liq = (1-f_s) c_L （单位体积的液相溶质量）。c_liq 是它的导出量。
        self.A_liq = np.full(self.shape, C0_V)
        self.c_liq = np.full(self.shape, C0_V)

    # ------------------------------------------------------------------ 单步
    def step_solute(self, dt, T, window=None, constitutional=False):
        """CA 几何推进 + 溶质再分配 + 液相扩散。返回本步捕获胞数。

        constitutional: 是否把上一步的 c_liq 接进【生长】判据（成分过冷）。
        默认 False => 历史行为逐位不变（既有算例可复现）。
        物理上应当为 True（这是"溶质 -> 拓扑"的显式反馈）；开启会改变结果。
        耦合是显式交错的（先几何、后化学），因此引入算子分裂误差：
        未耦合时不可分辨，耦合后约 1.8%（见 verify_ca3d_physics.T5b）。"""
        # ---- 1) CA 几何（固液界面推进 + 捕获）----
        nnew = self.step(dt, T, window=window,
                         c_l=(self.c_liq if constitutional else None))

        # ---- 2) 更新亚网格固相分数 f_s ----
        started = np.isfinite(self.ts)
        self.started |= started
        age = np.where(started, self.t - self.ts, 0.0)
        # 饱和于 1-F_MIN: 枝晶间液膜不可约 => 液相分数有下界,
        # 这同时消除了 c_L = A/(1-f_s) 在 f_s->1 时的数值放大（与框架 4.5 同一物理）
        fs_new = np.clip(age / self.dt_f, 0.0, 1.0 - F_MIN)
        df = fs_new - self.fs
        df = np.where(self.started, np.maximum(df, 0.0), 0.0)

        # ---- 3) 凝固再分配（严格守恒）----
        fs_old = self.fs
        need = df > 0
        if need.any():
            cl_here = self.c_liq[need]
            take = K_V * cl_here * df[need]
            denom = fs_old[need] + df[need]
            self.c_sol[need] = np.where(
                denom > 0,
                (self.c_sol[need] * fs_old[need] + take) / np.maximum(denom, 1e-30),
                C0_V)
            # 液相量的减少
            self.A_liq[need] = self.A_liq[need] - take
            self.fs[need] = fs_old[need] + df[need]

        # ---- 4) 液相扩散（只在液相中, 通道面积 = (1-f_s)）----
        self._diffuse_liquid(dt)

        # ---- 5) 由 A 反算 c_L ----
        self.c_liq = self.A_liq / np.maximum(1.0 - self.fs, FLOOR_ML)
        c_cap = C0_V * F_MIN ** (K_V - 1.0)        # 正则化后的物理上限
        self.n_clip = int((self.c_liq > c_cap).sum())
        self.c_liq = np.minimum(self.c_liq, c_cap)
        return nnew

    def set_liquid_composition(self, cl):
        """外部设定初始液相成分（同步主变量 A）。"""
        self.c_liq = np.asarray(cl, dtype=float) * np.ones(self.shape)
        self.A_liq = (1.0 - self.fs) * self.c_liq

    def _diffuse_liquid(self, dt):
        """显式有限体积: dA/dt = div( D_L (1-f_s)^p grad c_L ), 面值用两胞算术平均。"""
        A = self.A_liq
        cl = A / np.maximum(1.0 - self.fs, FLOOR_ML)
        cond = (1.0 - self.fs) ** self.tort
        coef = self.D_L * dt / self.dx ** 2
        dA = np.zeros(self.shape)
        for o, _ in OFFSETS:
            if sum(abs(v) for v in o) != 1:
                continue
            pr = self._pair(o, (0, self.nx, 0, self.ny, 0, self.nz))
            if pr is None:
                continue
            sx, tx = pr
            cf = 0.5 * (cond[sx] + cond[tx])
            flux = coef * cf * (cl[tx] - cl[sx])       # 从 sx 流向 tx 的量
            dA[sx] += flux
            dA[tx] -= flux
        self.n_Aclip = int((A + dA < 0).sum())
        self.A_liq = np.maximum(A + dA, 0.0)   # 物理下界（显式格式可能轻微越界）

    # ------------------------------------------------------------ 诊断量
    def total_solute(self):
        """守恒量: A_liq + f_s c_S = c0（用主变量 A_liq, 不受 c_L 截断影响）。"""
        return self.A_liq + self.fs * self.c_sol

    def excess_per_volume(self):
        """枝晶间溶质过剩, 按【单位总体积】计（与网格无关）:
           e_V = sum[(c_L - c0)(1-f_s)] V_cell / V_total"""
        m = self.started
        if not m.any():
            return 0.0
        tot = self.nx * self.ny * self.nz * self.dx ** 3
        return float(np.sum((self.c_liq[m] - C0_V) * (1.0 - self.fs[m])) * self.dx ** 3 / tot)

    def gamma_physical(self, lam1):
        """把 e_V 折算成【物理的】单位面积过剩 [mol/m2]。
        需要枝晶臂间距 lam1 估计枝晶间界面面积 A ~ 2 V_solid/lam1。
        CA 不解析 lam1, 所以这是显式声明的估计。参考: 单原子层约 1.7e-5 mol/m2。"""
        V_solid = float((self.gid > 0).sum()) * self.dx ** 3
        A_i = 2.0 * V_solid / lam1
        if A_i <= 0:
            return 0.0
        V_tot = self.nx * self.ny * self.nz * self.dx ** 3
        ex = self.excess_per_volume() * V_tot
        return float(ex * MOLAR_DENSITY / A_i)

    def enrichment(self):
        m = self.started
        if not m.any():
            return (C0_V, C0_V)
        return (float(self.c_liq[m].min()), float(self.c_liq[m].max()))
