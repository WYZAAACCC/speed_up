#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_lath.py —— **板条身份层**（对应 `BLOCK_DERIVATION.md` §2/§3/§4）。

## 它解决什么

现有引擎（`windowB_surface.py`）里 **场下标 = 变体下标**（双射，13 个场）。
后果：两根**同变体**的板条必须共用一个场 ⇒ **它们从初始条件起就是同一个对象**，
块内的低角晶界**结构上表示不出来**（`R1_PROBLEM_LEDGER.md` A-5）。

本模块把双射推广为 **场 = 板条、场 → 变体多对一**：

    phi[0]              = 母相 β
    phi[1..M]           = M 根板条，各自带 vmap[i] ∈ {1..12} 与一个小转动 omega_i

⇒ 同变体的两根板条成为**两个场** ⇒ 它们之间出现**第三类界面 F3**（低角晶界），
面能由 **Read–Shockley** γ_RS(θ) 给出。

## 三类面片（`BLOCK_DERIVATION.md` §2.3）

| 类 | 条件 | 面能 | 本模块 |
|---|---|---|---|
| F1 | 恰一侧是母相 | @@\\gamma_1(n)@@ | **不动**（退回 `gamma0` 标量） |
| F2 | @@v(k)\\ne v(l)@@ | @@\\gamma_2(n)@@ | **不动**（退回 `gamma0` 标量） |
| F3 | @@v(k)=v(l)\\ne0@@ | @@\\gamma_{\\rm RS}(\\theta_{kl})@@ | **本模块新增** |

★ **只改 F3** ⇒ 单变量改动：F1/F2 逐位不变，可与全部归档读数对照。

## 为什么 γ 可以"后乘"

`windowB_surface._stiff_of` 里三条分支（`herring_stiffness_cusp` / `herring_stiffness`
/ 无分支）**对 `gamma0` 全部严格线性**（见 `windowB_surface.py:293-328`）
⇒ 可以把**逐胞数组**当 `gamma0` 传进去，几何/迎风/Herring 代码**一行都不用动**。
`_selftest` 里 S-4 对这个线性性做了数值核对。

## 记账（改动前必读）

* `theta` 在层级 1（`BLOCK_DERIVATION.md` §2.2）下是**输入**，不是涌现量
  ⇒ **不得**声称"取向差自组织"。
* F3 迁移率**沿用** `M(n)`（低角晶界真实机制是位错芯扩散，与相界不同）
  ⇒ 记账 S-5；符号与量级对（F3 面法向 = `n*` ⇒ M 降 `e^{-3.5}`=0.030）。
* `gamma_ab`（α′/β 面能）**不在本模块的改动范围**：现有 F1 的 γ 是已标定的
  `[占位]` 0.15，改它会动全部归档读数。本模块只在**报告**里用它做润湿判据 C-1。
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ---------------------------------------------------------------------------
# 物理常数（Ti-6Al-4V α′/α′ 低角晶界）—— 与 BLOCK_DERIVATION.md §3.2 逐字对应
# ---------------------------------------------------------------------------
A_ALPHA = 0.2950e-9        # m     [文献] WINDOWB_PARAMS.md §1
E_TI64 = 114.0e9           # Pa    [文献]
NU_TI64 = 0.34             # -     [文献]
THETA_M_DEG = 15.0         # deg   [文献] Read–Shockley 平台角
# γ_α′β [J/m²]，Murzinova 2017 Lett.Mater. 7(1) 55-59, DOI 10.22226/2410-3535-2017-1-55-59
GAMMA_AB = dict(T600C=(0.298, 0.429), T975C=(0.201, 0.337))


def rs_constants(G=None, b=None, nu=None, theta_m_deg=None):
    """Read–Shockley 的两个常数：@@E_0=Gb/[4\\pi(1-\\nu)]@@、@@\\gamma_m=E_0\\theta_m@@。

    推导（`BLOCK_DERIVATION.md` §3.2）：对称倾转晶界 = 间距 @@D=b/\\theta@@ 的刃位错墙
    ⇒ 单位面积位错数 @@\\theta/b@@，单位长度位错能 @@\\frac{Gb^2}{4\\pi(1-\\nu)}\\ln(R/r_0)@@
    ⇒ @@\\gamma=E_0\\theta(1-\\ln(\\theta/\\theta_m))@@，在 @@\\theta_m@@ 处接平台 @@\\gamma_m=E_0\\theta_m@@。
    """
    G = E_TI64 / (2.0 * (1.0 + NU_TI64)) if G is None else float(G)
    b = A_ALPHA if b is None else float(b)
    nu = NU_TI64 if nu is None else float(nu)
    tm = THETA_M_DEG if theta_m_deg is None else float(theta_m_deg)
    E0 = G * b / (4.0 * np.pi * (1.0 - nu))
    return E0, E0 * np.deg2rad(tm)


