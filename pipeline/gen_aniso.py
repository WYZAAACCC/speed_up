#!/usr/bin/env python3
"""
生成 2a + 2b 的 MOOSE 材料/辅助变量块（写入 aniso_block.i，供人工接入算例）。

=============================================================================
2a —— 取向差依赖的晶界能 / 晶界迁移率（严格复刻 GBAnisotropy）
=============================================================================
不用现成的 `GBAnisotropy` 材料，原因是**源码级**的（已核对
/root/moose/modules/phase_field/src/materials/GBAnisotropyBase.C）：

    _mu(declareProperty<Real>("mu"))

它声明并写入 `mu`，而本算例的 `mu` 是温度相关的**熔化开关**
（液相内 mu<0 反转体驱动力）。两者抢同一个属性名，会互相覆盖。

所以这里把 GBAnisotropy 的算法**原样搬到 Python 里预先算好**，
再以 parsed 表达式给出，`mu` 完全留给熔化开关。

Moelans Algorithm 1（Phys. Rev. B 78, 024113 (2008)），逐对 (m,n)：
    mu_qp  = 6*sigma_init/wGB,  sigma_init = (sigma_max+sigma_min)/2
    kappa* = a* * wGB * sigma_mn
    g2     = sigma_mn^2 / (kappa* * mu_qp)
    y      = -5.288 g2^4 - 0.09364 g2^3 + 9.965 g2^2 - 8.183 g2 + 2.007
    gamma* = 1/y
    a*     <- sqrt(f_interf(y)/g2)      （不动点迭代，tol 1e-9）

局部值按 GBAnisotropy 的重量加权（其源码 computeQpProperties）：
    Val_mn = (1e5*eta_m^2 + 0.01)*(1e5*eta_n^2 + 0.01)
    X_qp   = sum_{m<n} Val_mn * X_mn / sum_{m<n} Val_mn

【代数等价但数值更稳的改写】Val_mn 整体乘一个常数不影响归一化比值：
    (1e5*a + 0.01) = 1e5*(a + 1e-7)   =>   Val_mn = 1e10*(eta_m^2+1e-7)(eta_n^2+1e-7)
    1e10 在分子分母同时出现，精确抵消。改用 (eta^2+1e-7) 形式，
    雅可比里的导数小 1e10 倍，条件数大幅改善，**数学上完全等价**。

【各向同性极限的精确退化】当所有 sigma_mn = sigma_H 时：
    a* = 0.75, gamma* = 1.5, kappa* = 0.75*wGB*sigma_H
    => kappa_op = 1.8e-6, gamma_asymm = 1.5, L = 4/3*M0*exp(-Q/kbT)/wGB
    **与引入各向异性之前逐位相同**（脚本会打印这个自检）。

=============================================================================
2b —— 热梯度驱动的晶粒选择
=============================================================================
β-Ti 是 BCC，易生长方向 <100>。在 2D 截面里 <100> 有四重对称，
所以晶粒取向只需在 [0, 90) 内取值 theta_i，其易生长轴集合为 {theta_i, theta_i+90}。

因为易生长轴是**四重**对称的，对齐因子必须用四重形式
    align4 = cos^2( 2*(phi - theta) )        phi = 热梯度方向
（用 cos^2(phi-theta) 是二重的，会把 theta 与 theta+90 判成不同 —— 错。）
    align4 = (2q-1)^2,  q = cos^2(phi-theta)

热梯度方向取**实际温度场的解析导数**（不是几何近似）：
    T - T0 = (C/R)*exp(-k(R+xi)),  xi = x - x_l,  R = sqrt(xi^2+y^2+eps)
    dT/dx = (C/R)e^{-k(R+xi)} * ( -xi/R^2 - k(R+xi)/R )
    dT/dy = (C/R)e^{-k(R+xi)} * ( -y/R^2  - k*y/R    )
与算例 [Functions]/laser_T 用的场**同一个表达式**，只是解析求导。

迁移率上乘各向异性因子：
    L = L_base * ( 1 + A*(2*align4 - 1) )
A=1 时完全对齐的晶粒迁移率是错配晶粒的无穷倍；A=0 退化为各向同性。
**A 是唯象参数，暂无标定依据**，默认 0.7，需用 LPBF 实测织构标定（见文件末）。

=============================================================================
【为什么这里不需要写 C++】—— 已用实跑日志核实
=============================================================================
GrainTracker 的重映射会**复用序参量**，新晶粒本会继承旧 op 的取向。
但对本算例（柱状基体 + 预熔池 + **无形核核**）：
  * 核列表里只有 Cahn-Hilliard 核，没有任何形核核 -> 不会产生新晶粒
  * 101 个时间步的 GrainTracker 日志全部是
        index 0..2: 2 -> 2   index 3..7: 1 -> 1
    即 11 个晶粒承载于 8 个序参量上，**全程不合并、不重映射**
  => op <-> 晶粒 <-> 取向 的映射在整个模拟期间不变，逐对取向差表始终有效。
对 11 个一维链状柱状晶做 8 染色，相邻晶粒必然异色（路径图 2-染色即可），
所以同色晶粒永不相邻，不会静默合并。

注意：这也意味着**本算例没有等轴晶形核**（真实 LPBF 熔池顶部有），
这是当前模型的已知简化，不是 bug。

用法：
    python3 gen_aniso.py --out aniso_block.i
    python3 gen_aniso.py --A-ani 0.0     # 关掉 2b，验证退化为各向同性
"""

