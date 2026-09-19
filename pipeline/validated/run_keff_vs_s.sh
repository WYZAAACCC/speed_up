#!/bin/bash
# ⚠⚠ **本脚本的第一版结论已被推翻，只保留作记录。用 `run_keff_convergence.sh`。**
#
# 为什么错（2026-09-19 当场发现）：
#   1. **预期本身就错**：移动前沿处的 `k_eff = c_solid/c_max` **不等于**平衡值 0.6303。
#      这一点 `VALIDATION_STATUS.md` 的 T7 段早就写明（T7 实测 `k_eff ≈ 0.887`）——
#      T4 量的是静止界面的**平衡**分配系数，两者不是同一个量。
#      实测 `s=1` 给 0.880，与 T7 一致 ✓ —— 是**我的判读**错了，不是模型错了。
#   2. **网格没收敛**：`s` 越大溶质边界层 `δ = D/V` 越薄。`s=1000` 时
#      `δ = 2 nm` 而 `dx = 250 nm` ⇒ 那几档测的是**网格伪影**。
#
# ⇒ 正确的问题在 `run_keff_convergence.sh`：**对每个 s 加密 dx，看 k_eff 收不收敛。**
#
# ---------------------------------------------------------------------------
# 缺口 #3 的第一版实验（**已被取代**）：模型的 k_eff 随界面 Péclet 数 s = ξV/D 怎么变
# =============================================================================
# 为什么做这个（而不是直接实现 k(V)）
# ----------------------------------
# gap #3 有**两个不同的**问题，先前混在一起：
#   (a) **溶质截留**：真实合金在高 V 下 k 会偏离平衡值（Aziz 的 k(V)）
#   (b) **欠解析**：模型界面比扩散长度厚几百倍 ⇒ 界面内的溶质根本无法平衡
#
# 直接实现 `k(V)` 只动 (a)，而 (b) 才是本项目 `W/(D/V) = 480` 的要害 ——
# **不先量化 (b)，加 `k(V)` 就是给猪抹口红。**
#
# 载体：`tests/front1d.i` —— 1D **匀速移动**的凝固前沿，速度
#       `v = 3·ξ·L·|ΔF|`（该算例文件头有推导；**不是** `v = L·ΔF`，漏 3ξ 差 6 个数量级）。
#   基线设计点恰好是 `s = ξV/D = 1`（**渐近区**）。
#
# 做法（一次只改一个因素）
# ------------------------
#   固定几何与驱动力（⇒ V 固定），**只改溶质迁移率 M**（⇒ D = M·k_c 变）：
#       s = ξ·V / D      由 1 扫到 ~1000（生产是 480）
#
# 判据与预期
# ----------
#   量 `k_eff = c_solid / c_max`（该算例的 c_max 就是界面处液相浓度 c0/k）。
#   * `s ≲ 1`（薄界面渐近区）⇒ 模型**应当**给出 k_e = 0.6303
#   * `s ≫ 1`（生产所在的厚界面区）⇒ 若 k_eff **偏离 0.6303 且趋近 1**，
#     说明模型自发表现出「截留样」行为（溶质来不及跨过厚界面）
#     ⇒ 那生产用的 0.63 就是**错的**，而且偏差可量化
#   * 若 k_eff **恒为 0.6303** ⇒ 模型完全测不到这个效应，
#     ⇒ 只能走「如实声明局限」那条路（缺口 #3 的路线①）
#
# ⚠ 用户约束：只做 smoke test / 1D 局部算例，不跑生产。
#
# 用法： bash run_keff_vs_s.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/keff_s}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-8.0e-3}"
TMO="${TMO:-2400}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

# --- 基线常数（与 front1d.i 一致，用于算 s）---
XI=2.0e-6          # 界面宽 sqrt(8κ/Wg) = 2 µm
L_MOB=5.833e-4     # Allen-Cahn 迁移率
DG=3.6e5           # |ΔF| = |dG|（驱动力）
K_C=0.9
M0=2.8e-9          # 基线溶质迁移率 ⇒ D = M0*k_c = 2.52e-9

