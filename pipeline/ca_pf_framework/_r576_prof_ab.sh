#!/bin/bash
# _r576_prof_ab.sh --- R576：新量具（`_r576_prof.py`）的**交错配对** A/B。
#
# 为什么要交错：本机是笔记本，本轮实测同一份代码同一命令的 `build.lam.c2c`
#   在 40 min 内从 6.39 s(N=48) 到 15.6 s(N=64)——按 O(N³) 折算其实一致，
#   但端到端 A/B 的**每轮 overhead 仍摆到 ±14%**（`_w2_r576_acctcost.log`）。
#   ⇒ 先跑完 A 再跑 B 会把宿主漂移整个算进 A/B 差里。**必须交错**。
#
# 判据：每臂 P0/P0b/P1/P2/P2b/P2c/P3/P5 全 PASS；P1（函数体口径覆盖）≥95%。
#       墙钟只报**每轮配对比值**的中位与区间，不报单点。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R576_N:-64}" R576_NV="${R576_NV:-24}"
export R576_STEPS="${R576_STEPS:-6}" R576_WORKERS="${R576_WORKERS:-4}"
ROUNDS="${R576_ROUNDS:-3}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r576_profab.log
: > "$LOG"

echo "=== R576 PROF A/B（交错）N=$R576_N NV=$R576_NV W=$R576_WORKERS STEPS=$R576_STEPS ROUNDS=$ROUNDS ===" | tee -a "$LOG"
$PY -c "import sys,numpy,scipy,platform;print('  py',sys.version.split()[0],'numpy',numpy.__version__,'scipy',scipy.__version__,'|',platform.platform())" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

A=(); B=()
for r in $(seq 1 "$ROUNDS"); do
  for arm in BEFORE AFTER; do
    if [ "$arm" = AFTER ]; then
      EXP="R561_FFT=rfft R561_EPS0=einsum R561_EDPAIR=gather"
    else
      EXP="R561_FFT=c2c R561_EPS0=loop R561_EDPAIR=full"
    fi
    OUTF="_w2_r576_prof_${arm}_r${r}_${SUF}.log"
    env $EXP R576_TAG="${arm}r${r}" R576_OUT="$OUTF" "$PY" _r576_prof.py \
        > "_w2_r576_prof_${arm}_r${r}_stdout.log" 2>&1
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
    AC=$(sed -n 's/.*记账跑单步 = \([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
    PJ=$(grep -E '^  P1 ' "$OUTF" | sed -E 's/.*= \*\*([0-9.]+)%.*/\1/')
    VD=$(grep -E '^  P0=' "$OUTF")
    echo "round $r $arm clean=$CL acct=$AC P1=$PJ" | tee -a "$LOG"
    echo "    $VD" | tee -a "$LOG"
    grep -E '^  P1 |^  P1b ' "$OUTF" | sed 's/^/    /' | tee -a "$LOG"
    if [ "$arm" = BEFORE ]; then A+=("$CL"); else B+=("$CL"); fi
  done
  echo "  round $r: BEFORE=${A[-1]} AFTER=${B[-1]}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
$PY - "$ROUNDS" "${A[@]}" "${B[@]}" <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1])
A = [float(x) for x in sys.argv[2:2 + n]]
B = [float(x) for x in sys.argv[2 + n:2 + 2 * n]]
r = [a / b for a, b in zip(A, B)]
print('  BEFORE(c2c/loop/full) = %s' % ['%.4f' % x for x in A])
print('  AFTER (rfft/einsum/gather) = %s' % ['%.4f' % x for x in B])
print('  每轮配对提速 = %s' % ['%.3fx' % x for x in r])
print('  **中位提速 = %.3fx**  区间 [%.3fx, %.3fx]'
      % (statistics.median(r), min(r), max(r)))
PYEOF
echo "=== R576 PROF A/B DONE $(date '+%F %T') ===" | tee -a "$LOG"
