#!/bin/bash
# _r578_kloop_ab.sh --- R578：`k_loop_mode='act'` 的**交错配对**墙钟 A/B 与计数回归。
#
# 判据（先写死）：
#   K-1 两臂 P0/P0b/P1/P2/P2b/P2c/P3/P5 全 PASS；
#   K-2 **计数回归**：`adv.step.vnk` 的**每步次数**必须从 nreg 掉到 `nact`
#       （这是"改动真的生效"的**唯一**硬证据；只看墙钟会被噪声骗）。
#       ⇒ 判据写成：`act` 臂的 `adv.step.vnk` 中位次数 **< full 臂**，且差 ≥ 2。
#   K-3 `adv.step.advphi` 次数两臂**必须相同**（活跃场没变）。
#   K-4 墙钟只报**每轮配对比值**的中位与区间。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R578_N:-64}" R576_NV="${R578_NV:-24}"
export R576_STEPS="${R576_STEPS:-6}" R576_WORKERS="${R576_WORKERS:-4}"
ROUNDS="${R578_ROUNDS:-3}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r578_kloopab.log
: > "$LOG"

echo "=== R578 K_LOOP A/B（交错）N=$R576_N NV=$R576_NV W=$R576_WORKERS STEPS=$R576_STEPS ROUNDS=$ROUNDS ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ⚠ 分配器口径：本脚本**不设** MALLOC_* 变量（= PLAIN）。两臂同一口径 ⇒ 比值有效。" | tee -a "$LOG"

A=(); B=()
for r in $(seq 1 "$ROUNDS"); do
  for arm in FULL ACT; do
    if [ "$arm" = ACT ]; then K="act"; else K="full"; fi
    OUTF="_w2_r578_kloop_${arm}_r${r}_${SUF}.log"
    env R561_KLOOP="$K" R576_TAG="${arm}r${r}" R576_OUT="$OUTF" "$PY" _r576_prof.py \
        > "_w2_r578_kloop_${arm}_r${r}_stdout.log" 2>&1
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
    VN=$(grep -E 'adv\.step\.vnk +[0-9]' "$OUTF" | head -1 | grep -oE '[0-9]+\.[0-9]+/步' | head -1)
    AP=$(grep -E 'adv\.step\.advphi +[0-9]' "$OUTF" | head -1 | grep -oE '[0-9]+\.[0-9]+/步' | head -1)
    UV=$(grep -E '    op\.upwind_flux_vec ' "$OUTF" | head -1 | awk '{print $2}')
    VD=$(grep -E '^  P0=' "$OUTF")
    echo "round $r $arm clean=$CL vnk=$VN advphi=$AP ufv=$UV" | tee -a "$LOG"
    echo "    $VD" | tee -a "$LOG"
    if [ "$arm" = FULL ]; then A+=("$CL"); else B+=("$CL"); fi
  done
  echo "  round $r: FULL=${A[-1]} ACT=${B[-1]}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
$PY - "$ROUNDS" ${A[@]} ${B[@]} <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1]); v = [x for x in sys.argv[2:] if x.strip()]
assert len(v) == 2 * n, '参数个数 %d != %d' % (len(v), 2 * n)
A = [float(x) for x in v[:n]]
B = [float(x) for x in v[n:]]
r = [a / b for a, b in zip(A, B)]
print('  FULL(range(nreg)) = %s' % ['%.4f' % x for x in A])
print('  ACT (unique karr∪larr) = %s' % ['%.4f' % x for x in B])
print('  每轮配对提速 = %s' % ['%.3fx' % x for x in r])
print('  **中位提速 = %.3fx**  区间 [%.3fx, %.3fx]'
      % (statistics.median(r), min(r), max(r)))
PYEOF
echo "=== R578 K_LOOP A/B DONE $(date '+%F %T') ===" | tee -a "$LOG"
