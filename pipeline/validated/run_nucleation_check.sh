#!/bin/bash
# =============================================================================
# 缺口 #2 第一步：**形核 + GrainTracker + 多序参量**能不能共存（最小验证）
# =============================================================================
# ## 为什么先做最小验证
#
# 提高 `op_num` 是**链级改动**，不是参数调整：
#   * `frozen/splice_aniso_nonad.py:102` 里 `n_op = 8` 是**硬编码**
#   * 生产源 `stage1_meltpool_c.i` 的 [Variables]/[Kernels]/[AuxKernels] 列到 gr7
#   * `make_jacfix.py` / `run_nonad_prod.sh` 的断言都绑在「恰好 8 个」
# 而 `GrainTracker` 的 `reserve_op` 是**永久槽位**（B0a 实测）
# ⇒ `op_num ≥ 基体晶粒数 + 期望形核次数`。
#
# ⇒ 在动那条链之前，先证明**机制本身**能跑：
#   4 个基体晶粒占 op0-3，`reserve_op = 4` 把 **gr4..gr7 留给形核**。
#
# ## 判据
#
#   1. **不崩**、`total_solute` 漂移 ≤ 1e-8
#   2. ⭐ **`grain_tracker`（晶粒数）必须增长** —— 这是「形核真的发生了」的唯一证据。
#      ⚠ 只看「跑完了没报错」不算 —— 老式 Adaptivity 那个假象的同类教训。
#   3. 形核前后守恒不破
#
# ⚠ 用户约束：只做 smoke test（缩小网格 + 短时间）。
#
# 用法： bash run_nucleation_check.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/nucchk}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
NX="${NX:-54}"; NY="${NY:-19}"
END="${END:-2.0e-6}"
TMO="${TMO:-2400}"
SEED="${SEED:-/root/work/jitcache_seed}"
BASE="${BASE:-/root/work/prod_merged}"

rm -rf "$ROOT"; mkdir -p "$ROOT/run"; cd "$ROOT/run"
if [ -d "$SEED" ]; then
  mkdir -p .jitcache; cp -rn "$SEED"/. .jitcache/ 2>/dev/null || true
fi