E0_TI64, GAMMA_M_TI64 = rs_constants()


def gamma_rs(theta, gamma_m=None, theta_m_deg=None):
    """Read–Shockley 面能 [J/m²]。`theta` 单位**弧度**，可为数组。

    @@\\gamma_{\\rm RS}(\\theta)=\\gamma_m\\frac{\\theta}{\\theta_m}
        \\big(1-\\ln\\frac{\\theta}{\\theta_m}\\big)@@，@@\\theta\\ge\\theta_m@@ 时取平台 @@\\gamma_m@@。

    性质（`BLOCK_DERIVATION.md` §3.1，`_bk_verify.py` A-2 逐条核过）：
      P1 @@\\gamma(0)=0@@ —— 与"根本没有界面"连续
      P2 @@C^1@@ 连续（@@\\gamma'(\\theta_m)=0@@）—— Gibbs–Thomson 项**无尖点**
      P3 @@\\gamma@@ 与 @@\\mathbf n@@ 无关 —— 与现有 Herring 各向异性**正交**
    """
    gm = GAMMA_M_TI64 if gamma_m is None else float(gamma_m)
    tm = np.deg2rad(THETA_M_DEG if theta_m_deg is None else float(theta_m_deg))
    th = np.asarray(theta, float)
    x = th / tm
    out = gm * x * (1.0 - np.log(np.clip(x, 1e-300, None)))
    return np.where(x >= 1.0, gm, out)


def gamma_rs_deg(theta_deg, **kw):
    return gamma_rs(np.deg2rad(theta_deg), **kw)


# ---------------------------------------------------------------------------
# 取向差（disorientation）：hcp 的**真转动**点群 = D6（阶 12）
# ---------------------------------------------------------------------------
def rodrigues(w):
    """旋转矢量 -> 旋转矩阵。"""
    w = np.asarray(w, float)
    th = float(np.linalg.norm(w))
    if th < 1e-300:
        return np.eye(3)
    k = w / th
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + np.sin(th) * K + (1.0 - np.cos(th)) * (K @ K)


def rot_angle(R):
    """旋转矩阵的转角 [rad]（@@\\arccos((\\mathrm{tr}R-1)/2)@@）。"""
    c = np.clip((np.trace(np.asarray(R, float)) - 1.0) / 2.0, -1.0, 1.0)
    return float(np.arccos(c))


def d6_ops():
    """hcp 点群 6/mmm 的**真转动**子群 D6（阶 12）：
       @@\\{C_{6z}^k,\\ C_{6z}^k C_{2x}\\}@@，@@k=0..5@@。

    ★ 为什么是 12 而不是 24：取向差要在晶体点群的**转动**上取极小
      （反演/镜面会把"转动"变成"非正常转动"，其"角"不是取向差）。
      `_bk_verify.py` A-1 核过：非恒等元的最小转角 = **60°**。
    """
    C6 = rodrigues([0.0, 0.0, np.pi / 3.0])
    C2 = rodrigues([np.pi, 0.0, 0.0])
    ops, M = [], np.eye(3)
    for _ in range(6):
        ops.append(M.copy())
        ops.append(M @ C2)
        M = M @ C6
    return ops


_D6 = d6_ops()


def disorientation(Ra, Rb, ops=None):
    """@@\\theta=\\min_{s\\in D6}\\arccos\\!\\big(\\tfrac12[\\mathrm{tr}(s\\,\\Delta R)-1]\\big)@@，
       @@\\Delta R=R_aR_b^{\\top}@@。返回弧度。"""
    ops = _D6 if ops is None else ops
    dR = np.asarray(Ra, float) @ np.asarray(Rb, float).T
    return min(rot_angle(np.asarray(s, float) @ dR) for s in ops)


