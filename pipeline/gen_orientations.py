#!/usr/bin/env python3
"""
生成每个序参量的「晶体取向」及其派生的晶界性质，供 2a（取向差依赖的晶界性质）
与 2b（热流方向驱动的晶粒选择）共同使用。

=== 为什么取向要统一生成 ===
2a 和 2b 必须用**同一套取向**，否则"晶粒 A 的易生长方向"在两边不一致，
物理上自相矛盾。

=== 关于 2a 的实现方式（重要限制）===
MOOSE 有现成的 `GBAnisotropy` 材料，它用**成对取向差表**（每个 op-pair 一组
σ/M0/Q），物理上更严格。但它会**声明 `mu` 属性**，而本算例的 `mu` 被熔化开关
占用（液相内变负），两者不能共存。

所以 2a 这里退一步：给**每个序参量**一组 GB 性质，局部值按 η² 加权平均。
这捕捉了"不同晶粒取向不同 → 晶界性质不同"的实质，但**不是严格的成对取向差**。
要严格版需要写 C++ 材料把 GBAnisotropy 的成对加权和自定义 mu 合并。

=== 取向约定 ===
β 相是 BCC，易生长方向为 <100>，在 2D 截面里有 4 重对称，所以取向只需
在 [0, 90°) 内取值。θ_i 就是该晶粒 <100> 方向与 x 轴的夹角。

=== 晶界性质随取向差的模型（占位，待核）===
用 Read–Shockley 形式，θ_m = 15°：
    Δθ < θ_m :  σ/σ_H = (Δθ/θ_m)·(1 − ln(Δθ/θ_m))
    Δθ ≥ θ_m :  σ/σ_H = 1
迁移率用较弱的依赖（∝ 该因子的平方根），激活能对低角晶界略高。

⚠️ **这些函数形式是占位**：真实 Ti64 的 β/β 晶界性质随取向差的依赖需查文献。
基线（大角极限）保持 2a 之前的值：σ_H=0.6 J/m², M0_H=232 m⁴/(J·s), Q_H=3.234 eV。

用法：
    python3 gen_orientations.py [--op-num 8] [--seed 3] [--out-prefix orient]
输出：
    <prefix>_constants.txt   —— 可直接粘进 MOOSE constant_names/constant_expressions
    <prefix>_table.csv       —— 逐对取向差与性质（供检查/画图）
"""

import argparse
import math

# --- 基线（大角极限），与引入取向之前保持一致 ---
SIGMA_H = 0.6          # J/m^2
MOB0_H = 232.0         # m^4/(J*s)
Q_H = 3.234            # eV
THETA_M = 15.0         # deg，Read-Shockley 的临界取向差


def rs_factor(dtheta_deg):
    """Read-Shockley 因子（归一化到大角极限）。"""
    if dtheta_deg >= THETA_M:
        return 1.0
    x = max(dtheta_deg, 1e-6) / THETA_M
    return x * (1.0 - math.log(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--op-num", type=int, default=8)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--out-prefix", default="orient")
    args = ap.parse_args()

    # --- 取向：在 [0, 90) 内尽量分散（用确定性的等间距 + 抖动，可复现）---
    n = args.op_num
    th = [(i * 90.0 / n + (i * 37 % 11) * 0.9) % 90.0 for i in range(n)]
    th = sorted(set(round(t, 4) for t in th))
    while len(th) < n:                       # 万一去重后不足，补几个
        th.append(round((len(th) * 13.7) % 90.0, 4))
    th = th[:n]

    print(f"取向 θ_i (度): {[round(t,2) for t in th]}")

    # --- 逐对取向差 -> 性质 ---
    rows = []
    sigma = [[0.0] * n for _ in range(n)]
    mob0 = [[0.0] * n for _ in range(n)]
    qact = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                sigma[i][j], mob0[i][j], qact[i][j] = SIGMA_H, MOB0_H, Q_H
                continue
            d = abs(th[i] - th[j]) % 90.0
            d = min(d, 90.0 - d)             # 4 重对称 -> 取向差取 [0,45]
            f = rs_factor(d)
            sigma[i][j] = SIGMA_H * f
            mob0[i][j] = MOB0_H * math.sqrt(f)
            qact[i][j] = Q_H * (1.0 + 0.2 * (1.0 - f))
            if i < j:
                rows.append((i, j, d, sigma[i][j], mob0[i][j], qact[i][j]))

    # --- 逐晶粒取「与所有邻居的平均」作为该 op 的单一性质（供 input 用）---
    def per_op(mat):
        return [sum(mat[i][j] for j in range(n) if j != i) / (n - 1) for i in range(n)]

    sig_i, mob_i, q_i = per_op(sigma), per_op(mob0), per_op(qact)

    # --- 输出：直接可粘进 MOOSE 的两个字符串 ---
    def fmt(vals):
        return " ".join(f"{v:.6g}" for v in vals)

    with open(f"{args.out_prefix}_constants.txt", "w") as f:
        f.write("# 由 gen_orientations.py 生成，勿手改\n")
        f.write(f"# 取向 θ_i (度): {[round(t,2) for t in th]}\n\n")
        f.write("constant_names = '"
                + " ".join(f"ct{i}" for i in range(n)) + " "
                + " ".join(f"st{i}" for i in range(n)) + " "
                + " ".join(f"sig{i}" for i in range(n)) + " "
                + " ".join(f"mob{i}" for i in range(n)) + " "
                + " ".join(f"q{i}" for i in range(n)) + "'\n")
        f.write("constant_expressions = '"
                + fmt([math.cos(math.radians(t)) for t in th]) + " "
                + fmt([math.sin(math.radians(t)) for t in th]) + " "
                + fmt(sig_i) + " "
                + fmt(mob_i) + " "
                + fmt(q_i) + "'\n")

    with open(f"{args.out_prefix}_table.csv", "w") as f:
        f.write("op_i,op_j,delta_theta_deg,sigma,mob0,Q\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]:.3f},{r[3]:.6g},{r[4]:.6g},{r[5]:.6g}\n")

    print()
    print(f"逐晶粒平均性质:")
    print(f"  σ_i  (J/m^2)   : {[round(v,4) for v in sig_i]}")
    print(f"  M0_i (m^4/Js)  : {[round(v,1) for v in mob_i]}")
    print(f"  Q_i  (eV)      : {[round(v,4) for v in q_i]}")
    print()
    print(f"写入 {args.out_prefix}_constants.txt 与 {args.out_prefix}_table.csv")


if __name__ == "__main__":
    main()