cp "$REPO/stage1_meltpool_c.i" case_nuc.i
for f in aniso_block.i; do [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true; done

# 4 个种子的基体（放在缩小后的域内）—— 只占 op0..op3，把 op4..op7 留给形核
cat > columnar_seeds.csv <<'CSV'
x,y
-2.1e-4,7.5e-5
-1.4e-4,7.5e-5
-0.7e-4,7.5e-5
0.0e+0,7.5e-5
CSV

python3 - "$ROOT" <<'PY'
import os, re, sys
run = os.path.join(sys.argv[1], "run")
p = os.path.join(run, "case_nuc.i")
t = open(p, encoding="utf-8").read()

# --- ① GrainTracker 保留最后 4 个槽位给形核 ---
t2, n = re.subn(r"(\[grain_tracker\]\n\s*type = GrainTracker\n)",
                r"\1    # 【形核】保留最后 4 个序参量（gr4..gr7）—— 它们**不参与 remap**，\n"
                r"    # 是留给形核事件的永久槽位（B0a 实测 reserve_op 是永久的）。\n"
                r"    reserve_op = 4\n", t)
assert n == 1, f"grain_tracker 匹配 {n} 处"
t = t2

# --- ② 形核概率（**异质**形核的 CNT 形式）---
prob = """  # =====================================================================
  # 【形核概率】**异质**形核的经典理论（CNT）
  # =====================================================================
  #     P(T) = A · exp( − f(θ)·16πγ³ / (3·kb·T·ΔG_v²) )      T < Tm
  #     ΔG_v = ΔH_f·(Tm − T)/Tm        （体积自由能差，J/m³）
  #     f(θ) = (2 + cosθ)(1 − cosθ)²/4 （异质形核的几何因子，0<f<1）
  #
  # ⚠ **为什么必须用「异质」而不是均匀形核**（本轮手算的结论）：
  #   均匀形核在 LPBF 的过冷度下**根本不可能发生**：
  #       ΔT = 100 K  ⇒ ΔG*/kT ≈ 1150 ⇒ exp(−1150) = 0
  #       要 ΔG*/kT ≈ 50 需要 ΔT ≈ 490 K —— 熔池只在 Tm 附近，达不到。
  #   ⇒ 真实的等轴晶来自**异质形核**（氧化夹杂 / 孕育剂）或枝晶破碎。
  #   异质形核把 ΔG* 乘上 f(θ)：θ=20° 时 f = 0.00267 ⇒
  #       ΔT =  50 K ⇒ ΔG*/kT = 12.5  ⇒ exp(−12.5) = 3.7e-6
  #       ΔT = 100 K ⇒ ΔG*/kT =  3.13 ⇒ exp(−3.13) = 0.044
  #   ⇒ 50~100 K 过冷度下就有可观速率 —— 正对应熔池**顶部**的等轴晶区。
  #
  # ⚠⚠ **参数来源必须分清**（论文里要照这个写）：
  #   | 参数 | 值 | 来源 |
  #   |---|---|---|
  #   | Tm   | 1923 K      | **文献**（Ti64 液相线） |
  #   | ΔH_f | 1.28e9 J/m³ | **文献**（2.9e5 J/kg × 4430 kg/m³） |
  #   | γ    | 0.2 J/m²    | **文献**（Ti64 固液界面能，文献区间 0.15~0.3） |
  #   | f(θ) | 0.00267     | ⚠ **指派值**（θ=20°）—— **没有 Ti64 孕育剂的润湿角实测数据** |
  #   | A    | 1e6 /s      | ⚠ **指派值** —— 它决定形核**数量**，需按目标晶粒密度反标 |
  #   ⇒ 前三个是文献值，**后两个是标定参数**，不是材料常数。
  #
  # ⚠ 用 3.14159… 的字面值而不是 `pi`：`pi` 只在 `ParsedFunction` 里保证可用
  #   （见 AGENTS.md 的 MOOSE 坑清单）。
  [nuc_probability]
    type = ParsedMaterial
    property_name = P
    coupled_variables = 'T'
    constant_names = 'Tm dHf gamma kb f_theta A'
    constant_expressions = '1923 1.28e9 0.2 1.380649e-23 0.002673 1.0e6'
    expression = 'if(T < Tm, A*exp(-f_theta*16*3.14159265358979*gamma^3/(3*kb*T*(dHf*(Tm-T)/Tm)^2)), 0)'
  []
  # 【形核自由能】在核位置把目标序参量「逼」到 op_values，持续 hold_time
  [nucleation]
    type = DiscreteNucleation
    property_name = Fn
    op_names = 'gr4 gr5 gr6 gr7'
    op_values = '1 1 1 1'
    penalty = 5
    penalty_mode = MIN
    map = nuc_map
  []
"""
m = re.search(r"^\[Materials\]\n", t, re.M)
assert m, "找不到 [Materials]"
t = t[:m.end()] + prob + t[m.end():]

# --- ③ UserObjects：inserter + map ---
uos = """  # 【形核插入器】每个时间步末把新形核事件加进核列表
  [nuc_inserter]
    type = DiscreteNucleationInserter
    hold_time = 1e-5
    probability = P
    radius = 1.0e-5
  []
  # 【形核映射】把形核点变成有半径的有限面积对象
  [nuc_map]
    type = DiscreteNucleationMap
    inserter = nuc_inserter
  []
"""
m = re.search(r"^\[UserObjects\]\n", t, re.M)
assert m, "找不到 [UserObjects]"
t = t[:m.end()] + uos + t[m.end():]

# --- ④ 把 Fn 接进 η 方程：给 4 个被保留的序参量各加一个 AllenCahn(Fn) ---
ker = ""
for i in range(4, 8):
    others = " ".join(f"gr{j}" for j in range(8) if j != i)
    ker += f"""  [gr{i}_nuc]
    type = AllenCahn
    variable = gr{i}
    f_name = Fn
    mob_name = L
    coupled_variables = '{others}'
  []
"""
m = re.search(r"^\[Kernels\]\n", t, re.M)
assert m, "找不到 [Kernels]"
t = t[:m.end()] + ker + t[m.end():]

open(p, "w", encoding="utf-8", newline="").write(t)
print("  已加：reserve_op=4、形核概率 P、DiscreteNucleation、inserter/map、4 个 AllenCahn(Fn)")
PY

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" "Executioner/end_time=$END" Outputs/exodus=false)

echo
echo "=== 跑（网格 ${NX}x${NY}，end_time=${END} s）==="
S=$(date +%s); RC=0
timeout "$TMO" "$MOOSE" -i case_nuc.i "${COMMON[@]}" Outputs/file_base=out_nuc \
    > run_nuc.log 2>&1 || RC=$?
printf "  rc=%-4s %4ss\n" "$RC" "$(( $(date +%s) - S ))"

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
run = os.path.join(sys.argv[1], "run")
log = os.path.join(run, "run_nuc.log")
f = os.path.join(run, "out_nuc.csv")
if os.path.exists(log):
    x = open(log, encoding="utf-8", errors="replace").read()
    for pat, msg in (("Segmentation", "❌ 段错误"), ("*** ERROR ***", "❌ 有 ERROR")):
        if pat in x:
            print("  " + msg)
            for l in x.splitlines():
                if pat in l:
                    print("    " + l.strip()[:110]); break
if not os.path.exists(f):
    print("  没有 csv 输出"); sys.exit(0)
r = list(csv.DictReader(open(f)))
if not r:
    print("  空"); sys.exit(0)
def col(n):
    k = [c for c in r[0] if n in c]
    return k[0] if k else None
kg, ks = col("grain_tracker"), col("total_solute")
print("  行数 = %d，末态 t = %s" % (len(r), r[-1].get("time")))
if kg:
    g = [x[kg] for x in r]
    print("  grain_tracker（晶粒数）序列：", g)
    try:
        g0, g1 = float(g[0]), float(max(g, key=lambda v: float(v)))
        print("  ⇒ %s" % ("⭐ **晶粒数增长了 —— 形核确实发生了**"
                          if g1 > g0 else "❌ 晶粒数没变 —— 形核没发生，要查"))
    except ValueError:
        pass
if ks:
    try:
        v0, v1 = float(r[0][ks]), float(r[-1][ks])
        print("  total_solute 漂移 = %.2e（判据 1e-8）" % (abs(v1-v0)/abs(v0)))
    except (TypeError, ValueError):
        pass
PY
