#!/bin/bash
# _r581_L5prof.sh --- ★ L5 的**生产口径**分块记账 A/B：`--argmin2-reuse 0` vs `1`。
#
# ## 为什么用记账器
# 预期收益 ~3%/步，**低于整步墙钟 ~7–10% 的噪声地板**（R581-L1 已实测过这个教训）
# ⇒ 必须用分块记账（钩子开销 0.2%）。
#
# ## 判据
#   M-1 `argmin2` 的秒/步必须下降；   M-2 `argmin2.winner` 计数必须 1→0；
#   M-3 **干净单步**也必须下降（证明落到了墙钟上）；
#   M-4 `P0..P5` 全 PASS；            M-5 `region` 的 n/步**不得变**（它不该变）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
export R576_N="${R581L5P_N:-96}" R576_NV="${R581L5P_NV:-48}"
export R576_STEPS="${R581L5P_STEPS:-6}" R576_WORKERS="${R581L5P_WORKERS:-4}"
ROUNDS="${R581L5P_ROUNDS:-3}"
LOG=_w2_r581_L5prof.log
: > "$LOG"
export R561_EPS0=einsum R561_EDPAIR=gather R561_KLOOP=act R561_ACT=bincount \
       R561_ARG2=copyto R561_PFPHI=onfly R561_GRAD=sliced R581_EXTEND=near \
       R581_EPS0TILE=4

echo "=== R581-L5 生产口径 A/B（N=$R576_N nv=$R576_NV onfly，$ROUNDS 轮）===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r ----" | tee -a "$LOG"
  for v in 0 1; do
    export R581_ARGREUSE="$v"
    export R576_TAG="a${v}r${r}"
    export R576_OUT="_w2_r581l5p_a${v}_r${r}.log"
    $PY _r576_prof.py > "_w2_r581l5p_a${v}_r${r}_stdout.log" 2>&1
    A=$(grep -E '^    argmin2 ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    W=$(grep -E '^    argmin2\.winner ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4, $5}')
    R=$(grep -E '^    region ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$R576_OUT" | head -1)
    PJ=$(grep -E '^  P0=' "$R576_OUT" | head -1)
    echo "  reuse=$v r$r 干净单步=$CL" | tee -a "$LOG"
    echo "      argmin2=[$A]  winner=[$W]  region=[$R]" | tee -a "$LOG"
    echo "      $PJ" | tee -a "$LOG"
  done
done
echo "" | tee -a "$LOG"
echo "############ 汇总" | tee -a "$LOG"
$PY - "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import re, statistics, sys
R = int(sys.argv[1])
def num(x):
    try:
        return float(x)
    except Exception:
        return None
A, W, CL, RG = {}, {}, {}, {}
for v in ('0', '1'):
    A[v], W[v], CL[v], RG[v] = [], [], [], []
    for r in range(1, R + 1):
        try:
            x = open('_w2_r581l5p_a%s_r%d.log' % (v, r), errors='replace').read()
        except OSError:
            continue
        m = re.search(r'^    argmin2\s+([\d.]+) s', x, re.M)
        if m:
            A[v].append(float(m.group(1)))
        m2 = re.search(r'^    argmin2\.winner\s+([\d.]+) s\s+[\d.]+%\s+n=\s*([\d.]+)/步', x, re.M)
        if m2:
            W[v].append((float(m2.group(1)), float(m2.group(2))))
        m3 = re.search(r'干净单步（钩子关）= \*\*([\d.]+) s', x)
        if m3:
            CL[v].append(float(m3.group(1)))
        m4 = re.search(r'^    region\s+([\d.]+) s\s+[\d.]+%\s+n=\s*([\d.]+)/步', x, re.M)
        if m4:
            RG[v].append((float(m4.group(1)), float(m4.group(2))))
for v, nm in (('0', '归档 reuse=0'), ('1', '复用 reuse=1')):
    print('  %-14s argmin2 = %s  ⇒ 中位 %.5f s/步'
          % (nm, ' '.join('%.5f' % z for z in A[v]), statistics.median(A[v]) if A[v] else float('nan')))
    print('  %-14s argmin2.winner = %s'
          % ('', ' '.join('%.5f(n=%.2f)' % t for t in W[v])))
    print('  %-14s region  = %s'
          % ('', ' '.join('%.5f(n=%.2f)' % t for t in RG[v])))
    print('  %-14s 干净单步 = %s  ⇒ 中位 %.5f s/步'
          % ('', ' '.join('%.5f' % z for z in CL[v]), statistics.median(CL[v]) if CL[v] else float('nan')))
if A['0'] and A['1']:
    a, b = statistics.median(A['0']), statistics.median(A['1'])
    ca, cb = statistics.median(CL['0']), statistics.median(CL['1'])
    print()
    print('  ⇒ M-1 `argmin2` 提速 **%.3f×**（%.5f → %.5f s/步，省 %.2f%% 单步）'
          % (a / b, a, b, 100 * (a - b) / ca))
    print('  ⇒ M-3 **整步**提速  **%.3f×**（%.5f → %.5f s/步）' % (ca / cb, ca, cb))
    nw1 = max(t[1] for t in W['1']) if W['1'] else 0.0
    print('  ⇒ M-2 `argmin2.winner` 的 n/步：归档 %s → 复用 %s ⇒ %s'
          % ([t[1] for t in W['0']], [t[1] for t in W['1']],
             '✅ PASS（复用档该行**整行消失** = 计数 0，正是本条优化的目的）'
             if nw1 == 0.0 else '❌ FAIL'))
    print('     ⚠ 量具口径：记账器**只打印有数据的 tag** ⇒ 计数为 0 时该行**不出现**，')
    print('        不是"没测到"。判据要按"缺失=0"解释（本脚本第一版就误报过 FAIL）。')
    nr0 = set(t[1] for t in RG['0']); nr1 = set(t[1] for t in RG['1'])
    print('  ⇒ M-5 `region` 的 n/步：%s → %s ⇒ %s'
          % (nr0, nr1, '✅ 未变' if nr0 == nr1 else '❌ 变了（不该变）'))
PYEOF
echo "=== R581 L5 PROF DONE $(date '+%F %T') ===" | tee -a "$LOG"
