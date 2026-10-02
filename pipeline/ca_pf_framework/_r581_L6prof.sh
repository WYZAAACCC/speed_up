#!/bin/bash
# _r581_L6prof.sh --- ★ L6 的**生产口径**分块记账 A/B：`--ufv-c 0` vs `1`。
#
# ## 判据
#   M-1 `op.upwind_flux_vec`（**墙** = ∥和 / 线程数）的秒/步必须显著下降；
#   M-2 `par.upwind_flux_vec` 也下降；
#   M-3 **干净单步**下降（证明落到墙钟）；
#   M-4 `P0..P5` 全 PASS；
#   M-5 ★ **计数回归的预期变化**：C 档下 `op.ufv.*` / `op._minmod` 的 n/步 → 0
#       （融合核内部不打点）。**这不是漏算** —— 替代活性判据是
#       `par.upwind_flux_vec` 的 n/步**不得变**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
export R576_N="${R581L6P_N:-96}" R576_NV="${R581L6P_NV:-48}"
export R576_STEPS="${R581L6P_STEPS:-6}" R576_WORKERS="${R581L6P_WORKERS:-4}"
ROUNDS="${R581L6P_ROUNDS:-3}"
LOG=_w2_r581_L6prof.log
: > "$LOG"
export R561_EPS0=einsum R561_EDPAIR=gather R561_KLOOP=act R561_ACT=bincount \
       R561_ARG2=copyto R561_PFPHI=onfly R561_GRAD=sliced R581_EXTEND=near \
       R581_EPS0TILE=4

echo "=== R581-L6 生产口径 A/B（N=$R576_N nv=$R576_NV onfly，$ROUNDS 轮）===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r ----" | tee -a "$LOG"
  for v in 0 1; do
    export R581_UFVC="$v"
    export R576_TAG="c${v}r${r}"
    export R576_OUT="_w2_r581l6p_c${v}_r${r}.log"
    $PY _r576_prof.py > "_w2_r581l6p_c${v}_r${r}_stdout.log" 2>&1
    UV=$(grep -E '^    op\.upwind_flux_vec ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    PV=$(grep -E '^    par\.upwind_flux_vec ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    MM=$(grep -E '^    op\._minmod ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$R576_OUT" | head -1)
    PJ=$(grep -E '^  P0=' "$R576_OUT" | head -1)
    echo "  ufv_c=$v r$r 干净单步=$CL" | tee -a "$LOG"
    echo "      op.ufv=[$UV]  par.ufv=[$PV]  _minmod=[$MM]" | tee -a "$LOG"
    echo "      $PJ" | tee -a "$LOG"
  done
done
echo "" | tee -a "$LOG"
echo "############ 汇总" | tee -a "$LOG"
$PY - "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import re, statistics, sys
R = int(sys.argv[1])
def grab(pat, v, r):
    try:
        x = open('_w2_r581l6p_c%s_r%d.log' % (v, r), errors='replace').read()
    except OSError:
        return None
    m = re.search(pat, x, re.M)
    return (float(m.group(1)), float(m.group(2))) if m else None
UV, PV, CL, MM = {}, {}, {}, {}
for v in ('0', '1'):
    UV[v] = [z for z in (grab(r'^    op\.upwind_flux_vec\s+([\d.]+) s\s+([\d.]+)%', v, r)
                         for r in range(1, R + 1)) if z]
    PV[v] = [z for z in (grab(r'^    par\.upwind_flux_vec\s+([\d.]+) s\s+[\d.]+%\s+n=\s*([\d.]+)/步', v, r)
                         for r in range(1, R + 1)) if z]
    MM[v] = [z for z in (grab(r'^    op\._minmod\s+([\d.]+) s\s+[\d.]+%\s+n=\s*([\d.]+)/步', v, r)
                         for r in range(1, R + 1)) if z]
    CL[v] = []
    for r in range(1, R + 1):
        try:
            x = open('_w2_r581l6p_c%s_r%d.log' % (v, r), errors='replace').read()
        except OSError:
            continue
        m = re.search(r'干净单步（钩子关）= \*\*([\d.]+) s', x)
        if m:
            CL[v].append(float(m.group(1)))
for v, nm in (('0', '归档 ufv_c=0'), ('1', '融合核 ufv_c=1')):
    s = ' '.join('%.5f(%.1f%%)' % z for z in UV[v])
    print('  %-16s op.upwind_flux_vec = %s  ⇒ 中位 %.5f'
          % (nm, s, statistics.median([z[0] for z in UV[v]]) if UV[v] else float('nan')))
    print('  %-16s par.upwind_flux_vec n/步 = %s'
          % ('', [z[1] for z in PV[v]]))
    print('  %-16s op._minmod n/步 = %s' % ('', [z[1] for z in MM[v]]))
    print('  %-16s 干净单步 = %s ⇒ 中位 %.5f'
          % ('', ' '.join('%.5f' % z for z in CL[v]),
             statistics.median(CL[v]) if CL[v] else float('nan')))
if UV['0'] and UV['1']:
    a = statistics.median([z[0] for z in UV['0']])
    b = statistics.median([z[0] for z in UV['1']])
    ca, cb = statistics.median(CL['0']), statistics.median(CL['1'])
    print()
    print('  ⇒ M-1 `op.upwind_flux_vec` 提速 **%.3f×**（%.5f → %.5f，省 %.2f%% 单步）'
          % (a / b, a, b, 100 * (a - b) / ca))
    print('  ⇒ M-3 **整步**提速 **%.3f×**（%.5f → %.5f）' % (ca / cb, ca, cb))
    _m1 = [z[1] for z in MM['1']]
    print('  ⇒ M-5 `op._minmod` 的 n/步：归档 %s → 融合核 %s ⇒ %s'
          % ([z[1] for z in MM['0']], _m1,
             '✅ 如预期归 0（融合核内部不做 Python 级打点）'
             if (not _m1) or all(x == 0.0 for x in _m1) else '⚠ 非 0'))
    print('     ⚠ 记账：C 档下 `op.ufv.*` / `op._minmod` 的**计数必然为 0**，')
    print('        所以 `_r576_prof.py` 的 **P2 自检会 FAIL** —— 那是量具的**预期**行为，')
    print('        不是缺陷。替代活性判据 = `par.upwind_flux_vec` 的 n/步**不得变**（见下）。')
    n0 = {z[1] for z in PV['0']}; n1 = {z[1] for z in PV['1']}
    print('  ⇒ M-5b `par.upwind_flux_vec` 的 n/步：%s → %s ⇒ %s'
          % (n0, n1, '✅ 未变' if n0 == n1 else '❌ 变了'))
PYEOF
echo "=== R581 L6 PROF DONE $(date '+%F %T') ===" | tee -a "$LOG"
