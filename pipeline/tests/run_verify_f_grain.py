#!/usr/bin/env python3
# =============================================================================
# f_grain 有限差分验证（Gate 0 步骤 4 的执行脚本）
# =============================================================================
#
# 【2026-09-19 ④ 修复后更新】
#   判据改成：
#     数值微分 d(∫f_grain dV)/dηᵢ
#     ==  解析积分 ∫ [ mu0·ηᵢ³ − mu_T·ηᵢ + 2·mu0·γ·ηᵢ·Σ_{j≠i}ηⱼ² ] dV
#
#   右边由 `verify_f_grain.i` 的 `dfdop_check*` 给出，而那是
#   「ACGrGrPoly.C:61 的逐字转录 + f_drive 的 AllenCahn 导数」的逐字组合。
#   所以本脚本核对的是 "我写的 f_grain 的梯度" vs "η 方程里两个核实际用的表达式"。
#
#   T 取 1870 K（不是 1000 K）⇒ mu_T = 0.25074·mu0 ≠ mu0，
#   新旧形式的判据**不相等**，本算例对 ④ 的改动有鉴别力。
#
# 用法：
#     conda activate moose
#     python3 tests/run_verify_f_grain.py [--moose <path>] [--keep]
#
# 退出码：0 = 通过；1 = 不通过（**此时 f_grain 不得用于诊断**）
# =============================================================================

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile

MOOSE_DEFAULT = "/root/moose/modules/phase_field/phase_field-opt"
HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(HERE, "verify_f_grain.i")

# 名义状态（与 .i 里的 initial_condition 一致）
ETA0, ETA1, ETA2 = 0.6, 0.35, 0.15
# 中心差分步长（两组，用于确认 FD 误差按 O(eps^2) 收敛 —— 这本身就是一道自检）
EPS_LIST = [1e-3, 1e-4]

REL_TOL = 1e-6          # 专家判据：相对误差 < 1e-6
MASS_TOL = 1e-10        # 与 M0 比较时也看一眼量级


