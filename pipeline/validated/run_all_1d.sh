#!/bin/bash
# =============================================================================
# 1D 验证套件：一条命令跑完审计测试矩阵里的 1D 项，并打印 PASS/FAIL 汇总
# =============================================================================
# 覆盖：
#   T1  溶质 Jacobian（1D 平界面，-snes_test_jacobian）
#   T2  总溶质守恒
#   T3  非负浓度（移动前沿）
#   T4  液固平衡分配 k_eff
#   T5  kappa_c 极限（每档两种 dx）        --full 才跑（慢）
#   T6  迁移率分层（三态 + 剖面）
#   T7  平面前沿的 dx 收敛
#   T11 晶界过剩 Γ_GB（dx / w_gb 收敛）    --full 才跑（慢）
#   T12 晶界快速扩散（扰动衰减）
#
# 用法：
#   bash run_all_1d.sh              # 快档（约 15 分钟）
#   bash run_all_1d.sh --full       # 加上 T5 / T11（约 1 小时）
#
# 输出：控制台汇总 + <ROOT>/SUMMARY.txt
# =============================================================================
set +u   # conda activate 引用未定义的 $CONDA_BUILD

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/validate_all}"
FULL=0
[ "${1:-}" = "--full" ] && FULL=1

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"
SUMMARY="$ROOT/SUMMARY.txt"
: > "$SUMMARY"

log() { echo "$@" | tee -a "$SUMMARY"; }
run() { log ""; log "########## $* ##########"; }

# ---------------------------------------------------------------------------
run "T1 + T2 + T4：1D 平界面静止算例"
# ---------------------------------------------------------------------------
python3 "$HERE/make_1d_static.py" --out "$ROOT/static.i" --kc 1.0e-14 > "$ROOT/static.gen.log" 2>&1
( cd "$ROOT" && "$MOOSE" -i static.i Executioner/end_time=3e-4 -snes_test_jacobian 1e-5 > static_jac.log 2>&1 )
NWARN=$(sed "s/\x1b\[[0-9;]*m//g" "$ROOT/static_jac.log" | grep -ac "Missing coupled")
RATIO=$(sed "s/\x1b\[[0-9;]*m//g" "$ROOT/static_jac.log" | grep -aoE "J - Jfd.._F/\|\|J\|\|_F = [0-9.e+-]+" | head -1 | grep -oE "[0-9.e+-]+$")
log "  T1  Missing coupled variables 条数 = $NWARN   （判据 0）"
log "  T1  首个 ||J-Jfd||/||J|| = ${RATIO:-?}   （判据 <= 1e-5）"

# 不带 -snes_test_jacobian 跑一遍拿守恒与 k_eff（测试模式太慢）
( cd "$ROOT" && "$MOOSE" -i static.i > static.log 2>&1 )
python3 - "$ROOT" "$SUMMARY" "$NWARN" "$RATIO" <<'PY' | tee -a "$SUMMARY"
import csv, os, sys
root, summary, nwarn, ratio = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
r = list(csv.DictReader(open(os.path.join(root, "static_out.csv"))))
tot = [float(x["total_c"]) for x in r]
drift = abs(tot[-1] - tot[0]) / abs(tot[0]) if tot[0] else 0.0
last = r[-1]
keff = float(last["c_solid"]) / float(last["c_max"])
THEORY = 0.9 / (0.9 + 2 * 0.264)
rel = abs(keff - THEORY) / THEORY

def verdict(ok): return "PASS" if ok else "FAIL"
try:
    rv = float(ratio)
except (TypeError, ValueError):
    rv = 1.0
print("  %-4s T1 雅可比：警告 %d 条，FD %.3e                     %s"
      % ("", nwarn, rv, verdict(nwarn == 0 and rv <= 1e-5)))
print("  %-4s T2 守恒：相对漂移 %.3e                        %s"
      % ("", drift, verdict(drift <= 1e-8)))
print("  %-4s T4 k_eff：%.8f vs 理论 %.8f（偏差 %.3f%%）      %s"
      % ("", keff, THEORY, rel * 100, verdict(rel <= 0.01)))
PY

