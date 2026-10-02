#!/bin/bash
# _r581_big4b.sh --- 那四条 N=160 大仿真的时间戳 + 第四条（p2_b5ps）的终态
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ 四条大仿真的时间戳（series.csv 的最后修改时间）════'
for t in p2_b3 p2_b5 p2_b5ov p2_b5ps p2_m12ov; do
  d="_exp/_bk_p2/dry_$t"
  [ -d "$d" ] || { echo "  $t（无目录）"; continue
  }
  printf '  %-9s 末次修改=%s  行数=%-5s 快照=%s 个\n' \
    "$t" "$(date -r "$d/series.csv" '+%m-%d %H:%M' 2>/dev/null)" \
    "$(wc -l < "$d/series.csv" 2>/dev/null)" \
    "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
done
echo
echo '════ 第四条 p2_b5ps 的终态（头 + 每 200 步 + 末行）════'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import csv
p = '_exp/_bk_p2/dry_p2_b5ps/series.csv'
rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
k = list(rows[0].keys())[0]
keys = ['Vt','nslab_n','nslab_n1','nf3','nf2','n_var_sig','n_habit','r_selfac','box_touch']
have = [c for c in keys if c in rows[0]]
print('  %-6s %s' % ('step', ' '.join('%-11s' % c[:11] for c in have)))
sel = [r for r in rows if r[k] == '0'] + [r for r in rows
        if r[k].isdigit() and int(r[k]) % 200 == 0] + [rows[-1]]
seen = set()
for r in sel:
    if r[k] in seen:
        continue
    seen.add(r[k])
    vals = []
    for c in have:
        v = (r.get(c, '') or '').strip()
        try:
            vals.append('%-11.6g' % float(v))
        except Exception:
            vals.append('%-11s' % v[:11])
    print('  %-6s %s' % (r[k], ' '.join(vals)))
PYEOF
echo
echo '════ 全库 N=160 的算例汇总 ════'
$PY - <<'PYEOF'
import csv, glob, json, os
recs = []
for d in glob.glob('_exp/**/dry_*', recursive=True):
    mp, sp = os.path.join(d, 'meta.json'), os.path.join(d, 'series.csv')
    if not (os.path.exists(mp) and os.path.exists(sp)):
        continue
    try:
        m = json.load(open(mp, encoding='utf-8', errors='replace'))
    except Exception:
        continue
    if int(m.get('N', 0)) != 160:
        continue
    try:
        rows = list(csv.DictReader(open(sp, encoding='utf-8', errors='replace')))
    except Exception:
        continue
    if not rows:
        continue
    k = list(rows[0].keys())[0]
    recs.append((os.path.basename(d)[4:], m.get('steps'), rows[-1][k], len(rows),
                 os.path.getmtime(sp), d))
recs.sort(key=lambda r: -float(r[2] or 0))
import time
print('  %-24s %-8s %-8s %-6s %s' % ('臂', '设计步数', '末步', '行数', '末次修改'))
for tag, want, last, nrow, mt, d in recs:
    print('  %-24s %-8s %-8s %-6d %s' % (tag[:24], want, last, nrow,
                                          time.strftime('%m-%d %H:%M', time.localtime(mt))))
PYEOF