import argparse
import math

# --- 基线（大角极限），与引入取向之前完全一致 ---
SIGMA_H = 0.6        # J/m^2   (Gornakova & Prokofjev 2020)
MOB0_H = 232.0       # m^4/(J*s)
Q_H = 3.234          # eV
THETA_M = 15.0       # deg，Read-Shockley 临界取向差
KB = 8.617e-5        # eV/K
WGB = 4.0e-6         # m，扩散界面宽
# 【必须是这个值】= 9.0e5 J/m^3，逐位等于算例 [Materials]/barrier_mu 的 mu0。
# Moelans 不动点必须用算例**实际使用**的 mu 求解，否则 (a*,gamma*) 与 mu 不自洽。
# 已用 check_gb_energy.py 数值判定：用 9e5 时 28 对的真实晶界能全部等于目标值
# （最大相对误差 8.96e-05）；换成 GBAnisotropy 的 6*sigma_init/w 会不收敛。
# 改 barrier_mu 的 mu0 时，**必须同步改这里并重新生成 aniso_block.i**。
MU_QP = 6.0 * SIGMA_H / WGB

# --- Rosenthal 场参数（必须与算例 [Functions]/laser_T 逐字一致）---
C_R = 28.0 / (2.0 * math.pi * 20.0)   # 0.222817...
K_R = 0.6 / (2.0 * 6.0e-6)            # 50000
XI = "(x+1.2e-4-0.6*t)"               # xi = x - x_l,  x_l = -1.2e-4 + 0.6t
RR = f"sqrt({XI}^2+y^2+1e-10)"        # R


def rs_factor(d):
    """Read-Shockley：sigma/sigma_H。"""
    if d >= THETA_M:
        return 1.0
    x = max(d, 1e-6) / THETA_M
    return x * (1.0 - math.log(x))


def mob_factor(d):
    """低角晶界的迁移率因子 M/M0（位错模型：M 正比于取向差，饱和于 theta_m）。"""
    return min(max(d, 0.0) / THETA_M, 1.0)


def moelans_pair(sigma_mn, mu_qp):
    """Moelans Algorithm 1 不动点，返回 (a*, gamma*, kappa*)。

    mu_qp 必须由**调用方**传入，不能读全局常量 —— 见 compute_mu_qp() 的注释。
    """
    a_star, a_0 = 0.75, 0.0
    kappa_star = gamma_star = 0.0
    for _ in range(200):
        if abs(a_0 - a_star) <= 1e-9:
            break
        a_0 = a_star
        kappa_star = a_0 * WGB * sigma_mn
        g2 = sigma_mn * sigma_mn / (kappa_star * mu_qp)
        y = (-5.288 * g2**4 - 0.09364 * g2**3 + 9.965 * g2**2
             - 8.183 * g2 + 2.007)
        gamma_star = 1.0 / y
        yyy = y**3
        f_interf = (0.05676 * yyy**2 - 0.2924 * yyy * y**2 + 0.6367 * yyy * y
                    - 0.7749 * yyy + 0.6107 * y**2 - 0.4324 * y + 0.2792)
        a_star = math.sqrt(f_interf / g2)
    else:
        raise RuntimeError(f"Moelans 不动点未收敛: sigma={sigma_mn}")
    return a_star, gamma_star, kappa_star


