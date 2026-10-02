#!/bin/bash
# _t5_blk_callsite.sh --- `_blk_cols` 的调用点与门控（决定 abA 为什么空）
cd "$(dirname "$0")" || exit 1
echo '════ ① 调用点 ════'
grep -n '_blk_cols(' _bk_exp.py | cut -c1-130 | sed 's/^/  /'
echo
echo '════ ② 调用点前后 30 行（看门控）════'
LN=$(grep -n '_blk_cols(' _bk_exp.py | grep -v 'def ' | head -1 | cut -d: -f1)
echo "  （调用行 = $LN）"
sed -n "$((LN-26)),$((LN+6))p" _bk_exp.py | cat -n | cut -c1-126 | sed 's/^/    /'
echo
echo '════ ③ 反查：非空 vs 全空，配置差在哪（pair_every / every / snap_every）════'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import csv, glob, json, os
from collections import Counter
def cfg(d):
    p = os.path.join(d, 'meta.json')
    try:
        m = json.load(open(p, encoding='utf-8'))
        a = m.get('exp_args', m)
        return {k: a.get(k) for k in ('pair_every', 'every', 'snap_every', 'N')}
    except Exception:
        return None
good, bad = [], []
for d in sorted(glob.glob('_exp/*/dry_*')):
    f = os.path.join(d, 'series.csv')
    if not os.path.exists(f):
        continue
    try:
        rows = list(csv.DictReader(open(f, encoding='utf-8', errors='replace')))
    except Exception:
        continue
    if not rows or 'nblk_sig' not in rows[0]:
        continue
    nz = set((r.get('nblk_sig') or '').strip() for r in rows)
    c = cfg(d)
    if c is None:
        continue
    (good if [v for v in nz if v not in ('', '0')] else bad).append(c)
def summ(name, lst):
    print('  ── %s（%d 个）──' % (name, len(lst)))
    for k in ('pair_every', 'every', 'snap_every'):
        c = Counter(str(x.get(k)) for x in lst)
        print('     %-12s %s' % (k, dict(c.most_common(6))))
summ('**非空**（量具出了数）', good)
summ('**全空**', bad)
PYEOF