def run_case(moose, workdir, eta0):
    """跑一次，返回 (F_grain, M0, M1, M2)。"""
    cmd = [
        moose, "-i", "verify_f_grain.i",
        "--n-threads=1",
        f"AuxVariables/gr0/initial_condition={eta0!r}",
    ]
    p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stdout[-4000:] + "\n" + p.stderr[-2000:] + "\n")
        raise RuntimeError(f"MOOSE 退出码 {p.returncode}（eta0={eta0}）")

    csv_path = os.path.join(workdir, "verify_f_grain_out.csv")
    if not os.path.exists(csv_path):
        raise RuntimeError(f"没有输出 CSV：{csv_path}")

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("CSV 为空")

    # 【坑】t=0 那一行后处理器全是 0（材料尚未求值）—— 取最后一行
    last = rows[-1]
    t = float(last["time"])
    if t <= 0.0:
        raise RuntimeError(f"只拿到 t=0 行，材料未求值：{last}")

    def g(key):
        # CSV 表头里键名可能带空格
        for k in last:
            if k.strip() == key:
                return float(last[k])
        raise KeyError(f"CSV 里没有 {key}，实际列={list(last)}")

    return g("F_grain"), g("M0"), g("M1"), g("M2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--moose", default=MOOSE_DEFAULT)
    ap.add_argument("--keep", action="store_true", help="保留临时目录")
    args = ap.parse_args()

    if not os.path.exists(args.moose):
        sys.exit(f"找不到 MOOSE 可执行文件：{args.moose}")
    if not os.path.exists(INPUT):
        sys.exit(f"找不到输入文件：{INPUT}")

    workdir = tempfile.mkdtemp(prefix="verify_f_grain_")
    shutil.copy(INPUT, workdir)
    print(f"工作目录：{workdir}")
    print(f"输入：{INPUT}")
    print()

    results = {}
    try:
        # 【必须先跑名义状态】M0 本身依赖 gr0：
        #     ④ 修复后 M0 = mu*gr0³ + gr0*(2*mu*gamma*(gr1²+gr2²) − mu_T)
        #     dM0/dgr0 = 3*mu*gr0² + 2*mu*gamma*(gr1²+gr2²) − mu_T
        #   在本算例的取值（mu=9e5, mu_T=0.25074*mu0, γ=1.5, η=(0.6,0.35,0.15)）下
        #     = 1.1378e6，而 M0 ≈ 2.939e5 ⇒ eps=1e-4 时相对偏差就有 3.9e-4。
        #   若拿**扰动点**的 M0 当判据，会引入这个系统偏差。
        #   这正是第一版脚本 FAIL 的原因 —— 公式本身没错，是比错了对象。
        nominal = run_case(args.moose, workdir, ETA0)
        print(f"名义状态 eta0={ETA0}  F_grain={nominal[0]:.12e}  "
              f"M0={nominal[1]:.12e}  M1={nominal[2]:.12e}  M2={nominal[3]:.12e}")
        print()

        for eps in EPS_LIST:
            F = {}
            for sign, tag in ((-2, "m2"), (-1, "m1"), (+1, "p1"), (+2, "p2")):
                eta0 = ETA0 + sign * eps
                F[tag] = run_case(args.moose, workdir, eta0)
                print(f"  eps={eps:g}  eta0={eta0:.8f}  F_grain={F[tag][0]:.12e}")
            # 四点中心差分：(F(-2e) - 8F(-e) + 8F(+e) - F(+2e)) / (12 eps)
            # 注：f_grain 对 gr0 是**四次**多项式，而该格式对 5 次以下多项式**精确**
            # （误差项 -(1/30)*eps^4*f'''''），所以这里不是"近似相等"而是"应当机器精度相等"。
            dFdeta0 = (F["m2"][0] - 8.0 * F["m1"][0]
                       + 8.0 * F["p1"][0] - F["p2"][0]) / (12.0 * eps)
            results[eps] = (dFdeta0, nominal[1])
            print()

        print("=" * 78)
        print(f"{'eps':>8} {'数值 dF/dη0':>20} {'解析 ∫dfdop0 dV':>20} "
              f"{'相对误差':>12} {'判定':>6}")
        print("-" * 78)
        ok = True
        for eps in EPS_LIST:
            dFdeta0, M0 = results[eps]
            rel = abs(dFdeta0 - M0) / abs(M0) if M0 != 0 else float("inf")
            good = rel < REL_TOL
            ok = ok and good
            print(f"{eps:>8g} {dFdeta0:>20.12e} {M0:>20.12e} "
                  f"{rel:>12.3e} {'OK' if good else 'FAIL':>6}")
        print("=" * 78)

        # 额外自检：两组 eps 的差应远小于截断误差量级（确认 FD 本身没问题）
        d1 = results[EPS_LIST[0]][0]
        d2 = results[EPS_LIST[1]][0]
        print(f"\nFD 自检：两组步长的 dF/dη0 相对差 = "
              f"{abs(d1 - d2) / abs(d2):.3e}（应 ~ eps^2 量级，说明差分本身稳定）")

        if ok:
            print("\n✅ 通过：f_grain 的梯度与「ACGrGrPoly(mu=mu0) + AllenCahn(f_drive)」两核之和一致，可用于诊断。")
        else:
            print(f"\n❌ 不通过（相对误差 > {REL_TOL:g}）：**f_grain 不得用于诊断**。")
            print("   依次核对：(1) 交叉项系数（Σ_{i<j} 前应为 γ，等价 Σ_{i≠j} 前 γ/2）；")
            print("             (2) 四次项系数应为 mu（常数 9e5），**不是** mu_T；")
            print("             (3) 二次项系数应为 −mu_T/2；")
            print("             (4) dfdop_check* 里的补正项应为 (mu − mu_T)*η，不是 mu_T*η。")
        return 0 if ok else 1
    finally:
        if args.keep:
            print(f"\n保留：{workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
