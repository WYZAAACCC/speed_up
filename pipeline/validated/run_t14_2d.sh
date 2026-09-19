#!/bin/bash
# =============================================================================
# T14-2D：AMR 能不能用在**真实生产配置**上
# =============================================================================
# 背景（见 VALIDATION_STATUS.md §1.6）
# --------------------------------
# 仓库旧结论「分裂式 CH + AMR ⇒ 段错误」已被推翻：
# 元凶是**硬编码 `elementid` 后处理**（1D 判决性实验 A/B/C）。
#
# 而**生产输入本身就避开了这个坑**（已核查）：
#   * `grep elementid N.i` **零命中**
#   * 后处理全是与网格无关的类型（`NodalExtremeValue` / `ElementAverageValue` /
#     `ElementExtremeValue`）
# ⇒ 生产配置**有望**直接开 AMR。
#
# ⚠ 但 1D 的结论**不能直接外推到 2D**：生产还有 `GrainTracker`、8 个序参量、
#   热场、`PolycrystalVoronoi` 的块结构。**必须实测。**
#
# 本脚本做三组对照（一次只改一个因素）
# ------------------------------------
#   uniform  无 `[Adaptivity]`（基准）
#   refine   只加密（`coarsen = 0`）
#   both     加密 + 粗化
#
# 判据（照抄审计 T14）
# --------------------
#   1. **不崩**（退出码 0）
#   2. **AMR 确实生效** —— 看 `n_elem` 初末是否变化。
#      ⚠ 这条必须查：老式 `Adaptivity` 写法会「跑完不报错但一个单元都没动」
#   3. **守恒** `total_solute` 漂移 ≤ 1e-8
#   4. 与 uniform 的观测量差异 ≤ 5%
#
# ⚠ 用户约束：**只做 smoke test，不跑全尺寸**。域缩小、end_time 取短。
#
# 用法： bash run_t14_2d.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BASE="${BASE:-/root/work/prod_merged}"
SRCI="${SRCI:-N.i}"
ROOT="${ROOT:-/root/work/t14_2d}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
NX="${NX:-54}"; NY="${NY:-19}"          # 生产的 1/8 分辨率（430x150 -> 54x19）
END="${END:-2.0e-6}"
TMO="${TMO:-2400}"
SEED="${SEED:-/root/work/jitcache_seed}"

[ -f "$BASE/$SRCI" ] || { echo "错误：找不到 $BASE/$SRCI" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT/run"; cd "$ROOT/run"
[ -d "$SEED" ] && { cp -r "$SEED" .jitcache; echo "  已预置 JIT 缓存：$(ls .jitcache | wc -l) 项"; }

cp "$BASE/$SRCI" case_uniform.i
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true
done

python3 - "$ROOT" <<'PY'
import os, sys
run = os.path.join(sys.argv[1], "run")
t = open(os.path.join(run, "case_uniform.i"), encoding="utf-8").read()

# 先核查生产输入里没有 elementid（本脚本的核心前提）
assert "elementid" not in t, "生产输入里有 elementid —— 本脚本的前提不成立，先看 §1.6"
print("  前提核查：生产输入零 `elementid`  ✓")

def adapt(refine, coarsen):
    return ("[Adaptivity]\n"
            "  marker = marker\n"
            "  interval = 2\n"
            "  max_h_level = 2\n"
            "  [Indicators]\n"
            "    [jump]\n"
            "      type = GradientJumpIndicator\n"
            "      variable = gr0\n"
            "    []\n"
            "  []\n"
            "  [Markers]\n"
            "    [marker]\n"
            "      type = ErrorFractionMarker\n"
            "      indicator = jump\n"
            f"      refine = {refine}\n"
            f"      coarsen = {coarsen}\n"
            "    []\n"
            "  []\n"
            "[]\n\n")

for tag, (r, c) in (("refine", (0.7, 0.0)), ("both", (0.7, 0.1))):
    i = t.index("[Outputs]")
    open(os.path.join(run, f"case_{tag}.i"), "w", encoding="utf-8").write(
        t[:i] + adapt(r, c) + t[i:])
    print(f"  写出 case_{tag}.i （refine={r}, coarsen={c}）")
PY

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" "Executioner/end_time=$END" Outputs/exodus=false)

echo
echo "=== 三组对照（网格 ${NX}x${NY}，end_time=${END} s）==="
for d in uniform refine both; do
  cd "$ROOT/run"
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
hdr = "  %-8s %-14s %-16s %-14s %-12s %s"
print(hdr % ("档", "n_elem 初→末", "AMR", "total_solute 漂移", "行数", "状态"))
print("  " + "-" * 78)
base = {}
for d in ("uniform", "refine", "both"):
    log = os.path.join(run, f"run_{d}.log")
    f = os.path.join(run, f"out_{d}.csv")
    crashed = ""
    if os.path.exists(log):
        t = open(log, encoding="utf-8", errors="replace").read()
        if "Segmentation" in t or "signal" in t.lower():
            crashed = "段错误"
    if not os.path.exists(f):
        print(hdr % (d, "—", "—", "—", "—", crashed or "无输出"))
        continue
    r = list(csv.DictReader(open(f)))
    if not r:
        print(hdr % (d, "空", "", "", "", crashed)); continue
    def col(name):
        k = [c for c in r[0] if name in c]
        return k[0] if k else None
    ke, ks = col("n_elem"), col("total_solute")
    # ⚠ 起点必须取**第二个数据行**：第 0 行是初始态，`NumElements` 还没算出来（记 0），
    #   拿它当起点会让**没有 AMR 的 baseline** 也被判成「AMR 已生效」。
    i0 = 1 if len(r) > 1 else 0
    e0, e1 = (r[i0][ke], r[-1][ke]) if ke else ("?", "?")
    amr = ("**已生效**" if ke and e0 != e1 else "未生效（无 AMR）") if ke else "?"
    drift = "?"
    if ks:
        try:
            v0, v1 = float(r[0][ks]), float(r[-1][ks])
            drift = f"{abs(v1-v0)/abs(v0):.2e}" if v0 else "0"
        except ValueError:
            pass
    print(hdr % (d, f"{e0}→{e1}", amr, drift, len(r), crashed or "ok"))
    if ks:
        base[d] = (r, r[-1][ks])

print()
print("  判据：")
print("    1. 三档都 **不崩**（rc=0）")
print("    2. `refine`/`both` 的 n_elem **必须变**（否则 AMR 没生效，结论不成立）")
print("    3. `total_solute` 漂移 ≤ 1e-8")
print("    4. 观测量与 uniform 差异 ≤ 5%")
PY
