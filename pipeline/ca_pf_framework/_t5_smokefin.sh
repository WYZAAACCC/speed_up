#!/bin/bash
# _t5_smokefin.sh --- 冒烟测试终态 + 碎片化复核（写成脚本，避免 PowerShell 引号）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5FIX
echo '════ ① 判决行 ════'
grep -E '判决|nslab_n 1→|主判据' _w2_t5_short_$TAG.log 2>/dev/null | tail -3 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② 块表末行 ════'
$PY - <<'PYEOF'
import csv
rows = list(csv.DictReader(open('_exp/_bk_t5/dry_t5FIX/series.csv', newline='')))
b = [r for r in rows if (r.get('nblk_sig') or '').strip()]
r = b[-1] if b else rows[-1]
for k in ('step', 'nslab_n', 'nf3_col', 'nf2', 'nblk_sig', 'n_var_sig', 'blk_laths', 'Vt'):
    if k in r:
        v = r[k]
        if k == 'Vt':
            try: v = '%.4f µm³' % (float(v) * 1e18)
            except Exception: pass
        print('  %-12s %s' % (k, v))
PYEOF
echo
echo '════ ③ ★ 碎片化复核（新场首现几块？**修复前 = 2–5 块**）════'
$PY _t5_fragbirth.py $TAG 2>&1 | tail -7
echo
echo '════ ④ 对照：修复前 t5N276 的同一指标 ════'
echo '  事件 34 · 不同场 19 · **唯一性 0.56** · nslab_n 19 · 新场首现碎片中位 2–5'
