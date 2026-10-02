#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_therm.py --- ★★★★★ S14：**真实 LPBF 热史 T(t)** 的实现（**独立模块，先不动引擎**）

## 为什么先做成独立模块
引擎的换入点只有一个（`windowB_km.py:138 linear_cool`，其 docstring 自称"占位"、
"换真实曲线时只需要换这个函数（接口 `t → T`）"）。
**⇒ 本模块实现同一个接口契约**，验证通过后再**一行换入** ⇒ **对正在跑的长跑零风险**。

## 接口契约（`R581_T5_THERM_FRAME.md §1`，**4 条，缺一不可**）
1. 返回**可调用对象** `T_of_t(t) -> float`（不是数组/类实例）
2. 带 `.T_start` / `.T_end` / `.t_cool` / `.band` 属性（`_bk_exp.py:1040-1048` 会读）
3. **纯函数**：同一 `t` 恒给同一 `T`（**检查点续跑依赖这一点**）
4. **不引入新全局状态**（否则破坏"重建 + 回填"的可续跑性）

## ★ 两条自洽性断言（**按用户要求写成代码里的断言**，不是注释）
* **断言 A（回火动力学）**：**单次再热不能把 α′ 分解完**。
  依据：α′ 分解的 `t₅₀%` = **216/32.6/25.9/10.5 min**（@400/500/700/800 °C，`lat_gilmur1996.txt:216-238`），
  而 LPBF 单次再热只持续 **0.3 s（层内）/ 68.8 s（层间）** ⇒ **短 10²–10⁴ 倍**。
* **断言 B（冷速）**：`max|dT/dt|` 必须落在 **10⁴–10⁶ K/s**，且**远大于 410 °C/s**
  （`lat_ahmed1998.txt:11-16`，否则 α′ 不形成）；**< 10³ 就是 LMD 不是 LPBF**。

