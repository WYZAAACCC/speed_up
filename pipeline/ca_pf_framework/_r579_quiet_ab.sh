#!/bin/bash
# _r579_quiet_ab.sh --- 机器**空闲**时的确认 A/B（3 臂 × 5 轮轮换）。
#
# ## 为什么必须另跑一次
# `_r578_r3_ab.sh` 的 6 臂那一次是**与 5 道其它作业同时**跑的
# （`_r579_par.sh` 的 T 道）⇒ 每轮配对比值散布极大（例如 KLOOP 1.092 vs 1.336）。
# 6 臂单跑要 30 次 × ~40 s ≈ 20 min，太久 ⇒ 只挑**两个端点 + 一个单项**：
#   BASE（全默认） / KLOOP（k_loop=act） / ALL5（三项 + einsum + gather）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R579Q_N:-64}" R576_NV="${R579Q_NV:-24}"
export R576_STEPS="${R579Q_STEPS:-6}" R576_WORKERS="${R579Q_WORKERS:-4}"
ROUNDS="${R579Q_ROUNDS:-5}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r579_quietab.log
: > "$LOG"

_LAST=""
run_arm() {
  local tag="$1" ev="$2"
  local OUTF="_w2_r579q_${tag}_${SUF}.log"
  env $ev R576_TAG="$tag" R576_OUT="$OUTF" "$PY" _r576_prof.py \
      > "_w2_r579q_${tag}_stdout.log" 2>&1
  local CL VN
  CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
  VN=$(grep -E 'adv\.step\.vnk +[0-9]' "$OUTF" | head -1 | grep -oE '[0-9]+\.[0-9]+/步' | head -1)
  echo "  $tag clean=$CL vnk=$VN $(grep -E '^  P0=' "$OUTF" | head -1)" | tee -a "$LOG"
  _LAST="$CL"
}
_env_of() {
  case "$1" in
    BASE) echo "R579Q_NOOP=1" ;;
    KLOOP) echo "R561_KLOOP=act" ;;
    ALL5) echo "R561_KLOOP=act R561_ACT=bincount R561_ARG2=copyto R561_EPS0=einsum R561_EDPAIR=gather" ;;
  esac
}

echo "=== R579 安静确认 A/B（3 臂 × $ROUNDS 轮，轮换）N=$R576_N NV=$R576_NV W=$R576_WORKERS ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ⚠ 无其它作业并发；不设 MALLOC_*（PLAIN 口径）" | tee -a "$LOG"

ARMS=(BASE KLOOP ALL5)
declare -A RES
for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r（偏移 $(( (r-1) % 3 ))）----" | tee -a "$LOG"
  for i in 0 1 2; do
    tag="${ARMS[$(( (i + (r-1)) % 3 ))]}"
    run_arm "${tag}r${r}" "$(_env_of "$tag")"
    RES[$tag]="${RES[$tag]:-}${_LAST} "
  done
done

echo "" | tee -a "$LOG"
$PY - "$ROUNDS" ${RES[BASE]} ${RES[KLOOP]} ${RES[ALL5]} <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1]); v = [x for x in sys.argv[2:] if x.strip()]
assert len(v) == 3 * n, '%d != %d' % (len(v), 3 * n)
B = [float(x) for x in v[:n]]
K = [float(x) for x in v[n:2*n]]
A = [float(x) for x in v[2*n:]]
print('  BASE  = %s   中位 %.4f' % (['%.4f' % x for x in B], statistics.median(B)))
print('  KLOOP = %s   中位 %.4f' % (['%.4f' % x for x in K], statistics.median(K)))
print('  ALL5  = %s   中位 %.4f' % (['%.4f' % x for x in A], statistics.median(A)))
for nm, arr in (('KLOOP(k_loop=act)', K), ('ALL5(三项+einsum+gather)', A)):
    r = [x / y for x, y in zip(B, arr)]
    print('  %-26s 每轮提速 = %s ⇒ **中位 %.4fx**  区间 [%.4f, %.4f]'
          % (nm, ['%.3f' % x for x in r], statistics.median(r), min(r), max(r)))
# 单项相减（信息性）：k_loop 之外的贡献
rk = [x / y for x, y in zip(B, K)]
ra = [x / y for x, y in zip(B, A)]
print('  ⇒ k_loop 之外的其余四项合计贡献 ≈ %.3fx（ALL5 / KLOOP）'
      % (statistics.median(ra) / statistics.median(rk)))
PYEOF
echo "=== R579 安静确认 A/B DONE $(date '+%F %T') ===" | tee -a "$LOG"
