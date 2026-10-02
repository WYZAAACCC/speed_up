#!/bin/bash
# _t5_nuc_ev.sh --- 取出修复臂的**全部形核事件**（步号/模式/累计）
cd "$(dirname "$0")" || exit 1
echo '════ 修复臂 t5G3 的形核事件 ════'
grep -E 'athermal 形核 @ step|引擎形核 @ step' _w2_t5_short_t5G3.log 2>/dev/null \
  | cut -c1-150 | sed 's/^/  /'
echo
echo '════ 对照：旧臂 t5L62（后续形核全被拒）════'
grep -E 'athermal 形核 @ step|引擎形核 @ step' _w2_t5_short_t5L62.log 2>/dev/null \
  | cut -c1-150 | sed 's/^/  /'
grep -c '被引擎拒' _w2_t5_short_t5L62.log 2>/dev/null | sed 's/^/  被拒总数: /'
echo
echo '════ abA 的形核事件（前 6，作时间尺度对照）════'
grep -E '形核 @ step' _r445_abA.log 2>/dev/null | head -6 | cut -c1-140 | sed 's/^/  /'
echo
echo '════ 当前进度 ════'
grep -oE '\[ *[0-9]+\] Vt=[0-9.]+' _w2_t5_short_t5G3.log 2>/dev/null | tail -2 | sed 's/^/  /'
/root/miniconda3/envs/ml/bin/python -c "
import csv
r=list(csv.DictReader(open('_exp/_bk_t5/dry_t5G3/series.csv',encoding='utf-8',errors='replace')))
print('  series %d 行，末步 %s，nslab_n=%s，nf3=%s' % (len(r), r[-1]['step'], r[-1].get('nslab_n'), r[-1].get('nf3')))
" 2>/dev/null
