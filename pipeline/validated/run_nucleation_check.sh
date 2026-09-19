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

# --- ② 形核概率（**成分过冷**驱动的异质形核）---
prob = """  # =====================================================================
  # 【形核概率】**成分过冷**驱动的异质形核（CNT）
  # =====================================================================
  #     f_s    = h_solid = min(1, 2Ση²)          （固相分数，模型已有的量）
  #     c_l    = c0·(1 − f_s)^(k−1)              （**Scheil**：液相富集）
  #     ΔT_CS  = |mL|·(c_l − c0)                 （**成分过冷**）
  #     ΔG_v   = ΔH_f·ΔT_CS/Tm                   （体积自由能差）
  #     P      = A·exp( − f(θ)·16πγ³/(3·kb·T·ΔG_v²) )
  #
  # ⚠⚠ **为什么必须用成分过冷，而不是热过冷**（本轮查清的关键）
  #
  # CET（柱状→等轴转变）的真实驱动力是**成分过冷**：柱状前沿排出的溶质
  # 在液相堆积，把当地液相线压低到实际温度以下，形成过冷区 →
  # **异质形核只发生在那个过冷区里**，也就是**最后凝固的液体**（熔池顶部）。
  #
  # ⚠ 而本模型的溶质场**堆不起来**（缺口 #3：动力学慢 10⁵ 倍，
  #   实测 t=2e-6 s 时 `c_max − c0 = 1.9e-05`，几乎为零）
  #   ⇒ **热过冷驱动是物理上错的**：它会让晶核在整个熔池里出现。
  #
  # ✅ **出路**：锐界面极限下成分过冷只取决于**固相分数**，不依赖溶质输运
  #   —— 用 **Scheil 公式**从 `f_s` 直接算 `c_l`。这样：
  #     * 晶核只出现在 `f_s` 大（最后凝固）的地方 = **熔池顶部** ✓ 真实物理
  #     * **不依赖那个不可靠的溶质场** ✓
  #
  #   k = 0.6303 < 1 ⇒ (k−1) = −0.37 < 0 ⇒ c_l 随 f_s 增长：
  #     f_s = 0.90 ⇒ c_l/c0 = 2.34 ⇒ ΔT_CS ≈ 24 K
  #     f_s = 0.99 ⇒ c_l/c0 = 5.50 ⇒ ΔT_CS ≈ 81 K
  #   ⇒ 正落在异质形核显著的区间（50~100 K ⇒ exp(−12.5) ~ exp(−3.13)）✓
  #
  # ⚠⚠ **参数来源必须分清**（论文里照这个写）：
  #   | 参数 | 值 | 来源 |
  #   |---|---|---|
  #   | Tm   | 1923 K      | **文献**（Ti64 液相线） |
  #   | ΔH_f | 1.28e9 J/m³ | **文献**（2.9e5 J/kg × 4430 kg/m³） |
  #   | γ    | 0.2 J/m²    | **文献**（Ti64 固液界面能，区间 0.15~0.3） |
  #   | k    | 0.6303      | **模型自洽**（由 A_part 定，T4 验证过） |
  #   | mL   | 600 K/摩尔分数 | ⚠ **指派值** —— Ti64 的 V 的液相线斜率，**本项目没有查到可引用的值** |
  #   | f(θ) | 0.00267     | ⚠ **指派值**（θ=20°）—— 没有 Ti64 孕育剂润湿角实测数据 |
  #   | A    | 1e6 /s      | ⚠ **指派值** —— 决定形核**数量**，需按目标晶粒密度反标 |
  #
  # ⚠ Scheil 的适用性：假设液相完全混合、固相无扩散 —— 对 AM 的快速凝固合理 ✓
  #
  # ⚠ 用 3.14159… 的字面值而不是 `pi`：`pi` 只在 `ParsedFunction` 里保证可用。
  [nuc_probability]
    type = ParsedMaterial
    property_name = P
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    constant_names = 'Tm dHf gamma kb f_theta A c0 k_eq mL'
    constant_expressions = '1923 1.28e9 0.2 1.380649e-23 0.002673 1.0e6 0.036 0.6303 600'
    expression = 'if(min(1, 2*(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2)) > 0.5, A*exp(-f_theta*16*3.14159265358979*gamma^3/(3*kb*1923*(dHf*mL*(c0*(1-min(1, 2*(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2)))^(k_eq-1)-c0)/Tm)^2)), 0)'
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