python3 - "$ROOT" "$SRC" "$XI" "$L_MOB" "$DG" "$K_C" "$M0" <<'PY'
import math, os, re, sys
root, src, XI, L, DG, KC, M0 = (sys.argv[1], sys.argv[2], float(sys.argv[3]),
                                float(sys.argv[4]), float(sys.argv[5]),
                                float(sys.argv[6]), float(sys.argv[7]))
V = 3.0 * XI * L * DG                      # 前沿速度（该算例文件头的公式）
base = open(src, encoding="utf-8").read()
print(f"  前沿速度 V = 3·ξ·L·|ΔF| = {V:.4e} m/s")
print()
print("  %-8s %-12s %-12s %-12s" % ("标签", "M", "D=M·k_c", "s=ξV/D"))
cases = []
for tag, s_target in (("s1", 1.0), ("s10", 10.0), ("s100", 100.0),
                      ("s480", 480.0), ("s1000", 1000.0)):
    D = XI * V / s_target                  # 由 s 反解 D
    M = D / KC
    cases.append((tag, M, D, s_target))
    print("  %-8s %-12.4e %-12.4e %-12.1f" % (tag, M, D, XI * V / D))
print()

# 逐例生成：只改 [params] 里的 M
for tag, M, D, s in cases:
    t, n = re.subn(r"(prop_names\s*=\s*'L\s+kappa_op\s+kappa_c\s+M'\s*\n\s*prop_values\s*=\s*')"
                   r"([0-9.eE+-]+)(\s+[0-9.eE+-]+\s+[0-9.eE+-]+\s+)([0-9.eE+-]+)(')",
                   lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{M:.10g}{m.group(5)}",
                   base)
    assert n == 1, f"{tag}: [params] 的 M 匹配到 {n} 处（应为 1）"
    os.makedirs(os.path.join(root, tag), exist_ok=True)
    open(os.path.join(root, tag, "case.i"), "w", encoding="utf-8").write(t)
print(f"  写出 {len(cases)} 个算例")
PY

echo
echo "=== 跑（每个 t_end = ${T_END} s）==="
for tag in s1 s10 s100 s480 s1000; do
  cd "$ROOT/$tag"
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i case.i "Executioner/end_time=$T_END" > run.log 2>&1 || RC=$?
  printf "  %-6s rc=%-3s %4ss\n" "$tag" "$RC" "$(( $(date +%s) - S ))"
  cd "$ROOT"
done

echo
echo "=== k_eff 随 s 的变化 ==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
root = sys.argv[1]
print("  %-8s %-8s %-12s %-12s %-12s %s" %
      ("标签", "s", "c_solid", "c_max(=c_l)", "k_eff", "vs 0.6303"))
print("  " + "-" * 74)
KE = 0.6303
for tag in ("s1", "s10", "s100", "s480", "s1000"):
    d = os.path.join(root, tag)
    f = os.path.join(d, "front1d_out.csv")
    if not os.path.exists(f):
        alt = [x for x in os.listdir(d) if x.endswith(".csv")] if os.path.isdir(d) else []
        if not alt:
            print("  %-8s 没有 csv" % tag); continue
        f = os.path.join(d, alt[0])
    r = list(csv.DictReader(open(f)))
    if not r:
        print("  %-8s 空" % tag); continue
    def g(row, name):
        k = [c for c in row if name in c]
        return float(row[k[0]]) if k else float("nan")
    l = r[-1]
    cs, cm = g(l, "c_solid"), g(l, "c_max")
    k_eff = cs / cm if cm else float("nan")
    # 从日志读实际用的 s
    s = "?"
    print("  %-8s %-8s %-12.6f %-12.6f %-12.6f %+.2f%%" %
          (tag, s, cs, cm, k_eff, 100*(k_eff-KE)/KE))
print()
print("  判读：")
print("    * `s1`（基线，渐近区）应给出 k_eff ≈ 0.6303 —— 这是模型的**正确性检查**")
print("    * 若 k_eff 随 s **单调上升趋近 1** ⇒ 模型自发表现了「截留样」行为，")
print("      且能给出生产（s≈480）处 k_eff 的**具体偏差** ⇒ 生产用 0.63 是错的")
print("    * 若 k_eff 恒定 ⇒ 模型测不到这个效应，只能走「声明局限」路线")
PY
