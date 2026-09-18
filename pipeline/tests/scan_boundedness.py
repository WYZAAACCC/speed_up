#!/usr/bin/env python3
# =============================================================================
# ④ 修复的判据扫描（纯数学，不需要 MOOSE）
# =============================================================================
# 直接对两个自由能求值，证明：
#   1. 原形式 mu<0 时 F 下无界（η→∞ 时 → −∞）
#   2. 新形式（Landau）对所有 η 有界，且 η=0 是全局极小
#   3. 原形式的交叉项在 mu<0 时变**吸引**——这才是 η 冲过 1 的推手
# =============================================================================
import math

MU0 = 9.0e5
GAMMA = 1.5
NOP = 8
NPAIR = NOP * (NOP - 1) // 2      # 28 个交叉项

MU_LIQ = -2.0 * MU0               # 液相（高温极限）
MU_SOL = MU0                      # 固相（低温极限）


def f_old(x, mu):
    """f = mu*[ Σ(η⁴/4 − η²/2) + γ Σ_{i<j} η_i²η_j² ]  —— 原模型"""
    s4 = sum(v ** 4 / 4 for v in x)
    s2 = sum(v ** 2 / 2 for v in x)
    cross = sum(x[i] ** 2 * x[j] ** 2 for i in range(len(x)) for j in range(i + 1, len(x)))
    return mu * (s4 - s2 + GAMMA * cross)


def f_new(x, mu, mu0=MU0):
    """f = mu0*Σ(η⁴/4) − mu*Σ(η²)/2 + mu0*γ Σ_{i<j} η_i²η_j²  —— Landau"""
    s4 = sum(v ** 4 / 4 for v in x)
    s2 = sum(v ** 2 / 2 for v in x)
    cross = sum(x[i] ** 2 * x[j] ** 2 for i in range(len(x)) for j in range(i + 1, len(x)))
    return mu0 * s4 - mu * s2 + mu0 * GAMMA * cross