# ---------------------------------------------------------------------------
run "T3：移动前沿非负浓度"
# ---------------------------------------------------------------------------
cp "$HERE/../tests/front1d.i" "$ROOT/moving.i"
( cd "$ROOT" && "$MOOSE" -i moving.i Executioner/end_time=2.0e-3 > moving.log 2>&1 )
python3 - "$ROOT" <<'PY' | tee -a "$SUMMARY"
import csv, os, sys
root = sys.argv[1]
r = list(csv.DictReader(open(os.path.join(root, "moving_out.csv"))))
cmin = min(float(x["c_min"]) for x in r)
print("  %-4s T3 min(c) = %.6g   （判据 >= -1e-10）            %s"
      % ("", cmin, "PASS" if cmin >= -1e-10 else "FAIL"))
PY

# ---------------------------------------------------------------------------
run "T6：迁移率分层（三态 + 剖面）"
# ---------------------------------------------------------------------------
python3 "$HERE/make_variant.py" --src "${SRC:-$HERE/stage1_meltpool_c.premerge.i}" \
    --out "$ROOT/dlayer.i" --d-layer 2.52e-9 4.0e-13 4.0e-10 > /dev/null 2>&1
if python3 "$HERE/check_D_layering.py" "$ROOT/dlayer.i" \
      --dl 2.52e-9 --ds 4.0e-13 --dgb 4.0e-10 >> "$SUMMARY" 2>&1; then
  log "  T6  三态 + 剖面判据                                         PASS"
else
  log "  T6  三态 + 剖面判据                                         FAIL"
fi

# ---------------------------------------------------------------------------
run "T12：晶界快速扩散（扰动衰减）"
# ---------------------------------------------------------------------------
for st in liquid grain gb; do
  D="$ROOT/decay_$st"; mkdir -p "$D"
  python3 "$HERE/make_1d_decay.py" --out "$D/case.i" --state "$st" > "$D/gen.log" 2>&1
  ( cd "$D" && "$MOOSE" -i case.i > run.log 2>&1 )
done
python3 "$HERE/analyze_decay.py" liquid="$ROOT/decay_liquid" grain="$ROOT/decay_grain" \
    gb="$ROOT/decay_gb" >> "$SUMMARY" 2>&1
tail -5 "$SUMMARY"

# ---------------------------------------------------------------------------
run "T14 诊断：AMR 段错误的真正原因（本轮新增）"
# ---------------------------------------------------------------------------
# 判决性实验：同一算例「原样 + AMR」崩、「只删掉 2 个 elementid 后处理 + AMR」正常。
ROOT="$ROOT/t14diag" bash "$HERE/run_t14_diag.sh" 2>&1 | tee -a "$SUMMARY"

# ---------------------------------------------------------------------------
run "T7：平面前沿的 dx 收敛"
# ---------------------------------------------------------------------------
ROOT="$ROOT/t7" NX_LIST="${T7_NX:-160 320 640}" END="${T7_END:-3.0e-3}" \
  bash "$HERE/run_t7.sh" 2>&1 | tee -a "$SUMMARY"

# ---------------------------------------------------------------------------
if [ "$FULL" = "1" ]; then
  run "T5：kappa_c 极限（每档两种 dx）"
  ROOT="$ROOT/t5" bash "$HERE/run_t5.sh" 2>&1 | tee -a "$SUMMARY"
  run "T11：晶界过剩 Γ_GB"
  ROOT="$ROOT/t11" bash "$HERE/run_t11.sh" 2>&1 | tee -a "$SUMMARY"
  run "Ω₀ 标定：wGB × {noseg, 旧, 新}（本轮新增）"
  # ⚠ 必须带 `--f-part h_solid`：默认的 Ση² 会让 noseg 档的基座就有
  #   222 at/nm²（比文献大 100 倍），把偏析项的贡献完全盖住。
  ROOT="$ROOT/omega" F_PART=h_solid WGB_LIST="0.4e-6 0.8e-6" \
    bash "$HERE/run_omega_calib.sh" 2>&1 | tee -a "$SUMMARY"
else
  log ""
  log "（T5 / T11 未跑 —— 加 --full）"
fi

log ""
log "=========== 汇总见 $SUMMARY ==========="
