#!/bin/bash
# =============================================================================
# 缺口 #3（溶质截留）的**真正判决性实验**：只改 kappa_c 这一个参数
# =============================================================================
# ## 为什么推翻之前的所有结论
#
# 之前所有「溶质截留」测量（run_keff_vs_s / run_keff_convergence /
# run_antitrap_test / run_antitrap_vs_s）都是跑 `tests/front1d.i`，
# 而它第 159 行的 `kappa_c = 1.125e-11` —— **生产在 2026-09-18 就已经把它
# 改成 1e-14 了**（stage1_meltpool_c.i 第 542-562 行），理由写得很清楚：
#     c 的界面宽 w_c = sqrt(kappa_c/k_c) 必须 **远小于** η 的界面宽
# 1D 测试算例漏改了。**所以"模型截留 +39%"是在一个已知坏掉的参数下测的。**
#
# ## 解析：模型里到底谁决定 k_eff
#
# 模型（SplitCHParsed，c 是混合成分）的稳态移动前沿，CH 方程积分一次：
#     −V(c−c0) = M·(f_cc·∂c/∂z − κ_c·∂³c/∂z³)
# 两端各积分一次，用固/液远场 c=c0（稳态质量守恒）得**精确关系**：
#
#     ∫(c−c0)dz = 2·M·A·c0 / V          ← 与 kappa_c **无关**
#
# 于是（c_max 是界面处液相峰值）
#     c_max − c0 = 2MAc0/(V·L_eff),     L_eff ≡ ∫(c−c0)dz/(c_max−c0)
#     k_eff = c0/c_max = 1/(1 + 2MA/(V·L_eff))
#
# 而 L_eff 由剖面宽度定。液相的 4 阶常微分方程（令 y = λ/ℓ_c, P = ℓ_c/δ_c）：
#     P·y³ − y² + 1 = 0 ,     ℓ_c = sqrt(κ_c/k_c) ,  δ_c = D/V
#   * P < 0.385  有实根 ⇒ 衰减指数，λ = δ_c·(1 − P²)   ⇒ **L_eff ≈ δ_c** ✓
#   * P > 0.385  复根   ⇒ 阻尼振荡，衰减长 1.6·ℓ_c 起 ⇒ **L_eff ≫ δ_c** ✗
#
# **目标 k_eff = k_e = 0.6303 ⇔ L_eff = δ_c ⇔ P ≪ 1。**
#
# 验算本算例（s=1：ξ=δ_c=2 µm, D=M·k_c=2.52e-9, V=1.26e-3）：
#     ℓ_c = sqrt(1.125e-11/0.9) = 3.54 µm > δ_c = 2 µm ⇒ P = 1.77 > 0.385 ✗
#     ⇒ 振荡 ⇒ L_eff 被撑到 ~4.3 δ_c ⇒ k_eff = 0.88（实测 0.880 ✓）
#     κ_c = 1e-14 ⇒ ℓ_c = 0.105 µm ⇒ P = 0.053 ⇒ L_eff ≈ δ_c ⇒ k_eff = 0.6303
#
# 目标 κ_c：P ≤ 0.2 ⇒ ℓ_c ≤ 0.4 µm ⇒ κ_c ≤ k_c·(0.4e-6)² = 1.4e-13
#
# ## 判据
#
#   ① **三个独立量必须同时对上**（这是本实验的强度所在）：
#        · k_eff → 0.6303（±2%）
#        · ∫(c−c0)dx = 2MAc0/V = 4.224e-8（与 κ_c 无关，验证"精确关系"成立）
#        · L_eff → δ_c = 2 µm
#   ② 守恒漂移 ≤ 1e-8
#   ③ 网格收敛：ℓ_c/dx ≥ 3（否则 κ_c 小到测的又是网格伪影，另一个坑）
#
# ⚠ 用户约束：只做 1D 局部算例，不跑生产。
#
# 用法： bash run_kc_vs_keff.sh
#   KC_LIST="1.125e-11 1e-12 1e-13 1e-14" NX=1280 bash run_kc_vs_keff.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/kc_keff}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-8.0e-3}"
TMO="${TMO:-2400}"
NX="${NX:-1280}"
KC_LIST="${KC_LIST:-1.125e-11 1e-12 1e-13 1e-14}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

python3 - "$ROOT" "$SRC" "$KC_LIST" <<'PY'
import os, re, sys
root, src, kclist = sys.argv[1], sys.argv[2], sys.argv[3].split()
base = open(src, encoding="utf-8").read()

