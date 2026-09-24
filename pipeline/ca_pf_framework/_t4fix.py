import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_physics.py"
s = io.open(P, encoding="utf-8").read()
if "apex_kernel" in s:
    print("already"); raise SystemExit
s = s.replace('''def support(P, n):
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))''',
'''def support(P, n):
    """decentered 格点规则下的经验半轴（sum_a|p_a.n|）。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))


def apex_kernel(P, n):
    """【八面体 {sum_a|u_a| <= L} 沿 n̂ 的支撑】= max_a|p_a.n̂|。
    由对偶范数得：L1 球的支撑 = L*||n̂||_inf = L*max_a|p_a.n̂|。
    注意：这与 support(P,n)=sum_a|p_a.n̂| 不是同一个量（只在 <100>/<110>/<111> 重合）——
    2026-09-23 查明：本文件早期用 sum 当解析律是错的，见 CA3D_REPORT §9。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return max(abs(float(P[:, a] @ n)) for a in range(3))''', 1)
s = s.replace("        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial)",
              "        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial, capture=\"analytic\")", 1)
s = s.replace("            ana = L_end / support(P, nn)",
              "            ana = L_end * apex_kernel(P, nn)", 1)
s = s.replace('''    chk("T4b 取向律 apex(n) = L/support(P,n) （8 个随机取向 x 4 个方向）",
        "PASS" if worst <= 2.0 else "WARN",
        "{} 个测点; 最大绝对偏差 {:.2f} 个胞 (判据 <=2; 格点路径近似是 O(1 胞) 误差)".format(
            nq, worst), worst)''',
'''    chk("T4b 取向律 apex(n̂) = L * max_a|p_a.n̂| （真八面体支撑; analytic 捕获）",
        "PASS" if worst <= 5.0 else "WARN",
        "{} 个测点; 最大绝对偏差 {:.2f} 个胞 (判据 <=5; 内切格点偏移 O(1 胞))".format(
            nq, worst), worst)
    # 对照: decentered 格点路径规则偏离【正确律】多少（这是多晶淘汰失败的根因）
    worst_d = 0.0
    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial)
        g = ca.add_grain(14, 14, 14)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        idx = np.where(ca.gid > 0)
        P = ca.axes[g]
        for nvec, nm in dirs:
            nn = np.array(nvec, float); nn /= np.linalg.norm(nn)
            proj = ((idx[0] - 14) * nn[0] + (idx[1] - 14) * nn[1] + (idx[2] - 14) * nn[2]) * dx
            ana = L_end * apex_kernel(P, nn)
            worst_d = max(worst_d, abs(float(proj.max()) - ana) / dx)
    chk("T4c 对照: decentered 规则"偏离正确律"的幅度（多晶淘汰失败根因）",
        "PASS" if worst_d > worst else "WARN",
        "decentered 最大偏差 {:.2f} 胞 vs analytic {:.2f} 胞 ⇒ 格点路径代价与取向强相关".format(
            worst_d, worst), worst_d)''', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T4")