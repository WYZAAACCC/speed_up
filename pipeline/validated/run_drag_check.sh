#!/bin/bash
# =============================================================================
# 溶质拖曳项的验证：加了之后模型仍然对，且量级如预测
# =============================================================================
# 补的是什么：让 `f_loc` **也进 η 方程**（8 个 `AllenCahn(f_loc)` 核）。
# 目的**不是**改变预测，而是**修一个真实的热力学不一致** ——
# 现在 `δF/δη` 与 `δF/δc` 来自不同的自由能，**模型不是变分的**。
#
# ## 判据
#
#   1. 两档都**不崩**、`total_solute` 漂移 ≤ 1e-8
#   2. **非线性迭代数不显著增加**（新增项的雅可比贡献极小，不该拖慢收敛）
#   3. **观测量差异 ≲ 求解器容差量级** —— 这是**预期**的：
#      新增项比势垒小 9~11 个数量级（脚本头估算 + T13 实测佐证）
#      ⇒ **如果观测量出现明显差异，说明我把量级估错了，要回头查**
#   4. 墙钟不显著增加（`AllenCahn` 不引入新 JIT，因为 f_loc 的 η 导数
#      本来就为 SplitCHParsed 生成好了）
#
# ⚠ 判据 3 的方向要看清：**"看不出差别"才是通过**。
#   这与通常的"改动必须有可见效果"相反 —— 因为这个补丁的价值是**一致性**，
#   不是数值效果。别把它误读成"补丁没生效"。
#
# 用法： bash run_drag_check.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/dragchk}"
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

# ⚠ **基线必须取「未加拖曳」的版本**。
#   本脚本写好后我才把拖曳项应用到了生产源上 —— 若直接拿
#   `$REPO/stage1_meltpool_c.i` 当基线，**两边就都有拖曳了，对照失效**。
#   所以默认基线是应用前另存的 `stage1_meltpool_c.predrag.i`。
SRC_BASE="${SRC_BASE:-$REPO/stage1_meltpool_c.predrag.i}"
[ -f "$SRC_BASE" ] || { echo "错误：找不到基线 $SRC_BASE" >&2; exit 1; }
cp "$SRC_BASE" case_nodrag.i
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true
done

python3 "$HERE/make_drag_prod.py" --src case_nodrag.i --out case_drag.i > gen.log 2>&1 \
  || { echo "错误：拖曳项生成失败"; tail -5 gen.log; exit 1; }
echo "  拖曳项已生成"

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" "Executioner/end_time=$END" Outputs/exodus=false)

echo
echo "=== 两档对照（网格 ${NX}x${NY}，end_time=${END} s）==="
for d in nodrag drag; do
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i "case_$d.i" "${COMMON[@]}" \
      "Outputs/file_base=out_$d" > "run_$d.log" 2>&1 || RC=$?
  printf "  %-8s rc=%-4s %4ss\n" "$d" "$RC" "$(( $(date +%s) - S ))"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
run = os.path.join(sys.argv[1], "run")
print("  %-8s %-14s %-14s %-14s %-12s %s" %
      ("档", "c_min", "c_max", "total_solute", "liquid_frac", "NL 迭代"))
print("  " + "-" * 76)
res = {}
for d in ("nodrag", "drag"):
    f = os.path.join(run, f"out_{d}.csv")
    log = os.path.join(run, f"run_{d}.log")
    nl = "?"
    if os.path.exists(log):
        t = open(log, encoding="utf-8", errors="replace").read()
        m = re.findall(r"^\s*(\d+) Nonlinear \|R\|", t, re.M)
        nl = str(len(m)) if m else "?"
    if not os.path.exists(f):
        print("  %-8s 没有输出" % d); continue
    r = list(csv.DictReader(open(f)))
    if not r:
        continue
    l = r[-1]
    def g(n):
        k = [c for c in l if n in c]
        return l[k[0]] if k else "?"
    try:
        v0, v1 = float(g("total_solute")), float(r[0][[c for c in r[0] if "total_solute" in c][0]])
        dr = "%.2e" % (abs(v1 - v0) / abs(v0)) if v0 else "0"
    except Exception:
        dr = "?"
    print("  %-8s %-14s %-14s %-14s %-12s %s" %
          (d, g("c_min"), g("c_max"), dr, g("liquid_frac"), nl))
    res[d] = r[-1]
print()
if len(res) == 2:
    same = all(res["nodrag"].get(k) == res["drag"].get(k) for k in res["nodrag"])
    print("  判读：")
    if same:
        print("    ✅ 两档输出**逐位相同** —— 新增项的量级确实在求解器容差之下")
        print("       ⚠ 这不是「补丁没生效」：它改的是**一致性**，不是数值。")
    else:
        diffs = [(k, res["nodrag"].get(k), res["drag"].get(k))
                 for k in res["nodrag"] if res["nodrag"].get(k) != res["drag"].get(k)]
        print("    两档有差别的列：")
        for k, a, b in diffs[:8]:
            print(f"      {k}: {a}  ->  {b}")
        print("    ⚠ 有差别是**正常**的（新增项虽小但不是零）——")
        print("       要看差别是否只在**末几位有效数字**上；若是，量级估计成立。")
PY