# ① 注入线采样器，把整条 c(x) 剖面拿出来（算 L_eff 必需）
vpp = """[VectorPostprocessors]
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
assert "[VectorPostprocessors]" not in base
base = base.rstrip() + "\n\n" + vpp

for kc in kclist:
    # prop_values = 'L kappa_op kappa_c M'  -> 换掉第 3 个数
    t, n = re.subn(
        r"(prop_values\s*=\s*')([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(')",
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}"
                  f"{kc}{m.group(7)}{m.group(8)}{m.group(9)}", base)
    assert n == 1, f"kappa_c={kc}: prop_values 匹配 {n} 处"
    d = os.path.join(root, "kc_" + kc)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(t)
print(f"  写出 {len(kclist)} 个算例（只差 kappa_c）")
PY

echo
echo "=== 跑（nx=$NX，end_time=$T_END s，V=1.26e-3 m/s，s=1）==="
for KC in $KC_LIST; do
  cd "$ROOT/kc_$KC"
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i case.i "Mesh/nx=$NX" "Executioner/end_time=$T_END" \
      "Outputs/exo/enable=false" > run.log 2>&1 || RC=$?
  printf "  kappa_c=%-10s rc=%-4s %4ss\n" "$KC" "$RC" "$(( $(date +%s) - S ))"
  cd "$ROOT"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" "$KC_LIST" "$NX" <<'PY'
import csv, math, os, sys
root, kclist, NX = sys.argv[1], sys.argv[2].split(), int(sys.argv[3])

# --- 算例常数（与 front1d.i 头部一致）---
XI   = 2.0e-6      # η 界面宽 = 2 µm
LMOB = 5.833e-4
DG   = 3.6e5
KC   = 0.9         # k_c
A    = 0.264       # A_part
C0   = 0.036
M    = 2.8e-9
V    = 3.0 * XI * LMOB * DG          # 1.26e-3 m/s
D    = M * KC                        # 2.52e-9 m²/s
DC   = D / V                         # δ_c = 2 µm
KE   = 1.0 / (1.0 + 2*A/KC)          # 0.6303
TOT  = 2*M*A*C0/V                    # 精确预测的 ∫(c−c0)dx

print(f"  V = {V:.4e} m/s   D = {D:.4e} m²/s   δ_c = D/V = {DC:.4e} m")
print(f"  平衡分配 k_e = 1/(1+2A/k_c) = {KE:.6f}")
print(f"  精确预测 ∫(c−c0)dx = 2MAc0/V = {TOT:.6e}  （与 kappa_c 无关）")
print()
print("  %-11s %-6s %-7s %-11s %-10s %-12s %-11s %s" %
      ("kappa_c", "ℓ_c[µm]", "P", "k_eff", "vs k_e", "∫(c−c0)dx", "L_eff[µm]", "L_eff/δ_c"))
print("  " + "-" * 96)

rows = []
for kc in kclist:
    kcf = float(kc)
    lc = math.sqrt(kcf / KC)
    P = lc / DC
    d = os.path.join(root, "kc_" + kc)
    f = os.path.join(d, "prof_prof.csv")
    if not os.path.exists(f):
        f2 = [x for x in os.listdir(d)] if os.path.isdir(d) else []
        cand = [x for x in f2 if x.endswith(".csv") and "prof" in x]
        f = os.path.join(d, cand[0]) if cand else None
    if not f or not os.path.exists(f):
        print("  %-11s %-6.3f %-7.3f  没有剖面输出" % (kc, lc*1e6, P)); continue
    r = list(csv.DictReader(open(f)))
    if not r:
        print("  %-11s 空" % kc); continue
    xs = [float(x["x"]) for x in r]
    cs = [float(x["c"]) for x in r]
    cmax = max(cs)
    # 梯形积分 ∫(c−c0)dx
    tot = 0.0
    for i in range(len(xs)-1):
        tot += 0.5*((cs[i]-C0)+(cs[i+1]-C0))*(xs[i+1]-xs[i])
    keff = C0 / cmax
    Leff = tot / (cmax - C0) if cmax > C0 else float("nan")
    rows.append((kc, lc, P, keff, tot, Leff))
    print("  %-11s %-6.3f %-7.3f %-11.6f %+-8.2f%% %-12.4e %-11.3f %.2f" %
          (kc, lc*1e6, P, keff, 100*(keff-KE)/KE, tot, Leff*1e6, Leff/DC))

print()
if len(rows) >= 2:
    print("  判读：")
    a, b = rows[0], rows[-1]
    print(f"    kappa_c {a[0]} → {b[0]}：k_eff {a[3]:.4f} → {b[3]:.4f}"
          f"（平衡值 {KE:.4f}）")
    dd = [abs(x[4]-TOT)/TOT for x in rows]
    print(f"    ∫(c−c0)dx 相对精确式 2MAc0/V 的最大偏差 = {max(dd)*100:.3f}%"
          f"  ⇒ {'精确关系成立 ✓' if max(dd) < 0.02 else '⚠ 关系不成立，需查'}")
    print(f"    L_eff/δ_c：{a[5]/DC:.2f} → {b[5]/DC:.2f}（目标 1.00）")
    if abs(b[3]-KE)/KE < 0.02:
        print("    ✅ **只改 kappa_c 就把 k_eff 拉回平衡值** ⇒ 缺口 #3 是参数漏改，不是物理缺陷")
    else:
        print("    ❌ k_eff 没回到平衡值 ⇒ 还有别的机制，继续查")
PY