# ---------------------------------------------------------------------------
# 板条表
# ---------------------------------------------------------------------------
def default_omega(M, theta_max_deg=5.0, axis=None, mode='ladder', seed=7):
    """构造 @@M@@ 个**小转动矢量** @@\\boldsymbol\\omega_i@@ [rad]（`BLOCK_DERIVATION.md` §2.2）。

    * `mode='ladder'`：转角按 **0, @@\\Delta@@, 2@@\\Delta@@, …, @@\\theta_{\\max}@@** 阶梯排布
      ⇒ 相邻板条差 @@\\Delta\\theta@@、首末差 @@\\theta_{\\max}@@
      ⇒ **同一块内出现一串不同的 @@\\theta@@** ⇒ γ 表非平凡（块内"转动梯度"是真实特征）。
      ⚠ **记账（`R30_AUDIT_LEDGER.md` §129 / P1-45）**：本模式把**总张角**固定成
        `theta_max_deg` 再**均分**给 `M−1` 个间隔 ⇒ 相邻取向差
        @@\\Delta\\theta=\\theta_{\\max}/(M-1)@@ **随 M 变**。
        实测（`_r172_omega_audit.py`）：**相邻同变体对的 γ 跨 M=2…20 变化 7.91 倍**
        （M=2 时 γ=0.2771=**1.108×γ₀** ⇒ **倒挂**；M=20 时 0.0350=0.140×γ₀）。
        ⇒ 块内界面能**不是材料常数，而是"你列了几根板条"的副作用**。
        ⇒ 想扫"M 的影响"而**不**混淆"块内界面能"时，用下面的 `'perstep'`。
    * `mode='perstep'`：★ **逐界面步长**模式（`§129` 的修法）。
      `theta_max_deg` **被解释成"每一步的取向差"** `Δθ`（材料性质）⇒
      @@\\omega_i=(i\\cdot\\Delta\\theta)\\cdot\\mathbf a@@。
      **⇒ 相邻同变体对的 γ 与 M 无关**（M=2 与 M=20 相同）。
      ⚠ **退化等价性（内置正对照）**：`perstep` 且 `Δθ = θ_max/(M−1)` 时，
      结果必须与 `ladder` **逐位相同** ⇒ `_r182_omega_check.py` 的 P-1 判据。
    * `mode='random'`：均匀随机（负对照用）。

    `axis` 默认取**长轴 @@\\mathbf a@@**（倾转轴落在板条长度方向）——
    这样界面（惯习面）**含**倾转轴 ⇒ 纯倾转晶界，与 Read–Shockley 的前提一致。
    """
    if M <= 1:
        return np.zeros((max(M, 0), 3))
    if mode == 'ladder':
        th = np.linspace(0.0, np.deg2rad(theta_max_deg), M)
    elif mode == 'perstep':
        # ★ `§129`：`theta_max_deg` 在这里是**逐界面步长**，不是总张角。
        th = np.arange(M, dtype=float) * np.deg2rad(theta_max_deg)
    elif mode == 'random':
        rng = np.random.default_rng(seed)
        th = np.deg2rad(theta_max_deg) * rng.random(M)
    else:
        raise ValueError('mode 必须是 ladder/perstep/random，收到 %r' % (mode,))
    u = np.array([1.0, 0.0, 0.0]) if axis is None else np.asarray(axis, float)
    u = u / (np.linalg.norm(u) + 1e-300)
    return th[:, None] * u[None, :]


