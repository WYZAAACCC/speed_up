#!/bin/bash
# _r132_chk.sh —— R132 选支对照的启动核对
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "现在：$(date '+%F %T')"
tail -2 _w2_r132_run.log 2>/dev/null
echo
grep -E '选支受控对照|受影响变体|正对照' _w2_r132_swapinv.log 2>/dev/null | head -4
grep -E '^     V[0-9]+ ' _w2_r132_swapinv.log 2>/dev/null | head -4
echo
grep -E '精确判据|播种后\*\*两块|多块：块心' _w2_r132_swapinv.log 2>/dev/null | head -4
grep -E 'n\*=\[' _w2_r132_swapinv.log 2>/dev/null | head -2
grep -E 'dt=' _w2_r132_swapinv.log 2>/dev/null | head -2
echo
echo "--- 进度 ---"
tail -2 _w2_r132_swapinv.log 2>/dev/null | cut -c1-125
echo
$PY - <<'PY'
import csv, os
for t in ('mb2fp10', 'swapinv'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-10s （无 series.csv）' % t); continue
    rs = list(csv.DictReader(open(p)))
    r0 = rs[0]
    print('  %-10s 行数=%-4d step0: nf2=%-6s nblk_sig=%-3s blk_laths=%-13s blk_nprof=%s'
          % (t, len(rs), r0.get('nf2'), r0.get('nblk_sig'),
             r0.get('blk_laths'), r0.get('blk_nprof')))
PY
