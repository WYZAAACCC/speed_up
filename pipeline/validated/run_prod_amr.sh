#!/bin/bash
# =============================================================================
# 生产 AMR 方案：验证「用 S=Ση² 作指示量 + max_h_level=1」能不能跑
# =============================================================================
# ## 为什么用 S = Ση² 当指示量（而不是 gr0）
#
# 生产输入的 AuxVariable 只有 `T`（节点）、`unique_grains`/`liquid_flag`（**单元常量**）。
# `GradientJumpIndicator` 对**单元常量**变量的梯度恒为 0 ⇒ 那两个用不了；
# `T` 的梯度最大处在**熔池内部**，不是界面 ⇒ 也不合适。
#
# `S = Ση²` 则同时捕捉**两类界面**：
#   * 固固晶界：S 从 1（晶粒内）掉到 0.5（晶界中点）
#   * 固液界面：S 从 1 到 0
# ⇒ 梯度跳变最大处正好是界面 ✓ 而我们要加密的正是界面。
#
# ⚠ 必须建成**节点型**（LAGRANGE）—— 单元常量没有单元内梯度。
#
# ## 为什么 max_h_level = 1
#
# Q10 裁决（见 VALIDATION_STATUS.md §2.2）：判据是 **d/dx ≥ 4**，
# 其中 `d = sqrt(2κ/μ0) = 2.00 µm` 是平衡剖面的**实际宽度**。
# 生产基础网格 `dx = 1 µm` ⇒ `d/dx = 2` ❌（T8b 实测 ε 偏 +6.85%）。
# **`max_h_level = 1` 把界面处加密到 `dx = 0.5 µm` ⇒ `d/dx = 4` ✅**
# —— 这正是 T8b 实测达标的那一档（+1.61%）。**不需要 level 2。**
#
# ## 判据
#   1. 不崩、`total_solute` 漂移 ≤ 1e-8
#   2. **`n_elem` 必须变**（老式 Adaptivity 写法会「跑完不报错但一个单元都没动」）
#   3. 观测量与 uniform 差异 ≤ 5%
#   4. 代价（墙钟、单元数）—— 这决定它能不能上笔记本
#
# ⚠ 用户约束：只做 smoke test（缩小网格 + 短时间），不跑全尺寸。
#
# 用法： bash run_prod_amr.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BASE="${BASE:-/root/work/prod_merged}"
SRCI="${SRCI:-N.i}"
ROOT="${ROOT:-/root/work/prodamr}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
NX="${NX:-54}"; NY="${NY:-19}"
END="${END:-2.0e-6}"
TMO="${TMO:-2400}"
SEED="${SEED:-/root/work/jitcache_seed}"