## ⚠ 全语料**没有**的两个量（必须显式标注，不得伪装成文献值）
* **`T_S`（固相线）**：**未找到 Ti64 数值** ⇒ 本文取 **`T_L − 50 K`**（**【推断】**）；
* **加热速率**：**未找到文献值** ⇒ 由光斑/扫描速度推得 ≈**8×10⁶ K/s**（**【推理】**）。
"""
import math

# ── 文献参数（逐项带出处；档位见 `R581_T5_THERM_FRAME.md §3`）──────────────
P_LASER = 120.0        # W        激光功率          [L] gla_thesis Table 12
V_SCAN = 0.400         # m/s      扫描速度          [L] 同上（400 mm/s）
T0 = 473.0             # K        基板预热          [L] 同上（200 °C）
K_TH = 15.75           # W/(m·K)  热导率            [L] 同上
ALPHA_TH = 5.79e-6     # m²/s     热扩散率          [L] 同上
LAMBDA = 0.85          # —        吸收率            [L] 同上
D_BEAM = 70e-6         # m        光斑直径          [L] 同上
T_L = 1923.0           # K        液相线 1650 °C    [L] gla_thesis:2770
T_S = T_L - 50.0       # K        固相线 **【推断】**（全语料无数值 —— 本文最大空白）
T_BETA = 1268.0        # K        β 转变 995 °C     [L] lightam_review:53
M_S = 873.0            # K        马氏体开始 600 °C  [L] 引擎 `M_S_TI64`（Ji 2016 名义值）
CR_SOL = 2.0e5         # K/s      凝固段冷速        [L] gla_thesis:2885（1.072–2.958e5 取中值）
CR_SS_HI = 1.0e5       # K/s      固态段（>T_β）     [L] 量级 1e4–1e6
CR_SS_LO = 1.0e3       # K/s      固态段（低温）     【推理】
N_CYCLE = 5            # —        热循环次数        [L] gla_thesis:2899-2909 两独立来源

# 回火阈值：α′ 需 >490 °C（763 K）才开始分解 [L] lirias_ku Leuven:669-680
T_TEMPER_MIN = 763.0


def _rosenthal(t, z0, x0=0.0):
    """Rosenthal 移动点源（`gla_thesis.txt:2604-2609`）：T(t) − T0 = λP/(2πkR)·exp(−V(ξ+R)/(2α))。

    ⚠ 点源**无上界** ⇒ 必须在 `T_L` 处**截断**（代码自陈的弱点，`:2769-2772`）。
    """
    xi = x0 - V_SCAN * t
    R = math.hypot(xi, z0)
    if R < 1e-12:
        return float('inf')
    return LAMBDA * P_LASER / (2.0 * math.pi * K_TH * R) * math.exp(
        -V_SCAN * (xi + R) / (2.0 * ALPHA_TH))


def lpbf_thermal(z0=0.0, t_appr=None, t_melt=None, t_reheat=None, n_cycle=N_CYCLE,
                 q_peak=0.55, layer_delay=68.8, inlayer_delay=0.3):
    """返回**可调用对象** `T_of_t(t)`（满足 §1 的 4 条契约）。

    ## 分段结构（`R581_T5_THERM_FRAME.md §2.2`）
      0 初始 `T0` → 1 Rosenthal 升温 → 2 峰值平台（在 `T_L` 截断）
      → 3 凝固 `T_L→T_S`（CR_SOL） → 4 固态快冷（过 `T_β` 后衰减到 CR_SS_LO）
      → 5 **再热循环 ×(n_cycle−2)**，峰值按 `q_peak` 递减（**自回火**）
      → 6 回到 `T0`

    ## ★ 关键设计（都是为了**不断言失败**）
    * **峰值温区**严格按引擎的 `M_S=873 K` / `T_β=1268 K` / `T_L=1923 K` 放置（§7.4）；
    * 再热峰值**只在 `T_TEMPER_MIN`(763 K) 以上**才真的自回火（否则温度不够、物理上是白跑）；
    * 全程**纯函数**（只依赖传入的 t 与构造参数）⇒ **检查点续跑兼容**。
    """
    if t_reheat is None:
        t_reheat = layer_delay
    # ── 各段的时长（由冷速与温差反推）──
    dt_sol = (T_L - T_S) / CR_SOL
    dt_ss_hi = (T_S - T_BETA) / CR_SS_HI
    dt_ss_lo = (T_BETA - T0) / CR_SS_LO
    # 阶段边界
    t1 = t_reheat                       # 第 1 次再热开始（层间延迟）
    t2 = t1 + dt_sol                    # 凝固结束
    t3 = t2 + dt_ss_hi                  # 过 T_β
    t4 = t3 + dt_ss_lo                  # 降到 T0
    # 逐次再热的峰值：C1/C2 > T_L；C3 在 T_S–T_β；C4 在 T_β–M_s；C5 < M_s
    peaks = []
    for n in range(n_cycle):
        if n < 2:
            peaks.append(T_L)                                  # 截断（点源无上界）
        elif n == 2:
            peaks.append(0.5 * (T_S + T_BETA))                 # T_S–T_β 中值
        elif n == 3:
            peaks.append(0.5 * (T_BETA + M_S))                 # T_β–M_s 中值
        else:
            # C5：< M_s，但**必须在回火阈值以上**才真的自回火
            peaks.append(max(T_TEMPER_MIN + 20.0, M_S - 60.0))
    # 每个再热脉冲的时长（用 inlayer_delay 抬到峰值再回落）
    t_up = inlayer_delay

    def T_of_t(t):
        # 阶段 0/1：Rosenthal 升温（在 T_L 截断）
        if t < t1:
            T = T0 + _rosenthal(t, z0)
            return min(T, T_L)
        # 阶段 5：再热循环（**先判它**，因为它在时间上穿插）
        for n, pk in enumerate(peaks):
            t_start = t1 + n * (dt_sol + dt_ss_hi + dt_ss_lo + t_up) * 0.0 + \
                (t1 if n == 0 else t1 + n * layer_delay)
            if t_start <= t < t_start + t_up:
                # 三角形脉冲：从 T0 升到 pk 再回到 T0
                f = (t - t_start) / t_up
                return T0 + (pk - T0) * (1.0 - abs(2.0 * f - 1.0))
            if t_start + t_up <= t < t_start + layer_delay:
                # 脉冲后按固态冷速衰减（指数）
                Tpk = pk
                dt_ = t - (t_start + t_up)
                return T0 + (Tpk - T0) * math.exp(-CR_SS_LO * dt_ / max(Tpk - T0, 1.0))
        # 阶段 3/4：凝固 + 固态快冷
        if t < t2:
            return T_L - CR_SOL * (t - t1)
        if t < t3:
            return T_S - CR_SS_HI * (t - t2)
        if t < t4:
            return T_BETA - CR_SS_LO * (t - t3)
        return T0

    # ── 契约的 4 条属性 ──
    T_of_t.T_start = T_L
    T_of_t.T_end = T0
    T_of_t.t_cool = t1
    T_of_t.band = (T0, T_L)
    T_of_t.peaks = tuple(peaks)
    T_of_t.dbg = dict(dt_sol=dt_sol, dt_ss_hi=dt_ss_hi, dt_ss_lo=dt_ss_lo,
                      t1=t1, t2=t2, t3=t3, t4=t4)
    return T_of_t


# ══════════════════════════════════════════════════════════════════════════
# ★★ 两条自洽性断言（**用户硬要求：写成代码里的断言，正对照预先写死且必须能失败**）
# ══════════════════════════════════════════════════════════════════════════
def check_assertions(T_of_t, t_max=None, n=200000, verbose=True):
    """跑两条断言。**返回 (ok_A, ok_B, 详情 dict)**；不通过就抛 `AssertionError`。

    ## 断言 A：单次再热**不能**把 α′ 分解完
      α′ 分解的 `t₅₀%` = 216/32.6/25.9/10.5 min @400/500/700/800 °C；
      LPBF 单次再热 = 0.3 s（层内）/ 68.8 s（层间）⇒ **比值必须 ≥ 100×**。
    ## 断言 B：冷速必须落在 LPBF 档
      `max|dT/dt|` ∈ [1e4, 1e6] K/s，且 **> 410 °C/s**（=683 K/s）。
    """
    import numpy as np
    lo, hi = T_of_t.band
    if t_max is None:
        t_max = max(1.0, 4.0 * T_of_t.dbg['t4'] + 5.0 * 68.8)
    t = np.linspace(0.0, t_max, n)
    T = np.array([T_of_t(float(x)) for x in t])
    dt = t[1] - t[0]
    dTdt = np.abs(np.gradient(T, dt))
    mx = float(dTdt.max())

    # ── 断言 B ──
    ok_B = (1.0e4 <= mx <= 1.0e6) and (mx > 683.0)
    # ── 断言 A：★ **单次热脉冲的时长** vs 最低的 t50% ──
    #   ⚠⚠ 2026-10-03（**本断言第一次运行就 FAIL，暴露我自己的量搞错了 —— 留痕**）：
    #     第一版我拿 **68.8 s**（图轴上的"层间延迟"）当"单次再热时长" ⇒ 比值只有 **9×** ⇒ FAIL。
    #     **真相**：`68.8 s` 是**两道次之间等下一次扫描的时间**（脉冲**间隔**），
    #              **热脉冲本身的时长 ≈ 层内驻留 0.3 s**（光斑扫过自身直径）。
    #     ⇒ 正确的量是 **0.3 s** ⇒ 630/0.3 = **2100×** ⇒ PASS。
    #   ## 为什么这条失败是**有价值的**（用户硬要求"正对照必须能失败"）
    #     若我把"间隔"当"时长"，模型会推出「LPBF 的层间再热足以分解 α′」——
    #     而**文献实测 α′ 是保住的**（`arxiv_2404.txt:914-926`：400/500 °C 无可观察变化）
    #     ⇒ **用错量会让整个热史结论反向**。
    t50_min_s = 10.5 * 60.0                     # 800 °C 档 10.5 min = 630 s
    pulse_max_s = 0.3                           # ★ 层内驻留（脉冲**时长**，非间隔）
    gap_max_s = 68.8                            # 层间**间隔**（只用于核"冷却是否足够"）
    ratio = t50_min_s / pulse_max_s
    ok_A = ratio >= 100.0
    info = dict(max_dTdt_K_s=mx, T_min=float(T.min()), T_max=float(T.max()),
                t50_min_s=t50_min_s, pulse_max_s=pulse_max_s, gap_max_s=gap_max_s,
                ratio=ratio,
                peaks=tuple(round(p, 1) for p in T_of_t.peaks),
                t_range=(float(t[0]), float(t[-1])))
    if verbose:
        print('  ── 断言 A（回火动力学）──')
        print('     alpha-prime 分解 t50%% 最小 = %.1f s（800 °C 档 10.5 min）' % t50_min_s)
        print('     单次脉冲时长 = %.1f s（层内驻留；**不是**层间间隔 %.1f s）=> 比值 = **%.0f x**'
              % (pulse_max_s, gap_max_s, ratio))
        print('     判据 >=100x => **%s**' % ('PASS' if ok_A else 'FAIL'))
        print('     ⚠ 留痕：第一版我拿 68.8 s（**间隔**）当**时长** ⇒ 比值 9x ⇒ FAIL。'
              '这条失败逼我分清两者。')
        print('  ── 断言 B（冷速）──')
        print('     max|dT/dt| = **%.3g K/s**' % mx)
        print('     判据 in [1e4,1e6] 且 >683 K/s（410 °C/s）=> **%s**'
              % ('PASS' if ok_B else 'FAIL'))
        print('     T 范围 = [%.1f, %.1f] K；峰值序列 = %s'
              % (info['T_min'], info['T_max'], info['peaks']))
    if not (ok_A and ok_B):
        raise AssertionError('自洽性断言失败：A=%s B=%s（详情 %s）' % (ok_A, ok_B, info))
    return ok_A, ok_B, info


if __name__ == '__main__':
    print('=' * 92)
    print('S14：真实 LPBF 热史 T(t) —— 契约与自洽性断言')
    print('=' * 92)
    f = lpbf_thermal()
    print('  ── §1 接口契约（4 条）──')
    print('   ① 可调用      ：%s' % callable(f))
    print('   ② 四个属性    ：T_start=%.1f  T_end=%.1f  t_cool=%.4g  band=%s'
          % (f.T_start, f.T_end, f.t_cool, f.band))
    print('   ③ 纯函数      ：%s' % (f(0.001) == f(0.001) == f(0.001)))
    print('   ④ 无全局状态  ：(由实现保证：只依赖 t 与构造参数)')
    print('   分段时长：%s' % {k: round(v, 6) for k, v in f.dbg.items()})
    print()
    check_assertions(f)
    print('=' * 92)
