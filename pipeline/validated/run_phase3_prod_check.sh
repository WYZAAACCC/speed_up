#!/bin/bash
# =============================================================================
# Phase 3 合入生产的**定量验证**：生产的 `Ση²` vs 合入版的 `h_solid` + 偏析项
# =============================================================================
# 背景（VALIDATION_STATUS.md §3.0）
# --------------------------------
# 生产 `f_loc = k_c/2(c-c0)^2 + A_part*c^2*(Ση²)` 里：
#   * 分配项由 `Ση²` 驱动，而 `Ση²` 在**固固晶界处是 0.5**（不是 1）
#     ⇒ 晶界被当成「另一种相」⇒ 平衡浓度与晶粒内不同
#     ⇒ **凭空造出 222 at/nm² 的晶界过剩**（1D 实测，比文献锚点大 100 倍）
#   * 没有独立的偏析项
#
# 合入版（`make_phase3_prod.py`）改三处：分配项改 `h_solid`、加偏析项、同步 `M` 的分母。
#
# ## 为什么**短算例就能看到**（这一点很关键）
#
# 溶质**输运**在可达的时间尺度上几乎不动（`sqrt(D_S·t)` 在 t=2e-6 s 时只有 ~1 nm）。
# 但 `h_solid` 与偏析项改变的是**局域平衡浓度**——那是个**静态（非输运受限）效应**，
# 第一步就该显现。⇒ 判据看 `c_max - c_min` 与 `c_solid_avg`，不是看梯度。
#
# ## 判据
#
#   1. 两档都 **不崩**、`total_solute` 漂移 ≤ 1e-8
#   2. 合入版的 `c_max - c_min` **显著小于**生产版
#      —— 生产的差值主要来自「晶界=另一种相」的伪效应
#   3. `c_min > 0`（非负）
#
# ⚠ 用户约束：**只做 smoke test**（小域 + 短时间），不跑全尺寸。
#
# 用法： bash run_phase3_prod_check.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BASE="${BASE:-/root/work/prod_merged}"
ROOT="${ROOT:-/root/work/p3check}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
NX="${NX:-54}"; NY="${NY:-19}"
END="${END:-2.0e-6}"
TMO="${TMO:-2400}"
SEED="${SEED:-/root/work/jitcache_seed}"

[ -f "$BASE/N.i" ] || { echo "错误：找不到 $BASE/N.i" >&2; exit 1; }

rm -rf "$ROOT"; mkdir -p "$ROOT/run"; cd "$ROOT/run"
[ -d "$SEED" ] && { cp -r "$SEED" .jitcache; echo "  已预置 JIT 缓存"; }

cp "$BASE/N.i" case_prod.i
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true
done

# 现场合入版（不依赖上一次生成的产物，保证可复现）
python3 /mnt/f/speed_up/pipeline/validated/make_phase3_prod.py \
    --src case_prod.i --out case_p3.i \
    --f-part h_solid --omega0 -5e-11 --wgb 4e-6 > gen.log 2>&1 \
  || { echo "错误：生成合入版失败"; tail -5 gen.log; exit 1; }
echo "  合入版已生成"

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" "Executioner/end_time=$END" Outputs/exodus=false)

echo
echo "=== 两档对照（网格 ${NX}x${NY}，end_time=${END} s）==="
for d in prod p3; do
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i "case_$d.i" "${COMMON[@]}" \
      "Outputs/file_base=out_$d" > "run_$d.log" 2>&1 || RC=$?
  printf "  %-6s rc=%-4s %4ss\n" "$d" "$RC" "$(( $(date +%s) - S ))"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
run = os.path.join(sys.argv[1], "run")
hdr = "  %-6s %-11s %-11s %-11s %-12s %-10s %s"
print(hdr % ("档", "c_min", "c_max", "max-min", "守恒漂移", "liquid_f", "状态"))
print("  " + "-" * 76)
res = {}
for d in ("prod", "p3"):
    log = os.path.join(run, f"run_{d}.log")
    f = os.path.join(run, f"out_{d}.csv")
    crashed = ""
    if os.path.exists(log):
        t = open(log, encoding="utf-8", errors="replace").read()
        if "Segmentation" in t: crashed = "段错误"
        elif "*** ERROR ***" in t: crashed = "ERROR"
    if not os.path.exists(f):
        print(hdr % (d, "—", "—", "—", "—", "—", crashed or "无输出")); continue
    r = list(csv.DictReader(open(f)))
    if not r:
        print(hdr % (d, "空", "", "", "", "", crashed)); continue
    def g(row, name):
        k = [c for c in row if name in c]
        return row[k[0]] if k else None
    l = r[-1]
    try:
        cmin, cmax = float(g(l,"c_min")), float(g(l,"c_max"))
        span = cmax - cmin
    except (TypeError, ValueError):
        cmin = cmax = span = float("nan")
    try:
        v0, v1 = float(g(r[0],"total_solute")), float(g(l,"total_solute"))
        drift = abs(v1-v0)/abs(v0) if v0 else 0.0
    except (TypeError, ValueError):
        drift = float("nan")
    print(hdr % (d, f"{cmin:.9f}", f"{cmax:.9f}", f"{span:.3e}",
                 f"{drift:.2e}", f"{float(g(l,'liquid_frac')):.6f}" if g(l,'liquid_frac') else "?",
                 crashed or "ok"))
    res[d] = span

print()
if len(res) == 2 and all(v == v for v in res.values()):
    sp, s3 = res["prod"], res["p3"]
    if sp > 0:
        print(f"  ⇒ c_max-c_min：生产 {sp:.3e} → 合入版 {s3:.3e}  （{s3/sp:.3f}×）")
        if s3 < sp * 0.5:
            print("     ✅ 合入版显著更小 ⇒ **伪晶界偏析被消掉**（h_solid 生效）")
        elif s3 < sp:
            print("     ⚠ 更小但幅度不大 —— 看下一条，可能这个算例里晶界占比太低")
        else:
            print("     ❌ 没有变小 —— h_solid 可能没起作用，要查")
print()
print("  判读要点：")
print("    * `h_solid` 改的是**局域平衡浓度**（静态效应）⇒ **短算例就能看到**")
print("      （溶质输运在 t=2e-6 s 时只走 ~1 nm，梯度看不出来，别拿梯度当判据）")
print("    * 生产的 `c_max-c_min` 主要来自「Ση² 在晶界=0.5 ⇒ 晶界被当成另一种相」")
PY
