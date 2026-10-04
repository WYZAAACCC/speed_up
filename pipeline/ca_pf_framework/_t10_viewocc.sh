#!/bin/bash
# 守卫 ON 那跑里，挑一个 2 块场出三维图
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== t10OCC step 1 全部场 ==="
$PY _t10_allfields.py t10OCC 1 2>&1 | head -25
echo
K=$($PY - <<'PY'
import os, glob
import numpy as np
from scipy import ndimage
S26 = ndimage.generate_binary_structure(3, 3)
f = sorted(glob.glob('_exp/_bk_t5/dry_t10OCC/snap_00001.npz'))
if not f:
    print(0); raise SystemExit
with np.load(f[0], allow_pickle=False) as z:
    N = int(np.asarray(z['N']))
    bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
    bv = np.asarray(z['band_val']).ravel()
    bf = np.asarray(z['band_fld']).ravel()
best = (0, 0)
for k in np.unique(bf[bv < 0]):
    if int(k) == 0:
        continue
    sel = (bf == k) & (bv < 0)
    if sel.sum() < 80:
        continue
    idx = bi[sel]
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    lab, nc = ndimage.label(g, structure=S26)
    if nc == 2:
        sz = np.bincount(lab.ravel())[1:]
        big = int(sz.max())
        if big > best[0]:
            best = (big, int(k))
print(best[1])
PY
)
echo "  挑中 2 块场 = $K"
[ "$K" != "0" ] && $PY _t5_split3d2.py t10OCC "$K" 1 2>&1 | tail -2