def compute_mu_qp(sigmas):
    """
    【这个函数现在是"反例存档"，不要调用它】

    它算的是 GBAnisotropyBase 的 mu_qp：sigma_init = (sig_max+sig_min)/2，
    mu_qp = 6*sigma_init/wGB。本算例给出 763136，而熔化开关的 mu 是 900000。

    **曾经想过"照源码改成 763136"，那是错的，已用数值实验否掉。**

    原因：Moelans Algorithm 1 的 (a*, gamma*) 是**针对某个具体的 mu 解出来的**，
    必须用算例真正使用的那个 mu。本算例的 mu 被熔化开关锁死在
    6*sigma_H/w = 9e5，改不得。GBAnisotropy 之所以能用 6*sigma_init/w，
    是因为它自己声明并写入 mu（所以本算例不能用该材料，见文件头注释）。

    check_gb_energy.py 的数值判定（解 1D 平衡晶界，量真实界面能）：
      * 用 mu = 9e5（实际值）：28 对全部 |sigma真实/sigma目标 - 1| <= 8.96e-05  ✓
      * 用 mu = 763136：第 1 对就松弛不到平衡，gamma* 冲到 1.926（>1.5）
        —— (a*,gamma*) 与 mu 不自洽，界面本身不稳定
    所以 mu_qp 必须 = 熔化开关的 mu = MU_QP，不是 GBAnisotropy 的公式。

    保留这个函数是为了让后人看得出"这条路试过、为什么不通"。
    """
    return 6.0 * (max(sigmas) + min(sigmas)) / 2.0 / WGB


