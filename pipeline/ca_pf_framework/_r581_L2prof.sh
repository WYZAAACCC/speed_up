#!/bin/bash
# _r581_L2prof.sh --- ★ L2 的**生产口径**分块记账 A/B：直接量 `el.e0.stream` 与整步。
#
# ## 为什么在生产口径（N=96/nv=48/onfly）上量
# `R581 §7` 实测：N=64/nv=24 的构成与生产**完全不同**（`el.epsh` 10.4% vs 47.5%）。
# ⇒ 只在小算例上验会**指向错靶子**。
#
# ## 判据
#   M-1 `el.e0.stream` 的**秒/步**必须显著下降；
#   M-2 **干净单步**（钩子关）也必须下降（证明真的落到了墙钟上）；
#   M-3 `P0..P5` 全 PASS（否则量具失效，读数不算数）；
#   M-4 `el.e0.stream` 的 n/步 == 1.00（钩子活性）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
export R576_N="${R581L2P_N:-96}" R576_NV="${R581L2P_NV:-48}"
export R576_STEPS="${R581L2P_STEPS:-6}" R576_WORKERS="${R581L2P_WORKERS:-4}"
ROUNDS="${R581L2P_ROUNDS:-3}"
LOG=_w2_r581_L2prof.log
: > "$LOG"
export R561_EPS0=einsum R561_EDPAIR=gather R561_KLOOP=act R561_ACT=bincount \
       R561_ARG2=copyto R561_PFPHI=onfly R561_GRAD=sliced R581_EXTEND=near

echo "=== R581-L2 生产口径 A/B（N=$R576_N nv=$R576_NV onfly，$ROUNDS 轮）===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

ARMS=(0 4)
for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r ----" | tee -a "$LOG"
  for t in "${ARMS[@]}"; do
    export R581_EPS0TILE="$t"
    export R576_TAG="t${t}r${r}"
    export R576_OUT="_w2_r581l2p_t${t}_r${r}.log"
    $PY _r576_prof.py > "_w2_r581l2p_t${t}_r${r}_stdout.log" 2>&1
    ST=$(grep -E '^    el\.e0\.stream ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$R576_OUT" | head -1)
    PJ=$(grep -E '^  P0=' "$R576_OUT" | head -1)
    echo "  tile=$t r$r 干净单步=$CL  el.e0.stream=[$ST]" | tee -a "$LOG"
    echo "           $PJ" | tee -a "$LOG"
  done
done
echo "" | tee -a "$LOG"
echo "############ 汇总" | tee -a "$LOG"
$PY - "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import re, statistics, sys
R = int(sys.argv[1])
sec, cln, nps = {}, {}, {}
for t in ('0', '4'):
    sec[t], cln[t], nps[t] = [], [], []
    for r in range(1, R + 1):
        try:
            x = open('_w2_r581l2p_t%s_r%d.log' % (t, r), errors='replace').read()
        except OSError:
            continue
        m = re.search(r'^    el\.e0\.stream\s+([\d.]+) s\s+[\d.]+%\s+n=\s*([\d.]+)/步', x, re.M)
        if m:
            sec[t].append(float(m.group(1))); nps[t].append(float(m.group(2)))
        m2 = re.search(r'干净单步（钩子关）= \*\*([\d.]+) s', x)
        if m2:
            cln[t].append(float(m2.group(1)))
for t, nm in (('0', '归档 tile=0'), ('4', '分块 tile=4')):
    if sec[t]:
        print('  %-14s el.e0.stream = %s  ⇒ 中位 %.5f s/步   n/步=%s'
              % (nm, ' '.join('%.5f' % v for v in sec[t]),
                 statistics.median(sec[t]), set(nps[t])))
        print('  %-14s 干净单步     = %s  ⇒ 中位 %.5f s/步'
              % ('', ' '.join('%.5f' % v for v in cln[t]), statistics.median(cln[t])))
if sec['0'] and sec['4']:
    a, b = statistics.median(sec['0']), statistics.median(sec['4'])
    ca, cb = statistics.median(cln['0']), statistics.median(cln['4'])
    print()
    print('  ⇒ M-1 `el.e0.stream` 提速 **%.3f×**（%.5f → %.5f s/步，省 %.2f%% 单步）'
          % (a / b, a, b, 100 * (a - b) / ca))
    print('  ⇒ M-2 **整步**提速       **%.3f×**（%.5f → %.5f s/步）' % (ca / cb, ca, cb))
    print('  ⇒ M-1 判据（stream 必须变快）：%s' % ('✅ PASS' if b < a else '❌ FAIL'))
    print('  ⇒ M-2 判据（整步必须变快）  ：%s' % ('✅ PASS' if cb < ca else '❌ FAIL'))
PYEOF
echo "=== R581 L2 PROF DONE $(date '+%F %T') ===" | tee -a "$LOG"