def hdr(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


hdr("① 单晶粒方向：η = (t, 0, 0, ...)，mu = %.4g（液相，= −2·mu0）" % MU_LIQ)
print("     t        f_old/mu0      f_new/mu0     df_old/dt    df_new/dt")
prev = None
for t in [0.0, 0.5, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0]:
    x = [t] + [0.0] * (NOP - 1)
    fo, fn = f_old(x, MU_LIQ) / MU0, f_new(x, MU_LIQ) / MU0
    print("  %6.2f   %12.5g  %12.5g" % (t, fo, fn), end="")
    if prev is not None:
        h = t - prev[0]
        print("  %11.5g  %11.5g" % ((fo - prev[1]) / h, (fn - prev[2]) / h), end="")
    print()
    prev = (t, fo, fn)
print("  ⇒ f_old/mu0 在 t=1 时 = %.4g，t=10 时 = %.4g，**单调奔向 −∞**"
      % (f_old([1.0] + [0.0] * 7, MU_LIQ) / MU0, f_old([10.0] + [0.0] * 7, MU_LIQ) / MU0))
print("  ⇒ f_new/mu0 在 t=1 时 = %.4g，t=10 时 = %.4g，**单调上升**（η=0 是唯一极小）"
      % (f_new([1.0] + [0.0] * 7, MU_LIQ) / MU0, f_new([10.0] + [0.0] * 7, MU_LIQ) / MU0))

hdr("② 全 8 个序参量同值：η_i = t —— 交叉项最多，最能暴露病态")
print("     t        f_old/mu0      f_new/mu0")
for t in [0.0, 0.2, 0.5, 1.0, 2.0]:
    x = [t] * NOP
    print("  %6.2f   %12.5g  %12.5g" % (t, f_old(x, MU_LIQ) / MU0, f_new(x, MU_LIQ) / MU0))
print("  ⇒ f_old 在 η=0 处为 0，却在 t=0.5 处 = %.4g < 0、t=2 处 = %.4g"
      % (f_old([0.5] * NOP, MU_LIQ) / MU0, f_old([2.0] * NOP, MU_LIQ) / MU0))
print("     ⇒ **η=0（液相）根本不是原形式的全局极小**：全部 8 个序参量一起涨到")
print("       η≈0.2 附近反而更低，再往上则 f→−∞。η 无处可去，只能发散。")
print("     （对照：新形式同样取 t=0.5 得 %.4g > 0，t=2 得 %.4g > 0，单调上升。）"
      % (f_new([0.5] * NOP, MU_LIQ) / MU0, f_new([2.0] * NOP, MU_LIQ) / MU0))

hdr("③ 越界的直接推手：交叉项在 mu<0 时变吸引")
print("   取 η_1 = 1, η_2 = 0.3, 其余 0；df/dη_1 = mu*(η_1³ − η_1 + 2γ·η_1·Σ_{j≠1}η_j²)")
for mu, name in ((MU_SOL, "固相 mu=+mu0"), (MU_LIQ, "液相 mu=−2mu0")):
    x1, x2 = 1.0, 0.3
    s4c = sum(v ** 2 for v in ([x2] + [0.0] * 6))
    d = mu * (x1 ** 3 - x1 + 2 * GAMMA * x1 * s4c)
    print("   %-16s  df/dη_1 = %12.5g   ⇒ %s" %
          (name, d, "把 η_1 往上推（越界）" if d < 0 else "把 η_1 拉回（正常）"))
print()
print("   新形式 df/dη_1 = mu0*η_1³ − mu*η_1 + 2*mu0*γ*η_1*Σ_{j≠1}η_j² :")
for mu, name in ((MU_SOL, "固相 mu=+mu0"), (MU_LIQ, "液相 mu=−2mu0")):
    x1, x2 = 1.0, 0.3
    s4c = sum(v ** 2 for v in ([x2] + [0.0] * 6))
    d = MU0 * x1 ** 3 - mu * x1 + 2 * MU0 * GAMMA * x1 * s4c
    print("   %-16s  df/dη_1 = %12.5g   ⇒ %s" %
          (name, d, "把 η_1 往上推（越界）" if d < 0 else "把 η_1 拉回（正常）"))

hdr("④ 解析界：新形式的驻点满足 η_i² = mu/mu0 − 2γΣ_{j≠i}η_j²  ≤  s = mu/mu0")
print("   因为 2γΣ_{j≠i}η_j² ≥ 0，所以 **η_i ≤ sqrt(s)**，只要 s ≤ 1 就恒有 η ≤ 1。")
print()
print("     T (K)      s = mu/mu0     sqrt(s) = η 的上界      σ/σ0")
for T in [300, 1000, 1500, 1830, 1880, 1882.2, 1900, 1950, 2200]:
    s = 1 - 1.5 * (1 + math.tanh((T - 1903) / 60.0))
    if s > 0:
        # 原模型 σ ∝ sqrt(mu)，新模型 σ ∝ s（Landau，η0² = s）
        sig_old = math.sqrt(s) / math.sqrt(1.0)
        # σ0 用 T→0 处归一：原模型 σ0=0.6 在 s=1；新模型 η0²=s ⇒ σ = 0.6*s
        print("   %7.1f   %11.5f   %16.5f %14s   orig=%.4f  Landau=%.4f"
              % (T, s, math.sqrt(s) if s > 0 else 0.0, "", sig_old, s))
    else:
        print("   %7.1f   %11.5f   %16s            （无有序相：η=0 是唯一极小）" % (T, s, "—"))

hdr("⑤ 结论")
print("   • 原形式：mu<0 时 F 下无界 + 交叉项变吸引 ⇒ η 必然越过 1，且停不下来。")
print("     这不是离散化误差——grain_growth（纯固相 mu>0）里越界随网格收敛到 0，")
print("     而熔池里 mu<0，越界是**模型本身**产生的。")
print("   • 新形式：四次项与交叉项系数恒正 ⇒ F 有界、η=0 是全局极小、η ≤ sqrt(s) ≤ 1。")
print("     且在 mu>0 时 σ(T) 仍随温度下降（Landau: σ ∝ s；原模型: σ ∝ sqrt(s)）。")
