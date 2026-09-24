# -*- coding: utf-8 -*-
"""_patch_t4.py --- 修 T4b/T4c：断言正确的径向函数律，并让判据能区分两种律；T4c 显式指定 decentered"""
import io, sys
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_physics.py"
s = io.open(P, encoding="utf-8").read()

# 1) apex_kernel 增加"径向函数"版本
old = '''def apex_kernel(P, n):
    """【八面体 {sum_a|u_a| <= L} 沿 n̂ 的支撑】= max_a|p_a.n̂|。
    由对偶范数得：L1 球的支撑 = L*||n̂||_inf = L*max_a|p_a.n̂|。
    注意：这与 support(P,n)=sum_a|p_a.n̂| 不是同一个量（只在 <100>/<110>/<111> 重合）——
    2026-09-23 查明：本文件早期用 sum 当解析律是错的，见 CA3D_REPORT §9。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return max(abs(float(P[:, a] @ n)) for a in range(3))'''
new = '''def apex_support(P, n):
    """八面体 {sum_a|u_a| <= L} 的【支撑函数】= max_a|p_a.n̂|（沿 n̂ 到支撑平面的距离）。

    ⚠ 2026-09-23 审计（CA3D_AUDIT §N2）纠正：**支撑函数不是包络沿 n̂ 的半径**。
    包络的【径向函数】是 L / sum_a|p_a.n̂|（即下面 apex_kernel）。两者只在
    <100>/<110>/<111> 上巧合相等，中间方向差最多 ~20%（在 ℓ=15 胞时 ~1~3 胞）。
    本文件早期把支撑函数当解析律（且容差给到 5 胞）⇒ 判据看不出任何东西。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return max(abs(float(P[:, a] @ n)) for a in range(3))


def apex_kernel(P, n):
    """八面体 {sum_a|u_a| <= L} 沿 n̂ 的【径向函数】= 1 / sum_a|p_a.n̂|（乘 L 即半径）。
    这是 MATH_FRAMEWORK §4.4 写的 r_g(n̂)=l_g/sum_a|p_a.n̂|，也是 CA 的 thr=dx*Σ 所实现的口径。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return 1.0 / sum(abs(float(P[:, a] @ n)) for a in range(3))'''
if old not in s: print("!! 1"); sys.exit(1)
s = s.replace(old, new)

# 2) T4b：同时算两个偏差，要求"径向律吻合"且"能区分支撑律"
old = '''    worst = 0.0
    nq = 0
    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial, capture="analytic")
        g = ca.add_grain(14, 14, 14)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        idx = np.where(ca.gid > 0)
        P = ca.axes[g]
        for nvec, nm in dirs:
            nn = np.array(nvec, float); nn /= np.linalg.norm(nn)
            proj = ((idx[0] - 14) * nn[0] + (idx[1] - 14) * nn[1] + (idx[2] - 14) * nn[2]) * dx
            apex = float(proj.max())
            ana = L_end * apex_kernel(P, nn)
            if ana > 3 * dx:
                worst = max(worst, abs(apex - ana) / dx)      # 按胞数
                nq += 1
    chk("T4b 取向律 apex(n̂) = L * max_a|p_a.n̂| （真八面体支撑; analytic 捕获）",
        "PASS" if worst <= 5.0 else "WARN",
        "{} 个测点; 最大绝对偏差 {:.2f} 个胞 (判据 <=5; 内切格点偏移 O(1 胞))".format(
            nq, worst), worst)'''
new = '''    worst = 0.0        # 与【径向函数】l/Σ 的偏差
    worst_sup = 0.0    # 与【支撑函数】l*max 的偏差（用于证明判据有区分度）
    nq = 0
    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial, capture="envelope")
        g = ca.add_grain(14, 14, 14)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        idx = np.where(ca.gid > 0)
        P = ca.axes[g]
        for nvec, nm in dirs:
            nn = np.array(nvec, float); nn /= np.linalg.norm(nn)
            proj = ((idx[0] - 14) * nn[0] + (idx[1] - 14) * nn[1] + (idx[2] - 14) * nn[2]) * dx
            apex = float(proj.max())
            ana = L_end * apex_kernel(P, nn)
            ana_s = L_end * apex_support(P, nn)
            if ana > 3 * dx:
                worst = max(worst, abs(apex - ana) / dx)      # 按胞数
                worst_sup = max(worst_sup, abs(apex - ana_s) / dx)
                nq += 1
    ok = (worst <= 2.5) and (worst < worst_sup - 0.2)     # 吻合径向律 + 判据有区分度
    chk("T4b 取向律 = L/Σ_a|p_a.n̂|（八面体径向函数; envelope 捕获）",
        "PASS" if ok else "WARN",
        "{} 个测点; 与 l/Σ 最大偏差 {:.2f} 胞, 与 l*max(支撑律) 偏差 {:.2f} 胞 "
        "(判据: <=2.5 胞 且 明显优于支撑律)".format(nq, worst, worst_sup), (worst, worst_sup))'''
if old not in s: print("!! 2"); sys.exit(1)
s = s.replace(old, new)

# 3) T4c：显式 decentered
old = '''    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial)
        g = ca.add_grain(14, 14, 14)'''
new = '''    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial, capture="decentered")
        g = ca.add_grain(14, 14, 14)'''
if old not in s: print("!! 3"); sys.exit(1)
s = s.replace(old, new)
old = '''    chk("T4c 对照: decentered 规则偏离正确律的幅度（多晶淘汰失败根因）",'''
new = '''    chk("T4c 对照: decentered 规则偏离径向律的幅度（多晶淘汰失败根因）",'''
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8").write(s)
print("T4 判据已修; 行数 =", s.count("\n")+1)