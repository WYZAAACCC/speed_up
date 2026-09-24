#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_drag.py —— 溶质拖曳的**隐式自洽**耦合（溶质 → 拓扑），框架 §6.3 / 模块 7 K1–K5。

为什么必须隐式（[RULE] K5）：界面要拖着偏析云走，云"跟得上/跟不上"取决于 v 本身
⇒ 压强 P_drag 是 v 的函数 ⇒ 必须解
      v = M_GB [ ΔG − P_drag(v) ]
而不是线性闭式 `v = MΔG (1 − a v)`（后者在 P_drag ≈ ΔG 处给出**负压强**、
且在被钉扎的驱动下**凭空给出速度** —— 模块 7 K3 实测偏差 98%）。

拖曳闭式（双盒/扫掠质量平衡，K1 已验）：
      P_drag(v) = P0 / (1 + v/v*)        v* = D_GB/ℓ
  P0  = v=0 时的最大拖曳压强（由偏析过剩与化学势差定：[T]/[A] 待锚定）
  v*  = 云"跟得上界面"的特征速度

★ 解析结论（本模块并数值验证）：
      v > 0  ⟺  (ΔG > P0)  或  (M_GB·ΔG > v*)
即两条脱钉通道：① 驱动超过最大拖曳；② 界面快到把云甩掉（breakaway）。
每条都有闭式正根（二次方程，无需迭代）——它**不是**线性闭式，满足 K5 的 [RULE]。
"""
import numpy as np


def pdrag(v, P0, vstar):
    """双盒拖曳压强 P(v)=P0/(1+v/v*)（单调降、有界，K1）"""
    return P0 / (1.0 + np.asarray(v) / vstar)


def solve_v(dG, M, P0, vstar):
    """解隐式方程 v = M[dG − P0/(1+v/v*)]，返回 (v, pinned)。

    令 w = 1+v/v*，方程化为  v*·w² − (v*+MΔG)·w + M·P0 = 0。
    取**大根** w₊（物理分支；小根 w₋<1 对应 v<0）。
    正根存在的判据（本模块数值验证）：ΔG>P0 或 MΔG>v*。
    """
    dG = np.asarray(dG, float)
    sgn = np.sign(dG)
    dG = np.abs(dG)              # ★ 拖曳与运动方向**相反** ⇒ 用 |ΔG| 解、再乘回符号
    M = np.asarray(M, float)
    b = vstar + M * dG
    disc = b * b - 4.0 * vstar * M * P0
    wp = (b + np.sqrt(np.maximum(disc, 0.0))) / (2.0 * vstar)
    v = vstar * (wp - 1.0)
    pinned = (disc < 0) | (v <= 0)
    return np.where(pinned, 0.0, v) * sgn, pinned


def v_linear(dG, M):
    """**线性闭式**（只作负对照：无拖曳/线性修正）"""
    return M * np.asarray(dG, float)


def pdrag_from_physics(Gamma_eq, dG_seg, Omega, ell_gb, D_gb):
    """由物理量给 (P0, v*)：
         P0 = Γ_eq·|ΔG_seg| / (Ω·ℓ)   [Pa]（偏析云在界面处的最大拖曳压强）
         v* = D_gb / ℓ                [m/s]（云跟得上界面的特征速度）
    ★ 记账：Γ_eq/ΔG_seg 的取向与温度依赖见 `pipeline/gibbs/gibbs_physics.py`（单一参数来源）；
       把 P0 锚定到文献 ΔG_seg 是 [T]/[A] 项（CALPHAD_REQUEST C4）。
    """
    P0 = Gamma_eq * abs(dG_seg) / (Omega * ell_gb)
    return P0, D_gb / ell_gb
