#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_km.py --- B1 子模型（β→α′，位移型/无扩散/athermal）的热力学-动力学闭合。

MATH_FRAMEWORK §5.5 把 Window B 拆成两个物理机制不同的子模型：
  B1: β → α′ （位移型、无扩散、athermal）   <-- 本模块
  B2: α′ → α+β（扩散型，守恒场）            <-- 另做
本模块补的正是 B1 缺的那一件：**T 依赖的驱动力 + 马氏体动力学（KM/Koistinen）**。
在此之前 PF3D 只有常数 dG（全库 M_s / Koistinen / athermal 0 命中 ⇒
IMPLEMENTATION_PLAN §7.9 的 W-1）。

物理与公式
----------
(1) 化学驱动力（每单位转变体积）[T]
      dG_chem(T) = -DS * (T0 - T)        [J/m^3]
    符号约定：dG < 0 表示 β→α′ 有利（与 PF3D/LevelSetMulti 的 df 约定一致）。
      * T0 : β/α′ 的化学平衡温度（dG = 0）
      * DS : 转变熵 = ΔS_tr / V_m        [J/(m^3 K)]

(2) 临界驱动力与 M_s [T]
      dG_chem(M_s) = dG_crit   =>   T0 = M_s + dG_crit / DS
    ⚠ **成核是输入**（HYBRID_FRAMEWORK §8 item 4）⇒ 本模块**不预测 M_s**，只把它当锚点。
      模型给出的是「**生长**的平衡分数 f_eq(dG)」。

(3) Koistinen–Marburger（唯象；作对照与反演）[L]
      f(T) = 1 - exp[-alpha (M_s - T)],   T < M_s
      <=> -ln(1-f) = alpha (M_s - T)      （对 T 线性 ⇒ 可最小二乘反演 alpha）

(4) athermal 指纹（判据用）
    * 固定 T（固定 dG）：到平台后 f 不随时间变
    * 改变 T：f 变
    => 「f 只依赖 T、不依赖 t」。任何有热激活（扩散型）的模型都会违反这一条。

(5) f_eq(dG)：把模型的能量（化学 + 弹性 + 界面）在给定 dG 下极小化得到的平衡分数。
    这是**模型自身**的 f(T) 预测；与 (3) 拟合得到的 alpha_KM 是**预测值**，不是输入。

记账
----
[L] 文献直读 | [T] 推导 | [A] 指派（必须做敏感度）
本模块**不引入任何没有标记的数**：DS 与 T0 以「敏感度带 / 由模型反解」给出，

