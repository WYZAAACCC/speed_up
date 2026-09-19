#!/usr/bin/env python3
"""
把**抗截留项**（antitrapping current）补进生产输入。

## 为什么必须补（这是缺口 #3 的修复主体）

实测（`validated/run_prod_1d.sh`）生产工作点上模型给出 `k_eff = 0.999015`，
而物理值（Aziz，`a0 = 0.3 nm`）是 `0.6549`
⇒ **界面排出的溶质被低估 350 倍 ⇒ 微偏析被低估 350 倍**。
而微偏析正是本课题要预测的量（晶界偏析 Γ_GB 的来源）。

根因不是网格，也不是 `kappa_c`（那两个都实测排除过）：

    L_eff = δ_c + 1.5·ξ        （4 个 s 档反解 1.29~1.36，跨 8 倍 δ_c；生产外推 476 倍仍成立）

**溶质是在整个弥散界面 ξ 上被排出的，不是在锐前沿上** ⇒ 富集区至少 ξ 宽。

抗截留项就是为消掉这一项而存在的（Karma–Rappel；Plapp 2011）。

## 系数

MOOSE 官方形式（读自 `phase_field/test/tests/GrandPotentialPFM/
GrandPotentialAnisotropyAntitrap.i`）：

    [int]  property_name = rhodiff   expression = 'int_width*(rhob-rhoa)'
    [rhoa] expression = 'w/Vm^2/ka + caeq/Vm'   ← 相 α 的浓度 c_α
    [rhob] expression = 'w/Vm^2/kb + cbeq/Vm'   ← 相 β 的浓度 c_β
    ⇒ F = W·(c_β − c_α) = W·(c_l − c_s) = W·(1−k)·c_l

本模型没有 per-phase 浓度拆分（`c` 是混合成分）⇒ 参数化为
`F_at = ALPHA·W·(1−k_eq)·c`，**在 1D 上标定**（`validated/run_antitrap2.sh`）：

    ALPHA:   0        1        2        3
    k_eff:   0.7962   0.7090   0.6259✅  0.5511     (s=1, k_e = 0.6303)
    k_eff:   0.8611   0.7288   0.6037    —         (s=2)

⇒ **同一个 `ALPHA = 2` 在两个 s 上都是最优** ⇒ 这是与界面宽无关的修正，不是曲线拟合。

⚠ **`ALPHA` 与 `W` 的乘积才是物理量**（`W` 的定义依赖约定）。1D 算例的 `η` 剖面是
标准 tanh、`W = 2 µm`；生产的 η 是 `ACGrGrPoly` 的剖面（不是 tanh）。
**两者的尾部衰减长相同**（`λ_tail = sqrt(2κ/Wg) = sqrt(κ_op/(2μ0)) = 1 µm`），
所以默认取 `--w 2e-6`。
⚠⚠ **这一条是本修复里唯一还需要标定的地方** —— 建议用生产参数的 1D 界面算例复核。

## ⚠ 必须乘 `(1 − h_gb)`：抑制晶界上的伪溶质流

本模型的 η **兼表两件事**：固/液 与 晶粒身份。晶粒长大时 `η̇ ≠ 0`
⇒ 不加抑制的话，**每条迁移中的晶界都会凭空产生溶质流**。
生产输入里**已有** `h_gb` 指示（`[solute_hgb]`：二元晶界 = 1、其余 = 0）
⇒ 直接用 `F_at = ALPHA·W·(1−k_eq)·c·(1 − h_gb)`。

## 为什么它不影响已有的全部验证

抗截留项是一个**散度项**，且在**静止界面**（`φ̇ = 0`）上恒为 0：
* 1D 实测守恒漂移 = **0.00e+00**
* `V = 0` 的平衡分配（T4）、晶界过剩（T11）、Ω₀ 标定 —— **一个都不受影响**

## 用法

    python3 make_antitrap_prod.py --src stage1_meltpool_c.i --out x.i --dry-run
    python3 make_antitrap_prod.py --src stage1_meltpool_c.i --out stage1_meltpool_c.i
"""

import argparse
import difflib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

