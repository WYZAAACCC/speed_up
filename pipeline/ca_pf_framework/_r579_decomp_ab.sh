#!/bin/bash
# _r579_decomp_ab.sh --- R579：**2×2 构成分解**（机器空闲，4 臂 × N 轮轮换）。
#
# ## 为什么要重做（v1 的两个问题）
# ① 六臂那次是**满载**跑的 ⇒ 单项散布 ±20%，分不开。
# ② 安静 3 臂那次发现 **KLOOP 单独 = 0.986×（无收益）**，与早先的 1.064× 矛盾
#    ⇒ 必须把"三项小改"与"R561 的两个开关"**分开**量，否则说不清 1.215× 是谁贡献的。
#
# 2×2 设计（每格一个臂）：
#            | 不加 R561 开关 | 加 einsum+gather
#   三项小改  |     BASE       |     SMALL+BIT = ALL5
#   不加      |     BASE       |     BIT
#   （SMALL = k_loop=act + act=bincount + argmin2=copyto）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R579D_N:-64}" R576_NV="${R579D_NV:-24}"
export R576_STEPS="${R579D_STEPS:-6}" R576_WORKERS="${R579D_WORKERS:-4}"
ROUNDS="${R579D_ROUNDS:-4}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r579_decompab.log
: > "$LOG"

_LAST=""
run_arm() {
  local tag="$1" ev="$2"
  local OUTF="_w2_r579d_${tag}_${SUF}.log"
  env $ev R576_TAG="$tag" R576_OUT="$OUTF" "$PY" _r576_prof.py \
      > "_w2_r579d_${tag}_stdout.log" 2>&1
  local CL VN
  CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
  VN=$(grep -E 'adv\.step\.vnk +[0-9]' "$OUTF" | head -1 | grep -oE '[0-9]+\.[0-9]+/步' | head -1)
  echo "  $tag clean=$CL vnk=$VN $(grep -E '^  P0=' "$OUTF" | head -1)" | tee -a "$LOG"
  _LAST="$CL"
}
_env_of() {
  case "$1" in
    BASE)  echo "R579D_NOOP=1" ;;
    SMALL) echo "R561_KLOOP=act R561_ACT=bincount R561_ARG2=copyto" ;;
    BIT)   echo "R561_EPS0=einsum R561_EDPAIR=gather" ;;
    ALL5)  echo "R561_KLOOP=act R561_ACT=bincount R561_ARG2=copyto R561_EPS0=einsum R561_EDPAIR=gather" ;;
  esac
}

echo "=== R579 2×2 构成分解（4 臂 × $ROUNDS 轮轮换）N=$R576_N NV=$R576_NV W=$R576_WORKERS ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ⚠ 机器空闲；不设 MALLOC_*（PLAIN 口径）；臂顺序每轮轮换" | tee -a "$LOG"

ARMS=(BASE SMALL BIT ALL5)
declare -A RES
for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r（偏移 $(( (r-1) % 4 ))）----" | tee -a "$LOG"
  for i in 0 1 2 3; do
    tag="${ARMS[$(( (i + (r-1)) % 4 ))]}"
    run_arm "${tag}r${r}" "$(_env_of "$tag")"
    RES[$tag]="${RES[$tag]:-}${_LAST} "
  done
done

echo "" | tee -a "$LOG"
$PY - "$ROUNDS" ${RES[BASE]} ${RES[SMALL]} ${RES[BIT]} ${RES[ALL5]} <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1]); v = [x for x in sys.argv[2:] if x.strip()]
assert len(v) == 4 * n, '%d != %d' % (len(v), 4 * n)
d = {k: [float(x) for x in v[i*n:(i+1)*n]]
     for i, k in enumerate(('BASE', 'SMALL', 'BIT', 'ALL5'))}
B = d['BASE']
print('  BASE（全默认）                    = %s  中位 %.4f'
      % (['%.4f' % x for x in B], statistics.median(B)))
DESC = {'SMALL': '三项小改(k_loop/act/argmin2)',
        'BIT': 'einsum+gather（R561 的两个开关）',
        'ALL5': '五项全开'}
res = {}
for k in ('SMALL', 'BIT', 'ALL5'):
    r = [a / b for a, b in zip(B, d[k])]
    res[k] = statistics.median(r)
    print('  %-6s(%-28s) = %s ⇒ **%.4fx**  区间 [%.4f, %.4f]'
          % (k, DESC[k], ['%.4f' % x for x in d[k]],
             statistics.median(r), min(r), max(r)))
print('')
print('  构成分解（相对 BASE 的中位提速）：')
print('     SMALL（三项小改）      %+.2f%%' % (100 * (res['SMALL'] - 1)))
print('     BIT  （einsum+gather） %+.2f%%' % (100 * (res['BIT'] - 1)))
print('     ALL5 （五项全开）      %+.2f%%' % (100 * (res['ALL5'] - 1)))
print('     ⇒ 两项**相乘**预期 = %.4fx；实测 ALL5 = %.4fx ⇒ %s'
      % (res['SMALL'] * res['BIT'], res['ALL5'],
         '✅ 与相乘一致（可加性/独立性成立）'
         if abs(res['SMALL'] * res['BIT'] - res['ALL5']) / res['ALL5'] < 0.03
         else '⚠ 与相乘不一致（差 %.1f%%）—— 记账，不要强行解释'
              % (100 * abs(res['SMALL'] * res['BIT'] - res['ALL5']) / res['ALL5'])))
PYEOF
echo "=== R579 2×2 分解 DONE $(date '+%F %T') ===" | tee -a "$LOG"
