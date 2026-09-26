#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 3D Gibbs 算例的 CSV：守恒、逐面 Gamma、物理量级。

用法： python3 analyze_run.py results_g3d_run2/case_out.csv
"""
import csv
import math
import os
import sys

GAM0 = 2.1421e-5      # mol/m^2 单层饱和（= 12.9 at/nm^2）
RHOMOL = 101292.8831  # mol/m^3
DH_SEG = -11931.1
RGAS = 8.314462618
AVOG = 6.02214076e23


def A_s(T):
    """A_s(T) = GAM0*exp(-dH_seg/(R T))  [mol/m^2]（Henry 极限的 McLean 斜率）"""
    return GAM0 * math.exp(-DH_SEG / (RGAS * T))


def moles_to_atnm2(g):
    """面过剩量 [mol/m^2] -> [at/nm^2]"""
    return g * AVOG / 1e18


def main(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("CSV 是空的")
    first, last = rows[0], rows[-1]

    def g(r, k):
        return float(r[k])

    print("=" * 78)
    print("CSV：%s   行数 %d" % (os.path.basename(path), len(rows)))
    print("=" * 78)
    print()
    print("【1】时间推进")
    print("  首行 t=%g   末行 t=%g   步数 %d" % (g(first, "time"), g(last, "time"), len(rows) - 1))
    print("  末态 n_elem=%d  n_nonlin=%d  n_lin=%d  dt=%g"
          % (g(last, "n_elem"), g(last, "n_nonlin"), g(last, "n_lin"), g(last, "dt")))
    print()
    print("【2】守恒（这是核心判据）")
    s0, s1 = g(first, "solute_total"), g(last, "solute_total")
    print("  solute_total（rho_mol*c 积分 + A_s*sum Gam 积分）[mol]")
    print("     初 % .12e" % s0)
    print("     末 % .12e" % s1)
    print("     相对漂移 %.3e" % (abs(s1 - s0) / abs(s0)))
    print("  生产自带的 total_solute（只有体相 rho_mol*c 的积分，不含面）")
    print("     初 % .12e   末 % .12e" % (g(first, "total_solute"), g(last, "total_solute")))
    print()
    print("【3】逐条晶界的 Gibbs 过剩量（每一条晶界一个独立状态量）")
    for k in range(6):
        key = "gam%d_int" % k
        if key not in last:
            break
        area = g(last, "gb%d_area" % k)
        gi = g(last, "gam%d_int" % k)
        gm = g(last, "gam%d_max" % k)
        gam_avg = gi / area if area else float("nan")
        print("  晶界 %d：面积 %.4e m^2   ∫Gam dA %.6e   Gam_avg %.6f   Gam_max %.6f"
              % (k, area, gi, gam_avg, gm))
        for T in (923.0, 1750.0, 1950.0):
            print("        @T=%4.0f K: Gamma = A_s*Gam = %.3e mol/m^2 = %.3f at/nm^2"
                  % (T, A_s(T) * gam_avg, moles_to_atnm2(A_s(T) * gam_avg)))
    print()
    print("【4】溶质场")
    print("  c_max %.6f   c_min %.6f   c_solid_avg %.6f" % (g(last, "c_max"), g(last, "c_min"),
                                                            g(last, "c_solid_avg")))
    print("  （初值 c0 = 0.036）")
    print()
    print("【5】序参量越界检查（应 <= ~1；超得多说明界面欠解析）")
    print("  " + "  ".join("gr%d=%.4f" % (k, g(last, "gr%d_max" % k)) for k in range(8)))
    print()
    print("【6】液相占比 / 晶粒数")
    print("  liquid_frac %.4f   grain_tracker %d" % (g(last, "liquid_frac"), g(last, "grain_tracker")))
    print()
    print("【7】逐步历史（时间, dt, c_min, c_max, solute_total, n_nonlin）")
    for r in rows:
        print("  %-14g %-11g % .6e % .6f % .12e %s"
              % (float(r["time"]), float(r["dt"]), float(r["c_min"]), float(r["c_max"]),
                 float(r["solute_total"]), r.get("n_nonlin", "?")))
    mass_balance(rows)
    profile(path)


def mass_balance(rows):
    """逐点算「面拿到的」vs「体相少的」 —— 守恒缺陷必须**直接量出来**，不能只看合计数。"""
    r0, r1 = rows[0], rows[-1]
    gam0, gam1 = float(r1["gam0_int"]), float(r1["gam1_int"])
    gam0_0, gam1_0 = float(r0["gam0_int"]), float(r0["gam1_int"])
    sum_g = (gam0 - gam0_0) + (gam1 - gam1_0)
    sum_g0 = float(r0.get("gam0_int", 0)) + 0
    t0 = float(r0["T_at_gb0"]) if "T_at_gb0" in r0 else 1800.0
    As = A_s(t0)
    surf = As * sum_g
    bulk = RHOMOL * (float(r1["c_int_pp"]) - float(r0["c_int_pp"]))
    print()
    print("【8】守恒缺陷（**逐项量出来**）")
    print("  面拿到   A_s*ΔΣ∫Gam dA = %.6e * %.6e = % .6e mol" % (As, sum_g, surf))
    print("  体相少了 ρ_mol*Δ∫c dV  = %.6e * %.6e = % .6e mol"
          % (RHOMOL, float(r1["c_int_pp"]) - float(r0["c_int_pp"]), bulk))
    if bulk != 0:
        ratio = abs(surf) / abs(bulk)
        print("  比值 面/体相 = %.4e   ⇒ %s" % (ratio,
              "守恒（差 ≤2%%）✓" if abs(ratio - 1) < 0.02
              else "**不守恒**（体相没有按量付出）"))
    if "depletion" in r1:
        print("  界面贫化率 1 - c(界面)/c(体相平均) = % .4e" % float(r1["depletion"]))
        print("     （晶界真在抽溶质时它应显著 > 0；**负值 = 界面处反而更浓 = 没有抽走**）")


def profile(path, gb_x_um=(-236.8661444, -195.9626031)):
    """跨晶界的浓度剖面。

    ⚠ AGENTS.md 教训 25：LineValueSampler **每个时间步写一个 CSV**，
      `os.listdir(...)[0]` 拿到的是随机时间步 ⇒ 必须按文件名里的步号排序取最后一步。
    """
    import glob
    import re
    d = os.path.dirname(os.path.abspath(path))
    fs = glob.glob(os.path.join(d, "*_profile_gb0_*.csv"))
    if not fs:
        print()
        print("【9】跨晶界剖面：没找到（旧算例没有这个后处理器）")
        return

    def step(f):
        m = re.search(r"_(\d+)\.csv$", f)
        return int(m.group(1)) if m else -1

    fs = sorted(fs, key=step)
    last = fs[-1]
    print()
    print("【9】跨晶界 c 剖面（最后一步 %s，共 %d 个时间步文件）"
          % (os.path.basename(last), len(fs)))
    with open(last, newline="") as f:
        rr = list(csv.DictReader(f))
    if not rr:
        print("  （空文件）")
        return
    xg = gb_x_um[0] * 1e-6
    print("  晶界在 x = %.4f µm；剖面 x 从 %.2f 到 %.2f µm"
          % (gb_x_um[0], float(rr[0]["x"]) * 1e6, float(rr[-1]["x"]) * 1e6))
    print("      Δx[µm]      x[µm]        c")
    for r in rr:
        dx = (float(r["x"]) - xg) * 1e6
        print("   %+8.3f  %10.4f   %.8f" % (dx, float(r["x"]) * 1e6, float(r["c"])))
    far = [float(r["c"]) for r in rr if abs((float(r["x"]) - xg)) > 5e-6]
    near = [float(r["c"]) for r in rr if abs((float(r["x"]) - xg)) <= 2e-6]
    if far and near:
        cf, cn = sum(far) / len(far), sum(near) / len(near)
        print()
        print("  远场(>5µm) 平均 c = %.8f   界面附近(±2µm) 平均 c = %.8f" % (cf, cn))
        print("  剖面贫化 = 1 - 近/远 = % .4e" % (1 - cn / cf))
    # 【网格振荡度量】二阶差分（棋盘振荡会把它放大到 ~1e-4 以上）
    cc = [float(r["c"]) for r in rr]
    d2 = [abs(cc[i + 1] - 2 * cc[i] + cc[i - 1]) for i in range(1, len(cc) - 1)]
    if d2:
        print("  网格振荡：max|c(i+1)-2c(i)+c(i-1)| = %.3e   相对 c0 = %.3e"
              % (max(d2), max(d2) / 0.036))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "case_out.csv")
