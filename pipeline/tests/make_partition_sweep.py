#!/usr/bin/env python3
# =============================================================================
# 生产几何下的分凝测试：扫 kappa_c，看 k_eff 是否还等于平衡值 0.6303
# =============================================================================
# 【要回答的问题】
#   生产配置 kappa_c = 1.125e-11 ⇒ c 的界面宽 w_c = sqrt(kappa_c/k_c) = 3.54 µm，
#   而晶界界面宽 d = sqrt(2*kappa_op/mu0) = 2.00 µm ⇒ **w_c > d**。
#   判据是 w_c << d。所以在生产几何下 k 到底偏多少，必须实测，不能从基准的
#   ξ=0.1 µm 那个极端情形外推。
#
# 【做法】静止界面（dG=0），初值取精确平衡剖面，跑到平衡后量 k_eff = c_s/c_l。
#   扫 kappa_c = {1.125e-11(生产), 1e-13, 1e-14, 1e-15, 1e-16}
#
# 用法： python3 make_partition_sweep.py     （生成 /root/work/g1/psweep/*）
# =============================================================================
import io
import math
import os

SRC = "/mnt/f/speed_up/pipeline/tests/front1d.i"
OUTDIR = "/root/work/g1/psweep"

# --- 用生产几何：d = 2 µm 的界面，网格 dx = 0.5 µm（4 单元/界面）---
D_IFACE = 2.0e-6          # = sqrt(2*kappa_op/mu0)，生产值
SIGMA = 0.6
K_C, A_PART, C0 = 0.9, 0.264, 0.036
M_MOB = 2.8e-9
D_L = M_MOB * K_C

# 双势阱参数：让 xi = D_IFACE、sigma = 0.6
kWg = (3.0 * math.sqrt(8.0) * SIGMA) ** 2
KAPPA = math.sqrt(kWg * D_IFACE ** 2 / 8.0)
WG = math.sqrt(kWg / (D_IFACE ** 2 / 8.0))

DX = D_IFACE / 4.0
LDOM = 40.0e-6
N = int(round(LDOM / DX))
X0 = LDOM * 0.25

KAPPAS = [1.125e-11, 1e-13, 1e-14, 1e-15, 1e-16]


def main():
    base = io.open(SRC, encoding="utf-8").read()
    os.makedirs(OUTDIR, exist_ok=True)
    print("生产几何：界面宽 = %.2f um, 网格 dx = %.2f um (%.0f 单元/界面), 域长 %.0f um, %d 单元"
          % (D_IFACE * 1e6, DX * 1e6, D_IFACE / DX, LDOM * 1e6, N))
    print()
    print("%-12s %-12s %-16s" % ("kappa_c", "w_c (um)", "w_c / d"))
    for kc in KAPPAS:
        wc = math.sqrt(kc / K_C)
        print("%-12.4g %-12.5f %-16.3f" % (kc, wc * 1e6, wc / D_IFACE))
    print()

    for kc in KAPPAS:
        t = base
        reps = [
            ("  nx = 160", "  nx = %d" % N),
            ("  xmax = 4.0e-5", "  xmax = %.6e" % LDOM),
            ("    prop_values = '5.833e-4   3.6e-6    1.125e-11 2.8e-9'",
             "    prop_values = '5.833333e-04   %.6e    %.6e 2.8e-9'" % (KAPPA, kc)),
            ("    constant_expressions = '7.2e6 -3.6e5 0.9 0.036 0.264'",
             "    constant_expressions = '%.6e 0 0.9 0.036 0.264'" % WG),   # dG = 0
            ("expression = '0.5*(1-tanh((x-5.0e-6)/2.0e-6))'",
             "expression = '0.5*(1-tanh((x-%.6e)/%.6e))'" % (X0, D_IFACE)),
            ("    elementid = 4", "    elementid = %d" % max(2, int(X0 / DX / 4))),
            ("    elementid = 155", "    elementid = %d" % (N - 4)),
            ("  end_time = 8.0e-3", "  end_time = 2.0e-2"),
        ]
        for a, b in reps:
            assert a in t, "模板里找不到 %r" % a[:40]
            t = t.replace(a, b, 1)
        # 溶质初值 -> 静止界面平衡剖面 c = c0*k_c/(k_c + 2A*eta^2)
        old_c = ("expression = 'if(x<5.0e-6, 0.036,\n"
                 "                    0.036*(1 + (1-0.6303)/0.6303*exp(-1.26e-3*(x-5.0e-6)/2.52e-9)))'")
        assert old_c in t, "找不到解析初值"
        t = t.replace(old_c,
                      "expression = '0.036*0.9/(0.9 + 2*0.264*pow(0.5*(1-tanh((x-%.6e)/%.6e)),2))'"
                      % (X0, D_IFACE), 1)
        d = os.path.join(OUTDIR, "kc%.4g" % kc)
        os.makedirs(d, exist_ok=True)
        io.open(os.path.join(d, "front1d.i"), "w", encoding="utf-8", newline="").write(t)
        print("  已写 %s/front1d.i" % d)


if __name__ == "__main__":
    main()