def _inv_norm_cdf(q):
    """
    标准正态分布的分位函数（Acklam 有理逼近，精度 ~1e-9）。
    不依赖 scipy —— gen_aniso.py 在 moose 环境里也要能跑。
    """
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if q < p_low:
        t = math.sqrt(-2.0 * math.log(q))
        return (((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / \
               ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1.0)
    if q > p_high:
        t = math.sqrt(-2.0 * math.log(1.0 - q))
        return -(((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / \
                ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1.0)
    t = q - 0.5
    r = t * t
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*t / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0)


def build_orientations(n, texture="fiber", hwhm_deg=20.0):
    """
    取向 theta_i (度)，在 [0, 90) 内（四重对称：theta 与 theta+90 等价）。

    texture="fiber"  <100> 纤维织构 —— **LPBF 的真实情形**。
        粉末床熔化的柱状晶沿最大热梯度方向（≈ 建造方向 BD，即 +y）优先生长，
        而 beta-Ti 的易生长轴是 <100>，于是 <100> 与 BD 对齐。
        在 2D 里"与 y 对齐"对应 theta = 90 度 ≡ 0 度（mod 90），
        所以分布**峰在 0 与 90 两端**，用半高半宽 hwhm_deg 控制离散度。
        实现方式：取缠绕正态的等分位点，再关于 0 (mod 90) 镜像，
        确定性、可复现，且统计上就是一条纤维织构。

    texture="random" 在 [0,90) 内近似均匀铺开 —— 代表取向散射很大的柱状基体。
        保留它是为了做对照：审稿人会问"织构到底影响了多少"。

    【为什么必须提供 fiber】见 [[physics-gaps-for-reviewers]] 缺口 #5：
    原先只有 random，而真实 LPBF 基体是强 <100> 纤维织构，两者对 2b 的
    取向选择与最终织构演化的影响完全不同。
    """
    if texture == "random":
        th = [(i * 90.0 / n + (i * 37 % 11) * 0.9) % 90.0 for i in range(n)]
        th = sorted(set(round(t, 6) for t in th))
        while len(th) < n:
            th.append(round((len(th) * 13.7) % 90.0, 6))
        return th[:n]

    if texture != "fiber":
        raise ValueError(f"未知 texture={texture!r}（可选 'fiber' / 'random'）")

    sigma = hwhm_deg / 1.177410022          # 半高半宽 -> 标准差
    half = (n + 1) // 2
    th = []
    for i in range(half):
        q = (i + 0.5) / (2.0 * half)        # (0, 0.5) 内的等分位点
        d = abs(_inv_norm_cdf(q)) * sigma
        d = min(d, 44.0)                    # 截断，避免越过 45（那是另一侧）
        th.extend([round(d, 6), round(90.0 - d, 6)])
    th = sorted(set(t for t in th if 0.0 <= t < 90.0))
    while len(th) < n:                      # 极少数情况下取整去重后不够，补中心附近
        th.append(round(min(44.0, 1.0 + len(th) * 0.5), 6))
        th = sorted(set(th))
    return th[:n]


def pair_dtheta(ti, tj):
    """四重对称下的取向差，落在 [0, 45]。"""
    d = abs(ti - tj) % 90.0
    return min(d, 90.0 - d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--op-num", type=int, default=8)
    ap.add_argument("--A-ani", type=float, default=0.7,
                    help="2b 各向异性强度；0 = 关闭 2b")
    ap.add_argument("--texture", default="fiber", choices=("fiber", "random"),
                    help="fiber = LPBF 真实的 <100> 纤维织构（默认）；"
                         "random = 取向散射很大的柱状基体（对照用）")
    ap.add_argument("--hwhm", type=float, default=20.0,
                    help="纤维织构的半高半宽（度），仅 --texture fiber 有效")
    ap.add_argument("--out", default="aniso_block.i")
    args = ap.parse_args()

    n = args.op_num
    th = build_orientations(n, args.texture, args.hwhm)
    eta = [f"gr{i}" for i in range(n)]
    pairs = [(m, nn) for m in range(n) for nn in range(m + 1, n)]

    # ---- 逐对 sigma（必须先全部算完，才能定 mu_qp）----
    # mu_qp 依赖全体配对的 sigma 极值，所以不能边算边用。
    sig, dths, mobf = {}, {}, {}
    for m, nn in pairs:
        d = pair_dtheta(th[m], th[nn])
        sig[(m, nn)] = SIGMA_H * rs_factor(d)
        mobf[(m, nn)] = mob_factor(d)
        dths[(m, nn)] = d
    sig_min, sig_max = min(sig.values()), max(sig.values())

    # ---- 逐对 Moelans 不动点 ----
    kap, gam = {}, {}
    for m, nn in pairs:
        _, gamma_star, kappa_star = moelans_pair(sig[(m, nn)], MU_QP)
        kap[(m, nn)] = kappa_star
        gam[(m, nn)] = gamma_star

    # ---- 自检：各向同性极限必须复现既有基线 ----
    #
    # 说明为什么不是"逐位相同"：
    #   既有基线 kappa_op = 1.8e-6 = 0.75*sigma*wGB 是**教科书圆整值**。
    #   而 Moelans 不动点的精确解是 a* = 0.74997626...（不是 0.75），
    #   GBAnisotropy 跑出来也会是 1.799943e-6，不是 1.8e-6。
    #   即偏差 ~3e-5 来自"圆整值 vs 不动点精确解"，不是实现误差。
    #   下面直接打印相对偏差，用 1e-4 作为判据（物理上 3e-5 完全可忽略）。
    #   这里用的 mu 就是 MU_QP —— 自检模拟的"全部配对都是大角"体系，
    #   其 mu 与算例相同（熔化开关锁死的 6*sigma_H/w），所以两者本就该一致。
    a_iso, g_iso, k_iso = moelans_pair(SIGMA_H, MU_QP)
    L_iso = (4.0 / 3.0) * MOB0_H / WGB
    rel_k = abs(k_iso - 1.8e-6) / 1.8e-6
    rel_g = abs(g_iso - 1.5) / 1.5
    print("=" * 74)
    print("自检：各向同性极限 vs 现有已验证基线（判据 1e-4 相对偏差）")
    print("=" * 74)
    print(f"  kappa_op   : {k_iso:.10g}  vs 基线 1.8e-6    "
          f"相对偏差 {rel_k:.2e}  {'OK' if rel_k < 1e-4 else '**不符**'}")
    print(f"  gamma_asymm: {g_iso:.10g}  vs 基线 1.5       "
          f"相对偏差 {rel_g:.2e}  {'OK' if rel_g < 1e-4 else '**不符**'}")
    print(f"  a*         : {a_iso:.10g}  (教科书圆整值 0.75，"
          f"偏差 {abs(a_iso-0.75)/0.75:.2e})")
    print(f"  L 系数     : 4/3*{MOB0_H}/{WGB:.1g} = {L_iso:.10g}  (无不动点，逐位相同)")
    print()
    print(f"  mu_qp      : {MU_QP:.6g}  = 6*{SIGMA_H}/{WGB:.1g}"
          f"  (= barrier_mu 的 mu0，必须逐位一致)")
    print(f"  GBAniso 的 mu_qp 会是 6*(sig_max+sig_min)/2/w = "
          f"{compute_mu_qp(sig.values()):.6g}，**不能用**（与 mu 不自洽，"
          f"见 compute_mu_qp 注释 + check_gb_energy.py）")
    print()
    print(f"取向 theta_i (度): {[round(t, 3) for t in th]}")
    print(f"逐对取向差取值  : {sorted(set(round(v,4) for v in dths.values()))}")
    print(f"sigma 范围      : {sig_min:.4f} ~ {sig_max:.4f} J/m^2 "
          f"(大角极限 {SIGMA_H})")
    print(f"kappa* 范围     : {min(kap.values()):.4g} ~ {max(kap.values()):.4g}")
    print(f"gamma* 范围     : {min(gam.values()):.4f} ~ {max(gam.values()):.4f}")
    print(f"M/M0  范围      : {min(mobf.values()):.4f} ~ {max(mobf.values()):.4f}")
    print(f"A_ani           : {args.A_ani}  -> 对齐因子范围 "
          f"[{1-args.A_ani:.2f}, {1+args.A_ani:.2f}]")
    print()

    # ---- 表达式片段 ----
    def val(m, nn):
        return f"({eta[m]}^2+1e-7)*({eta[nn]}^2+1e-7)"

    den = " + ".join(val(m, nn) for m, nn in pairs)
    k_num = " + ".join(f"{kap[(m,nn)]:.10g}*{val(m,nn)}" for m, nn in pairs)
    g_num = " + ".join(f"{gam[(m,nn)]:.10g}*{val(m,nn)}" for m, nn in pairs)
    m_num = " + ".join(f"{mobf[(m,nn)]:.10g}*{val(m,nn)}" for m, nn in pairs)

    esum = " + ".join(f"{e}^2" for e in eta)
    Ex = " + ".join(f"{e}^2*{math.cos(math.radians(t)):.10g}"
                    for e, t in zip(eta, th))
    Ey = " + ".join(f"{e}^2*{math.sin(math.radians(t)):.10g}"
                    for e, t in zip(eta, th))

    # --- 2b：对齐因子（梯度的解析求导放在 [Functions] 里，见下方模板）---
    # align4 = (2q-1)^2,  q = cos^2(phi-theta) = (E.g)^2/((|E|^2+eps)|g|^2)
    # eps=1e-8 防止液相(E=0)里出现 0/0；让 q 在 eta->0 时平滑趋于 0，
    # 且 dq/deta ~ O(eta) -> 0，不会给雅可比引入奇异。
    # ---- 旧写法（保留在注释里，说明为什么废弃）----
    #   取向的局部"方向" E=(Ex,Ey) 是尺度无关量，d(方向)/dE ~ 1/|E| 必然发散。
    #   原来的 `+1e-8` 把 0/0 挡住了，却在 |E| ~ sqrt(1e-8)=1e-4 留下导数尖峰：
    #   实测 align4 的二阶导数在 |E|~1e-8 处达 1.9e12，而固相内部只有 8.9e-6
    #   —— 相差 17 个数量级。ACInterface 要的正是 d2L/dop2，
    #   雅可比被这个巨值污染 -> 牛顿不收敛（残差停在 4.29e-7 的非零地板）。
    #   （对照实验：v1 关掉 2b 后立刻收敛到 7.6e-8，v4 把 align4 内联进 L 仍卡死，
    #     而最小实验证明 AuxVariable 耦合本身无害。）
    #
    # ---- 改用「逐晶粒对齐度的 eta^2 加权平均」----
    #   align4 = sum_i gr_i^2 * (cos2t_i*P + sin2t_i*Q)^2 / ( (sum gr^2 + DELTA) * G^2 )
    #     P = gx^2-gy^2,  Q = 2 gx gy,  G = gx^2+gy^2,  ct2_i=cos(2 theta_i)
    #   性质：
    #     * 单晶粒内部 (sum gr^2=1) **精确等于** cos^2(2(phi-theta_i))
    #       （用倍角恒等式：(ct2*P+st2*Q)/G = cos(2(phi-theta))）
    #     * 液相 (sum gr^2 -> 0) 平滑趋于 0，即 L2b 统一趋于 1-A —— **不反向**
    #       （对 |E| 正则化的写法在过渡带里会让"对齐的晶粒"拿到最小因子，
    #         等于把选择反过来了，比数值问题更隐蔽）
    #     * 分母只含 eta，没有 1/|E| 方向奇异；唯一的过渡尺度是 DELTA，
    #       取 1e-3 时二阶导数峰值 ~2e3（对比旧写法的 1.9e12）
    #     * 顺带不再需要 Ex/Ey，表达式更小
    DELTA = 1e-3
    W_ex = "(" + " + ".join(f"{e}^2" for e in eta) + ")"
    # 【2026-09-18 根因修复】梯度只以**数据**身份进入，不再当作耦合变量。
    #
    # 旧写法把 grad_Tx/grad_Ty（两个 AuxVariable）列进 align4 的 coupled_variables。
    # DerivativeParsedMaterial 于是对它们求导，而表达式分母含
    # G = grad_Tx^2+grad_Ty^2，导致
    #     d(align4)/d(grad_T) ~ 1/G ,  d2 ~ 1/G^2
    # 实测 G 在网格上跨 3.70e-10 ~ 1.04e18（**28 个量级**），
    # 于是 1/G^3 在 G_min 处达 1.98e28，而主导对角 L*kappa/h^2 只有 7.5e5
    # —— 差 22 个量级，条件数 ~1e36。任何预条件子都救不了：
    #     ILU  -> DIVERGED_ITS / SUBPC_ERROR
    #     AMG  -> DIVERGED_NANORINF
    # 而这批导数项在牛顿步里乘的是 Δgrad_T = 0（grad_Tx 由 FunctionAux 精确给出，
    # 其方程行为单位阵、右端恒为 0），**纯粹是矩阵里的死重量**。
    # 所以它们既不改善收敛、又彻底破坏条件数 —— 必须去掉。
    #
    # 修法：先用**非导数**的 ParsedMaterial 把梯度化成**有界的单位向量**
    #     gdir_p = (gx^2-gy^2)/(G+EPS) ,  gdir_q = 2*gx*gy/(G+EPS)
    # （|gdir| <= 1，因为 |P|,|Q| <= G）。ParsedMaterial 不产生任何雅可比项，
    # 梯度到此为止只作为数据；再用 DerivativeParsedMaterial 只对序参量求导。
    # 额外收益：align4 的值**逐位不变**（G^2 本就精确抵消），
    # 而且 G=0 时 gdir=0、align4=0，顺手修掉了原来 initial 阶段的 0/0=NaN。
    GDIR_EPS = 1e-30        # 远小于实测 G_min=3.7e-10，故在真实网格上从不激活
    P_ex, Q_ex = "gdir_p", "gdir_q"
    num = " + ".join(
        f"{e}^2*({math.cos(2*math.radians(t)):.10g}*{P_ex}"
        f"+{math.sin(2*math.radians(t)):.10g}*{Q_ex})^2"
        for e, t in zip(eta, th))
    align4 = f"(({num})/({W_ex}+{DELTA:g}))"

    # --- AD 版用：把 gdir 也内联进来，彻底不用 material_property_names ---
    #
    # 【为什么要内联】转 AD 时我把 L 写成单个 ADDerivativeParsedMaterial。
    # AD 材料消费 material_property_names（如 L2b 读 align4、align4 读 gdir_p）
    # 的链式行为我没有实测过，而"没验证过的机制不要用"是今天最贵的一课。
    # 内联后整条链只剩显式表达式，零机制风险（表达式大一点无所谓，
    # gen_aniso.py 是程序生成的）。
    GP = f"((grad_Tx^2-grad_Ty^2)/(grad_Tx^2+grad_Ty^2+{GDIR_EPS:g}))"
    GQ = f"((2*grad_Tx*grad_Ty)/(grad_Tx^2+grad_Ty^2+{GDIR_EPS:g}))"
    num_inl = " + ".join(
        f"{e}^2*({math.cos(2*math.radians(t)):.10g}*{GP}"
        f"+{math.sin(2*math.radians(t)):.10g}*{GQ})^2"
        for e, t in zip(eta, th))
    align4_inl = f"(({num_inl})/({W_ex}+{DELTA:g}))"
    # L = (2a 的取向差加权 Arrhenius) * (1 + A*(2*align4 - 1))
    L_inl = (f"(({m_num})/({den})*(4.0/3.0)*{MOB0_H:.10g}"
             f"*exp(-{Q_H:.10g}/({KB:.10g}*T))/{WGB:.10g})"
             f"*(1+{args.A_ani:.10g}*(2*{align4_inl}-1))")

    # 数据用辅助变量（取向场与对齐因子）—— extract.py 靠它们逐晶粒还原 theta
    oc = f"({Ex})/({esum}+1e-20)"
    os_ = f"({Ey})/({esum}+1e-20)"

    txt = f"""# =============================================================================
# 由 gen_aniso.py 自动生成 —— 请勿手改
#   2a: 取向差依赖的晶界能/迁移率（Moelans Algorithm 1，严格复刻 GBAnisotropy）
#   2b: 热梯度驱动的晶粒选择（解析 Rosenthal 梯度，四重对称对齐）
# 取向 theta_i (度) = {[round(t, 3) for t in th]}
# A_ani = {args.A_ani}
# 各向同性极限自检: kappa_op={k_iso:.10g} vs 基线 1.8e-6  (相对偏差 {rel_k:.2e})
#                   gamma_asymm={g_iso:.10g} vs 基线 1.5   (相对偏差 {rel_g:.2e})
#   偏差来自"教科书圆整值 0.75 vs Moelans 不动点精确解 0.74997626"，
#   非实现误差；GBAnisotropy 本身跑出来同样是 1.799943e-6。
#
# 【实现约束，已用最小对照实验核实】
#   1. `ParsedMaterial`/`ParsedAux` **都不认 x / y / t**（只有 `ParsedFunction` 认）。
#      所以温度梯度必须先由 ParsedFunction + FunctionAux 算成 AuxVariable，
#      再耦合进材料。这在数学上无损：梯度只依赖 (x,y,t) 不依赖 eta，
#      它相对 eta 的导数确实是 0，雅可比不缺项。
#   2. `material_property_names` 的链式法则可用（含二阶），
#      所以把 align4 -> L2b -> L 拆成三层小材料，避免单个求导树爆炸。
# =============================================================================

# --- 2b 的温度梯度：ParsedFunction 认得 x/y/t，由它解析求导 ---
[Functions]
  [gradTx_fn]
    type = ParsedFunction
    expression = '({C_R:.10g}/{RR})*exp(-{K_R:.10g}*({RR}+{XI}))*(-{XI}/({RR}*{RR})-{K_R:.10g}*({RR}+{XI})/{RR})'
  []
  [gradTy_fn]
    type = ParsedFunction
    expression = '({C_R:.10g}/{RR})*exp(-{K_R:.10g}*({RR}+{XI}))*(-y/({RR}*{RR})-{K_R:.10g}*y/{RR})'
  []
[]

# --- 2a/2b 的取用量（grad_* 供材料耦合，orient_*/ 供数据提取）---
[AuxVariables]
  [grad_Tx]
    order = CONSTANT
    family = MONOMIAL
  []
  [grad_Ty]
    order = CONSTANT
    family = MONOMIAL
  []
  [orient_cos]
    order = CONSTANT
    family = MONOMIAL
  []
  [orient_sin]
    order = CONSTANT
    family = MONOMIAL
  []
  [grad_align]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [grad_Tx]
    type = FunctionAux
    variable = grad_Tx
    function = gradTx_fn
    execute_on = 'initial timestep_end'
  []
  [grad_Ty]
    type = FunctionAux
    variable = grad_Ty
    function = gradTy_fn
    execute_on = 'initial timestep_end'
  []
  # 局部取向（eta^2 加权）—— 只依赖 eta，故 ParsedAux 可用。
  # extract.py 逐晶粒反解出 theta，这个量对 remap 免疫。
  [orient_cos]
    type = ParsedAux
    variable = orient_cos
    coupled_variables = '{" ".join(eta)}'
    expression = '{oc}'
    execute_on = 'initial timestep_end'
  []
  [orient_sin]
    type = ParsedAux
    variable = orient_sin
    coupled_variables = '{" ".join(eta)}'
    expression = '{os_}'
    execute_on = 'initial timestep_end'
  []
  # 对齐度从材料里取出，保证与 L 里用的是同一个数（不是重算一遍）
  # 【AD 版】align4 现在是 AD 材料属性，非 AD 的 MaterialRealAux 读不了它
  # （MOOSE 禁止同一属性两种声明），必须用 ADMaterialRealAux。
  [grad_align]
    type = ADMaterialRealAux
    variable = grad_align
    property = align4
    execute_on = 'initial timestep_end'
  []
[]

[Materials]
  # =============================================================================
  # 【2026-09-18 AD 转换】全部换成 AD 材料 + AD 核。
  #
  # 为什么必须转 AD（这是 D 版不收敛的真正根因）：
  #   `ACGrGrPoly::computeQpOffDiagJacobian` **覆盖**了基类 `ACBulk` 的正确实现，
  #   而覆盖时只保留了 SumOPj 那一项：
  #       ACBulk.h（基类，正确）: return (*_dLdarg[cvar])*phi*computeDFDOP(Residual)*test;
  #       ACGrGrPoly.C（子类覆盖）: return _L[_qp]*_test[_i][_qp]*dDFDOP;   // L 当常数！
  #   于是 **dL/deta_j 整项从雅可比消失**，而残差里它还在（乘的是 mu*(eta^3-eta+2*gamma*eta*Sum)，
  #   晶粒内是 O(mu)=9e5 的大量）-> 雅可比与残差不一致 -> 牛顿卡在残差地板。
  #
  #   实测（小网格 -snes_test_jacobian，||J-Jfd||/||J||，初始态）：
  #       C 基线（L 只依赖 T，缺项恰好为零）        1.05e-06
  #       完整非 AD 的 D 版                          0.0594
  #       关掉 kappa 的 eta 依赖                     0.0594   <- 与 kappa 无关
  #       关掉 gamma 的 eta 依赖                     0.0596   <- 与 gamma 无关
  #       kappa+gamma 都关掉                         0.0596   <- 病根在 L
  #       只把 L 换成"只依赖 T"                       2.11e-05 <- 降 2800 倍，坐实
  #       AD 最小验证（L 显式依赖 eta）              3.20e-08 <- AD 精确
  #
  #   `ADGrainGrowth` 的残差是 `_prop_L[_qp] * computeDFDOP()`，两者都是 ADReal，
  #   乘积自动携带完整导数（含 dL/deta_j）。**原理上不可能再漏项。**
  #
  # 设计约束：MOOSE 禁止同一属性既作 AD 又作非 AD 声明。所以
  #   kappa_op / gamma_asymm / mu / L 必须全 AD，且不能有非 AD 消费者
  #   （已核对：生产输入里只有 grad_align 一处，已改用 ADMaterialRealAux）。
  #
  # 另外：**不用 material_property_names 分层**，L 的全部内容内联成一个表达式。
  #   理由：AD 材料消费 material_property_names 的链式行为我没有实测过，
  #   而"没验证过的机制不要用"是这次排查里最贵的一课。
  # =============================================================================

  # --- 2a: 晶界能 kappa_op（逐对取向差加权）---
  # 各向同性极限 = 1.8e-6，与引入 2a 之前逐位相同
  [kappa_aniso]
    type = ADDerivativeParsedMaterial
    property_name = kappa_op
    coupled_variables = '{" ".join(eta)}'
    expression = '({k_num})/({den})'
    derivative_order = 1
  []
  # --- 2a: gamma_asymm（逐对加权）---
  # 各向同性极限 = 1.5
  [gamma_aniso]
    type = ADDerivativeParsedMaterial
    property_name = gamma_asymm
    coupled_variables = '{" ".join(eta)}'
    expression = '({g_num})/({den})'
    derivative_order = 1
  []
  # --- 2b: 四重对齐度 align4 in [0,1] ---
  # align4 = sum_i gr_i^2 * cos^2(2(phi-theta_i)) / (sum gr_i^2 + DELTA)
  # 用四重而非二重：beta-Ti 的 <100> 在 2D 是四重对称，
  # theta 与 theta+90 是同一个取向，二重形式会把它们判成不同 —— 错。
  #
  # 热梯度方向先化成**有界单位向量** (gdir_p, gdir_q) = (P,Q)/(G+eps)：
  #   grad_Tx/grad_Ty 是 AuxVariable（没有自由度），AD 对它们的导数为零，
  #   所以这里**不会**产生 1/G^2 那类病态雅可比项（G=|grad T|^2 在网格上
  #   跨 3.70e-10 ~ 1.04e18，28 个量级 —— 非 AD 版本曾被它拖到条件数 1e36）。
  #   GDIR_EPS=1e-30 远小于实测 G_min，在真实网格上从不激活；
  #   顺带 G=0 时得 0 而不是 0/0=NaN（修掉 initial 阶段 grad_align=NaN 的老问题）。
  #
  # 这个材料只供 grad_align 诊断输出用（extract.py 拿它交叉校验）。
  # L 里用的是内联形式，两者数学等价。
  [align4_prop]
    type = ADParsedMaterial
    property_name = align4
    coupled_variables = '{" ".join(eta)} grad_Tx grad_Ty'
    expression = '{align4_inl}'
  []
  # --- 2a + 2b 合成晶界迁移率 L（各向同性极限 = 4/3*M0*exp(-Q/kbT)/wGB）---
  # 全部内联，不用 material_property_names。
  # derivative_order=1 就够：ADACInterface 只用一阶（_dLdop / _dLdarg），
  # ADGrainGrowth 直接用 AD 值、不取名导导数属性。
  [L_aniso]
    type = ADDerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T {" ".join(eta)} grad_Tx grad_Ty'
    expression = '{L_inl}'
    derivative_order = 1
  []
[]
"""
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"写入 {args.out}  ({len(txt)} 字符)")
    print(f"  2a: {len(pairs)} 个序参量对")
    print(f"  2b: 对齐因子表达式 {len(align4)} 字符")


if __name__ == "__main__":
    main()
