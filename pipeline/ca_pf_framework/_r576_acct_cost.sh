#!/bin/bash
# _r576_acct_cost.sh --- R576：**记账钩子本身的代价**（交错配对 A/B）。
#
# 为什么必须量：本轮的 P1 覆盖率目标是 ≥95%，代价是把 ~30 个钩子点写进
#   `advance()` 的热路径。如果钩子本身吃掉几个百分点，那"覆盖率"就是**买来的**，
#   必须如实登记（AGENTS「不得编造没有实测依据的加速比」）。
#
# 设计（先写死）：
#   * 臂 A = HOOKED（钩子开着，真计时真计数）
#   * 臂 B = STRIPPED（导入期把钩子点改写掉 ⇒ **一次钩子调用都不发生**）
#   * **交错** ROUNDS 轮：A B A B …（单步墙钟 run-to-run 有 ~10% 抖动，
#     只有交错配对才能把系统漂移消掉）
#   * 判据：每轮 overhead = A/B - 1；报**中位与区间**；中位 ≤ 1% 才算过。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R576_N:-64}" R576_NV="${R576_NV:-24}"
export R576_WORKERS="${R576_WORKERS:-4}" R576_STEPS="${R576_STEPS:-4}"
ROUNDS="${R576_ROUNDS:-4}"
LOG=_w2_r576_acctcost.log
: > "$LOG"

echo "=== R576 ACCT-COST  N=$R576_N NV=$R576_NV W=$R576_WORKERS STEPS=$R576_STEPS ROUNDS=$ROUNDS ===" | tee -a "$LOG"
echo "--- 宿主指纹 ---" | tee -a "$LOG"
$PY -c "import sys,numpy,scipy,platform;print('py',sys.version.split()[0],'numpy',numpy.__version__,'scipy',scipy.__version__,'|',platform.platform())" | tee -a "$LOG"
nproc | sed 's/^/nproc /' | tee -a "$LOG"

A=(); B=()
for r in $(seq 1 "$ROUNDS"); do
  for arm in HOOKED STRIPPED; do
    if [ "$arm" = STRIPPED ]; then EXP="R576_STRIP=1"; else EXP="R576_STRIP=0"; fi
    OUT=$(env $EXP "$PY" _r576_bench_one.py 2>&1)
    MED=$(printf '%s\n' "$OUT" | sed -n 's/^MEDIAN=//p' | head -1)
    HK=$(printf '%s\n' "$OUT" | sed -n 's/^HOOKEXEC=//p' | head -1)
    CO=$(printf '%s\n' "$OUT" | sed -n 's/^CORRUPT=//p' | head -1)
    ST=$(printf '%s\n' "$OUT" | sed -n 's/^STRIPSTAT=//p' | head -1)
    echo "round $r $arm median=$MED hooks=$HK corrupt=$CO strip=$ST" | tee -a "$LOG"
    if [ "$arm" = HOOKED ]; then A+=("$MED"); else B+=("$MED"); fi
  done
  echo "  round $r: A=${A[-1]} B=${B[-1]}" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "--- 配对汇总 ---" | tee -a "$LOG"
$PY - "$ROUNDS" "${A[@]}" "${B[@]}" <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1])
A = [float(x) for x in sys.argv[2:2 + n]]
B = [float(x) for x in sys.argv[2 + n:2 + 2 * n]]
r = [a / b - 1.0 for a, b in zip(A, B)]
print('  A(HOOKED)   = %s' % ['%.4f' % x for x in A])
print('  B(STRIPPED) = %s' % ['%.4f' % x for x in B])
print('  每轮 overhead = %s' % ['%+.2f%%' % (100 * x) for x in r])
print('  中位 overhead = **%+.2f%%**   区间 [%+.2f%%, %+.2f%%]'
      % (100 * statistics.median(r), 100 * min(r), 100 * max(r)))
print('  中位 A=%.4f  B=%.4f' % (statistics.median(A), statistics.median(B)))
print('  判据（中位 overhead ≤ 1%%）: %s'
      % ('✅ PASS' if statistics.median(r) <= 0.01 else '❌ FAIL ⇒ 钩子代价过大，必须减点'))
PYEOF
echo "=== R576 ACCT-COST DONE $(date '+%F %T') ===" | tee -a "$LOG"
