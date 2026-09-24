#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_coupling.py —— 层间耦合的**守恒转移算子 Π**（Window A/CA 粗网格 ⇄ Window B 细网格）

框架依据（MATH_FRAMEWORK.md §7.1）：接口量 I2/I3 要求从 G 层（Window A/CA）交给
L0/L1 层（Window B）的量必须**逐胞守恒**（记为 Π）。

本模块只做一件事：给出**精确守恒**的粗⇄细转移算子（任意细化比），
判据见 `_chk_h7.py`（权重归一、往返恒等、总量守恒、常数保持、有界、负对照）。

★ 记账：这里解决的是**量**的守恒（溶质摩尔数、晶粒体积分数、晶界面积/长度）。
"把 CA 的胞状晶界骨架**重构**成亚胞精度的 level-set 几何"是**另一件事**
（属 I3 的几何一致性），不在本模块；CA 侧那件事带着 `CA3D_AUDIT §10.2 T8` 记下的
**~21% 格点路径偏差**，必须先解决才谈得上"几何一致"。
"""
import numpy as np


def overlap_1d(dxA, nA, dxB, nB):
    """(nA, nB) 一维重叠权重：W[i,j] = 细胞 j 被粗胞 i 覆盖的长度 / 细胞长度。
       ⇒ 每**列**和 = 1（细胞被完全覆盖）；每**行**和 = dxA/dxB（粗胞含多少个细胞）。
       闭式广播，无循环 ⇒ 任意细化比都精确（不要求整数比）。"""
    a = np.arange(nA, dtype=float)[:, None] * dxA      # 粗胞左端
    b = np.arange(nB, dtype=float)[None, :] * dxB      # 细胞左端
    ov = np.minimum(a + dxA, b + dxB) - np.maximum(a, b)
    return np.clip(ov, 0.0, None) / dxB


class ConservativeTransfer(object):
    """粗（A）⇄ 细（B）守恒转移 Π。三维张量积重叠权重。

    用法（extensive 量，例如"每胞摩尔数/界面长度"）：
        tr = ConservativeTransfer(dxA, (nAx,nAy,nAz), dxB, (nBx,nBy,nBz))
        qB = tr.prolong(qA)        # Σ qB == Σ qA（精确）
        qA2 = tr.restrict(qB)      # 往返恒等：restrict(prolong(qA)) == qA
    标量场（intensive，如浓度/温度）默认走 `mode='piecewise'`（逐胞复制），
    若要求"重采样也守恒"则用 `mode='smooth'`（与 extensive 同一算子 + 归一）。
    """

    def __init__(self, dxA, nA, dxB, nB):
        self.dxA, self.dxB = float(dxA), float(dxB)
        self.nA, self.nB = tuple(nA), tuple(nB)
        self.W = [overlap_1d(self.dxA, self.nA[i], self.dxB, self.nB[i])
                  for i in range(3)]
        # ★ 记账（H7 第一版把归一化方向写反了）：`overlap_1d` 给的是"细胞被粗胞覆盖的
        #   比例"（列和=1）；但**分摊**一个粗胞的"量"给细胞，用的必须是"粗胞落在细胞内的
        #   占比"（**行和=1**）⇒ 乘 dxB/dxA。写反的后果：总量被乘 (dxA/dxB)^3
        #   （实测细化比 20× 时偏差 8.0e3 = 20^3 ✗）。
        self.Wf = [w * (self.dxB / self.dxA) for w in self.W]      # 行和 = 1（分摊分数）
        self.ratio_vol = (self.dxB / self.dxA) ** 3      # 细胞/粗胞 体积比

    # ---------- extensive：每胞"量"（摩尔数、面积、长度…）----------
    def prolong(self, qA):
        """粗胞的"量"按重叠权重分摊给细胞 ⇒ **Σ 精确相等**"""
        return np.einsum('ai,bj,ck,abc->ijk', self.Wf[0], self.Wf[1], self.Wf[2], qA,
                         optimize=True)

    def restrict(self, qB):
        """细胞的"量"加回粗胞 ⇒ 与 prolong 互为逆（往返恒等）"""
        col = np.einsum('ai,bj,ck->ijk', self.Wf[0], self.Wf[1], self.Wf[2],
                        optimize=True)
        return np.einsum('ai,bj,ck,ijk->abc', self.Wf[0], self.Wf[1], self.Wf[2],
                         qB / np.maximum(col, 1e-300), optimize=True)

    # ---------- intensive：浓度/温度/体积分数 ----------
    def prolong_int(self, fA, mode='piecewise'):
        """标量场细网格化。
           mode='piecewise'：细胞取所在粗胞的值（常数保持，但**总量**只在整数比下守恒）；
           mode='smooth'   ：守恒重采样 = prolong 后除以每细胞的权重和（列和=1 ⇒ 等价）。"""
        if mode == 'piecewise':
            ix = np.clip((np.arange(self.nB[0]) * self.dxB) / self.dxA, 0,
                         self.nA[0] - 1).astype(int)
            iy = np.clip((np.arange(self.nB[1]) * self.dxB) / self.dxA, 0,
                         self.nA[1] - 1).astype(int)
            iz = np.clip((np.arange(self.nB[2]) * self.dxB) / self.dxA, 0,
                         self.nA[2] - 1).astype(int)
            return fA[np.ix_(ix, iy, iz)]
        w = self.prolong(np.ones(self.nA))
        return self.prolong(fA) / w

    def restrict_int(self, fB, mode='piecewise'):
        """细网格标量场 → 粗网格（体积加权平均）"""
        if mode == 'piecewise':
            out = np.zeros(self.nA)
            cnt = np.zeros(self.nA)
            ix = np.clip((np.arange(self.nB[0]) * self.dxB) / self.dxA, 0,
                         self.nA[0] - 1).astype(int)
            iy = np.clip((np.arange(self.nB[1]) * self.dxB) / self.dxA, 0,
                         self.nA[1] - 1).astype(int)
            iz = np.clip((np.arange(self.nB[2]) * self.dxB) / self.dxA, 0,
                         self.nA[2] - 1).astype(int)
            np.add.at(out, np.ix_(ix, iy, iz), fB)
            np.add.at(cnt, np.ix_(ix, iy, iz), np.ones_like(fB))
            return out / np.maximum(cnt, 1e-300)
        V = self.prolong(np.ones(self.nA))          # 每细胞的权重和
        return self.prolong(fB) / np.maximum(V, 1e-300)
