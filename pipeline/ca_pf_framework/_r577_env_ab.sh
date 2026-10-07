#!/bin/bash
# _r577_env_ab.sh --- R577：**分配器/环境变量**对单步墙钟的影响（交错配对）。
#
# 为什么要查这个：`_r576` 的账显示 `upwind_flux_vec` 每次调用要造 **~35 个整场临时量**
#   （N=64 每个 2 MB）⇒ 每步 ~0.9 GB 的 malloc/free。glibc 默认 `MMAP_THRESHOLD=128 KB`
#   ⇒ **每个都走 mmap + 缺页**，free 时又 munmap。而本仓库的 `_r30_regress.sh` **一直**在设
#       MALLOC_MMAP_THRESHOLD_=65536  MALLOC_TRIM_THRESHOLD_=65536  MALLOC_ARENA_MAX=2
#   ⇒ **回归跑与我的基准跑用的不是同一套分配器行为**，这是一个真实的混杂因子，
#     而且如果它有用，那是一条**零风险、零改动**的收益。
#
# 判据：交错 N 轮，报每轮配对提速的中位与区间；**必须同时给出 `adv.step.advphi` 的
#       内部读数**（若只有总时间变而算子内部不变，说明是别的块在变）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R577_N:-64}" R576_NV="${R577_NV:-24}"
export R576_STEPS="${R577_STEPS:-6}" R576_WORKERS="${R577_WORKERS:-4}"
ROUNDS="${R577_ROUNDS:-3}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r577_envab.log
: > "$LOG"

echo "=== R577 ENV A/B（交错）N=$R576_N NV=$R576_NV W=$R576_WORKERS STEPS=$R576_STEPS ROUNDS=$ROUNDS ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ENV_TUNED = MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2" | tee -a "$LOG"

A=(); B=(); AV=(); BV=()
for r in $(seq 1 "$ROUNDS"); do
  for arm in PLAIN TUNED; do
    if [ "$arm" = TUNED ]; then
      EV="MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2"
    else
      EV="R577_NOOP=1"
    fi
    OUTF="_w2_r577_env_${arm}_r${r}_${SUF}.log"
    env $EV R576_TAG="${arm}r${r}" R576_OUT="$OUTF" "$PY" _r576_prof.py \
        > "_w2_r577_env_${arm}_r${r}_stdout.log" 2>&1
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
    VK=$(grep -E '    adv\.step\.advphi ' "$OUTF" | head -1 | awk '{print $2}')
    UV=$(grep -E '    op\.upwind_flux_vec ' "$OUTF" | head -1 | awk '{print $2}')
    MN=$(grep -E '    op\._minmod ' "$OUTF" | head -1 | awk '{print $2}')
    PJ=$(grep -E '^  P1 ' "$OUTF" | sed -E 's/.*= \*\*([0-9.]+)%.*/\1/')
    echo "round $r $arm clean=$CL advphi=$VK ufv=$UV minmod=$MN P1=$PJ" | tee -a "$LOG"
    if [ "$arm" = PLAIN ]; then A+=("$CL"); AV+=("$VK"); else B+=("$CL"); BV+=("$VK"); fi
  done
  echo "  round $r: PLAIN=${A[-1]}  TUNED=${B[-1]}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
$PY - "$ROUNDS" "${A[@]}" "${B[@]}" "${AV[@]}" "${BV[@]}" <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1])
v = sys.argv[2:]
A = [float(x) for x in v[0:n]]
B = [float(x) for x in v[n:2*n]]
AV = [float(x) for x in v[2*n:3*n]]
BV = [float(x) for x in v[3*n:4*n]]
r = [a / b for a, b in zip(A, B)]
print('  单步 PLAIN = %s' % ['%.4f' % x for x in A])
print('  单步 TUNED = %s' % ['%.4f' % x for x in B])
print('  每轮配对提速 = %s' % ['%.3fx' % x for x in r])
print('  **中位提速 = %.3fx**  区间 [%.3fx, %.3fx]'
      % (statistics.median(r), min(r), max(r)))
rv = [a / b for a, b in zip(AV, BV)]
print('  advphi(并发和) PLAIN=%s TUNED=%s ⇒ 中位比 %.3fx'
      % (['%.4f' % x for x in AV], ['%.4f' % x for x in BV], statistics.median(rv)))
PYEOF
echo "=== R577 ENV A/B DONE $(date '+%F %T') ===" | tee -a "$LOG"
