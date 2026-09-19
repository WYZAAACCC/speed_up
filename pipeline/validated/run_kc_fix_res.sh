#!/bin/bash
# =============================================================================
# 缺口 #3 修复方案的**设计实验**：需要多少个网格解析溶质边界层？
# =============================================================================
# 承 run_kc_vs_keff.sh：确认 `kappa_c` 是根因后，这里固定生产值 `kappa_c = 1e-14`
# （ℓ_c = sqrt(κ_c/k_c) = 0.105 µm），扫**界面 Péclet 数** `s = ξV/D` 与网格。
#
# ## 判据（从精确关系推出来）
#
#     ∫(c−c0)dz = 2MAc0/V       （与 κ_c、与网格无关，精确）
#     k_eff = 1/(1 + 2MA/(V·L_eff))       目标 L_eff = δ_c = D/V
#
# 模型能给对 `k_eff` 的**充要条件**是 `L_eff = δ_c`，而 `L_eff` 只能是
# 「δ_c」或「网格」或「ℓ_c」三者里**最大**的那个（剖面不可能比它们更细）：
#
#     L_eff ≈ max(δ_c, C·ℓ_c, C·dx)
#
#   ⇒ **`δ_c` 必须 ≥ 若干个网格**，否则 `L_eff` 被网格卡住 ⇒ `k_eff → 1`（全截留）。
#
# 这一条对生产是决定性的：生产 `D_L = 2.52e-9`、`V_scan = 0.6 m/s`、`dx = 1 µm`
#   ⇒ `δ_c = D_L/V = 4.2 nm`，**比一个网格还小 238 倍** ⇒ 生产必然全截留。
#
# 本实验量的是：**几个网格 / δ_c 才够**（即 `δ_c/dx` 的阈值）。
#
# ## 矩阵
#
#   s = ξV/D ∈ {0.25, 0.5, 1, 2, 4}    （s 越大边界层越薄）
#   nx ∈ {40, 80, 160, 320}            （δ_c/dx = (ξ/s)/dx）
#
# ⚠ `s = 4` + `nx = 40` 恰好复现生产的 `δ_c/dx = 2`（ξ=2µm, dx=1µm）——
#   这是**生产分辨率的 1D 代理**。
#
# ⚠ 用户约束：只做 1D 局部算例，不跑生产。
#
# 用法： S_LIST="1 2 4" NW_LIST="40 80 160" bash run_kc_fix_res.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/kc_fix}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-1.0e-2}"
TMO="${TMO:-900}"
KC_FIX="${KC_FIX:-1e-14}"
S_LIST="${S_LIST:-0.25 0.5 1 2 4}"
NW_LIST="${NW_LIST:-40 80 160 320}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

python3 - "$ROOT" "$SRC" "$KC_FIX" "$S_LIST" "$NW_LIST" <<'PY'
import os, re, sys
root, src, kc, slist, nwlist = (sys.argv[1], sys.argv[2], sys.argv[3],
                               sys.argv[4].split(), sys.argv[5].split())
XI, L, DG, K_C, M0 = 2.0e-6, 5.833e-4, 3.6e5, 0.9, 2.8e-9
V = 3.0 * XI * L * DG
base = open(src, encoding="utf-8").read()