[ -f "$BASE/$SRCI" ] || { echo "错误：找不到 $BASE/$SRCI" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT/run"; cd "$ROOT/run"
# ⚠ 种子复制必须**幂等**：并发跑两次时 `cp -r "$SEED" .jitcache` 会因为
#   目标已存在而报 "cannot create directory '.jitcache': File exists" 并让整个
#   脚本 abort（`set -e`）。实测踩过。
if [ -d "$SEED" ]; then
  mkdir -p .jitcache
  cp -rn "$SEED"/. .jitcache/ 2>/dev/null || true
  echo "  已预置 JIT 缓存（$(ls .jitcache | wc -l) 项）"
fi
cp "$BASE/$SRCI" case_uniform.i
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true
done

python3 - "$ROOT" <<'PY'
import os, re, sys
run = os.path.join(sys.argv[1], "run")
t = open(os.path.join(run, "case_uniform.i"), encoding="utf-8").read()

assert "elementid" not in t, "生产输入里有 elementid —— 先看 VALIDATION_STATUS §1.6"

# --- ① 加节点型 AuxVariable S_eta2 ---
m = re.search(r"^\[AuxVariables\]\n", t, re.M)
assert m, "找不到 [AuxVariables]"
t = t[:m.end()] + """  # 【AMR】固相指示 S = Ση² —— 晶粒内 1、固固晶界 0.5、液相 0。
  # 建**节点型**：单元常量没有单元内梯度，GradientJumpIndicator 会恒为 0。
  [S_eta2_aux]
    order = FIRST
    family = LAGRANGE
  []
""" + t[m.end():]

# --- ② 加对应的 AuxKernel ---
vars8 = " ".join(f"gr{i}" for i in range(8))
expr = "+".join(f"gr{i}^2" for i in range(8))
m = re.search(r"^\[AuxKernels\]\n", t, re.M)
assert m, "找不到 [AuxKernels]"
t = t[:m.end()] + f"""  [S_eta2_k]
    type = ParsedAux
    variable = S_eta2_aux
    coupled_variables = '{vars8}'
    expression = '{expr}'
  []
""" + t[m.end():]

# --- ③ 加 [Adaptivity]，max_h_level 可配 ---
def adapt(level):
    return ("[Adaptivity]\n"
            "  marker = marker\n"
            "  interval = 2\n"
            f"  max_h_level = {level}\n"
            "  [Indicators]\n"
            "    [jump]\n"
            "      type = GradientJumpIndicator\n"
            "      variable = S_eta2_aux\n"
            "    []\n"
            "  []\n"
            "  [Markers]\n"
            "    [marker]\n"
            "      type = ErrorFractionMarker\n"
            "      indicator = jump\n"
            "      refine = 0.5\n"
            "      coarsen = 0.0\n"
            "    []\n"
            "  []\n"
            "[]\n\n")

i = t.index("[Outputs]")
for tag, lv in (("amr1", 1), ("amr2", 2)):
    open(os.path.join(run, f"case_{tag}.i"), "w", encoding="utf-8").write(
        t[:i] + adapt(lv) + t[i:])
print("  写出 case_uniform.i / case_amr1.i（max_h_level=1）/ case_amr2.i（=2）")
print("  指示量 = GradientJumpIndicator(S_eta2_aux)，节点型")
PY

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" "Executioner/end_time=$END" Outputs/exodus=false)

echo
echo "=== 三档对照（基础网格 ${NX}x${NY}，end_time=${END} s）==="
for d in uniform amr1 amr2; do
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i "case_$d.i" "${COMMON[@]}" \
      "Outputs/file_base=out_$d" > "run_$d.log" 2>&1 || RC=$?
  printf "  %-8s rc=%-4s %4ss\n" "$d" "$RC" "$(( $(date +%s) - S ))"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
run = os.path.join(sys.argv[1], "run")
hdr = "  %-6s %-14s %-16s %-16s %-12s %s"
print(hdr % ("档", "n_elem 首→末", "AMR", "total_solute 漂移", "liquid_frac", "状态"))
print("  " + "-" * 78)
base = {}
for d in ("uniform", "amr1", "amr2"):
    log = os.path.join(run, f"run_{d}.log")
    f = os.path.join(run, f"out_{d}.csv")
    bad = ""
    if os.path.exists(log):
        x = open(log, encoding="utf-8", errors="replace").read()
        if "Segmentation" in x: bad = "段错误"
        elif "*** ERROR ***" in x: bad = "ERROR"
    if not os.path.exists(f):
        print(hdr % (d, "—", "—", "—", "—", bad or "无输出")); continue
    r = list(csv.DictReader(open(f)))
    if not r:
        print(hdr % (d, "空", "", "", "", bad)); continue
    def col(n):
        k = [c for c in r[0] if n in c]
        return k[0] if k else None
    ke, ks, kl = col("n_elem"), col("total_solute"), col("liquid_frac")
    i0 = 1 if len(r) > 1 else 0
    e0, e1 = (r[i0][ke], r[-1][ke]) if ke else ("?", "?")
    amr = ("**已生效**" if ke and e0 != e1 else "未生效") if ke else "?"
    try:
        v0, v1 = float(r[0][ks]), float(r[-1][ks])
        dr = f"{abs(v1-v0)/abs(v0):.2e}" if v0 else "0"
    except (TypeError, ValueError):
        dr = "?"
    lf = r[-1][kl] if kl else "?"
    print(hdr % (d, f"{e0}→{e1}", amr, dr, lf, bad or "ok"))
    if kl:
        base[d] = (r, lf)
print()
if "uniform" in base:
    lfu = float(base["uniform"][1])
    for d in ("amr1", "amr2"):
        if d in base:
            v = float(base[d][1])
            print("  %s 的 liquid_frac 与 uniform 相差 %.3f%%（判据 5%%）" %
                  (d, 100 * abs(v - lfu) / abs(lfu)))
PY
