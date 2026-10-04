#!/bin/bash
# _t5_waitalign.sh --- ★★★★★★ 等 t5B6np 到 step ≥400，然后与 t5N276F **同步对齐**比较
#
# ## 为什么必须同步对齐（**本会话第九次口径提醒**）
# step 40 时两臂都是"瓣数 1、占比 100%"（场刚形成，碎裂未开始）⇒ **不可比**。
# `t5N276F` 从 step 160 起出现多块、step 400+ 明显 ⇒ 比较点必须在 **step ≥400**。
#
# ## 判据（**预先写死**）
#  在**同一 step** 上比较（物理量具 φ<0 的 26-连通分量）：
#   * `--B 6` 的**瓣数中位显著低于** `--B 3`（后者 step 400 已多块）且**占比更高**
#     ⇒ **变体数↑ ⇒ 溶解↓ 成立** ⇒ **设计级根因确认** ✓
#   * 两者相近 ⇒ **变体数不是关键** ⇒ 需回到其它候选
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TGT=${1:-400}; LIM=${2:-7200}; T=0
echo "  等 t5B6np 的末步 ≥ $TGT（最多 ${LIM} s）"
while [ "$T" -lt "$LIM" ]; do
  S=$(tail -1 _exp/_bk_t5/dry_t5B6np/series.csv 2>/dev/null | cut -d, -f1)
  S=${S:-0}
  [ "$S" -ge "$TGT" ] 2>/dev/null && { echo "  ★ t5B6np 末步 = $S"; break; }
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5B6np')
  [ "$P" -eq 0 ] && { echo "  ⚠ t5B6np 进程消失（末步 $S）"; break; }
  sleep 120; T=$((T + 120))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★★ 同步对齐比较（物理量具 φ<0 · 26-连通分量）════'
$PY - <<'PYEOF'
import glob, numpy as np, os
from scipy import ndimage
S26 = ndimage.generate_binary_structure(3, 3)
STEPS = [160, 240, 400, 600, 800]

def frag(tag, st):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag) if ('%05d' % st) in f]
    if not fs:
        return None
    with np.load(fs[0], allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
    neg = bv < 0
    nc, fr = [], []
    for k in sorted(int(x) for x in np.unique(bf[neg]) if x != 0):
        sel = neg & (bf == k)
        n = int(sel.sum())
        if n < 30:
            continue
        idx = bi[sel]
        g = np.zeros((N, N, N), bool)
        g[idx // (N * N), (idx // N) % N, idx % N] = True
        lab, c = ndimage.label(g, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        nc.append(c); fr.append(100.0 * sz.max() / max(sz.sum(), 1))
    if not nc:
        return None
    return dict(nf=len(nc), nc=float(np.median(nc)), ncmax=int(max(nc)),
                frac=float(np.median(fr)))

print('  %-7s | %-34s | %s' % ('step', '--B 6 (修复)', '--B 3 (对照)'))
for st in STEPS:
    a = frag('t5B6np', st); b = frag('t5N276F', st)
    fa = ('场=%-3d 瓣中位=%-5.1f 最大=%-3d 占比=%.0f%%' % (a['nf'], a['nc'], a['ncmax'], a['frac'])) if a else '（无快照/无场）'
    fb = ('场=%-3d 瓣中位=%-5.1f 最大=%-3d 占比=%.0f%%' % (b['nf'], b['nc'], b['ncmax'], b['frac'])) if b else '（无快照/无场）'
    print('  %-7d | %-34s | %s' % (st, fa, fb))
print()
print('  ── 判据（**预先写死**）──')
print('  * **同一 step 上**：`--B 6` 的**瓣数中位更低** 且 **占比更高**')
print('    ⇒ **变体数 3→6 ⇒ 溶解减轻** ⇒ **设计级根因确认** ✓')
print('  * 两者相近 ⇒ 变体数不是关键 ⇒ 需回到其它候选')
PYEOF
echo
echo '════ 块表（n_var_sig）与形核事件 ════'
$PY - <<'PYEOF'
import csv, os
for tag in ('t5B6np', 't5N276F'):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P): continue
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    if not rows: print('  %s （无块表行）' % tag); continue
    b = rows[-1]
    print('  %-9s step %-6s nslab_n=%-4s **n_var_sig=%s** nblk_sig=%-4s blk_laths=%s'
          % (tag, b['step'], b.get('nslab_n'), b.get('n_var_sig'), b.get('nblk_sig'),
             (b.get('blk_laths') or '')[:30]))
PYEOF
for m in fresh attach stack; do
  printf '  t5B6np %-7s = %s\n' "$m" "$(grep -cE "模式 \*\*$m\*\*" _w2_t5_short_t5B6np.log 2>/dev/null)"
done
$PY - <<'PYEOF'
import glob
for tag in ('t5B6np','t5N276F'):
    L='_w2_t5_short_%s.log'%tag
    try:
        s=open(L,errors='ignore').read()
    except Exception:
        continue
    print('  %-9s 带符号 Δed 行数 = %d' % (tag, s.count('Δed 带符号')))
PYEOF
grep -E 'Δed 带符号' _w2_t5_short_t5B6np.log 2>/dev/null | tail -3 | cut -c1-200 | sed 's/^/     /'
grep -E 'Δed 带符号' _w2_t5_short_t5N276F.log 2>/dev/null | tail -2 | cut -c1-200 | sed 's/^/     /'
