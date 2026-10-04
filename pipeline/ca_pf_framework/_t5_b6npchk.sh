#!/bin/bash
# _t5_b6npchk.sh --- ★★★★★★ `t5B6np`（无补丁 · --B 6）六条判据 vs A 臂（--B 3）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B6np
echo "NOW = $(date '+%F %T')"
printf '  进程 = %s ｜ 末步 = %s ｜ 快照 = %s ｜ 事件 = %s\n' \
  "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")" \
  "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)"
echo
echo '════ ★ 判据①：`n_var_sig`（块表）════'
$PY - <<'PYEOF'
import csv, os
for tag, lab in (('t5B6np', '--B 6 (修复)'), ('t5N276F', '--B 3 (对照)')):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        print('  %-16s （无数据）' % lab); continue
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    print('  ── %s：块表 %d 行 ──' % (lab, len(rows)))
    for r in rows[-4:]:
        print('     step %-6s nslab_n=%-4s **n_var_sig=%s** nblk_sig=%-4s nf2=%-6s blk_laths=%s'
              % (r['step'], r.get('nslab_n'), r.get('n_var_sig'), r.get('nblk_sig'),
                 r.get('nf2'), (r.get('blk_laths') or '')[:30]))
    ks = [int(r['n_var_sig']) for r in rows if (r.get('n_var_sig') or '').strip().isdigit()]
    if ks:
        print('     ⇒ **n_var_sig 末值 = %d**' % ks[-1])
PYEOF
echo
echo '════ ★ 判据②：`Δed` 带符号（A 臂 = −2.955e8，<0 占 100%）════'
grep -E 'Δed 带符号' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | cut -c1-200 | sed 's/^/  /'
echo '  ── 对照 A 臂 ──'
grep -A1 'F1 含母相' _w2_t5_short_t5N276F.log 2>/dev/null | tail -2 | cut -c1-190 | sed 's/^/  /'
echo '  （为空 ⇒ 诊断还没到输出步）'
echo
echo '════ ★ 判据③：Vt 轨迹（每 20 步；看是否下降）════'
grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -8 | cut -c1-115 | sed 's/^/  /'
echo
echo '════ ★ 判据④：逐场瓣数（物理量具 φ<0）—— A 臂孤立种子 1→22 ════'
$PY - <<'PYEOF' 2>/dev/null
import glob, numpy as np
from scipy import ndimage
S26 = ndimage.generate_binary_structure(3, 3)
for tag in ('t5B6np', 't5N276F'):
    fs = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if len(fs) < 2:
        print('  %-9s （快照不足）' % tag); continue
    print('  ── %s ──' % tag)
    for P in fs[-2:]:
        st = int(P.split('snap_')[1].replace('.npz', ''))
        with np.load(P, allow_pickle=False) as z:
            N = int(np.asarray(z['N']))
            bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
            bv = np.asarray(z['band_val']).ravel()
            bf = np.asarray(z['band_fld']).ravel()
        neg = bv < 0
        out = []
        for k in sorted(int(x) for x in np.unique(bf[neg]) if x != 0):
            sel = neg & (bf == k)
            n = int(sel.sum())
            if n < 30:
                continue
            idx = bi[sel]
            g = np.zeros((N, N, N), bool)
            g[idx // (N * N), (idx // N) % N, idx % N] = True
            lab, nc = ndimage.label(g, structure=S26)
            sz = np.bincount(lab.ravel())[1:]
            out.append((k, n, nc, 100.0 * sz.max() / max(sz.sum(), 1)))
        if out:
            print('     step %-6d 场数=%-3d **瓣数中位=%.0f 最大=%d** ｜ 最大分量占比中位=%.0f%%'
                  % (st, len(out), float(np.median([o[2] for o in out])),
                     max(o[2] for o in out), float(np.median([o[3] for o in out]))))
        else:
            print('     step %-6d （无场）' % st)
PYEOF
free -m | sed -n 2p | sed 's/^/  /'