而不是猜一个数。
"""

import math

import numpy as np

# =============================================================================
# 一、锚点与量级（全部带来源标记）
# =============================================================================

M_S_TI64 = 848.0           # K  Ti-6Al-4V 马氏体开始温度（M_s）        [L] WINDOWB_PARAMS §1
T_BETA_TI64 = 1268.0       # K  Ti-6Al-4V 的 β 转变温度（扩散平衡）    [L] WINDOWB_PARAMS
DG_REF = -1.0e8            # J/m^3  马氏体化学驱动力的常见量级        [T] 与 M2 用的 Δf 同量级
DG_CRIT_REF = 1.0e8        # J/m^3  临界驱动力**幅值**的参考（|dG(M_s)|）[T] 同量级（正数！）
DS_REF = 3.0e5             # J/(m^3 K)  β→α′ 转变熵的参考量级       [T] 由
                           #       「dG(298 K) 应为 O(1e8)」反推：DS·(848-298)=1.65e8
DS_BAND = (1.5e5, 6.0e5)   # J/(m^3 K)  敏感度带（覆盖 ΔS_f(Ti)/V_m 的 1/4 ~ 1 倍）


# =============================================================================
# 二、闭式
# =============================================================================

def dG_chem(T, T0, DS):
    """β→α′ 的化学驱动力 [J/m^3]（T<T0 时为负 = 有利）。[T]  支持标量/数组。"""
    return -float(DS) * (float(T0) - np.asarray(T, float))


def T0_from_Ms(Ms, dG_crit_mag, DS):
    """由 M_s 与临界驱动力的**幅值**反解 T0（避免猜 T0）。[T]

        |dG_chem(M_s)| = dG_crit_mag,   dG_chem(T) = -DS (T0 - T)
        =>  DS (T0 - Ms) = dG_crit_mag   =>   T0 = Ms + dG_crit_mag / DS

    ⚠ 物理约束：T0 必须 **大于** M_s（必须有过冷才开动）⇒ dG_crit_mag 传正数。
      本函数用 abs() 兜底，避免把符号搞反（本项目在此推错过一次）。
    """
    return float(Ms) + abs(float(dG_crit_mag)) / float(DS)


def T_from_dG(dG, T0, DS):
    """反解：给定 dG 求 T。[T]"""
    return float(T0) + float(dG) / float(DS)


def koistinen(T, Ms=M_S_TI64, alpha=None, f_end=None):
    """Koistinen–Marburger 分数 f(T) = 1 - exp[-alpha (Ms - T)]（T<Ms）。[L]

    alpha 可给定值；也可给 f_end（在 T=298 K 处希望达到的分数）来反解 alpha。
    """
    T = np.asarray(T, float)
    if alpha is None:
        if f_end is None:
            raise ValueError('koistinen: 需要 alpha 或 f_end 之一')
        alpha = alpha_from_f(f_end, Ms, 298.0)
    f = 1.0 - np.exp(-alpha * np.maximum(Ms - T, 0.0))
    return f


def alpha_from_f(f, Ms, T):
    """由 (T, f) 反解 KM 参数 alpha [1/K]。[T]

        f = 1 - exp[-alpha (Ms - T)]  =>  alpha = -ln(1-f) / (Ms - T)
    """
    f = float(f)
    if not (0.0 < f < 1.0):
        raise ValueError('alpha_from_f: f 必须在 (0,1) 内，收到 %r' % f)
    dT = float(Ms) - float(T)
    if dT <= 0:
        raise ValueError('alpha_from_f: 需要 T < Ms')
    return -math.log1p(-f) / dT


def fit_alpha(Ts, fs, Ms=M_S_TI64):
    """最小二乘反演 alpha：-ln(1-f) = alpha (Ms - T)。返回 (alpha, R2, 斜率/截距)。[T]

    用无截距线性回归（理论上截距应为 0 ⇒ 截距本身是一条判据）。
    """
    Ts = np.asarray(Ts, float)
    fs = np.asarray(fs, float)
    ok = (fs > 1e-6) & (fs < 1.0 - 1e-9)
    y = -np.log1p(-fs[ok])
    x = Ms - Ts[ok]
    if x.size < 2:
        return float('nan'), float('nan'), float('nan'), float('nan')
    alpha = float(np.sum(x * y) / np.sum(x * x))          # 无截距
    pred = alpha * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    b, a = np.polyfit(x, y, 1)                             # 带截距（做对照）
    return alpha, r2, float(b), float(a)


def f_eq_table(dfs, fs):
    """把 (dG, f_eq) 整理成可拟合的表（去重、单调化检查）。[T]"""
    dfs = np.asarray(dfs, float)
    fs = np.asarray(fs, float)
    o = np.argsort(dfs)                                    # 按 dG 升序 = 按 T 降序
    return dfs[o], fs[o]


def alpha_sensitivity(dG_of_T_scale, Ms=M_S_TI64, f_target=None):
    """alpha_KM 对 DS（= 温度到驱动的换算尺度）的敏感度。[T]

    给定「模型的 f_eq(dG)」与一组 DS，返回 {DS: (T0, alpha)}。
    dG_of_T_scale: 可调用，签名 (DS) -> (T0, alpha)，由调用者用实测 f_eq(dG) 闭包给出。
    """
    out = {}
    for DS in np.asarray(DS_scale()):
        out[float(DS)] = dG_of_T_scale(float(DS))
    return out


def DS_scale():
    """默认敏感度带（5 档，含两端）。[T]"""
    return np.array([1.5e5, 2.0e5, 3.0e5, 4.0e5, 6.0e5])


# =============================================================================
# 三、模型侧的 f_eq(dG)：跑 RVE（延迟 import，避免模块级依赖）
# =============================================================================

def feq_run(df, N=32, nstep=60, tag='', **kw):
    """跑一次 12 变体 RVE，返回 f_trans。参数同 windowB_surface.M2_twelve_variants。【实测】"""
    import windowB_surface as W
    out = W.M2_twelve_variants(N=N, nstep=nstep, df=float(df), quiet=True, **kw)
    return float(out['f_trans'])


def feq_scan(dfs, N=32, nstep=60, **kw):
    """扫描一组 dG，返回 (dfs, fs)。【实测】

    ⚠ 建议用 _run_t21b.sh 并行跑（每次 RVE ~20 s @N=32/nstep=40）；
    本函数是串行版，仅供少量点或调试使用。
    """
    fs = [feq_run(d, N=N, nstep=nstep, **kw) for d in dfs]
    return np.asarray(dfs, float), np.asarray(fs, float)


# =============================================================================
# 四、★ T2.1b-8：athermal 形核层（2026-09-25）
# =============================================================================
# 为什么必须有这一层（WINDOWB_SURFACE_AUDIT §11.7 的实测结论）：
#   自协调 12 变体下 sum_v dev(eps0_v) = 0（C4 已验）⇒ 弹性能几乎不随 f 增长
#   ⇒ 驱动力不随 f 消失 ⇒ **只靠生长**任何正驱动都会推到几何饱和（实测 f ~= 0.96，
#     且与驱动无关，5 个驱动点离散仅 0.019）。
#   ⇒ α' 的分数 vs T **只能来自 athermal 形核**（HYBRID_FRAMEWORK §8 item 4：
#     形核是输入）。马氏体形核是 athermal 的：**只在降温时新增晶核**，等温不新增。
#
# 闭合（KJMA + 线性形核律 ⇒ 自动给出 KM）：
#   形核数密度        N_v(T) = alpha_KM * (M_s - T) / v_0        [1/m^3]，T < M_s；T >= M_s 为 0
#   与 KM 的关系      f(T) = 1 - exp(-alpha_KM (M_s - T)) = 1 - exp(-N_v v_0)   （KJMA）
#   => **v_0（单个晶核最终能占的体积）必须由模型自己量出来**，不能猜：
#        v_0 = -(V / N_seed) * ln(1 - f_sat)          （由 N_seed 个预置晶核的饱和分数反解）
#   => alpha_KM 是**输入**（本模块给 [A] 占位 + 敏感度带）；模型给的是
#      N_v(T) 与"生长 + 碰撞"共同产生的 f(T)，再由 fit_alpha 反解 alpha_meas 与输入比对。
#
# 记账：[A] = 指派/待标定。ALPHA_KM_BAND 是**占位值 + 敏感度带**，不是文献直读值
#       （Ti64 的 alpha_KM 需检索，见 docs/LIT_SEARCH_BRIEF）；【未核实】。

ALPHA_KM_BAND = (5.0e-3, 1.1e-2, 2.0e-2)   # 1/K  [A] 占位（文献常见量级 1e-2 量级，【未核实】）
ALPHA_KM_REF = 1.1e-2                      # 1/K  [A] 默认占位


def v0_from_saturation(f_sat, N_seed, V):
    """由 N_seed 个预置晶核的饱和分数反解单个晶核的特征体积 v_0 [m^3]。【实测】
        f_sat = 1 - exp(-N_seed * v_0 / V)  =>  v_0 = -(V/N_seed) ln(1-f_sat)
    ★ 用模型自己的饱和分数，而不是猜几何尺寸（碰撞/吞并会让等效体积远大于几何体积）。"""
    import math
    if not (0.0 < f_sat < 1.0):
        raise ValueError('v0_from_saturation: 需要 0 < f_sat < 1，收到 %r' % f_sat)
    return -(float(V) / float(N_seed)) * math.log1p(-float(f_sat))


def Nv_of_T(T, Ms=M_S_TI64, alpha=ALPHA_KM_REF, v0=1.0):
    """athermal 形核数密度 [1/m^3]（T >= M_s 时为 0）。[T]"""
    T = np.asarray(T, float)
    return np.where(T < Ms, alpha * (Ms - T) / v0, 0.0)


def N_target(T, Ms, alpha, v0, V):
    """体积 V 内到温度 T 为止的**累计晶核数**（浮点；调用者做累计取整）。[T]"""
    return float(np.asarray(Nv_of_T(T, Ms, alpha, v0), float)) * float(V)


def alpha_from_Nv(Nv, T, Ms=M_S_TI64, v0=1.0):
    """由 (N_v, T) 反解 alpha_KM [1/K]：alpha = N_v v_0/(M_s - T)。[T]"""
    dT = float(Ms) - float(T)
    if dT <= 0:
        raise ValueError('alpha_from_Nv: 需要 T < M_s')
    return float(Nv) * float(v0) / dT