N = 8
# 由 [free_energy] 的 constant_expressions 给出：k_c = 0.9, A_part = 0.264
#   ⇒ k_eq = 1/(1 + 2A/k_c) = 0.6303
K_EQ = 0.6303


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--alpha", type=float, default=2.0,
                    help="1D 标定值（见文件头）")
    ap.add_argument("--w", type=float, default=2.0e-6,
                    help="界面宽参数 [m]；生产 η 不是 tanh，见文件头的警告")
    ap.add_argument("--k-eq", type=float, default=K_EQ)
    ap.add_argument("--no-gb-suppress", action="store_true",
                    help="⚠ 危险：关掉 (1−h_gb) 抑制，会在晶界上产生伪溶质流")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()
    out = src
    gb = "" if a.no_gb_suppress else "*(1-h_gb)"

    # ---- ① susceptibility 材料 ----
    # ⚠ MOOSE 的 CoupledSusceptibilityTimeDerivative 会索取 `dF/dw`（w = 核作用的变量）。
    #   我们的 F 不依赖 w ⇒ 正确值是 0，但**不能指望它被静默填零**
    #   （本仓库 3.1 那条「静默为 0」的教训）⇒ 显式写 `+ 0*w` 把属性做实。
    mat = (
        f"  # 【抗截留】Karma–Rappel / Plapp 薄界面抗截留项的 susceptibility\n"
        f"  #   F = ALPHA·W·(1−k_eq)·c·(1−h_gb)\n"
        f"  #   ALPHA = {a.alpha:g} 是 1D 标定值（validated/run_antitrap2.sh）\n"
        f"  #   (1−h_gb)：抑制晶界上的伪溶质流 —— 本模型的 η 兼表晶粒身份，\n"
        f"  #             晶粒长大时 η̇ ≠ 0，不抑制就会凭空产生溶质流\n"
        f"  #   `+ 0*w`：让 dF/dw 这个属性确实存在（值为 0），避免依赖静默默认\n"
        f"  [at_susc]\n"
        f"    type = DerivativeParsedMaterial\n"
        f"    property_name = F_at\n"
        f"    coupled_variables = 'c w'\n"
        + ("    material_property_names = 'h_gb'\n" if not a.no_gb_suppress else "")
        + f"    constant_names = 'ALPHA W k_eq'\n"
        f"    constant_expressions = '{a.alpha:g} {a.w:.6g} {a.k_eq:g}'\n"
        f"    expression = 'ALPHA*W*(1-k_eq)*c{gb} + 0*w'\n"
        f"    derivative_order = 2\n"
        f"  []\n"
    )
    m = re.search(r"^\[Materials\]\n", out, re.M)
    if not m:
        sys.exit("错误：找不到 [Materials] 块")
    out = out[:m.end()] + mat + out[m.end():]

    # ---- ② 每个序参量一个 AntitrappingCurrent 核 ----
    others = " ".join(f"gr{j}" for j in range(N))
    ker = ""
    for i in range(N):
        ker += (
            f"  # 【抗截留】gr{i} 的界面推进所带的溶质再分配修正\n"
            f"  [gr{i}_antitrap]\n"
            f"    type = AntitrappingCurrent\n"
            f"    variable = w\n"
            f"    v = gr{i}\n"
            f"    f_name = F_at\n"
            f"    # 必须列出 F_at 依赖的全部变量：c 直接依赖，gr_j 经 h_gb 依赖。\n"
            f"    # 少列 ⇒ _dFdarg 拿不到 ⇒ 非对角雅可比缺项（P0-1 同类）。\n"
            f"    coupled_variables = 'c {others}'\n"
            f"  []\n"
        )
    m = re.search(r"^\[Kernels\]\n", out, re.M)
    if not m:
        sys.exit("错误：找不到 [Kernels] 块")
    out = out[:m.end()] + ker + out[m.end():]

    print("将做以下改动：")
    print(f"  1. 新增 1 个 `[at_susc]` 材料：F_at = {a.alpha:g}·{a.w:.3g}·(1−{a.k_eq:g})·c{gb} + 0*w")
    print(f"  2. 新增 {N} 个 `AntitrappingCurrent` 核（每个序参量一个）")
    print(f"  3. 每个核的 coupled_variables = 'c gr0..gr{N-1}'")
    if a.no_gb_suppress:
        print("  ⚠⚠ --no-gb-suppress：晶界上会有伪溶质流，仅供对照实验")
    print()

    diff = list(difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile=a.src, tofile=a.out))
    nchg = len([d for d in diff if d.startswith(("+", "-"))]) - 2
    print(f"diff：{nchg} 行变化")

    if a.dry_run:
        sys.stdout.writelines(diff[:80])
        print("\n(--dry-run：没有写文件)")
        return

    open(a.out, "w", encoding="utf-8", newline="").write(out)
    open(a.out + ".diff", "w", encoding="utf-8", newline="").write("".join(diff))
    print(f"\n写出 {a.out}    diff 存到 {a.out}.diff")
    print("\n自检：")
    n_at = out.count("type = AntitrappingCurrent")
    n_susc = out.count("property_name = F_at")
    n_fat = out.count("f_name = F_at")
    n_hgb = out.count("material_property_names = 'h_gb'")
    print(f"  AntitrappingCurrent 核数 : {n_at}（应为 {N}）")
    print(f"  F_at 定义数              : {n_susc}（应为 1）")
    print(f"  `f_name = F_at` 引用数   : {n_fat}（应为 {N}）")
    print(f"  h_gb 引用数              : {n_hgb}（带抑制时应为 1 = 只有 at_susc；"
          f"`h_gb` 在 [solute_hgb] 里是 property_name，不在这里数）")
    assert n_at == N, f"AntitrappingCurrent 数不对：{n_at} != {N}"
    assert n_susc == 1, f"F_at 定义数不对：{n_susc} != 1"
    assert n_fat == N, f"f_name = F_at 数不对：{n_fat} != {N}"
    assert n_hgb == (0 if a.no_gb_suppress else 1), f"h_gb 引用数不对：{n_hgb}"
    # 生产输入里 w 必须存在（核作用在 w 上）
    assert re.search(r"^\s*\[w\]\s*$", out, re.M), "生产输入里找不到变量 w"


if __name__ == "__main__":
    main()
