#!/bin/bash
# _r209_readdiag.sh —— 读 `_w2_r208_on.log` 里的三项量级明细（避免 PowerShell 吃掉引号）。
cd "$(dirname "$0")" || exit 1
echo "=== 三项量级明细 ==="
grep -E '三项量级|异变体|同变体|含母相|df_k' _w2_r208_on.log | tail -26
echo
echo "=== diag_terms.json 的 F2 段 ==="
/root/miniconda3/envs/ml/bin/python - <<'PY'
import json, os
p = '_exp/_bk_dt/dry_dtON/diag_terms.json'
d = json.load(open(p))
print('  记录 %d 条；note = %s' % (d['n_rec'], d['note'][:60]))
for i in (0, len(d['rec']) - 1):
    r = d['rec'][i]
    print('  --- rec[%d] step=%s vmap_split=%s ---' % (i, r['step'], r['vmap_split']))
    for cls in ('vv', 'f3', 'vb'):
        c = r.get(cls) or {}
        if 'med_ed' not in c:
            print('     %-4s n=%s（不足）' % (cls, c.get('n')))
            continue
        print('     %-4s n=%-7d med_df=%.3e med_ed=%.4e med_sk=%.4e '
              'med_ratio=%.5f p99=%.5f frac_ed0=%.3f'
              % (cls, c['n'], c['med_df'], c['med_ed'], c['med_sk'],
                 c['med_ratio'], c['p99_ratio'], c['frac_ed0']))
PY
