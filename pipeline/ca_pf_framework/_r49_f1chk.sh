#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
CSV=_exp/_bk_mb/dry_mb1s62/series.csv
echo '=== F1/F3 拆分列是否真有值（新列必须非空）'
/root/miniconda3/envs/ml/bin/python - "$CSV" <<'PY'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
cols = ['step', 'n_tip', 'n_side', 'n_wide', 'f1_tip', 'f1_side', 'f1_wide',
        'v_tip_nabs', 'v_tip_f1', 'v_side_nabs', 'v_side_f1', 'v_wide_nabs', 'v_wide_f1']
print('  ' + ' '.join('%-10s' % c for c in cols))
for r in rows:
    print('  ' + ' '.join('%-10s' % (r.get(c, '(缺)') or '(空)') for c in cols))
PY
