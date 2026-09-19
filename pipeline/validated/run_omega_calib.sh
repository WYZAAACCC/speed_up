#!/bin/bash
# =============================================================================
# Ω₀ 标定：把生产值从 −4.6e-9 改到 ≈−5e-11，用文献锚点验收
# =============================================================================
# 依据见 pipeline/GB_SEGREGATION_LITERATURE.md §0.3（理论公式 = Cahn 1962）。
#
# ## 为什么当前值错
#
#   Δc    = |Ω₀| / (w_GB · f_cc)
#   ∫h_gb dx = (4/3)·w_GB          ← 解析：h_gb = sech⁴u，∫sech⁴ = 4/3
#   ⇒ Γ_len = ∫(c−c_far)dx = (4/3)·|Ω₀| / f_cc      ← 与 w_GB 无关（重标定生效）
#
#   ⚠ **c 是摩尔分数 ⇒ Γ_len 的单位是【米】，不是 mol/m²。**
#     要得到物理的 Gibbs 过剩必须乘摩尔密度：
#         Γ_phys [at/nm²] = Γ_len [m] × ρ_mol × N_A / 1e18
#                         = Γ_len × 1.01e5 × 6.022e23 / 1e18
#                         = Γ_len × 6.082e10
#     （ρ_mol(β-Ti) = 1.01e5 mol/m³，由 Tan 2016 原文的 ρ(β)=61.0 at·nm⁻³ 换算）
#
#   实测 Γ_len = 4.79e-9（wGB=0.4 µm 的 seg−noseg）
#   ⇒ Γ_phys = 291 at·nm⁻²，而 Tan 的 V 锚点是 2.2~5.3 at·nm⁻²
#   ⇒ **大了 55~133 倍** ⇒ Ω₀ 应为约 −5e-11。
#
# ## 本脚本做什么
#
#   1. wGB 扫描 × {noseg, seg(旧 Ω₀), seg(新 Ω₀)}，**验证 1/wGB 重标定在新值下仍成立**
#   2. 把 Γ 换算成物理单位并与文献锚点对比
#   3. 报告富集比 s（注意：模型无法同时对上 s 与 Γ，见 §0.3.4）
#
# ⚠ 一次只改一个因素：这里只动 Ω₀ 的**数值**，形式、网格、时间步全不动。
#
# 用法： bash run_omega_calib.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/root/work/omega_calib}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
DX="${DX:-2.5e-8}"
LDOM="${LDOM:-1.2e-5}"
WGB_LIST="${WGB_LIST:-0.4e-6}"
T_END="${T_END:-30.0}"                 # 照抄已验证的 run_t11.sh（慢扩散过程别凭感觉设）
OMEGA_OLD="${OMEGA_OLD:--4.6e-9}"
OMEGA_NEW="${OMEGA_NEW:--5.0e-11}"
# ⚠ **第一版把这个设成默认的 `S`（Ση²），结果 `noseg` 对照档给出 222 at/nm²**
#   —— 基座本身就比文献锚点大 100 倍，而它**全部来自分配项**，与 Ω₀ 无关。
#   ⇒ 只改 Ω₀ 修不了 Γ 的量级。必须同时把分配项由 Ση² 换成 h_solid（T11 第二增量）。
F_PART="${F_PART:-h_solid}"

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

echo "Ω₀ 标定：dx=$DX m，域长=$LDOM m，T_END=$T_END s"
echo "  旧值 $OMEGA_OLD   新值 $OMEGA_NEW   分配项驱动 = $F_PART"
echo

for WGB in $WGB_LIST; do
  for TAG in noseg old new; do
    EXTRA=""
    [ "$TAG" = "old" ] && EXTRA="--f-seg $OMEGA_OLD"
    [ "$TAG" = "new" ] && EXTRA="--f-seg $OMEGA_NEW"
    D="$ROOT/${TAG}_${WGB}"; mkdir -p "$D"; cd "$D"
    # shellcheck disable=SC2086
    python3 "$HERE/make_1d_gb.py" --out gb.i --dx "$DX" --ldom "$LDOM" \
        --wgb "$WGB" --t-end "$T_END" --f-part "$F_PART" $EXTRA > gen.log 2>&1 \
      || { echo "  生成失败 $TAG $WGB"; tail -3 gen.log; cd "$ROOT"; continue; }
    timeout 1800 "$MOOSE" -i gb.i > run.log 2>&1 || true
    cd "$ROOT"
  done
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" "$F_PART" <<'PY'
import csv, os, re, sys
root = sys.argv[1]
F_PART = sys.argv[2]     # heredoc 用了引号定界符 ⇒ shell 变量不展开，必须从 argv 传

RHO_MOL = 1.01e5          # mol/m^3, 由 Tan 2016 的 rho(beta)=61.0 at/nm^3 换算
NA      = 6.02214076e23
TO_AT_NM2 = RHO_MOL * NA / 1e18      # = 6.082e10  [at/nm2 per m]

# Tan 2016 Table 2（923 K，α/β 相界面）的 V 锚点
TAN_V_LO, TAN_V_HI = 2.2, 5.3

res = {}
for d in sorted(os.listdir(root)):
    m = re.match(r"(noseg|old|new)_([\d.eE+-]+)$", d)
    if not m:
        continue
    f = os.path.join(root, d, "gb_out.csv")
    if not os.path.exists(f):
        continue
    rows = list(csv.DictReader(open(f)))
    if not rows:
        continue
    key = [k for k in rows[0] if "amma" in k or "GB" in k]
    if not key:
        print("  %s: 找不到 Γ 后处理列 %s" % (d, list(rows[0])[:8]))
        continue
    res[d] = float(rows[-1][key[0]])

def get(tag, wgb):
    return res.get(f"{tag}_{wgb}")

wbgs = sorted({d.split("_", 1)[1] for d in res})
print("  %-7s %-7s %-15s %-13s %-13s" %
      ("wGB(µm)", "档", "Γ_len (m)", "Γ (at/nm²)", "偏析项贡献"))
print("  " + "-" * 62)
for wgb in wbgs:
    wu = float(wgb) * 1e6
    base = get("noseg", wgb)
    for tag in ("noseg", "old", "new"):
        v = get(tag, wgb)
        if v is None:
            continue
        phys = v * TO_AT_NM2
        if tag == "noseg":
            note = "—（基座：分配项造成）"
        else:
            d = (v - base) * TO_AT_NM2 if base is not None else float("nan")
            note = f"{d:+.1f} at/nm²"
        print("  %-7.2f %-7s %-15.4e %-13.2f %s" % (wu, tag, v, phys, note))
    print()

print("  判读：")
print("    * `noseg` 是**基座** —— 只由分配项 `A_part·c²·f_part` 造成，与 Ω₀ 无关。")
print("      ⚠ 若 `--f-part S`（Ση²），这一档本身就有 ~222 at/nm²（比文献大 100 倍）。")
print("      ✅ 若 `--f-part h_solid`，固固晶界上分配驱动力处处相同 ⇒ 基座应接近 0。")
print(f"      （本轮的 f_part = {F_PART}）")
print("    * `old`/`new` 与 `noseg` 的差值 = **偏析项自己的贡献**，可直接对标 Tan 锚点。")
print("    * 两个 wGB 上 `noseg` 应接近相等、`new−noseg` 也应接近相等")
print("      ⇒ 1/wGB 重标定生效。")
PY