class LathTable(object):
    """把「变体表」铺成「板条表」。

    参数
    ----
    variants : 长度 M 的变体标号列表（1..NV），第 i 项 = 第 i 根板条的变体
    omegas   : (M,3) 小转动矢量 [rad]；`None` ⇒ 全零（**注意：全零 ⇒ γ=0**）
    eps0_var : 长度 NV 的 3×3 本征应变表（默认从 `T16_verify_rve` 取）
    npref_var: 长度 NV+1 的惯习面法向表（index 0 = 母相，可缺）
    gamma0   : F1/F2 沿用的标量面能（= 引擎的 `gamma`，**不改**）

    产出（供引擎直接吃）
    -------------------
    `eps0`   : 长度 M 的列表（逐场复制，**同变体逐位相同**）
    `npref`  : dict {i: n_i}（i=1..M），另含 {0: 母相}（若给了）
    `gtab`   : (M+1,M+1) 逐**面片身份**的基础面能；**F1/F2 = NaN**（⇒ 调用方退回标量）
    """

    def __init__(self, variants, omegas=None, eps0_var=None, npref_var=None,
                 gamma0=0.15, gamma_m=None, theta_m_deg=None, f2_lam=0.0,
                 theta_ref_deg=None, label=''):
        self.vmap = [int(v) for v in variants]
        self.M = len(self.vmap)
        self.nreg = self.M + 1
        self.gamma0 = float(gamma0)
        self.gamma_m = GAMMA_M_TI64 if gamma_m is None else float(gamma_m)
        self.theta_m_deg = THETA_M_DEG if theta_m_deg is None else float(theta_m_deg)
        self.label = label
        if self.M < 1:
            raise ValueError('至少要一根板条')
        if self.M + 1 > 32760:
            # ★★★ R474（2026-10-01，任务(3)）：守卫从 **120** 放宽到 **32760**。
            #   原守卫 `M+1 > 120` 的理由是「`region()` 用 int8」（有符号上限 127）
            #   ⇒ 实际天花板 **nv ≤ 119**。而任务(5) 要"填满 ≥10 µm 盒子"需要
            #   **220–450 根**（`NEXT_TASKS_FOR_REVIEW.md §4.1`/`§202`）
            #   ⇒ **不改就做不了任务(5)**。
            #   现已把 `region()` 改成 `int16`（`windowB_surface.py:region()`）
            #   ⇒ 上限提到 **32760**（留 7 的余量，避免贴边）。
            #   ⚠ **这不是"够用就行"**：`nv` 还要受**内存**约束
            #     （`phi` 是 `(nv+1, N³)` —— N=160/nv=300 时 f64 就是 9.2 GB），
            #     所以本条只解除**表示**上限，**内存**上限由任务(4)/(5) 另算。
            raise ValueError('nreg=%d 超过 int16 安全上限（region() 用 int16）'
                             % (self.M + 1))
        self.omegas = (np.zeros((self.M, 3)) if omegas is None
                       else np.asarray(omegas, float).reshape(self.M, 3))

        # ---- 相对转动矩阵与取向差角 -------------------------------------
        self.Rs = [rodrigues(w) for w in self.omegas]
        self.theta = np.zeros((self.nreg, self.nreg))       # rad
        for i in range(self.M):
            for j in range(i + 1, self.M):
                t = disorientation(self.Rs[i], self.Rs[j])
                self.theta[i + 1, j + 1] = self.theta[j + 1, i + 1] = t
        # ★ 独立核对：同变体时（式 2.3）θ 应等于裸角 |ω_i − ω_j|
        self.theta_bare = np.zeros_like(self.theta)
        for i in range(self.M):
            for j in range(self.M):
                self.theta_bare[i + 1, j + 1] = float(
                    np.linalg.norm(self.omegas[i] - self.omegas[j]))

        # ---- 面能表 gtab ------------------------------------------------
        # F3（同变体、都在变体里）⇒ γ_RS(θ)；其余 = NaN ⇒ 调用方退回标量 gamma0
        self.gtab = np.full((self.nreg, self.nreg), np.nan)
        for i in range(self.M):
            for j in range(self.M):
                if i == j:
                    continue
                if self.vmap[i] == self.vmap[j]:
                    self.gtab[i + 1, j + 1] = float(
                        gamma_rs(self.theta[i + 1, j + 1], self.gamma_m,
                                 self.theta_m_deg))
        self.n_f3 = int(np.isfinite(self.gtab).sum() // 2)

        # ---- ★★★★ R164（**`R30_AUDIT_LEDGER.md` §122**）：**F2 的配对依赖** ----
        #   ## 缺口（本文件 `:23-25` 自己写着）
        #     F1/F2 的 γ **不动**（退回标量 `gamma0`）⇒ **V1/V3 界面的能量与 V1/V5 一样**
        #     ⇒ 这正是 `§112` 测到的「**生长竞争通道没有自协调机制**」的代码原因。
        #
        #   ## 补法的物理依据（由**模型自身**的量导出，不是外来参数）
        #     界面的**共格性**由失配 `Δε = ε_v − ε_w` 决定（`_r1_pairgeo2.py` 的 Hadamard 判据）。
        #     【实测，66 对】`‖Δε‖_F/scale` 的范围 0.1830–1.7056（中位 1.6776），而
        #     **同惯习面（同 packet）的那 6 对恰好 = 0.1830 = 全库最小**（小 9 倍）
        #     ⇒ **同 packet 界面失配极小 ⇒ 共格低能**（且实测 `g3 = 0`，共格判据吻合）。
        #
        #   ## 参数化（**λ = 0 ⇒ 逐位不变**，这是硬约束）
        #     γ_F2(v,w) = γ₀·[(1−λ) + λ·min(1, ‖Δε(v,w)‖_F / Δε_ref)]
        #     * **λ = 0** ⇒ **不填 `gtab`**（保持 NaN）⇒ 引擎走原标量路径 ⇒ **逐位不变**；
        #       ⚠ 注意：**不能**在 λ=0 时填成 `γ₀` —— 那会让 `facet_gamma_sub` 返回
        #       **数组**而不是标量，从而**换掉引擎的代码路径**（本文件 `:280` 的 `bad.all()`）。
        #     * **λ = 1** ⇒ 最共格的对（`‖Δε‖` 最小）拿到 `γ_lo = 0`，最不相容的退回 `γ₀`。
        #     ⇒ **packet 形成会被促进**（同惯习面的两个变体贴在一起变便宜）。
        #
        #   ⚠ **记账（`§122` 第五节）**：这条补法有一个**方向不显然**的后果 ——
        #     "促进 packet" 与 "`§94` 的 `k*=6` 六变体自协调"是**两个不同的物理目标**，
        #     而后者要求"6 个惯习面各取一个" ⇒ **在面内聚集可能反而远离 `r = 0` 那一族**。
        #     ⇒ **必须做受控对照（λ = 0 / 0.5 / 1），不得预设哪个对。**
        self.f2_lam = float(f2_lam)
        self.n_f2 = 0
        if self.f2_lam > 0.0:
            if eps0_var is None:
                raise ValueError('--f2-pair-gamma > 0 需要 `eps0_var`（拿来算失配 Δε）')
            _E = {i + 1: np.asarray(eps0_var[v - 1], float)
                  for i, v in enumerate(self.vmap)}
            self.de_ref = max(
                (float(np.linalg.norm(_E[i + 1] - _E[j + 1]))
                 for i in range(self.M) for j in range(i + 1, self.M)
                 if self.vmap[i] != self.vmap[j]), default=0.0)
            if self.de_ref > 0:
                for i in range(self.M):
                    for j in range(self.M):
                        if i == j or self.vmap[i] == self.vmap[j]:
                            continue
                        d = float(np.linalg.norm(_E[i + 1] - _E[j + 1]))
                        self.gtab[i + 1, j + 1] = self.gamma0 * (
                            (1.0 - self.f2_lam)
                            + self.f2_lam * min(1.0, d / self.de_ref))
                        self.n_f2 += 1
                self.n_f2 //= 2
        else:
            self.de_ref = float('nan')

        # ---- 逐场属性（从变体表复制）----------------------------------
        self.eps0_var = eps0_var
        self.npref_var = npref_var
        if eps0_var is not None:
            self.eps0 = [np.asarray(eps0_var[v - 1], float).copy()
                         for v in self.vmap]
        else:
            self.eps0 = None
        if npref_var is not None:
            self.npref = {}
            if 0 in npref_var or (isinstance(npref_var, dict)
                                  and npref_var.get(0) is not None):
                self.npref[0] = np.asarray(npref_var[0], float)
            for i, v in enumerate(self.vmap):
                self.npref[i + 1] = np.asarray(npref_var[v], float)
        else:
            self.npref = None

    # ---------------------------------------------------------------
    def is_f3(self, k, l):
        return (k > 0 and l > 0 and k != l
                and self.vmap[k - 1] == self.vmap[l - 1])

    def facet_gamma_sub(self, k, lsub, gamma0=None):
        """逐胞基础面能 @@\\gamma_\\Sigma@@（**只覆盖 F3**）。

        * 子盒里**没有** F3 ⇒ 返回**标量** `gamma0` ⇒ 引擎走原路径，**逐位不变**。
        * 有 F3 ⇒ 返回数组；非 F3 的胞填 `gamma0`。
        """
        g0 = self.gamma0 if gamma0 is None else float(gamma0)
        idx = np.clip(np.asarray(lsub, int), 0, self.nreg - 1)
        row = self.gtab[k]
        g = row[idx]
        bad = ~np.isfinite(g)
        if bad.all():
            return g0
        return np.where(bad, g0, g)

    # ---------------------------------------------------------------
    def theta_report(self):
        rows = []
        for i in range(self.M):
            for j in range(i + 1, self.M):
                gi = self.gtab[i + 1, j + 1]
                rows.append((i + 1, j + 1, self.vmap[i], self.vmap[j],
                             np.rad2deg(self.theta[i + 1, j + 1]),
                             np.rad2deg(self.theta_bare[i + 1, j + 1]),
                             gi))
        return rows

    def summary(self):
        L = ['LathTable M=%d nreg=%d  F3 面片对=%d  gamma0(标量,F1/F2)=%.4f'
             % (self.M, self.nreg, self.n_f3, self.gamma0)]
        for (i, j, vi, vj, td, tb, gi) in self.theta_report():
            if not np.isfinite(gi):
                tag = 'F2(γ 退回标量)'
            elif vi == vj:
                tag = 'F3 γ_RS=%.4f' % gi
            else:
                # ★ R164：F2 被 `--f2-pair-gamma` 填了配对值（`§122`）
                tag = '**F2 配对 γ=%.4f**' % gi
            L.append('   板条%d(V%d) - 板条%d(V%d): θ=%6.3f° (裸角 %6.3f°)  %s'
                     % (i, vi, j, vj, td, tb, tag))
        return '\n'.join(L)

    def wetting_report(self, gamma_ab=None):
        """润湿判据（`BLOCK_DERIVATION.md` (4.6)(4.7)）。

        @@\\gamma_{\\rm LAGB}(\\theta)>2\\gamma_{\\alpha'\\beta}@@ ⇒ 有膜；否则**干晶界**。
        返回 (max_gamma_rs, 2*gamma_ab, wets?)
        """
        gmax = float(np.nanmax(self.gtab)) if self.n_f3 else 0.0
        if gamma_ab is None:
            ga = float(np.mean(GAMMA_AB['T600C']))
        elif np.isscalar(gamma_ab):
            ga = float(gamma_ab)
        else:
            ga = float(np.mean(gamma_ab))
        return gmax, 2.0 * ga, bool(gmax > 2.0 * ga)


# ---------------------------------------------------------------------------
def build_from_T16(variants, omegas=None, gamma0=0.15, label='', **kw):
    """用仓库**唯一**的变体表（`T16_verify_rve` 的 `EPS0/NPF`）建板条表。
       ★ 不另建一份变体表 —— 避免"同一参数两处"（`AGENTS.md` §3.24）。"""
    from T16_verify_rve import EPS0, NPF                       # noqa: E402
    return LathTable(variants, omegas=omegas, eps0_var=EPS0, npref_var=NPF,
                     gamma0=gamma0, label=label, **kw)


def suggest_gap_nm(theta_deg=None, nstep=700, dx_nm=62.5, beta_h=3.5,
                   dT_dL=None):
    """**规划辅助（不是物理量）**：给定沿 @@\\mathbf n^*@@ 堆叠的初始间隔 @@g@@，
       估算 700 步内法向能长多厚 —— 用来决定"先分开、再长到一起"的布置。

    @@\\Delta T=\\frac{dT}{dL}\\cdot\\Delta L@@，@@\\Delta L\\approx v_{\\rm tip}t_{\\rm sim}@@，
    @@v_{\\rm tip}=M_0\\Delta f@@（尖端法向 ≈ @@\\mathbf a@@，未被钉扎）。
    `dT_dL` 默认取设计速率比 @@e^{-\\beta_h}=0.030@@ —— **那是设计值不是实测值**
    （R1 实测 `ΔT:ΔL`=0.027，见 `R1_VERDICTS_RESTATED.md`）。
    """
    dT_dL = float(np.exp(-beta_h)) if dT_dL is None else float(dT_dL)
    DF, M0 = 3.5e8, 1.0e-9
    dx = dx_nm * 1e-9
    dt = 0.15 * dx / (M0 * DF)
    dL = M0 * DF * nstep * dt                     # m
    return dT_dL * dL * 1e9, dL * 1e6             # (ΔT nm, ΔL µm)


# ===========================================================================
def _selftest():
    F = []

    def ck(tag, ok, det=''):
        print('  %-52s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
        if not ok:
            F.append(tag)

    print('=' * 84)
    print('windowB_lath._selftest')
    print('=' * 84)

    # --- S-1 点群 ---
    ck('S-1.1 |D6| == 12', len(_D6) == 12, 'n=%d' % len(_D6))
    ck('S-1.2 D6 全为真转动', all(abs(np.linalg.det(o) - 1) < 1e-12 for o in _D6))
    _a = sorted(round(np.degrees(rot_angle(o)), 6) for o in _D6)
    ck('S-1.3 非恒等元最小转角 = 60°', abs(_a[1] - 60.0) < 1e-6, '%.3f' % _a[1])

    # --- S-2 disorientation == 裸角（**只到 O(θ³)** —— 见式 (2.3)）---
    rng = np.random.default_rng(3)
    worst = 0.0
    for _ in range(500):
        wa = rng.normal(size=3); wa *= np.deg2rad(rng.uniform(0, 6)) / np.linalg.norm(wa)
        wb = rng.normal(size=3); wb *= np.deg2rad(rng.uniform(0, 6)) / np.linalg.norm(wb)
        Ra, Rb = rodrigues(wa), rodrigues(wb)
        worst = max(worst, abs(disorientation(Ra, Rb)
                               - float(np.linalg.norm(wa - wb))))
    ck('S-2.1 |disorientation − |ω_i−ω_j|| < 1e-3 rad (θ≤6°)', worst < 1e-3,
       'max|Δ|=%.2e rad' % worst)

    # ★ 偏差的**阶**必须是 3（式 2.3 写的是 +O(θ³)，不是 +O(θ²)）
    sc = np.array([0.2, 0.4, 0.8, 1.6, 3.2])          # 度
    dev = []
    for s in sc:
        w = 0.0
        rr = np.random.default_rng(11)
        for _ in range(4000):
            wa = rr.normal(size=3); wa *= np.deg2rad(rr.uniform(0, s)) / np.linalg.norm(wa)
            wb = rr.normal(size=3); wb *= np.deg2rad(rr.uniform(0, s)) / np.linalg.norm(wb)
            w = max(w, abs(disorientation(rodrigues(wa), rodrigues(wb))
                           - float(np.linalg.norm(wa - wb))))
        dev.append(w)
    dev = np.array(dev)
    slope = float(np.polyfit(np.log(np.deg2rad(sc)), np.log(dev), 1)[0])
    ck('S-2.2 偏差阶 == 3（式 2.3 的 O(θ³)）', 2.5 < slope < 3.5,
       'slope=%.3f  dev=%s' % (slope, np.array2string(dev, precision=2)))

    # --- S-3 RS 常数与表 ---
    E0, gm = rs_constants()
    ck('S-3.1 E0 == 1.5130', abs(E0 - 1.51300) < 5e-5, '%.6f' % E0)
    ck('S-3.2 gamma_m == 0.3961', abs(gm - 0.39610) < 5e-5, '%.6f' % gm)
    ok = True
    for th, ref in [(0.5, 0.058), (1, 0.098), (1.83, 0.150), (2, 0.159),
                    (3, 0.207), (5, 0.277), (10, 0.371), (15, 0.396)]:
        if abs(float(gamma_rs_deg(th)) - ref) > 1e-3:
            ok = False
        ck('S-3.3 γ_RS(%5.2f°) == %.3f' % (th, ref),
           abs(float(gamma_rs_deg(th)) - ref) <= 1e-3,
           '%.6f' % float(gamma_rs_deg(th)))
    ck('S-3.4 γ_RS(0) == 0 (P1)', abs(float(gamma_rs_deg(1e-9))) < 1e-9)
    e = 1e-6
    dL = (float(gamma_rs_deg(15 - e)) - gm) / (-np.deg2rad(e))
    ck('S-3.5 γ_RS\'(θ_m)=0 (P2, C¹)', abs(dL) < 1e-5, 'd=%.2e' % dL)

    # --- S-4 _stiff_of 对 gamma0 严格线性（本模块设计的前提）---
    import windowB_surface as W
    for nm, fn in (('herring_stiffness', W.herring_stiffness),
                   ('herring_stiffness_cusp', W.herring_stiffness_cusp)):
        c2 = np.array([0.0, 0.3, 1.0])
        if nm.endswith('cusp'):
            a1, a2 = fn(c2, 0.3, 0.4, 0.05), fn(c2, 0.6, 0.4, 0.05)
        else:
            a1, a2 = fn(c2, 0.3, 0.4, True), fn(c2, 0.6, 0.4, True)
        ck('S-4 %s 对 gamma0 线性' % nm,
           np.allclose(a2, 2.0 * a1, rtol=0, atol=1e-14),
           'max|2a1-a2|=%.2e' % np.max(np.abs(2 * a1 - a2)))

    # --- S-5 表构造：只有 F3 有 γ ---
    lt = LathTable([1, 1, 1], omegas=default_omega(3, 4.0))
    ck('S-5.1 3 根同变体 ⇒ F3 对 = 3', lt.n_f3 == 3, 'n_f3=%d' % lt.n_f3)
    ck('S-5.2 对角与母相行全 NaN',
       np.all(~np.isfinite(np.diag(lt.gtab)))
       and np.all(~np.isfinite(lt.gtab[0, :]))
       and np.all(~np.isfinite(lt.gtab[:, 0])))
    lt2 = LathTable([1, 2, 3], omegas=default_omega(3, 4.0))
    ck('S-5.3 异变体 ⇒ F3 对 = 0（γ 全退回标量）', lt2.n_f3 == 0,
       'n_f3=%d' % lt2.n_f3)
    lt3 = LathTable([1, 1, 2], omegas=default_omega(3, 4.0))
    ck('S-5.4 混合 [1,1,2] ⇒ F3 对 = 1', lt3.n_f3 == 1, 'n_f3=%d' % lt3.n_f3)

    # --- S-6 facet_gamma_sub：无 F3 必须返回标量（逐位兼容的守卫）---
    lsub = np.array([0, 1, 2, 3])
    g = lt2.facet_gamma_sub(1, lsub, 0.15)
    ck('S-6.1 无异变体时返回**标量** ⇒ 原路径逐位不变',
       np.ndim(g) == 0 and abs(float(g) - 0.15) < 1e-15, repr(g))
    g3 = lt3.facet_gamma_sub(1, lsub, 0.15)
    # lsub=[0,1,2,3] ⇒ 下标 2 处是"与板条2"（同变体 ⇒ F3），其余是母相/自己/异变体
    ck('S-6.2 有 F3 时返回**数组**且非 F3 胞填 0.15',
       np.ndim(g3) == 1 and abs(g3[0] - 0.15) < 1e-15 and abs(g3[1] - 0.15) < 1e-15
       and abs(g3[3] - 0.15) < 1e-15 and g3[2] > 0.15,
       np.array2string(g3, precision=4))

    # --- S-7 阶梯 ω ⇒ γ 单调升（正对照）---
    lt4 = LathTable([1] * 4, omegas=default_omega(4, 6.0))
    gg = [lt4.gtab[1, j] for j in (2, 3, 4)]
    ck('S-7.1 阶梯取向差 ⇒ γ_RS 单调增（正对照）',
       all(gg[i] < gg[i + 1] for i in range(2)),
       ' '.join('%.4f' % x for x in gg))
    ck('S-7.2 θ 与裸角一致（表内）',
       np.max(np.abs(lt4.theta - lt4.theta_bare)) < 1e-12,
       'max|Δ|=%.2e' % np.max(np.abs(lt4.theta - lt4.theta_bare)))

    # --- S-8 润湿判据 C-1 ---
    #   ★ C-1 的正确陈述是"**任何** θ 都不润湿"，所以判据要挂在 **γ_m**（γ_RS 的上确界）上，
    #     不是挂在这张表的最大值上（表里 θ_max=6° ⇒ γ=0.304 < γ_m=0.396）。
    gmax, g2ab, wets = lt4.wetting_report()
    ck('S-8.1 γ_RS(θ) ≤ γ_m 恒成立（含 θ>θ_m 平台）',
       gmax <= GAMMA_M_TI64 + 1e-12, 'gmax=%.4f  gm=%.4f' % (gmax, GAMMA_M_TI64))
    _lo = min(v[0] for v in GAMMA_AB.values())
    ck('S-8.2 C-1：γ_m=0.3961 < 2γ_αβ 的**最小**档 0.402(975°C,γ=0.201) ⇒ 任何 θ 都不润湿',
       GAMMA_M_TI64 < 2 * _lo,
       'gm=%.4f  2*%.3f=%.4f  余量=%.3fx' % (GAMMA_M_TI64, _lo, 2 * _lo,
                                            2 * _lo / GAMMA_M_TI64))
    ck('S-8.3 C-1：600°C 档余量 1.51~2.17x',
       abs(2 * GAMMA_AB['T600C'][0] / GAMMA_M_TI64 - 1.505) < 0.01,
       '%.3f ~ %.3f' % (2 * GAMMA_AB['T600C'][0] / GAMMA_M_TI64,
                        2 * GAMMA_AB['T600C'][1] / GAMMA_M_TI64))
    ck('S-8.4 wetting_report 在本表上给 wets=False', not wets,
       'gmax=%.4f 2g_ab=%.4f' % (gmax, g2ab))

    # --- S-9 全零 ω ⇒ γ=0（**必须显式警告**）---
    lt5 = LathTable([1, 1], omegas=np.zeros((2, 3)))
    ck('S-9.1 ω≡0 ⇒ F3 面能 = 0（物理上就是同一块晶体！）',
       lt5.n_f3 == 1 and abs(lt5.gtab[1, 2]) < 1e-15,
       'γ=%.3e  ⇒ 默认必须给非零 ω' % lt5.gtab[1, 2])

    print('-' * 84)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 84)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(_selftest())
