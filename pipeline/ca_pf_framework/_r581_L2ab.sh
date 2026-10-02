#!/bin/bash
# _r581_L2ab.sh --- L2 的**真实路径 gate 4**：`--eps0-tile 0` vs `4`，全部落盘列逐位。
#
# 为什么还要单独跑一次：单元判据（`_r581_L2check.py`）与生产口径记账（`_r581_L2prof.sh`）
# 都在**引擎内部**；而 gate 4 要求的是**真实 `_bk_exp.py` 算例的全部落盘列**
# （R580 的教训：`onfly` 起初对 `g.phi` 逐位，却让诊断量 `E_el_J` 差 3.1×）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

COMMON="--N 64 --dx-nm 62.5 --steps 12 --every 1 --snap-every 99999 \
        --pair-every 12 --norm-smooth 0 --nthreads 4 --reinit-dt 1e-4 \
        --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
        --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
        --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
        --cool-rate 2.3524e6 --plate-L 1000 --plate-W 500 --plate-T 510 \
        --gamma0 0.25 --beta-h 6.477 --facet-proj 0 --facet-excl 0 \
        --eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
        --argmin2-mode copyto --grad-mode sliced --pf-phi onfly --h-chunk 4 \
        --extend-mode near"

echo "############ 归档改名（绝不删除）"
for t in l2a l2b; do
  d="_exp/_bk_l2/$t"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)" && echo "  已改名 $d"
done

for spec in "l2a 0" "l2b 4"; do
  set -- $spec
  echo "############ $1 : --eps0-tile $2"
  taskset -c 8-15 $PY -u _bk_exp.py $COMMON --out _exp/_bk_l2 --tag "$1" \
      --eps0-tile "$2" > "_w2_r581_l2ab_$1.log" 2>&1
  echo "  exit=$?  Traceback=$(grep -c '^Traceback' "_w2_r581_l2ab_$1.log" || true)"
  grep -m1 '算子开关' "_w2_r581_l2ab_$1.log" | sed 's/.*算子开关：/  /' | cut -c1-100
done

echo ""
echo "############ gate 4：全部共有列逐位"
$PY - <<'PYEOF'
import os
import numpy as np
R = '_exp/_bk_l2'
def rd(t):
    p = os.path.join(R, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)
h0, a0 = rd('l2a')
if a0 is None:
    print('  ❌ 缺 l2a/series.csv'); raise SystemExit(1)
h1, a1 = rd('l2b')
if a1 is None:
    print('  ❌ 缺 l2b/series.csv'); raise SystemExit(1)
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
    (real if np.array_equal(fx, fy) else []).append(c) if np.array_equal(fx, fy) else None
    if not np.array_equal(fx, fy):
        npos += 1
print('  BASE(l2a) %d 列；共有 %d 列（排除 wall_s）' % (len(h0), len(common)))
print('  有限列 %d，全 NaN 列 %d' % (nfin, nnan))
print('  ⇒ 真有差异的列 %d %s ；nan 位置不同的列 %d'
      % (len(real), real[:6], npos))
print('  ⇒ gate 4 判定：%s'
      % ('✅ PASS（全部共有列逐位一致）' if not real and not npos else '❌ FAIL'))
PYEOF
echo "=== R581 L2 AB DONE $(date '+%F %T') ==="
