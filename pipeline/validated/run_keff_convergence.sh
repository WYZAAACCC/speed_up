#!/bin/bash
# =============================================================================
# 缺口 #3 的**修正版**判决性实验：模型在哪个界面 Péclet 数之前还能**网格收敛**
# =============================================================================
# ## 为什么改掉了第一版
#
# 第一版（`run_keff_vs_s.sh`）固定 `nx=160`、扫 `s = ξV/D` 从 1 到 1000，
# 得到 k_eff = 0.880/0.954/0.813/0.769/0.756。**那个结果不能用**，两个原因：
#
#   1. **我的预期本来是错的**（这一点文档 T7 早就写明了）：
#      移动前沿处的 `k_eff = c_solid/c_max` **本来就不等于平衡值 0.6303** ——
#      T4 量的是静止界面的**平衡**分配系数，两者不是同一个量。
#      T7 实测 `k_eff ≈ 0.887`（nx=160），与本轮 `s=1` 的 0.880 一致 ✓。
#
#   2. **更要命的是网格**：`s` 越大，溶质边界层 `δ = D/V` 越薄。
#      `s = 1000` 时 `δ = ξ/1000 = 2 nm`，而 `dx = 250 nm` ⇒ **完全没解析**。
#      所以大 `s` 档测的是**网格伪影**，不是物理。
#
# ## 这一版问的是对的问题
#
#   **对每个 `s`，加密 `dx`，看 `k_eff` 收不收敛。**
#
#   * 收敛 ⇒ 该 `s` 下模型是可信的，`k_eff` 是物理量
#   * 不收敛 ⇒ 该 `s` 超出模型能力，只能用「声明局限」处置（缺口 #3 路线①）
#
# 做法沿用 T7 的 nx 扫描（只改 dx，不改物理），但**对多个 s 各做一次**。
#
# ⚠ 用户约束：只做 1D 局部算例，不跑生产。
#
# 用法： bash run_keff_convergence.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/keff_conv}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-8.0e-3}"
TMO="${TMO:-1800}"

XI=2.0e-6; L_MOB=5.833e-4; DG=3.6e5; K_C=0.9
# 可被环境变量覆盖，便于延到更大的 s（生产是 ~480）
# 格式："标签:s 标签:s …"
S_SPEC="${S_SPEC:-s1:1 s10:10 s100:100}"
NW_LIST="${NW_LIST:-160 320 640}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

python3 - "$ROOT" "$SRC" "$XI" "$L_MOB" "$DG" "$K_C" "$S_SPEC" "$NW_LIST" <<'PY'
import os, re, sys
root, src = sys.argv[1], sys.argv[2]
XI, L, DG, KC = (float(x) for x in sys.argv[3:7])
S_SPEC, NW_LIST = sys.argv[7], [int(x) for x in sys.argv[8].split()]
V = 3.0 * XI * L * DG
base = open(src, encoding="utf-8").read()
print(f"  前沿速度 V = {V:.4e} m/s")
print()
S_LIST = [(p.split(":")[0], float(p.split(":")[1])) for p in S_SPEC.split()]
print("  %-8s %-10s %-12s %-14s %-14s" % ("标签", "s", "D", "D/V (m)", "ξ/dx"))
print("  " + "-" * 64)
for tag, s in S_LIST:
    D = XI * V / s
    M = D / KC
    for nx in NW_LIST:
        t, n = re.subn(
            r"(prop_names\s*=\s*'L\s+kappa_op\s+kappa_c\s+M'\s*\n\s*prop_values\s*=\s*')"
            r"([0-9.eE+-]+)(\s+[0-9.eE+-]+\s+[0-9.eE+-]+\s+)([0-9.eE+-]+)(')",
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{M:.10g}{m.group(5)}", base)
        assert n == 1, f"{tag}: M 匹配 {n} 处"
        d = os.path.join(root, f"{tag}_nx{nx}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "case.i"), "w", encoding="utf-8").write(t)
    # ⚠ 分辨率指标是 **ξ/dx**（界面宽/网格），**不是** δ/dx（D/V 除以网格）！
    #   弥散模型里溶质剖面宽度由**界面宽 ξ** 决定，不是由 D/V。
    #   本轮先用 δ/dx 当指标，误判「s=100 网格受限」——实测它完全收敛。
    print("  %-8s %-10.0f %-12.4e %-14.4e %-14.1f" %
          (tag, s, D, D / V, XI / (4.0e-5 / NW_LIST[-1])))
print()
print(f"  写出 {len(S_LIST)*len(NW_LIST)} 个算例")
PY

echo
echo "=== 跑（每个 t_end = ${T_END} s）==="
for spec in $S_SPEC; do
  tag="${spec%%:*}"
  for nx in $NW_LIST; do
    cd "$ROOT/${tag}_nx${nx}"
    S=$(date +%s); RC=0
    timeout "$TMO" "$MOOSE" -i case.i Mesh/nx=$nx "Executioner/end_time=$T_END" \
        > run.log 2>&1 || RC=$?
    printf "  %-8s nx=%-5s rc=%-3s %3ss\n" "$tag" "$nx" "$RC" "$(( $(date +%s) - S ))"
    cd "$ROOT"
  done
done

echo
echo "=== k_eff 对 dx 的收敛性（判据：相邻档相对变化 < 1%）==="
python3 - "$ROOT" "$S_SPEC" "$NW_LIST" <<'PY'
import csv, os, sys
root = sys.argv[1]
S_LIST = [p.split(":")[0] for p in sys.argv[2].split()]
NW_LIST = [int(x) for x in sys.argv[3].split()]
print("  %-8s %-6s %-12s %-12s %-12s %s" %
      ("s", "nx", "dx(µm)", "c_solid", "k_eff", "相邻档变化"))
print("  " + "-" * 68)
for tag in S_LIST:
    prev = None
    for nx in NW_LIST:
        d = os.path.join(root, f"{tag}_nx{nx}")
        fs = [x for x in os.listdir(d) if x.endswith(".csv")] if os.path.isdir(d) else []
        if not fs:
            print("  %-8s %-6s 没有 csv" % (tag, nx)); continue
        r = list(csv.DictReader(open(os.path.join(d, fs[0]))))
        if not r:
            continue
        l = r[-1]
        def g(n):
            k = [c for c in l if n in c]
            return float(l[k[0]]) if k else float("nan")
        cs, cm = g("c_solid"), g("c_max")
        ke = cs / cm if cm else float("nan")
        dx = 4.0e-5 / nx
        chg = "" if prev is None else "%.3f%%" % (100 * abs(ke - prev) / prev)
        print("  %-8s %-6d %-12.4f %-12.6f %-12.6f %s" % (tag, nx, dx * 1e6, cs, ke, chg))
        prev = ke
    print()
print("  判读：")
print("    * 相邻档变化 **< 1%** ⇒ 该 `s` 下模型**网格收敛**，`k_eff` 可信")
print("    * 变化 **> 1% 且不随 nx 增大而变小** ⇒ 该 `s` 超出模型能力")
print("    * ⚠ 分辨率指标要用 **ξ/dx**（界面宽/网格），**不是** δ/dx ——")
print("      弥散模型里溶质剖面宽度由界面宽 ξ 决定，不是由 D/V。")
print("    * `k_eff ≠ 0.6303` 是**正常的**（移动前沿 vs 静止界面的平衡值，不是同一个量）")
PY