# 线采样器（拿整条剖面算 L_eff）
base = base.rstrip() + """

[VectorPostprocessors]
  [prof]
    type = LineValueSampler
    variable = 'c eta'
    start_point = '0 0 0'
    end_point = '4.0e-5 0 0'
    num_points = 4001
    sort_by = x
  []
[]
"""
for s in slist:
    sv = float(s)
    D = XI * V / sv                 # s = ξV/D  =>  D = ξV/s
    M = D / K_C
    t, n = re.subn(
        r"(prop_values\s*=\s*')([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(')",
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}"
                  f"{kc}{m.group(7)}{M:.10g}{m.group(9)}", base)
    assert n == 1, f"s={s}: prop_values 匹配 {n} 处"
    # 初始剖面用**该 s 的解析稳态**（否则前几 µm 全在瞬态里）
    # 只替换 exp(...) 那一小段，别去凑整个多行表达式（跨行正则极易失配）
    t2, n2 = re.subn(
        r"exp\(-1\.26e-3\*\(x-5\.0e-6\)/2\.52e-9\)",
        f"exp(-{V:.6e}*(x-5.0e-6)/{D:.6e})", t)
    assert n2 == 1, f"s={s}: IC 替换了 {n2} 处（应为 1）"
    t = t2
    # 大 s 时 elementid=155 会落在固相里，索性关掉这两个后处理
    t = t.replace("[c_far]\n    type = ElementalVariableValue",
                  "[c_far]\n    enable = false\n    type = ElementalVariableValue")
    for nx in nwlist:
        d = os.path.join(root, f"s{s}_n{nx}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(t)
print(f"  写出 {len(slist)*len(nwlist)} 个算例（κ_c={kc} 固定，V={V:.4e} m/s）")
PY

echo
echo "=== 跑 ==="
for S in $S_LIST; do
  for NX in $NW_LIST; do
    cd "$ROOT/s${S}_n${NX}"
    S0=$(date +%s); RC=0
    timeout "$TMO" "$MOOSE" -i case.i "Mesh/nx=$NX" "Executioner/end_time=$T_END" \
        "Outputs/exo/enable=false" > run.log 2>&1 || RC=$?
    printf "  s=%-5s nx=%-4s rc=%-4s %4ss\n" "$S" "$NX" "$RC" "$(( $(date +%s) - S0 ))"
    cd "$ROOT"
  done
done

echo
echo "=== 结果：k_eff 需要几个网格解析边界层 ==="
python3 - "$ROOT" "$KC_FIX" "$S_LIST" "$NW_LIST" <<'PY'
import csv, math, os, sys
root, kc, slist, nwlist = sys.argv[1], float(sys.argv[2]), sys.argv[3].split(), sys.argv[4].split()
XI, L, DG, K_C, A, C0 = 2.0e-6, 5.833e-4, 3.6e5, 0.9, 0.264, 0.036
V = 3.0*XI*L*DG
LC = math.sqrt(kc/K_C)
KE = 1.0/(1.0+2*A/K_C)
DOM = 4.0e-5

print(f"  κ_c = {kc}  →  ℓ_c = sqrt(κ_c/k_c) = {LC*1e6:.4f} µm")
print(f"  平衡分配 k_e = {KE:.6f}   V = {V:.4e} m/s")
print()
print("  %-6s %-9s %-9s %-9s %-11s %-10s %-11s" %
      ("s", "δ_c[µm]", "δ_c/dx", "ξ/dx", "k_eff", "vs k_e", "L_eff/δ_c"))
print("  " + "-" * 74)
for s in slist:
    sv = float(s); D = XI*V/sv; DC = D/V
    for nx in nwlist:
        dx = DOM/int(nx)
        d = os.path.join(root, f"s{s}_n{nx}")
        fs = [x for x in os.listdir(d) if "prof" in x and x.endswith(".csv")] if os.path.isdir(d) else []
        if not fs:
            continue
        r = list(csv.DictReader(open(os.path.join(d, fs[0]))))
        if not r:
            continue
        xs = [float(x["x"]) for x in r]; cs = [float(x["c"]) for x in r]
        cmax = max(cs)
        tot = sum(0.5*((cs[i]-C0)+(cs[i+1]-C0))*(xs[i+1]-xs[i]) for i in range(len(xs)-1))
        keff = C0/cmax
        Leff = tot/(cmax-C0) if cmax > C0 else float("nan")
        flag = ""
        if abs(keff-KE)/KE < 0.02: flag = " ✅"
        elif keff > KE + 0.05:     flag = " ← 被网格卡住"
        print("  %-6s %-9.4f %-9.2f %-9.2f %-11.6f %+-8.2f%% %-11.2f%s" %
              (s, DC*1e6, DC/dx, XI/dx, keff, 100*(keff-KE)/KE, Leff/DC, flag))
    print()
print("  读法：`δ_c/dx` 是横轴。`k_eff` 在 `δ_c/dx` 大到某个值时收敛到 k_e。")
print("  生产是 δ_c/dx = 4.2nm/1µm = 0.004 ⇒ 远在左边 ⇒ 必然 k_eff→1。")
PY
