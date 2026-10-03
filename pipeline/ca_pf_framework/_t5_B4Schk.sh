#!/bin/bash
# _t5_B4Schk.sh --- ★★★★★★ B4S 判定：单根（只有场 1）会不会自己碎裂？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B4S
echo "NOW = $(date '+%F %T')"
printf '  引擎进程 = %s   末步 = %s   快照 = %s\n' \
  "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")" \
  "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)"
echo
echo '════ 是否发生了形核（判"单根"前提是否成立）════'
awk '/@ step/ && /模式/{n++} END{print "  形核事件数 = " n+0}' _w2_t5_short_$TAG.log 2>/dev/null
echo
echo '════ ★ 场 1 的 φ<0 瓣数随时间（物理量具）════'
$PY - <<'PYEOF'
import glob, numpy as np
from scipy import ndimage
S26 = ndimage.generate_binary_structure(3, 3)
TAG = 't5B4S'
fs = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not fs:
    print('  （无快照）'); raise SystemExit
print('  %-7s %-8s %-8s %-9s %-9s %s' % ('step', '胞数', '瓣数', '最大占比', 'L(nm)', 'W(nm) T(nm) 宽比'))
prev = None
for P in fs:
    st = int(P.split('snap_')[1].replace('.npz', ''))
    with np.load(P, allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    sel = (bf == 1) & (bv < 0)
    n = int(sel.sum())
    if n < 10:
        print('  %-7d （场 1 无相）' % st); continue
    idx = bi[sel]
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    lab, nc = ndimage.label(g, structure=S26)
    sz = np.bincount(lab.ravel())[1:]
    big = (lab == (int(np.argmax(sz)) + 1))
    P3 = np.argwhere(big).astype(float)
    c = P3 - P3.mean(0)
    w, v = np.linalg.eigh(c.T @ c)
    o = np.argsort(w)[::-1]
    L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * 62.5
    W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * 62.5
    T = float((c @ nh).max() - (c @ nh).min() + 1) * 62.5 if nh is not None else 0.0
    print('  %-7d %-8d **%-8d** %-9.0f%% %-9.0f %.0f %.0f **%.2f**'
          % (st, n, nc, 100.0 * sz.max() / max(sz.sum(), 1), L, W, T, L / max(W, 1e-9)))
print()
print('  ── 判据（**预先写死**）──')
print('  * **瓣数 1 → ≥2** ⇒ **演化方程本身会造成碎裂** ⇒ 范围缩到演化;')
print('  * **恒 = 1 且体积不缩** ⇒ **演化无辜** ⇒ 原因在**形核/播种路径**。')
PYEOF
