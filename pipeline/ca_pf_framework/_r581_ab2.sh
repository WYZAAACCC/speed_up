#!/bin/bash
# _r581_ab2.sh --- 通用**真实路径 gate 4**：跑两臂 `_bk_exp.py`，比**全部共有列**逐位。
#
# 用法: bash _r581_ab2.sh <题签> <臂A名> "<臂A额外CLI>" <臂B名> "<臂B额外CLI>" [N]
# 例:   bash _r581_ab2.sh L5 l5a "" l5b "--argmin2-reuse 1"
#
# ⚠ 判据口径（R580 修正版）：不用 `d > worst`（那个写法会**静默跳过 NaN 列**），
#   而是分三类报：**有限列逐位** / **both-NaN 列** / **nan 位置不同**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

TITLE="$1"; AN="$2"; AARG="$3"; BN="$4"; BARG="$5"; N="${6:-64}"
ROOT="_exp/_bk_${TITLE}"
echo "############ 归档改名（绝不删除）"
for t in "$AN" "$BN"; do
  d="$ROOT/$t"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)" && echo "  已改名 $d"
done

COMMON="--N $N --dx-nm 62.5 --steps 12 --every 1 --snap-every 99999 \
        --pair-every 12 --norm-smooth 0 --nthreads 4 --reinit-dt 1e-4 \
        --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
        --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
        --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
        --cool-rate 2.3524e6 --plate-L 1000 --plate-W 500 --plate-T 510 \
        --gamma0 0.25 --beta-h 6.477 --facet-proj 0 --facet-excl 0 \
        --eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
        --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4 \
        --extend-mode near --eps0-tile 4"

for spec in "$AN|$AARG" "$BN|$BARG"; do
  t="${spec%%|*}"; ar="${spec#*|}"
  echo "############ $t : $ar"
  taskset -c 8-15 $PY -u _bk_exp.py $COMMON --out "$ROOT" --tag "$t" $ar \
      > "_w2_r581_${TITLE}_$t.log" 2>&1
  echo "  exit=$?  Traceback=$(grep -c '^Traceback' "_w2_r581_${TITLE}_$t.log" || true)"
  grep -m1 '算子开关' "_w2_r581_${TITLE}_$t.log" | sed 's/.*算子开关：/  /' | cut -c1-110
done

echo ""
echo "############ gate 4：全部共有列逐位（$AN vs $BN）"
$PY - "$ROOT" "$AN" "$BN" <<'PYEOF'
import os, sys
import numpy as np
R, AN, BN = sys.argv[1], sys.argv[2], sys.argv[3]
def rd(t):
    p = os.path.join(R, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)
h0, a0 = rd(AN); h1, a1 = rd(BN)
if a0 is None or a1 is None:
    print('  ❌ 缺 series.csv（%s=%s, %s=%s）' % (AN, a0 is not None, BN, a1 is not None))
    raise SystemExit(1)
common = [c for c in h0 if c in h1 and c != 'wall_s']
nfin = nnan = npos = 0
real = []
for c in common:
    x = np.atleast_1d(a0[c]).astype(float); y = np.atleast_1d(a1[c]).astype(float)
    m = min(len(x), len(y))
    if m == 0:
        continue
    x, y = x[:m], y[:m]
    fx, fy = np.isfinite(x), np.isfinite(y)
    both = fx & fy
    if not both.any():
        nnan += 1; continue
    nfin += 1
    if np.array_equal(x[both], y[both]):
        continue
    if np.array_equal(fx, fy):
        real.append(c)
    else:
        npos += 1
print('  %s: %d 列；%s: %d 列；共有 %d 列（排除 wall_s）' % (AN, len(h0), BN, len(h1), len(common)))
print('  有限列 %d，全 NaN 列 %d' % (nfin, nnan))
print('  ⇒ 真有差异的列 %d %s ；nan 位置不同的列 %d' % (len(real), real[:6], npos))
print('  ⇒ gate 4 判定：%s'
      % ('✅ PASS（全部共有列逐位一致）' if not real and not npos else '❌ FAIL'))
PYEOF
echo "=== R581 $TITLE AB DONE $(date '+%F %T') ==="
