#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ca3d.py --- Window A: 三维元胞自动机（prior-beta 凝固晶粒骨架）

对应 MATH_FRAMEWORK.md 第 4 节（L1-G 层）。

职责（与本文件严格对应）：
  * 4.2 形核：基底/外延形核 + 体形核（连续形核谱）
  * 4.3 生长：界面响应函数 V(dT)（读 irf_ti64.csv 插值表）
  * 4.4 取向与捕获：decentered octahedron + 26 邻居（三维）
  * 4.5 凝固化学：Scheil（本文件给出逐胞闭式，供 Window B/C 用）
  * 4.1 滑动窗口：只在前沿邻域推进（active region）
  * 输出：冻结的 grain ID / 取向 / t_s / c（这就是「冻结的晶粒骨架 + 晶界网络几何」）

**本实现以三维为准。** ny=1 的二维模式只用于代码交叉校验，不是仿真结果。

术语（不要搞混，见 RESEARCH_INTENT.md 2.1）：
  本文件推进的是**固液界面**；晶界是 grain ID 场的间断集合，是**涌现**的，不在这里被推进。
"""

import math
import os
import numpy as np

# ------------------------------------------------------------------ 默认参数
R_GAS = 8.314462618

T_LIQ = 1911.1          # K   由 (k, c0) 闭式推出（MATH_FRAMEWORK 5.2）
T_SOL = 1893.2          # K   同上
K_V = 0.6303            # -   分配系数
C0_V = 0.036            # -   V 的摩尔分数
M_L = -818.4            # K  液相线斜率 (mol frac)  van t Hoff
F_LAST = 0.99           # -   [A] 末态残余液相分数（旧口径，仅作参照）
F_MIN = 0.05            # -   [A] 不可约残余液相分数（枝晶间液膜）
                        #     用来正则化 Scheil 奇点: c_l -> c0 (1-f)^(k-1) 在 f->1 发散,
                        #     物理上被「枝晶间液膜孤立」截断。见 MATH_FRAMEWORK 4.5/6.1。
                        #     敏感度: f_min=0.02/0.05/0.10 -> c_l,max=0.155/0.112/0.084

# 26 邻居（三维）
OFFSETS = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)
           if not (a == 0 and b == 0 and c == 0)]
OFFSETS = [(o, math.sqrt(o[0] ** 2 + o[1] ** 2 + o[2] ** 2)) for o in OFFSETS]


def quat_to_axes(q):
    """四元数 (w,x,y,z) -> 3x3, 列为晶体主轴 p1,p2,p3 (实验室系)。"""
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def rand_quat(rng):
    u1, u2, u3 = rng.random(3)
    return (math.sqrt(1 - u1) * math.sin(2 * math.pi * u2),
            math.sqrt(1 - u1) * math.cos(2 * math.pi * u2),
            math.sqrt(u1) * math.sin(2 * math.pi * u3),
            math.sqrt(u1) * math.cos(2 * math.pi * u3))


class IRF(object):
    """界面响应函数 V(dT): 直接查表（ExaCA 做法），不是多项式拟合。

    **严禁外推。** LKT/KGT 的解只在有限区间内存在:
      * dT < dT_lo(~4.75 K): 平面界面稳定, 没有枝晶尖端解 -> 取 dT_lo 处的速度
        (保守: 不假装知道更快或更慢)
      * dT > dT_hi(~17.97 K): 尖端过冷度预算饱和。物理含义是
        「多出来的过冷度不可用于尖端生长」=> 把 dT 截断在 dT_hi, 并【计数】。
        第一版把它写成常数外推是错的 —— 数值上一样, 但丢失了「越界」这个物理报警。
    理由详见 MATH_FRAMEWORK 4.3 与 CA3D_REPORT 4/#6。
    """

    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "irf_ti64.csv")
        if os.path.exists(path):
            tab = np.loadtxt(path, delimiter=",", skiprows=1)
            o = np.argsort(tab[:, 0])
            self.dT, self.V = tab[o, 0], tab[o, 1]
            self.R_tip = tab[o, 2]
        else:
            self.dT, self.V = np.array([0.0, 30.0]), np.array([0.0, 3.0])
            self.R_tip = np.zeros(2)
        self.dT_lo = float(self.dT.min())
        self.dT_hi = float(self.dT.max())
        self.V_lo = float(self.V.min())
        self.V_at_lo = float(np.interp(self.dT_lo, self.dT, self.V))
        self.V_at_hi = float(np.interp(self.dT_hi, self.dT, self.V))

    def __call__(self, dT):
        """不截断的查表（保留给需要原始值的场合）。"""
        dT = np.asarray(dT, dtype=float)
        return np.interp(dT, self.dT, self.V, left=self.V_at_lo, right=self.V_at_hi)

    def capped(self, dT):
        """返回 (V, dT_used, n_low, n_high)。n_* 是落在有效区间外的胞数。"""
        dT = np.asarray(dT, dtype=float)
        n_low = int(np.count_nonzero(dT < self.dT_lo))
        n_high = int(np.count_nonzero(dT > self.dT_hi))
        dTu = np.clip(dT, self.dT_lo, self.dT_hi)
        return np.interp(dTu, self.dT, self.V), dTu, n_low, n_high

class CA3D(object):
    def __init__(self, nx, ny, nz, dx, irf=None, seed=12345, n_halo=2,
                 periodic=(False, False, False), capture="envelope",
                 lg_percentile=90.0, chem_local=False):
        self.nx, self.ny, self.nz, self.dx = nx, ny, nz, dx
        # capture 三档（见 CA3D_AUDIT_2026-09-23.md）：
        #   "envelope"   ← **新默认**（审计后修复）：逐晶粒连续包络 l_g + 外延(26)邻接
        #                  + 逐胞 argmax(l_g/sup_g) 定归属 ⇒ 顺序无关、各向异性正确。
        #                  实测 r(<100>)/l=1.00+-0.05、<100>:<111>=1.73+-0.10、体积 +-5%。
        #   "analytic"   历史：从【种子】出发的连续八面体，但 l 只记在种子胞上
        #                  ⇒ 滑动窗口下会僵死（审计 N6），仅留作对照。
        #   "decentered" 历史/生产：逐胞 L 预算 + 格点路径代价 ⇒ 各向异性被毁
        #                  （r(<100>)/l=0.60~0.76、体积 -25%、不随 dx 收敛），仅留作考古对照。
        self.capture = capture
        self.lg_percentile = float(lg_percentile)   # l_g 驱动量取前沿 V 的该分位（规划 D1）
        # capture="cell" 的裁决规则："ratio"（取 ℓ/crit 最大，与顺序无关；本框架默认）
        #                          "firstcome"（ExaCA 口径：按源胞索引+偏移顺序先到先得）
        self.cell_tiebreak = "ratio"
        self._Lg = None
        # --- 局部凝固化学（默认开；见 CA3D_AUDIT §F5~F7）---
        # 旧 scheil_chemistry() 用【全局】固相分数代入 Scheil ⇒ 池内 c 几乎常数、
        # 基底给 k*c0（应为 c0）、全局质量守恒只有 0.732。这条路径按【逐胞局部凝固路径】演化，
        # 并允许相邻胞间液相扩散（空间偏析图案的真正来源）。旧路径完整保留（测试零风险）。
        self.chem_local = bool(chem_local)
        self.D_L = 9.5e-9            # m2/s  液相扩散 (V in Ti64)  [L] JOM 2018
        self.tort = 1.0
        self.dtf_default = 1.73e-4   # s  局部凝固时间兜底 = dT0/(GR)，框架 4.5
        _shp = (nx, ny, nz)
        self.fs = np.zeros(_shp)                    # 亚网格固相分数
        self.c_sol = np.full(_shp, C0_V)            # 固相成分
        self.A_liq = np.full(_shp, C0_V)            # (1-fs)*c_L（主守恒量）
        self.c_liq = np.full(_shp, C0_V)            # 局部液相成分（Window C 输入）
        self.cl = np.full(_shp, C0_V)
        self.c_cell = np.full(_shp, C0_V)           # 体平均成分（质量守恒）
        self.seeds = [None]                     # seeds[gid] = (i,j,k) 种子位置
        # 轴向周期边界（默认全关；开后在 _pair 里环绕）。
        # 用途：倾斜/竖直梯度下的晶粒竞争，去掉侧壁对竞争的约束。
        self.periodic = tuple(bool(p) for p in periodic)
        self.shape = (nx, ny, nz)
        self.irf = irf if irf is not None else IRF()
        self.rng = np.random.default_rng(seed)
        self.n_halo = n_halo

        self.gid = np.zeros(self.shape, np.int32)      # 0 = 液相
        self.L = np.zeros(self.shape, np.float64)      # 八面体半对角（m）
        self.ts = np.full(self.shape, np.nan)          # 凝固(被捕获)时刻 s
        self.Tc = np.full(self.shape, np.nan)          # 被捕获时的温度 K
        self.c = np.full(self.shape, C0_V)             # 逐胞 V 摩尔分数（Scheil 闭式）
        self.axes = [None]                             # axes[gid] = 3x3
        self.t = 0.0
        self.n_captured_steps = 0
        self._fs_hist = [(0.0, 0.0)]

    # ---------------------------------------------------------- 坐标与温度
    def coords(self):
        x = (np.arange(self.nx) + 0.5) * self.dx
        y = (np.arange(self.ny) + 0.5) * self.dx
        z = (np.arange(self.nz) + 0.5) * self.dx
        return np.meshgrid(x, y, z, indexing="ij")

    def T_iso(self, dT_uniform):
        """全场均匀过冷：用于包络几何/取向竞争的纯正对照。"""
        return np.full(self.shape, T_LIQ - dT_uniform)

    def T_directional(self, G, v_pull, z0=0.0):
        """定向凝固：T = T_LIQ + G*(z - (z0 + v_pull*t))，下方为过冷。"""
        X, Y, Z = self.coords()
        return T_LIQ + G * (Z - (z0 + self.t * v_pull))

    def T_inclined(self, G, v_pull, n_hat, x0=None):
        """倾斜梯度的定向凝固: T = T_LIQ + G (n.(x-x0) - v t)。
        用于验证【倾斜梯度下的晶粒淘汰】(Walton-Chalmers 的多晶版本)。"""
        X, Y, Z = self.coords()
        n = np.array(n_hat, float); n /= np.linalg.norm(n)
        if x0 is None:
            x0 = np.array([0.0, 0.0, 0.0])
        s_ = (X - x0[0]) * n[0] + (Y - x0[1]) * n[1] + (Z - x0[2]) * n[2]
        return T_LIQ + G * (s_ - v_pull * self.t)

    def T_meltpool(self, T_peak, sigma, tau, T_bath=353.0, x0=0.0, y0=-0.0, z_top=True):
        """静态熔池（激光关掉）：T(x,t)=T_bath+(T_field-T_bath)*exp(-t/tau)。
        热场与 thermal_layer.py 同一设定（决策 D3）。"""
        X, Y, Z = self.coords()
        xc, yc, zc = X.mean(), Y.mean(), Z.max() if z_top else Z.mean()
        zs = sigma * 3.0
        Tf = T_bath + (T_peak - T_bath) * np.exp(
            -((X - xc - x0) ** 2 + (Y - yc - y0) ** 2 + (Z - zc) ** 2) / (2 * sigma ** 2))
        return T_bath + (Tf - T_bath) * math.exp(-self.t / tau)

    # -------------------------------------------- 初始固相区（基底/已凝固材料）
    def seed_solid_from_substrate(self, T, T_thresh, max_iter=500):
        """把 T < T_thresh 的胞划为固相, 并把已有晶粒身份按【各向异性 L1 距离】分给它们。

        【2026-09-23 审计后重写】旧版是按 OFFSETS 顺序的 26 邻域洪泛：
          实测打乱顺序会让 **30.16% / 32.84%** 的胞换归属 ⇒ 初始条件不是良定义的；
          而且它是**各向同性**的，丢掉了取向 —— 方向错了：基底晶粒同样是定向凝固的产物。
        新规则（顺序无关 + 带取向）：冷区每个胞归给 min_g sup_g(x) 的晶粒
          （= 各晶粒的 KD 包络"谁先到"；t=0 时 l_g 全为 0、V 相同 ⇒ 就是各向异性 Voronoi）。
        max_iter 只为兼容保留，不再使用。
        """
        cold = T < T_thresh
        n0 = int(((self.gid == 0) & cold).sum())
        seeds = [(g, self.seeds[g]) for g in range(1, len(self.axes))
                 if self.seeds[g] is not None]
        ti = np.argwhere((self.gid == 0) & cold)
        M = len(ti)
        if M and seeds:
            best = np.full(M, np.inf)
            bg = np.full(M, 1 << 30, np.int64)
            chunk = 400000
            for g, sg in seeds:
                g = int(g)
                for a in range(0, M, chunk):
                    b = min(a + chunk, M)
                    ix = ti[a:b, 0]; iy = ti[a:b, 1]; iz = ti[a:b, 2]
                    # 精确剪枝: sup_g(x) = Σ_a|p_a·Δ| >= |Δ|（正交基上 Σ|c| >= sqrt(Σc²)），
                    # 所以 |Δ| 已经大于当前最优的胞不可能赢 ⇒ 跳过。结果与不剪枝逐位相同。
                    d2 = ((ix - sg[0])**2 + (iy - sg[1])**2 + (iz - sg[2])**2).astype(np.float64)
                    sub = d2 <= (best[a:b] / self.dx) ** 2
                    if not sub.any():
                        continue
                    tmp_best = best[a:b]; tmp_bg = bg[a:b]
                    tmp_sup = np.full(b - a, np.inf)
                    tmp_sup[sub] = self.envelope_sup(g, ix[sub], iy[sub], iz[sub])
                    upd = sub & ((tmp_sup < tmp_best) | ((tmp_sup == tmp_best) & (g < tmp_bg)))
                    tmp_best[upd] = tmp_sup[upd]
                    tmp_bg[upd] = g
            self.gid[ti[:, 0], ti[:, 1], ti[:, 2]] = bg
        done = (self.gid > 0) & cold
        self.ts[done] = -1.0            # 负时间 = t=0 之前就是固相
        self.L[done] = 0.0
        if hasattr(self, "fs"):
            self.fs[done] = 1.0
            self.c_sol[done] = C0_V
            if hasattr(self, "A_liq"):
                self.A_liq[done] = 0.0
                self.c_liq = self.A_liq / np.maximum(1.0 - self.fs, 1e-6)
        return int(n0 - ((self.gid == 0) & cold).sum())


    # ---------------------------------------------------------------- 形核
    def add_grain(self, i, j, k, quat=None):
        g = len(self.axes)
        q = quat if quat is not None else rand_quat(self.rng)
        self.axes.append(quat_to_axes(q))
        self.seeds.append((i, j, k))
        self.gid[i, j, k] = g
        self.L[i, j, k] = 0.0
        self.ts[i, j, k] = self.t
        self._ensure_Lg()[g] = 0.0          # 逐晶粒包络半轴（新默认判定用）
        Lc, CC = self._ensure_cell_state()  # capture="cell" 的逐胞 (ℓ, 中心)
        Lc[i, j, k] = self.INIT_OCT
        CC[i, j, k, :] = (i + 0.5, j + 0.5, k + 0.5)
        return g

    def nucleate_substrate(self, n_grains, layer=1, jitter=0.0):
        """熔池底部/侧壁的外延形核：在底面若干胞上布种子（取向随机或给定）。"""
        idx = [(i, j, 0) for i in range(self.nx) for j in range(self.ny)]
        self.rng.shuffle(idx)
        for (i, j, k) in idx[:n_grains]:
            self.add_grain(i, j, k)
        return n_grains

    def nucleate_substrate_grid(self, nx_g, ny_g, quats=None):
        """规则布种（便于与解析解对照）：底面 nx_g x ny_g 个种子。"""
        li = np.linspace(0, self.nx - 1, nx_g).astype(int)
        lj = np.linspace(0, self.ny - 1, ny_g).astype(int)
        out = []
        m = 0
        for i in li:
            for j in lj:
                q = None if quats is None else quats[m % len(quats)]
                out.append(self.add_grain(i, j, 0, q))
                m += 1
        return out

    def nucleate_bulk(self, T, dT_mean, dT_sigma, N_max, dt, c_l=None, m_L=None):
        """体形核（CET）：连续形核谱 dN/ddT = Gaussian，中心 dT_mean，总密度 N_max [1/m3]。

        【2026-09-23 物理修法】驱动量可切到【成分过冷】(MATH_FRAMEWORK §4.2(b) 的判据
        "成分过冷 ΔT_CS > ΔT_n")：
            给了 c_l 与 m_L 时，用【局部液相线】T_L = T_LIQ + m_L (c_l - c_0)，
            驱动量 dT = clip(T_L - T, 0, inf)。
        ⇒ 这样在【热前沿之前】被溶质富集的液体里也会形核 —— 这才是 LPBF 里
          等轴晶/细晶带（CET）的物理来源；纯热过冷版本只能在热前沿【之后】形核，
          等于把 CET 退化掉了。
        """
        from scipy.special import erf as _erf
        if c_l is not None and m_L is not None:
            T_L = T_LIQ + m_L * (np.asarray(c_l) - C0_V)     # 局部液相线（线性化）
            dT = np.clip(T_L - T, 0.0, None)
        else:
            dT = np.clip(T_LIQ - T, 0.0, None)
        cdf = 0.5 * (1.0 + _erf((dT - dT_mean) / (dT_sigma * math.sqrt(2.0))))
        Nv = N_max * cdf                                  # 累积数密度 1/m3
        expect = Nv * self.dx ** 3
        if not hasattr(self, "_Nv_done"):
            self._Nv_done = np.zeros(self.shape)
        inc = np.clip(expect - self._Nv_done, 0.0, None)
        self._Nv_done = np.maximum(self._Nv_done, expect)
        cand = (self.gid == 0) & (inc > 0)
        if not cand.any():
            return 0
        draws = self.rng.random(self.shape) < inc
        ii, jj, kk = np.where(cand & draws)
        for i, j, k in zip(ii, jj, kk):
            self.add_grain(int(i), int(j), int(k))
        return len(ii)

    # =============================================== 逐晶粒连续包络（新默认判定）
    # 物理依据: MATH_FRAMEWORK 4.4
    #     晶粒 g 的虚拟包络 = 晶体坐标系下的 L1 球 { sum_a |p_a.(x-x_g)| <= l_g }
    #     径向函数  r_g(n_hat) = l_g / sum_a |p_a . n_hat|
    #     推进      l_g(t+dt) = l_g(t) + V(dT) dt
    # 职责划分（审计 §5 的架构结论）：
    #     **热场定"哪个胞此刻可固"，包络竞争定"归哪个晶粒"** —— 不再让 CA 前沿去追等温线、
    #     追不上就交给"格点洪泛"（那个构件既顺序依赖又会自形核，已删）。
    def _ensure_Lg(self):
        n = len(self.axes)
        if getattr(self, "_Lg", None) is None or len(self._Lg) < n:
            old = getattr(self, "_Lg", None)
            self._Lg = np.zeros(n + 8)
            if old is not None:
                self._Lg[:len(old)] = old[:len(self._Lg)]
        return self._Lg

    def _ensure_Lc(self):
        """逐胞包络尺寸（m）。capture="cell" 用：每个前沿胞按【自己的局部 ΔT】累加；
        判据相对【该晶粒的种子】做精确 L1 隶属；捕获后【继承】(不扣减) ⇒ 不累加路径代价。"""
        if getattr(self, "_Lcarr", None) is None:
            self._Lcarr = np.zeros(self.shape)
        return self._Lcarr

    # ===== capture="cell"：精确复刻 ExaCA 的 decentered octahedron =====
    # 每胞状态：c = 该胞八面体中心（胞单位, 3 个 float），ℓ = 尺寸（胞单位）
    #   · ℓ 每步按【该胞自己的局部 V(ΔT)】累加：ℓ += V·dt/dx
    #   · 捕获判据：crit = Σ_a|p_a·(x_邻 − c_src)| ≤ ℓ_src   （与 ExaCA 的 max_i|(x0)·f_i| 等价）
    #   · 捕获后新胞的 (c, ℓ) 由【捕获面三角形的角点几何】现算（ExaCA::createNewOctahedron）
    INIT_OCT = 0.01                      # ExaCA 的 _init_oct_size 默认值（胞）

    def _ensure_cell_state(self):
        if getattr(self, "_cellC", None) is None or self._cellC.shape != self.shape + (3,):
            self._cellC = np.zeros(self.shape + (3,), np.float64)   # 八面体中心（胞单位）
            self._cellL = np.zeros(self.shape, np.float64)          # 尺寸 ℓ（胞单位）
        return self._cellL, self._cellC

    def cell_crit_vec(self, gvec, ccoord, xcoord):
        """crit = Σ_a|p_a·(x − c)|（逐个 pair 用其所属晶粒的取向）。ccoord/xcoord 为胞单位。"""
        out = np.zeros(len(gvec))
        for g in np.unique(gvec):
            m = (gvec == g)
            Pg = self.axes[int(g)]
            d = xcoord[m] - ccoord[m]
            out[m] = (np.abs(d @ Pg[:, 0]) + np.abs(d @ Pg[:, 1]) + np.abs(d @ Pg[:, 2]))
        return out

    def _oct_recenter_one(self, g, csrc, xnbr, crit):
        """ExaCA src/CAinterface.hpp::createNewOctahedron 的逐胞标量实现（逐行转写）"""
        Pg = self.axes[int(g)]
        s3 = 3.0 ** 0.5
        x0 = xnbr - csrc
        pos = [(Pg[:, k] @ x0) > 0.0 for k in range(3)]
        diag = [Pg[:, k] * (2.0 * (1.0 if pos[k] else 0.0) - 1.0) for k in range(3)]
        T = [csrc + crit * diag[k] for k in range(3)]
        dd = [float(np.linalg.norm(T[k] - xnbr)) for k in range(3)]
        c01 = dd[0] < dd[1]; c12 = dd[1] < dd[2]; c20 = dd[2] < dd[0]
        ti = 2 * (int(c20) - int(c12)) * int(c20) + (int(c12) - int(c01)) * int(c12)
        mind = dd[ti]; Tc = T[ti]
        T1 = T[(ti + 1) % 3]; T2 = T[(ti + 2) % 3]
        d1 = float(np.linalg.norm(Tc - T1)); d2 = float(np.linalg.norm(Tc - T2))
        j1, j1n, j2, j2n = 0.0, d1, 0.0, d2
        if mind != 0.0:
            j1 = float((xnbr - T1) @ (Tc - T1)) / max(d1, 1e-30); j1n = d1 - j1
            j2 = float((xnbr - T2) @ (Tc - T2)) / max(d2, 1e-30); j2n = d2 - j2
        l12 = 0.5 * (min(j1, s3) + min(j1n, s3))
        l13 = 0.5 * (min(j2, s3) + min(j2n, s3))
        lnew = (2.0 ** 0.5) * max(l12, l13)
        cap = Tc - csrc
        nrm = float(np.linalg.norm(cap))
        uhat = cap / nrm if nrm > 1e-30 else np.zeros(3)
        return lnew, Tc - lnew * uhat

    def oct_recenter(self, gvec, csrc, xnbr, crit, s3=3.0**0.5):
        """逐胞标量版（正确性优先；矢量优化以后再做）"""
        M = len(gvec)
        lnew = np.empty(M); cnew = np.empty((M, 3))
        for i in range(M):
            ln, cn = self._oct_recenter_one(gvec[i], np.asarray(csrc[i], float),
                                            np.asarray(xnbr[i], float), float(crit[i]))
            lnew[i] = ln; cnew[i] = cn
        return lnew, cnew

    def grow_envelopes(self, dt, V, front):
        """逐晶粒推进包络半轴 l_g：取该晶粒【前沿胞】上 V 的 lg_percentile 分位（默认 90%）。

        为什么用分位而不是裸 max：单个热胞（例如池心）不该把整个晶粒的包络带走；
        分位既保留"最深尖端驱动"的物理，又对单点噪声稳健。lg_percentile=100 即裸 max。
        """
        Lg = self._ensure_Lg()
        if not front.any():
            return Lg
        gf = self.gid[front]
        Vf = V[front]
        for g in np.unique(gf):
            if g <= 0:
                continue
            vg = float(np.percentile(Vf[gf == g], self.lg_percentile))
            Lg[int(g)] += vg * dt
        return Lg

    def envelope_sup(self, g, ix, iy, iz):
        """sup_g(x) = sum_a |p_a.(x - x_g)|（单位 m），x 取胞心。
        ix/iy/iz 是胞索引（标量或任意形状数组）。"""
        Pp = self.axes[int(g)]
        s = self.seeds[int(g)]
        dxv = (np.asarray(ix) - s[0]) * self.dx
        dyv = (np.asarray(iy) - s[1]) * self.dx
        dzv = (np.asarray(iz) - s[2]) * self.dx
        return (np.abs(Pp[0, 0] * dxv + Pp[1, 0] * dyv + Pp[2, 0] * dzv) +
                np.abs(Pp[0, 1] * dxv + Pp[1, 1] * dyv + Pp[2, 1] * dzv) +
                np.abs(Pp[0, 2] * dxv + Pp[1, 2] * dyv + Pp[2, 2] * dzv))

    def envelope_sup_vec(self, gvec, ix, iy, iz):
        """一组 (晶粒, 胞) 对的 sup（每对晶粒取自己的取向）。"""
        gvec = np.asarray(gvec, dtype=np.int64)
        out = np.zeros(len(gvec))
        for g in np.unique(gvec):
            m = (gvec == g)
            out[m] = self.envelope_sup(int(g), np.asarray(ix)[m], np.asarray(iy)[m],
                                       np.asarray(iz)[m])
        return out

    def capture_ratio(self, gvec, ix, iy, iz):
        """ratio = l_g / sup_g(x)：无量纲的"该晶粒的包络还差多远"。
        ratio >= 1 表示包络已经覆盖该胞。"""
        Lg = self._ensure_Lg()
        sup = self.envelope_sup_vec(gvec, ix, iy, iz)
        return Lg[np.asarray(gvec, dtype=np.int64)] / np.maximum(sup, 1e-30)

    # ---------------------------------------------------------- 取向阈值表
    def _thr_tables(self):
        """对每个偏移量 o，给出 thr[g] = dx * sum_a |p_a . o|。
        这正是八面体 {|u1|+|u2|+|u3| <= L} 在方向 o 上的支撑距离。"""
        ng = len(self.axes)
        if getattr(self, "_tabs_ng", None) == ng and hasattr(self, "_tabs"):
            return self._tabs
        tabs = {}
        for o, _ in OFFSETS:
            t = np.zeros(ng + 8)          # 预留新增晶粒
            for g in range(1, ng):
                P = self.axes[g]
                t[g] = self.dx * sum(abs(float(P[:, a] @ np.array(o))) for a in range(3))
            tabs[o] = t
        self._tabs, self._tabs_ng = tabs, ng
        return tabs

    # ------------------------------------------------- 偏移配对（统一入口）
    def _pair(self, o, box):
        """返回 (src_idx, tgt_idx)：两个 np.ix_ 索引元组，使 src 处的胞与 tgt=src+o 配对。

        非周期轴上与旧的 slice 实现**逐位等价**（arange(s0,s1) 就是原来的 slice(s0,s1)）；
        周期轴（self.periodic）上环绕：ti = (si + d) % n。
        两个索引数组都只含【互不相同】的下标，所以 `A[tgt] = ...` 的赋值语义与 slice 版一致。
        box = (i0,i1,j0,j1,k0,k1) 是当前活动窗口（滑动窗口的落点）。"""
        i0, i1, j0, j1, k0, k1 = box
        if not any(self.periodic):
            # 快速路径：与历史实现逐位一致（slice）。
            rr = []
            for (a0, a1, d, n) in ((i0, i1, o[0], self.nx),
                                   (j0, j1, o[1], self.ny),
                                   (k0, k1, o[2], self.nz)):
                s0 = max(a0, -d)
                s1 = min(a1, n - d)
                if s1 <= s0:
                    return None
                rr.append((s0, s1, s0 + d, s1 + d))
            return (tuple(slice(r[0], r[1]) for r in rr),
                    tuple(slice(r[2], r[3]) for r in rr))
        si_ax, ti_ax = [], []
        for (a0, a1, d, n, per) in ((i0, i1, o[0], self.nx, self.periodic[0]),
                                    (j0, j1, o[1], self.ny, self.periodic[1]),
                                    (k0, k1, o[2], self.nz, self.periodic[2])):
            if per:
                if d == 0:
                    return None                      # 周期轴上 d=0 即自身配对，无意义
                si = np.arange(a0, a1)
                ti = (si + d) % n
            else:
                s0 = max(a0, -d)
                s1 = min(a1, n - d)
                if s1 <= s0:
                    return None
                si = np.arange(s0, s1)
                ti = si + d
            si_ax.append(si)
            ti_ax.append(ti)
        return np.ix_(*si_ax), np.ix_(*ti_ax)


    # ------------------------------------------------------------ 单步推进
    def step(self, dt, T, window=None, c_l=None):
        """推进一步。T 为当前温度场（K）。

        window: 可选 (i0,i1,j0,j1,k0,k1) 限制计算区（滑动窗口的 active region）。
        c_l:    可选，逐胞【液相成分】。给了就启用【成分过冷】驱动 —— 见下。

        【2026-09-23 物理修法：把溶质接进"生长"判据】
        物理上的 CET（等轴晶带）要求热前沿【之前/附近】的液体因溶质富集而被压低液相线：
            ΔT_CS = [T_LIQ + m_L (c_l - c_0)] - T
        只把 c_l 接进【形核】(nucleate_bulk) 不够 —— 决定形貌的是【生长】。
        这里把驱动量换成 ΔT_CS，且**只在前沿固相胞上生效**：
          · 前沿胞里的 c_l 正是"枝晶间液相成分" = 固相此刻正在由它长出的那个液相
            ⇒ 用它是物理正确的局部液相线；
          · 非前沿（深处）固相胞不参与新胞捕获，保持纯热驱动即可（避免无液相的胞
            被 c_liq 的 floor 值污染）。
        c_l=None（默认）时行为与历史完全一致。
        """
        gid = self.gid
        front = self._front_solid()
        dT = np.clip(T_LIQ - T, 0.0, None)
        if c_l is not None:
            dT_cs = np.clip(T_LIQ + M_L * (np.asarray(c_l) - C0_V) - T, 0.0, None)
            dT = np.where(front, dT_cs, dT)
            self.n_cs_cells = int(front.sum())
        V, dT_used, _, _ = self.irf.capped(dT)
        # 越界计数: 只有【前沿固相胞】(有液相邻居的固相胞) 的 V 才真正驱动生长。
        # 已凝固的冷区 dT 必然很大但那里不生长; 纯液相胞的 V 也从不被使用。
        self.n_front_steps = getattr(self, "n_front_steps", 0) + int(front.sum())
        self.n_dT_below = getattr(self, "n_dT_below", 0) + int(
            np.count_nonzero(front & (dT > 0.0) & (dT < self.irf.dT_lo)))
        self.n_dT_high = getattr(self, "n_dT_high", 0) + int(np.count_nonzero(front & (dT > self.irf.dT_hi)))
        self.n_dT_super = getattr(self, "n_dT_super", 0) + int(np.count_nonzero(front & (dT <= 0.0)))

        solid = gid > 0
        liquid = ~solid

        # ---- 1) 只在前沿邻域推进包络（active region） ----
        if window is None:
            window = self.active_box(front=front)      # 复用本步已算好的前沿（省一次全域扫描）
        elif window == "full":    # 关掉滑动窗口（用于一致性对照）
            window = (0, self.nx, 0, self.ny, 0, self.nz)
        i0, i1, j0, j1, k0, k1 = window
        sl = (slice(i0, i1), slice(j0, j1), slice(k0, k1))
        Ls = self.L[sl]
        Ls += V[sl] * dt * solid[sl]
        self.L[sl] = Ls
        if self.capture == "envelope":
            self.grow_envelopes(dt, V, front)      # 逐晶粒 l_g 推进（新默认）

        # ---- 2) 捕获：26 邻居，decentered octahedron ----
        tabs = self._thr_tables()
        flat = np.arange(gid.size).reshape(gid.shape)
        best = np.full(gid.shape, -1.0)
        bsrc = np.full(gid.shape, -1, np.int64)
        bthr = np.zeros(gid.shape)

        if self.capture == "cell":
            # ---- 精确复刻 ExaCA：逐胞 (c, ℓ) + 角点几何重定心 ----
            Lc, CC = self._ensure_cell_state()
            Lc += (V * dt / self.dx) * front              # ℓ（胞单位）按局部 V 累加
            fi_all = np.argwhere(front)
            if len(fi_all):
                inside = ((fi_all[:, 0] >= i0) & (fi_all[:, 0] < i1) & (fi_all[:, 1] >= j0) &
                          (fi_all[:, 1] < j1) & (fi_all[:, 2] >= k0) & (fi_all[:, 2] < k1))
                fi0 = fi_all[inside]
                if len(fi0):
                    fg0 = gid[fi0[:, 0], fi0[:, 1], fi0[:, 2]].astype(np.int64)
                    fL0 = Lc[fi0[:, 0], fi0[:, 1], fi0[:, 2]]
                    fc0 = CC[fi0[:, 0], fi0[:, 1], fi0[:, 2]]
                    src0 = (fi0[:, 0] * self.ny + fi0[:, 1]) * self.nz + fi0[:, 2]
                    bf = best.reshape(-1)
                    sf = bsrc.reshape(-1)
                    bgid = np.full(gid.size, 1 << 30, np.int32)
                    for oi, (o, _) in enumerate(OFFSETS):
                        tx = fi0[:, 0] + o[0]; ty = fi0[:, 1] + o[1]; tz = fi0[:, 2] + o[2]
                        inb = ((tx >= 0) & (tx < self.nx) & (ty >= 0) & (ty < self.ny) &
                               (tz >= 0) & (tz < self.nz))
                        if not inb.any():
                            continue
                        tx, ty, tz = tx[inb], ty[inb], tz[inb]
                        gg, LL, CCs = fg0[inb], fL0[inb], fc0[inb]
                        sflat = src0[inb]
                        free = gid[tx, ty, tz] == 0
                        if not free.any():
                            continue
                        tx, ty, tz = tx[free], ty[free], tz[free]
                        gg, LL, CCs, sflat = gg[free], LL[free], CCs[free], sflat[free]
                        xn = np.stack([tx + 0.5, ty + 0.5, tz + 0.5], 1).astype(np.float64)
                        crit = self.cell_crit_vec(gg, CCs, xn)      # 从【该胞八面体中心】量的精确 L1
                        cand = crit <= LL
                        if not cand.any():
                            continue
                        cx, cy, cz = tx[cand], ty[cand], tz[cand]
                        gg2, LL2 = gg[cand], LL[cand]
                        crit2, sfl2 = crit[cand], sflat[cand]
                        fidx = (cx * self.ny + cy) * self.nz + cz
                        if self.cell_tiebreak == "firstcome":
                            # ExaCA 口径：key = 源胞索引*26 + 偏移序号，取最小（= 先到先得）
                            key = sfl2.astype(np.float64) * 26.0 + oi
                            upd = key < bf[fidx]
                            bf[fidx[upd]] = key[upd]
                            sf[fidx[upd]] = sfl2[upd]
                        else:
                            ratio = LL2 / np.maximum(crit2, 1e-30)
                            prev = bf[fidx]; prevg = bgid[fidx]
                            upd = (ratio > prev) | ((ratio == prev) & (gg2 < prevg))
                            bf[fidx[upd]] = ratio[upd]
                            sf[fidx[upd]] = sfl2[upd]
                            bgid[fidx[upd]] = gg2[upd]

        if self.capture == "envelope":
            # ---- 新默认：逐晶粒连续包络 + 外延邻接 + 逐胞 argmax（与语句顺序无关）----
            # 候选胞 x 被 g 捕获 <=> sup_g(x) <= l_g 且 x 的 26 邻居里有 g 的胞（外延附着）
            Lg = self._ensure_Lg()
            wsub = (slice(i0, i1), slice(j0, j1), slice(k0, k1))
            gwin = gid[wsub]
            fw = front[wsub]
            if fw.any():
                fi = np.argwhere(fw)
                fg = gwin[fi[:, 0], fi[:, 1], fi[:, 2]]
                bf = best.reshape(-1)
                sf = bsrc.reshape(-1)
                for g in np.unique(fg):
                    g = int(g)
                    if g <= 0 or Lg[g] <= 0.0:
                        continue
                    sel = fi[fg == g]                      # 该晶粒的前沿胞（窗口内）
                    lo = sel.min(0) - 1
                    hi = sel.max(0) + 2
                    lo = np.maximum(lo, 0)
                    hi = np.minimum(hi, (i1 - i0, j1 - j0, k1 - k0))
                    if np.any(hi <= lo):
                        continue
                    gx, gy, gz = np.meshgrid(np.arange(i0 + lo[0], i0 + hi[0]),
                                             np.arange(j0 + lo[1], j0 + hi[1]),
                                             np.arange(k0 + lo[2], k0 + hi[2]),
                                             indexing="ij")
                    sup = self.envelope_sup(g, gx, gy, gz)
                    cand = (gid[gx, gy, gz] == 0) & (sup <= Lg[g])
                    if not cand.any():
                        continue
                    ci = np.argwhere(cand)
                    cx = gx[ci[:, 0], ci[:, 1], ci[:, 2]]
                    cy = gy[ci[:, 0], ci[:, 1], ci[:, 2]]
                    cz = gz[ci[:, 0], ci[:, 1], ci[:, 2]]
                    ok = np.zeros(len(ci), bool)
                    for o, _ in OFFSETS:
                        ox = cx + o[0]; oy = cy + o[1]; oz = cz + o[2]
                        inb = ((ox >= 0) & (ox < self.nx) & (oy >= 0) & (oy < self.ny) &
                               (oz >= 0) & (oz < self.nz))
                        vv = np.zeros(len(ci), np.int32)
                        vv[inb] = gid[ox[inb], oy[inb], oz[inb]]
                        ok |= (vv == g)
                    if not ok.any():
                        continue
                    cx = cx[ok]; cy = cy[ok]; cz = cz[ok]
                    sup_ok = sup[ci[ok, 0], ci[ok, 1], ci[ok, 2]]
                    ratio = Lg[g] / np.maximum(sup_ok, 1e-30)
                    fidx = (cx * self.ny + cy) * self.nz + cz
                    upd = ratio > bf[fidx]             # 平局（测度零）保留先到者=小 gid
                    bf[fidx[upd]] = ratio[upd]
                    sf[fidx[upd]] = g

        if self.capture == "analytic":
            # ---- 连续八面体判据（种子相对）：去掉格点路径代价的取向偏差 ----
            # 到达判据:  support_g(x) = sum_a |p_a . (x - x_g)|  <=  L_g
            # 谁的比例 L_g / support_g 最大谁先到 => 直接比较该比例。
            X, Y, Z = self.coords()
            for g in range(1, len(self.axes)):
                sg = self.seeds[g]
                if sg is None:
                    continue
                Lg = float(self.L[sg[0], sg[1], sg[2]])
                if Lg <= 0.0:
                    continue
                Pg = self.axes[g]
                # 包围盒: support >= |d|  =>  只在 |d| <= Lg 内可能被捕获
                m = int(math.ceil(Lg / self.dx)) + 1
                i0g = max(window[0], sg[0] - m); i1g = min(window[1], sg[0] + m + 1)
                j0g = max(window[2], sg[1] - m); j1g = min(window[3], sg[1] + m + 1)
                k0g = max(window[4], sg[2] - m); k1g = min(window[5], sg[2] + m + 1)
                if i1g <= i0g or j1g <= j0g or k1g <= k0g:
                    continue
                dxv = (X[i0g:i1g, j0g:j1g, k0g:k1g] - X[sg[0], sg[1], sg[2]])
                dyv = (Y[i0g:i1g, j0g:j1g, k0g:k1g] - Y[sg[0], sg[1], sg[2]])
                dzv = (Z[i0g:i1g, j0g:j1g, k0g:k1g] - Z[sg[0], sg[1], sg[2]])
                sup = (np.abs(Pg[0, 0] * dxv + Pg[1, 0] * dyv + Pg[2, 0] * dzv) +
                       np.abs(Pg[0, 1] * dxv + Pg[1, 1] * dyv + Pg[2, 1] * dzv) +
                       np.abs(Pg[0, 2] * dxv + Pg[1, 2] * dyv + Pg[2, 2] * dzv))
                sub = (slice(i0g, i1g), slice(j0g, j1g), slice(k0g, k1g))
                free = gid[sub] == 0
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = np.where(sup > 0, Lg / np.maximum(sup, 1e-300), -1.0)
                cand = free & (ratio >= 1.0)
                if not cand.any():
                    continue
                upd = cand & (ratio > best[sub])
                np.copyto(best[sub], np.where(upd, ratio, best[sub]))
                np.copyto(bsrc[sub], np.where(upd, np.int64(g), bsrc[sub]))
                np.copyto(bthr[sub], np.where(upd, sup, bthr[sub]))
        for o, _ in OFFSETS if self.capture == "decentered" else []:
            pr = self._pair(o, window)
            if pr is None:
                continue
            sx, tx = pr
            gS = gid[sx]
            # 源必须实心且落在窗口内的实心集合里
            ok_src = gS > 0
            if not ok_src.any():
                continue
            thr = tabs[o][gS]
            ratio = np.where(ok_src, self.L[sx] / np.maximum(thr, 1e-300), -1.0)
            free = gid[tx] == 0
            cand = (ratio >= 1.0) & free
            if not cand.any():
                continue
            prev = best[tx]
            upd = cand & (ratio > prev)
            best[tx] = np.where(upd, ratio, prev)
            bsrc[tx] = np.where(upd, flat[sx], bsrc[tx])
            bthr[tx] = np.where(upd, thr, bthr[tx])

        cap = bsrc >= 0
        n_new = int(cap.sum())
        if n_new:
            ti = flat[cap]
            # decentering: 新胞继承【剩余】半对角 = L - 已用掉的距离
            if self.capture == "decentered":
                si = bsrc[cap]                        # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            elif self.capture == "cell":
                si = bsrc[cap]                        # 存的是扁平胞索引（源胞）
                Lc, CC = self._ensure_cell_state()
                gg = self.gid.flat[si].astype(np.int64)
                cs = CC.reshape(-1, 3)[si]            # 源胞八面体中心（胞单位）
                tix = ti % self.nz
                tiy = (ti // self.nz) % self.ny
                tixx = ti // (self.nz * self.ny)
                xn = np.stack([tixx + 0.5, tiy + 0.5, tix + 0.5], 1).astype(np.float64)
                crit = self.cell_crit_vec(gg, cs, xn)
                ln, cn = self.oct_recenter(gg, cs, xn, crit)
                self.gid.flat[ti] = self.gid.flat[si]
                Lc.flat[ti] = ln
                CC.reshape(-1, 3)[ti] = cn
            else:
                self.gid[cap] = bsrc[cap]             # analytic: 存的是 grain id
                self.L[cap] = 0.0                     # 未使用
            self.ts.flat[ti] = self.t + dt
            self.Tc.flat[ti] = T.flat[ti]
            self.n_captured_steps += 1

        self.t += dt
        # 热力学约束: T < T_SOL 的液相必须为固相（外延并入 / 隔离则自发形核）
        self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", None), dt=dt)
        if self.chem_local:
            self.solidify_local(dt, T, V)          # 可选的逐胞亚网格路径（Window B 用）
        self._fs_hist.append((self.t, float((self.gid > 0).mean())))
        # 【新默认化学的驱动量】合金【体积元】= t=0 时的液相区（熔池）。
        # 旧 scheil_chemistry() 用【全域】固相分数：基底占 91.5% ⇒ 池一凝固 f 就跳到 0.95，
        # 液相成分立刻顶到 F_MIN 天花板 ⇒ 池内 c 几乎常数（审计 F5）。
        if getattr(self, "_liq0", None) is None:
            self._liq0 = (self.gid == 0)
            self._n_liq0 = max(int(self._liq0.sum()), 1)
            self._fpool_hist = [(0.0, 0.0)]
        f_pool = 1.0 - float((self._liq0 & (self.gid == 0)).sum()) / self._n_liq0
        self._fpool_hist.append((self.t, f_pool))
        return n_new

    # --------------------------- 热力学约束（T < T_SOL 必须为固相）
    def _front_solid(self):
        """有液相邻居的固相胞 —— 只有这些胞的 V 真正驱动包络推进。"""
        solid = self.gid > 0
        liquid = ~solid
        nb = np.zeros_like(solid)
        full = (0, self.nx, 0, self.ny, 0, self.nz)
        for o, _ in OFFSETS:
            pr = self._pair(o, full)
            if pr is None:
                continue
            sx, tx = pr
            nb[tx] |= liquid[sx]
        return solid & nb


    def thermal_capture(self, T, spontaneous=None, mode=None, dt=None):
        """热力学约束: T < T_SOL 的液相胞必须为固相（合金不能在固相线以下长期保持液态）。

        【2026-09-23 审计后重写】旧实现是"按 OFFSETS 顺序的 26 邻域洪泛（最多 6 层）"，实测两个致命问题：
          (1) 归属依赖扫描顺序 —— 碰撞前沿有 0.13~0.31% 的胞换主、晶粒面积 ±10%；
          (2) 洪泛后残留的孤立冷液相会【每胞一颗】自发形核（41^3 盒造出 68578 个 1 胞晶粒）。
        新规则（逐胞 argmax，与语句顺序无关、无层数上限、**不自形核**）：
          每个冷液相胞 x，在【与 x 26 邻接】的固相晶粒里选
              key = (ratio = l_g/sup_g(x) 最大, 然后 sup 最小, 然后 gid 最小)   ← 全序、确定
          · 相邻固相取"归属前的固相图"，所以整步结果与遍历顺序无关；
          · 没有固相邻居的冷液相胞**不**被强行固化（物理上它需要形核，不是"立即变固")，
            只计入 self.n_unresolved —— 下一步前沿推进后它们会有邻居。
        mode:
          "count"（默认）只计数记账；"fail" 一旦出现未归属就抛错（严格档）；
          "spectrum" 走连续形核谱（需 self.bulk_spec=(dT_mean,dT_sigma,N_max) 与 dt）。
        返回 (n_assigned, n_unresolved)。
        """
        if mode is None:
            mode = "none" if spontaneous is False else "count"
        cold = T < T_SOL
        ti = np.argwhere((self.gid == 0) & cold)
        M = len(ti)
        n_th = 0
        n_left = M
        if M:
            Lg = self._ensure_Lg()
            best = np.full(M, -1.0)
            bsup = np.full(M, np.inf)
            bg = np.full(M, 1 << 30, np.int64)
            for o, _ in OFFSETS:
                ox = ti[:, 0] + o[0]; oy = ti[:, 1] + o[1]; oz = ti[:, 2] + o[2]
                inb = ((ox >= 0) & (ox < self.nx) & (oy >= 0) & (oy < self.ny) &
                       (oz >= 0) & (oz < self.nz))
                nb = np.zeros(M, np.int32)
                nb[inb] = self.gid[ox[inb], oy[inb], oz[inb]]
                sn = np.nonzero(nb > 0)[0]
                if not len(sn):
                    continue
                gg = nb[sn].astype(np.int64)
                sup = self.envelope_sup_vec(gg, ti[sn, 0], ti[sn, 1], ti[sn, 2])
                rr = Lg[gg] / np.maximum(sup, 1e-30)
                b_r = best[sn]; b_s = bsup[sn]; b_g = bg[sn]
                upd = (rr > b_r) | ((rr == b_r) & ((sup < b_s) | ((sup == b_s) & (gg < b_g))))
                sel = sn[upd]
                best[sel] = rr[upd]; bsup[sel] = sup[upd]; bg[sel] = gg[upd]
            got = bg < (1 << 30)
            if got.any():
                gi = np.nonzero(got)[0]
                ii, jj, kk = ti[gi, 0], ti[gi, 1], ti[gi, 2]
                self.gid[ii, jj, kk] = bg[gi]
                self.ts[ii, jj, kk] = self.t
                self.Tc[ii, jj, kk] = T[ii, jj, kk]
                n_th = int(got.sum())
                n_left = int(M - n_th)
        if n_left and mode == "spectrum":
            spec = getattr(self, "bulk_spec", None)
            if spec is None:
                raise RuntimeError('thermal_capture: mode="spectrum" 需要 self.bulk_spec=(dT_mean,dT_sigma,N_max)')
            n_new = self.nucleate_bulk(T, spec[0], spec[1], spec[2], dt if dt else 0.0)
            self.n_spont = getattr(self, "n_spont", 0) + int(n_new)
            n_left = int(((self.gid == 0) & cold).sum())
        if n_left and mode == "fail":
            raise RuntimeError(
                "thermal_capture: %d 个 T<T_SOL 的液相胞在 26 邻域里没有固相邻居（无法外延）。"
                "若确实需要形核请设 mode='spectrum' 并给 bulk_spec。" % n_left)
        self.n_thermal = getattr(self, "n_thermal", 0) + n_th
        self.n_unresolved = getattr(self, "n_unresolved", 0) + n_left
        return n_th, n_left


    def active_box(self, margin=None, front=None):
        """前沿（有液相邻居的实心胞）的包围盒 + margin。
        这就是「滑动窗口」在本实现中的落点：只在前沿邻域计算。

        front 可传入 step() 里已经算好的 `_front_solid()` 结果，避免每步重复做一次
        26 偏移的全域扫描（审计 N9 的冗余项）。传 None 时自带计算，行为不变。"""
        if margin is None:
            margin = 2
        solid = self.gid > 0
        if not solid.any():
            return (0, self.nx, 0, self.ny, 0, self.nz)
        if front is None:
            liquid = ~solid
            nb_liq = np.zeros_like(solid)
            full = (0, self.nx, 0, self.ny, 0, self.nz)
            for o, _ in OFFSETS:
                pr = self._pair(o, full)
                if pr is None:
                    continue
                sx, tx = pr
                nb_liq[tx] |= liquid[sx]
            front = solid & nb_liq
        if not front.any():
            front = solid
        idx = np.where(front)
        return (max(0, idx[0].min() - margin), min(self.nx, idx[0].max() + 1 + margin),
                max(0, idx[1].min() - margin), min(self.ny, idx[1].max() + 1 + margin),
                max(0, idx[2].min() - margin), min(self.nz, idx[2].max() + 1 + margin))

    # ---------------------------------------------------------------- 化学
    def _dtf_field(self, T, V):
        """局部凝固时间 dt_f(x) = dT0 /(|grad T| V(x))（框架 4.5 的 t_f = dT0/(GR)）。
        梯度取不到/异常时退化为常数 dtf_default。"""
        try:
            gz, gy, gx = np.gradient(T, self.dx)
        except Exception:
            return np.full(self.shape, self.dtf_default)
        G = np.sqrt(gx * gx + gy * gy + gz * gz)
        with np.errstate(divide="ignore", invalid="ignore"):
            dtf = (T_LIQ - T_SOL) / np.maximum(G * V, 1e-12)
        bad = (~np.isfinite(dtf)) | (dtf <= 0.0) | (dtf > 1.0e3)
        return np.where(bad, self.dtf_default, dtf)

    def _diffuse_liquid(self, dt):
        """液相扩散（显式有限体积，通道面积 = (1-fs)^tort）: dA/dt = div(D_L (1-fs) grad c_L)。
        稳定性: dt <= dx^2/(2 D_L)（本框架 dx=3um, D_L=9.5e-9 时上限 ~0.47 s，远大于 dt）。"""
        A = self.A_liq
        a = np.clip(1.0 - self.fs, 0.0, 1.0) ** self.tort
        cl = A / np.maximum(a, 1e-6)
        coef = self.D_L * dt / self.dx ** 2
        dA = np.zeros(self.shape)
        for o, _ in OFFSETS:
            if sum(abs(v) for v in o) != 1:
                continue
            pr = self._pair(o, (0, self.nx, 0, self.ny, 0, self.nz))
            if pr is None:
                continue
            sx, tx = pr
            a1 = a[sx]; a2 = a[tx]
            den = a1 + a2
            # 【调和平均】面导电率：任一侧没有液相(1-fs=0) ⇒ 面通量必须为 0。
            # 用算术平均会让 1-fs->0 的胞里 c_L=A/(1-fs) 被放大成假浓度，A 指数爆炸
            # （2026-09-23 实测：算术平均使 A 由 0.036 涨到 3382）。
            harm = np.where(den > 1e-12, 2.0 * a1 * a2 / np.maximum(den, 1e-30), 0.0)
            flux = coef * harm * (cl[tx] - cl[sx])
            dA[sx] += flux
            dA[tx] -= flux
        Anew = A + dA
        self.n_Aclip = int((Anew < 0.0).sum())
        self.A_liq = np.maximum(Anew, 0.0)

    def solidify_local(self, dt, T, V, diffuse=True):
        """逐胞局部凝固：fs 沿 age/dt_f 从 0 长到 1-F_MIN，固相按 k*c_L 取走溶质。

        物理: 枝晶间液膜不可约（框架 4.5 的 F_MIN）⇒ fs 饱和在 1-F_MIN，
        c_L 因此有物理上限 c0*F_MIN^(k-1)（不再发散）。守恒量 = A_liq + fs*c_sol（逐胞）。
        返回本步"正在凝固"的胞数。"""
        cap = np.isfinite(self.ts) & (self.ts >= 0.0)
        pending = cap & (self.fs < 1.0 - F_MIN - 1e-12)
        if not pending.any():
            self.c_liq = np.minimum(self.A_liq / np.maximum(1.0 - self.fs, 1e-6),
                                    C0_V * F_MIN ** (K_V - 1.0))
            self.cl = self.c_liq
            self.c_cell = self.fs * self.c_sol + (1.0 - self.fs) * self.c_liq
            return 0
        dtf = self._dtf_field(T, V)
        age = np.where(cap, np.maximum(self.t - self.ts, 0.0), 0.0)
        fs_new = np.clip(age / np.maximum(dtf, 1e-30), 0.0, 1.0 - F_MIN)
        df = np.where(cap, np.maximum(fs_new - self.fs, 0.0), 0.0)
        need = df > 0.0
        n_act = int(need.sum())
        if n_act:
            cl_here = self.c_liq[need]
            take = K_V * cl_here * df[need]
            fs_old = self.fs[need]
            denom = fs_old + df[need]
            self.c_sol[need] = np.where(
                denom > 0,
                (self.c_sol[need] * fs_old + take) / np.maximum(denom, 1e-30), C0_V)
            self.A_liq[need] = self.A_liq[need] - take
            self.fs[need] = fs_old + df[need]
        if diffuse:
            self._diffuse_liquid(dt)
        self.c_liq = self.A_liq / np.maximum(1.0 - self.fs, 1e-6)
        self.n_clip = int((self.c_liq > C0_V * F_MIN ** (K_V - 1.0)).sum())
        self.c_liq = np.minimum(self.c_liq, C0_V * F_MIN ** (K_V - 1.0))
        self.cl = self.c_liq
        self.c_cell = self.fs * self.c_sol + (1.0 - self.fs) * self.c_liq
        return n_act

    def total_solute(self):
        """守恒量（逐胞）: A_liq + fs*c_sol = c0（不受 c_L 显示截断影响）。"""
        return self.A_liq + self.fs * self.c_sol

    def mass_balance(self):
        """全局质量守恒: <总溶质>/c0（1.0 = 守恒）。"""
        return float(self.total_solute().mean() / C0_V)

    def fs_at(self, t):
        th = np.array(self._fs_hist)
        return float(np.interp(t, th[:, 0], th[:, 1]))

    def finalize_chemistry(self, k_eff=None):
        """**新默认化学**：合金【体积元（= t=0 的液相区，即熔池）】尺度的 Scheil 路径 + 逐胞捕获时刻。

        物理（框架 4.5 的口径，但把体积元取对）：
            c_l(f) = c0 (1-f)^(k-1),   c_s(f) = k c_l(f),   f = 体积元的固相分数
          体积元的固相分数在该胞【被捕获那一刻】的值 f_i 决定该胞刚沉积那一层壳的成分：
            cl_i = c_l(f_i)  (正则化到 F_MIN) ;  c_i = k cl_i
        逐胞质量恒等式 f*c_s_avg + (1-f)*c_l = c0 保证【体积元总体守恒】（见 mass_balance）。
        基底（ts<0，t=0 前就是固相）取 c = c0（审计 F6：旧代码给 k*c0 = 0.0227，偏低 37%）。
        输出字段:
          self.cl / self.c_liq  -> 该胞凝固时刻的【枝晶间液相成分】（Window C 输入）
          self.c  / self.c_sol  -> 该胞沉积固相的成分（Window B 输入）
          self.c_cell           -> 体平均成分 = c0（守恒恒等式 ⇒ 全域常数，作为守恒核对）
        返回 (cl_min, cl_max, c_sol_min, c_sol_max)。
        """
        kk = K_V if k_eff is None else float(k_eff)
        cap = np.isfinite(self.ts)
        hist = getattr(self, "_fpool_hist", None)
        if hist is None or len(hist) < 2:
            th = np.array([[0.0, 0.0], [1.0, 1.0]])
        else:
            th = np.array(hist)
        f = np.clip(np.interp(np.where(cap, self.ts, 0.0), th[:, 0], th[:, 1]), 0.0, 1.0)
        f_eff = np.minimum(f, 1.0 - F_MIN)
        cl = C0_V * (1.0 - f_eff) ** (kk - 1.0)
        self.cl_max = C0_V * F_MIN ** (kk - 1.0)
        self.c_last = self.cl_max
        self.fcap = np.where(cap, f, 0.0)
        self.cl = np.where(cap, cl, C0_V)
        self.c_liq = self.cl
        self.c = np.where(cap, kk * cl, C0_V)
        self.c_sol = self.c
        # 基底（t=0 前就是固相）与仍为液相的胞都取 c0
        sub = np.isfinite(self.ts) & (self.ts < 0.0)
        self.c[sub] = C0_V
        self.c_sol[sub] = C0_V
        self.cl[sub] = C0_V
        self.c_liq[sub] = C0_V
        self.c_cell = np.full(self.shape, C0_V)
        return (float(self.cl[cap].min()), float(self.cl[cap].max()),
                float(self.c[cap].min()), float(self.c[cap].max()))

    def mass_balance(self):
        """全局质量守恒核对（体积元口径）:
             f*c_s_avg(f) + (1-f)*c_l(f) = c0  ⇒ 每个胞体平均 = c0。
        返回 <体平均成分>/c0（1.0 = 守恒）。"""
        cap = np.isfinite(self.ts) & (self.ts >= 0.0)
        if not cap.any():
            return 1.0
        f = np.clip(self.fcap[cap], 0.0, 1.0)
        cs_avg = np.where(f > 1e-12, C0_V * (1.0 - (1.0 - f) ** K_V) / np.maximum(f, 1e-12),
                          K_V * C0_V)
        cl = C0_V * (1.0 - np.minimum(f, 1.0 - F_MIN)) ** (K_V - 1.0)
        tot = f * cs_avg + (1.0 - f) * cl
        # 基底胞按 c0 计（它们不在 cap 里），整体平均
        n_sub = int((np.isfinite(self.ts) & (self.ts < 0.0)).sum())
        val = float(tot.sum() + n_sub * C0_V) / float(cap.sum() + n_sub)
        return val / C0_V

    def scheil_chemistry(self):
        """【旧路径，保留】用【全域】固相分数代入 Scheil 闭式。

        ⚠ 2026-09-23 审计（F5）：基底占全域 91.5% ⇒ 池凝固时 f_global 从 0.915 跳到 1
        ⇒ 池内 c 几乎常数、60% 顶在 F_MIN 天花板。Window C 的输入请用 finalize_chemistry()。
        本方法保留是为了不改变既有回归判据的数值（G5a~G5f）。

        设 f = 该胞被捕获时刻的【全局固相分数】，沿全局 Scheil 路径：
            c_liquid(f)    = c0 (1-f)^(k-1)            <- 该时刻液相成分
            c_solid_avg(f) = c0 [1-(1-f)^k]/f          <- 已形成固相的平均成分
        质量守恒恒等式（逐点精确，check_scheil_conservation 会数值验证）：
            f*c_solid_avg + (1-f)*c_liquid = c0

        逐胞取出：
            cl[c] = c_liquid(f(t_capture))    <- Window C 的输入（胞界/枝晶间）
            c[c]  = k * cl[c]                 <- 该胞在凝固前沿刚沉积那一层的成分
        胞内完整剖面由 Pi 给出（下一步, MATH_FRAMEWORK 4.6）。
        """
        cap = np.isfinite(self.ts)
        self.fcap = np.zeros(self.shape)
        self.cl = np.full(self.shape, C0_V)
        self.cl_max = C0_V * F_MIN ** (K_V - 1.0)   # 正则化上限: (1-f_eff)=F_MIN
        if not cap.any():
            return None
        th = np.array(self._fs_hist)
        f = np.clip(np.interp(self.ts[cap], th[:, 0], th[:, 1]), 0.0, 1.0)
        self.fcap[cap] = f
        # 正则化: 截断 Scheil 奇点 (f -> 1 时 c_l 发散), 物理上是枝晶间液膜孤立
        f_eff = np.minimum(f, 1.0 - F_MIN)
        c_l = C0_V * (1.0 - f_eff) ** (K_V - 1.0)
        self.cl[cap] = c_l
        self.c[cap] = K_V * c_l
        self.c_last = C0_V * (1.0 - F_MIN) ** (K_V - 1.0)
        return self.c_last

    def check_scheil_conservation(self, fs=None):
        """质量守恒恒等式 f*c_solid_avg + (1-f)*c_liquid = c0（逐点精确）。"""
        if fs is None:
            fs = np.array([0.0, 0.2, 0.5, 0.8, 0.95, 0.99])
        out = []
        for f in fs:
            cs = C0_V * (1.0 - (1.0 - f) ** K_V) / max(f, 1e-12)
            cl = C0_V * (1.0 - f) ** (K_V - 1.0)
            out.append((float(f), float(f * cs + (1.0 - f) * cl)))
        return out

    # -------------------------------------------------------------- 诊断量
    def solid_fraction(self):
        return float((self.gid > 0).mean())

    def grain_ids(self):
        u = np.unique(self.gid)
        return u[u > 0]

    def gb_area(self):
        """晶界网络面积：只统计【面邻居】(6 个方向) 且 grain ID 不同。棱/角邻不共享面，计入会高估。"""
        A = 0.0
        full = (0, self.nx, 0, self.ny, 0, self.nz)
        for o, _ in OFFSETS:
            if sum(abs(v) for v in o) != 1:      # 只有面邻居贡献面积（棱/角邻不共享面）
                continue
            pr = self._pair(o, full)
            if pr is None:
                continue
            sx, tx = pr
            a, b = self.gid[sx], self.gid[tx]
            m = (a > 0) & (b > 0) & (a != b)
            A += m.sum() * self.dx ** 2
        return float(A)

    def grain_volume_frac(self):
        s = (self.gid > 0).sum()
        out = {}
        for g in self.grain_ids():
            out[int(g)] = float((self.gid == g).sum() / max(s, 1))
        return out

    # ---------------------------------------------------------------- 输出
    def save(self, path):
        np.savez_compressed(path, gid=self.gid, L=self.L, ts=self.ts, Tc=self.Tc,
                            c=self.c, t=self.t, dx=self.dx, shape=np.array(self.shape))
        return path

    def write_vtk(self, path, fields=("gid", "c", "ts")):
        """极简 legacy VTK（structured points），可直接用 ParaView 看 3D 结果。"""
        nx, ny, nz = self.shape
        with open(path, "w") as f:
            f.write("# vtk DataFile Version 3.0\nCA3D\nASCII\n")
            f.write("DATASET STRUCTURED_POINTS\nDIMENSIONS %d %d %d\n" % (nx, ny, nz))
            f.write("ORIGIN 0 0 0\nSPACING %g %g %g\n" % (self.dx, self.dx, self.dx))
            f.write("POINT_DATA %d\n" % (nx * ny * nz))
            for name in fields:
                arr = getattr(self, name).astype(np.float64)
                f.write("SCALARS %s double 1\nLOOKUP_TABLE default\n" % name)
                np.savetxt(f, arr.ravel(order="F"), fmt="%.6g")
        return path


def run(ca, T_func, t_end, dt, bulk=None, verbose=True, every=None, stop_when_solid=False):
    """时间推进。T_func(t) -> 温度场。bulk=(dT_mean,dT_sigma,N_max) 打开体形核。

    stop_when_solid=True: 域内没有液相（gid 全 > 0）就停。**纯效率改动**：
    液相归零之后 CA 没有任何事可做（审计实测：熔池算例第 103 步就全固，
    却跑到 1083 步 ⇒ 90.5% 的步是白算，省 ~94% 机时；结果逐位不变）。"""
    n = int(round(t_end / dt))
    hist = []
    for s in range(n):
        ca.t = s * dt
        T = T_func(ca.t)
        nnew = ca.step(dt, T)
        nbulk = 0
        if bulk is not None:
            nbulk = ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)
        if every and (s % every == 0 or s == n - 1):
            hist.append(dict(t=ca.t, fs=ca.solid_fraction(),
                             ng=len(ca.grain_ids()), new=nnew, bulk=nbulk))
            if verbose:
                print("  t={:.3e} s  fs={:.3f}  grains={}  new={} bulk={}".format(
                    ca.t, hist[-1]["fs"], hist[-1]["ng"], nnew, nbulk))
        if stop_when_solid and not (ca.gid == 0).any():
            break
    ca.scheil_chemistry()
    return hist
